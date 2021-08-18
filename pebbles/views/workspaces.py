import datetime
import logging
import re

import flask_restful as restful
from dateutil.relativedelta import relativedelta
from flask import Blueprint as FlaskBlueprint
from flask import abort, g
from flask_restful import marshal, marshal_with, reqparse, fields, inputs
from sqlalchemy.orm import subqueryload

from pebbles import rules
from pebbles.app import app
from pebbles.forms import WorkspaceForm
from pebbles.models import db, Workspace, User, WorkspaceUserAssociation, Environment, Instance
from pebbles.utils import requires_admin, requires_workspace_owner_or_admin
from pebbles.views.commons import auth, user_fields

workspaces = FlaskBlueprint('workspaces', __name__)
join_workspace = FlaskBlueprint('join_workspace', __name__)

workspace_fields_admin = {
    'id': fields.String,
    'pseudonym': fields.String,
    'name': fields.String,
    'join_code': fields.String,
    'description': fields.Raw,
    'create_ts': fields.Integer,
    'expiry_ts': fields.Integer,
    'owner_ext_id': fields.String,
    'environment_quota': fields.Integer,
}

workspace_fields_owner = {
    'id': fields.String,
    'name': fields.String,
    'join_code': fields.String,
    'description': fields.Raw,
    'create_ts': fields.Integer,
    'expiry_ts': fields.Integer,
    'owner_ext_id': fields.String,
    'environment_quota': fields.Integer,
}

workspace_fields_manager = {
    'id': fields.String,
    'name': fields.String,
    'join_code': fields.String,
    'description': fields.Raw,
    'create_ts': fields.Integer,
    'expiry_ts': fields.Integer,
    'environment_quota': fields.Integer,
}

workspace_fields_user = {
    'id': fields.String,
    'name': fields.String,
    'description': fields.Raw,
}

total_users_fields = {
    'owner': fields.Nested(user_fields),
    'manager_users': fields.List(fields.Nested(user_fields)),
    'normal_users': fields.List(fields.Nested(user_fields)),
    'banned_users': fields.List(fields.Nested(user_fields))
}


def marshal_based_on_role(user, workspace):
    if user.is_admin:
        return restful.marshal(workspace, workspace_fields_admin)
    elif rules.is_user_owner_of_workspace(user, workspace):
        return restful.marshal(workspace, workspace_fields_owner)
    elif rules.is_user_manager_in_workspace(user, workspace):
        return restful.marshal(workspace, workspace_fields_manager)
    else:
        return restful.marshal(workspace, workspace_fields_user)


class WorkspaceList(restful.Resource):
    @auth.login_required
    def get(self):
        user = g.user
        workspace_user_query = WorkspaceUserAssociation.query
        results = []
        if not user.is_admin:
            workspace_mappings = workspace_user_query.filter_by(user_id=user.id, is_banned=False).all()
            workspaces = [workspace_obj.workspace for workspace_obj in workspace_mappings]
        else:
            query = Workspace.query
            workspaces = query.all()

        workspaces = sorted(workspaces, key=lambda ws: ws.name)
        for workspace in workspaces:
            if not user.is_admin and workspace.name.startswith('System.'):
                continue

            if not workspace.status == Workspace.STATUS_ACTIVE:
                continue

            owner = next((woa.user for woa in workspace.user_associations if woa.is_owner), None)
            workspace.owner_ext_id = owner.ext_id if owner else None

            # marshal results based on role
            results.append(marshal_based_on_role(user, workspace))

        return results

    @auth.login_required
    @requires_workspace_owner_or_admin
    def post(self):
        user = g.user
        user_owned_workspaces = WorkspaceUserAssociation.query.filter_by(user_id=user.id, is_owner=True)
        num_user_owned_workspaces = [
            w.workspace.status == Workspace.STATUS_ACTIVE for w in user_owned_workspaces].count(True)
        if not user.is_admin and num_user_owned_workspaces >= user.workspace_quota:
            logging.warning("Maximum workspace quota %s is reached" % user.workspace_quota)
            return dict(
                message="You reached maximum number of workspaces that can be created."
                        " If you wish create more workspaces please contact the support"
            ), 422
        form = WorkspaceForm()
        if not form.validate_on_submit():
            logging.warning("validation error on creating workspace")
            return form.errors, 422
        workspace = Workspace(form.name.data)
        workspace.description = form.description.data

        workspace_owner_obj = WorkspaceUserAssociation(user=user, workspace=workspace, is_manager=True, is_owner=True)
        workspace.user_associations.append(workspace_owner_obj)

        workspace.create_ts = datetime.datetime.utcnow().timestamp()
        workspace.expiry_ts = (datetime.datetime.utcnow() + relativedelta(months=+6)).timestamp()

        # If users can later select the clusters, then this should be taken from the form and verified
        workspace.cluster = app.config['DEFAULT_CLUSTER']

        db.session.add(workspace)
        db.session.commit()

        # marshal based on role
        return marshal_based_on_role(user, workspace)


