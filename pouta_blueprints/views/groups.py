from flask.ext.restful import marshal_with
from flask import abort, g
from flask import Blueprint as FlaskBlueprint
import logging
from pouta_blueprints.models import db, Group, User
from pouta_blueprints.forms import GroupForm
from pouta_blueprints.server import restful
from pouta_blueprints.views.commons import auth, group_fields
from pouta_blueprints.utils import requires_admin, requires_group_owner_or_admin

groups = FlaskBlueprint('groups', __name__)


class GroupList(restful.Resource):
    @auth.login_required
    @requires_group_owner_or_admin
    @marshal_with(group_fields)
    def get(self):

        user = g.user
        results = []
        if not user.is_admin:  # group owner
            groups = user.owned_groups
        else:
            query = Group.query
            groups = query.all()
        for group in groups:
            group.config = {"name": group.name, "join_code": group.join_code, "description": group.description}
            results.append(group)
        return results

    @auth.login_required
    @requires_group_owner_or_admin
    def post(self):
        form = GroupForm()
        if not form.validate_on_submit():
            logging.warn("validation error on creating group")
            return form.errors, 422
        group = Group(form.name.data)
        group.description = form.description.data
        user_config = form.user_config.data
        try:
            group = group_users_add(group, user_config)
        except:
            abort(422)
        group.user_config = user_config
        db.session.add(group)
        db.session.commit()


class GroupView(restful.Resource):
    @auth.login_required
    @requires_admin
    @marshal_with(group_fields)
    def get(self, group_id):

        query = Group.query.filter_by(id=group_id)
        group = query.first()
        if not group:
            abort(404)
        return group

    @auth.login_required
    @requires_group_owner_or_admin
    def put(self, group_id):
        form = GroupForm()
        if not form.validate_on_submit():
            logging.warn("validation error on creating group")
            return form.errors, 422
        user = g.user
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            abort(404)
        if not user.is_admin and group not in user.owned_groups:
            abort(403)
        if group.name != form.name.data:
            group.name = form.name.data
            group.join_code = form.name.data  # hybrid property
        group.description = form.description.data

        user_config = form.user_config.data
        try:
            group = group_users_add(group, user_config)
        except KeyError:
            abort(422)
        group.user_config = user_config
        db.session.add(group)
        db.session.commit()

    @auth.login_required
    @requires_admin
    def delete(self, group_id):
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            logging.warn("trying to delete non-existing group")
            abort(404)
        db.session.delete(group)
        db.session.commit()


def group_users_add(group, user_config):
    # Add Banned users
    banned_users_final = []
    if 'banned_users' in user_config:
        banned_users = user_config['banned_users']
        for banned_user_item in banned_users:
            banned_user_id = banned_user_item['id']
            banned_user = User.query.filter_by(id=banned_user_id).first()
            if not banned_user:
                logging.warn("user %s does not exist", banned_user_id)
                continue
            banned_users_final.append(banned_user)
    group.banned_users = banned_users_final  # setting a new list adds and also removes relationships
    # Now add users
    users_final = []
    if 'users' in user_config:
        users = user_config['users']
        for user_item in users:
            user_id = user_item['id']
            if user_item in banned_users:  # Check if the user is not banned
                logging.warn("user %s is blocked, cannot add", user_id)
                continue
            user = User.query.filter_by(id=user_id).first()
            if not user:
                logging.warn("trying to add non-existent user %s", user_id)
                continue
            users_final.append(user)
    group.users = users_final
    # Group owners
    owners_final = []
    owners_final.append(g.user)  # Always add the user creating/modifying the group
    if 'owners' in user_config:
        owners = user_config['owners']
        for owner_item in owners:
            owner_id = owner_item['id']
            if owner_item in banned_users:  # Check if the user is not banned
                logging.warn("user %s is blocked, cannot add as owner", owner_id)
                continue
            owner = User.query.filter_by(id=owner_id).first()
            if not owner:
                logging.warn("trying to add non-existent owner %s", owner_id)
                continue
            owners_final.append(owner)
    group.owners = owners_final
    return group


class GroupJoin(restful.Resource):

    @auth.login_required
    def put(self, join_code):
        if not join_code:
            return {"error": "no join code given"}, 422

        user = g.user
        group = Group.query.filter_by(join_code=join_code).first()
        if not group:
            return {"error": "The code entered is invalid. Please recheck and try again"}, 422
        if user in group.banned_users:
            logging.warn("user banned from the group with code %s", join_code)
            return {"error": "You are banned from this group, please contact the concerned person"}, 403
        if user in group.users:
            logging.warn("user %s already exists in group", user.id)
            return {"error": "User already in the group"}, 422
        group.users.append(user)
        user_config = group.user_config
        if 'users' not in user_config:
            user_config['users'] = []
        user_config['users'].append({'id': user.id})
        group.user_config = user_config
        db.session.add(group)
        db.session.commit()