class WorkspaceView(restful.Resource):
    @auth.login_required
    @requires_admin
    @marshal_with(workspace_fields_admin)
    def get(self, workspace_id):

        query = Workspace.query.filter_by(id=workspace_id)
        workspace = query.first()

        if not workspace:
            abort(404)
        if workspace.status == Workspace.STATUS_DELETED:
            abort(404)

        return workspace

    @auth.login_required
    @requires_workspace_owner_or_admin
    def put(self, workspace_id):
        form = WorkspaceForm()
        if not form.validate_on_submit():
            logging.warning("validation error on creating workspace")
            return form.errors, 422
        user = g.user
        workspace = Workspace.query.filter_by(id=workspace_id).first()
        if not workspace:
            abort(404)
        if not workspace.status == Workspace.STATUS_ACTIVE:
            abort(422)
        workspace_owner_obj = WorkspaceUserAssociation.query.filter_by(workspace_id=workspace.id, is_owner=True).first()
        owner = workspace_owner_obj.user
        if not (user.is_admin or user.id == owner.id):
            abort(403)
        if workspace.name != form.name.data:
            workspace.name = form.name.data
            workspace.join_code = form.name.data  # hybrid property
        workspace.description = form.description.data

        user_config = form.user_config.data
        try:
            workspace = workspace_users_add(workspace, user_config, owner, workspace_owner_obj)
        except KeyError:
            abort(422)
        except RuntimeError as e:
            return {"error": "{}".format(e)}, 422

        db.session.add(workspace)
        db.session.commit()

        # marshal based on role
        return marshal_based_on_role(user, workspace)

    @auth.login_required
    def patch(self, workspace_id):
        user = g.user
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str)
        new_status = parser.parse_args().get('status')

        return self.handle_status_change(user, workspace_id, new_status)

    @auth.login_required
    def delete(self, workspace_id):
        user = g.user
        return self.handle_status_change(user, workspace_id, Workspace.STATUS_DELETED)

    def handle_status_change(self, user, workspace_id, new_status):
        workspace = Workspace.query.filter_by(id=workspace_id).first()

        if not workspace:
            abort(404)
        # allow only predefined set
        if new_status not in Workspace.VALID_STATUSES:
            abort(403)
        # reactivation is not supported
        if new_status == Workspace.STATUS_ACTIVE:
            abort(403)
        # resurrection is not allowed
        if workspace.status == Workspace.STATUS_DELETED:
            abort(403)
        # System. can't be changed
        if workspace.name.startswith('System.'):
            logging.warning('Cannot change the status of System workspace')
            return {'error': 'Cannot change the status of System workspace'}, 422
        # you have to be an admin or the owner
        if not (user.is_admin or rules.is_user_owner_of_workspace(user, workspace)):
            abort(403)

        # archive
        if new_status == Workspace.STATUS_ARCHIVED:
            logging.info('Archiving workspace %s "%s"', workspace.id, workspace.name)
            workspace.status = Workspace.STATUS_ARCHIVED
            environments = workspace.environments.all()
            for environment in environments:
                environment.status = Environment.STATUS_DELETED
            db.session.commit()

        # delete
        if new_status == Workspace.STATUS_DELETED:
            logging.info('Deleting workspace %s "%s"', workspace.id, workspace.name)
            workspace.status = Workspace.STATUS_DELETED
            environments = workspace.environments.all()
            for environment in environments:
                environment.status = Environment.STATUS_DELETED
                for instance in environment.instances:
                    if instance.state in (Instance.STATE_DELETING, Instance.STATE_DELETED):
                        continue
                    logging.info('Setting instance %s to be deleted', instance.name)
                    instance.to_be_deleted = True
                    instance.state = Instance.STATE_DELETING
                    instance.deprovisioned_at = datetime.datetime.utcnow()
            db.session.commit()

        # marshal based on role
        return marshal_based_on_role(user, workspace)


def workspace_users_add(workspace, user_config, owner, workspace_owner_obj):
    """Validate and add the managers, banned users and normal users in a workspace"""
    # Generate a 'set' of Workspace Managers
    managers_list = []
    managers_list.append(owner)  # Owner is always a manager
    managers_list.append(g.user)  # always add the user creating/modifying the workspace
    # add new workspace owner
    if 'owner' in user_config:
        new_owner = user_config['owner']
        for new_owner_item in new_owner:
            new_owner_id = new_owner_item['id']
            new_owner = User.query.filter_by(id=new_owner_id).first()
            if new_owner != owner:
                workspace_owner_obj.user = new_owner
                workspace.user_associations.append(workspace_owner_obj)
                managers_list.append(new_owner)

    if 'managers' in user_config:
        managers = user_config['managers']
        for manager_item in managers:
            manager_id = manager_item['id']
            managers_list.append(manager_id)
    managers_set = set(managers_list)  # use this set to check if a user was appointed as a manager
    # Add Banned users
    banned_users_final = []
    if 'banned_users' in user_config:
        banned_users = user_config['banned_users']
        for banned_user_item in banned_users:
            banned_user_id = banned_user_item['id']
            banned_user = User.query.filter_by(id=banned_user_id).first()
            if not banned_user:
                logging.warning("user %s does not exist", banned_user_id)
                raise RuntimeError("User to be banned, does not exist")
            if banned_user_id in managers_set:
                logging.warning("user %s is a manager, cannot ban" % banned_user_id)
                raise RuntimeError("User is a manager, demote to normal status first")
            banned_users_final.append(banned_user)
    workspace.banned_users = banned_users_final  # setting a new list adds and also removes relationships
    # add the users
    users_final = []
    if workspace.user_associations:
        for workspace_user_obj in workspace.user_associations:  # Association object
            if workspace_user_obj.user in banned_users_final:
                logging.warning("user %s is banned, cannot add", workspace_user_obj.user.id)
                continue
            if workspace_user_obj.user.id in managers_set:  # if user is a manager
                workspace_user_obj.is_manager = True
            elif not workspace_user_obj.is_owner:  # if the user is not an owner then keep all users to non manager status
                workspace_user_obj.manager = False
            users_final.append(workspace_user_obj)
    workspace.user_associations = users_final

    return workspace


class JoinWorkspace(restful.Resource):
    @auth.login_required
    def put(self, join_code):
        user = g.user
        workspace = Workspace.query.filter_by(join_code=join_code).first()
        if not workspace:
            logging.warning("invalid workspace join code %s", join_code)
            return {"error": "The code entered is invalid. Please recheck and try again"}, 422

        existing_relation = next(filter(lambda wua: wua.user_id == user.id, workspace.user_associations), None)
        if existing_relation and existing_relation.is_banned:
            logging.warning("banned user %s tried to join workspace %s with code %s",
                            user.ext_id, workspace.name, join_code)
            return {"error": "You are banned from this workspace, please contact the concerned person"}, 403
        if existing_relation:
            logging.warning("user %s already exists in workspace", user.id)
            return {"error": "User already exists in the workspace"}, 422

        workspace_user_obj = WorkspaceUserAssociation(user=user, workspace=workspace)
        workspace.user_associations.append(workspace_user_obj)
        db.session.add(workspace)
        db.session.commit()

        # marshal based on role
        return marshal_based_on_role(user, workspace)


class WorkspaceExit(restful.Resource):
    @auth.login_required
    def put(self, workspace_id):
        user = g.user
        workspace = Workspace.query.filter_by(id=workspace_id).first()
        if not workspace:
            logging.warning("no workspace with id %s", workspace_id)
            abort(404)
        if re.match('^System.+', workspace.name):  # Do not allow exiting system level workspaces
            abort(403)

        workspace_user_filtered_query = WorkspaceUserAssociation.query.filter_by(
            workspace_id=workspace.id,
            user_id=user.id
        )
        if rules.is_user_owner_of_workspace(user, workspace):
            logging.warning("cannot exit the owned workspace %s", workspace_id)
            return {"error": "Cannot exit the workspace which is owned by you"}, 422
        user_in_workspace = workspace_user_filtered_query.first()
        if not user_in_workspace:
            logging.warning("user %s is not a part of the workspace", user.id)
            abort(403)
        workspace.user_associations.remove(user_in_workspace)
        db.session.add(workspace)
        db.session.commit()


class WorkspaceUsersList(restful.Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('members_count', type=inputs.boolean, default=False, location='args')

    @auth.login_required
    @requires_workspace_owner_or_admin
    def get(self, workspace_id):
        args = self.get_parser.parse_args()
        user = g.user
        workspace = Workspace.query.filter_by(id=workspace_id).first()
        if not workspace:
            logging.warning('workspace %s does not exist', workspace_id)
            abort(404)

        if not (user.is_admin or rules.is_user_owner_of_workspace(user, workspace)):
            logging.warning('Workspace %s not owned, cannot see users', workspace_id)
            abort(403)

        user_associations = WorkspaceUserAssociation.query.filter_by(workspace_id=workspace_id).options(
            subqueryload(WorkspaceUserAssociation.user)
        ).all()

        owners = [wua.user for wua in user_associations if wua.is_owner]
        if len(owners) == 1:
            owner_user = owners[0]
        else:
            owner_user = None
            logging.warning('number of owners for workspace %s is not exactly 1', workspace_id)

        banned_users = [wua.user for wua in user_associations if wua.is_banned]
        normal_users = [wua.user for wua in user_associations if not (wua.is_owner or wua.is_manager)]
        manager_users = [wua.user for wua in user_associations if wua.is_manager]
        total_users = {
            'owner': owner_user,
            'manager_users': manager_users,
            'normal_users': normal_users,
            'banned_users': banned_users
        }
        if args is not None and 'members_count' in args and args.get('members_count'):
            # count the list of members. Exclude owner as he is counted as a manager
            total_users_count = sum([len(total_users[key]) for key in total_users.keys() if key != 'owner'])
            return total_users_count
        return marshal(total_users, total_users_fields)


class WorkspaceClearUsers(restful.Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('workspace_id', type=str)

    @auth.login_required
    @requires_workspace_owner_or_admin
    def post(self, workspace_id):

        user = g.user
        workspace = Workspace.query.filter_by(id=workspace_id).first()
        workspace_user_query = WorkspaceUserAssociation.query

        if not workspace:
            logging.warning('Workspace %s does not exist', workspace_id)
            return {"error": "The workspace does not exist"}, 404

        if workspace.name.startswith('System.'):
            logging.warning("cannot clear a System workspace")
            return {"error": "Cannot clear a System workspace"}, 422

        if user.is_admin or rules.is_user_owner_of_workspace(user, workspace):
            workspace_user_query.filter_by(workspace_id=workspace_id, is_owner=False, is_manager=False).delete()
            db.session.commit()
        else:
            logging.warning('Workspace %s not owned, cannot clear users', workspace_id)
            return {"error": "Only the workspace owner can clear users"}, 403
