import logging
import re
from functools import wraps

from flask import g, render_template, abort, current_app
from flask_httpauth import HTTPBasicAuth
from flask_restful import fields

from pebbles.models import db, ActivationToken, User, Workspace, WorkspaceUserAssociation
from pebbles.utils import load_cluster_config, find_driver_class

user_fields = {
    'id': fields.String,
    'eppn': fields.String,
    'email_id': fields.String,
    'pseudonym': fields.String,
    'workspace_quota': fields.Integer,
    'is_active': fields.Boolean,
    'is_admin': fields.Boolean,
    'is_workspace_owner': fields.Boolean,
    'is_workspace_manager': fields.Boolean,
    'is_deleted': fields.Boolean,
    'is_blocked': fields.Boolean,
    'expiry_date': fields.DateTime,
}

# TODO: remove when AngularJS based old UI has been phased out
admin_icons = ["Dashboard", "Users", "Workspaces", "Environments", "Configure", "Statistics", "Account"]
workspace_owner_icons = ["Dashboard", "", "Workspaces", "Environments", "", "", "Account"]
workspace_manager_icons = ["Dashboard", "", "", "Environments", "", "", "Account"]
user_icons = ["Dashboard", "", "", "", "", "", "Account"]

auth = HTTPBasicAuth()
auth.authenticate_header = lambda: "Authentication Required"


@auth.verify_password
def verify_password(userid_or_token, password):
    g.user = User.verify_auth_token(userid_or_token, current_app.config['SECRET_KEY'])
    if not g.user:
        g.user = User.query.filter_by(eppn=userid_or_token).first()
        if not g.user:
            return False
        if not g.user.check_password(password):
            return False
    return True


def create_worker():
    return create_user('worker@pebbles', current_app.config['SECRET_KEY'], is_admin=True, email_id=None)


def create_user(eppn, password, is_admin=False, email_id=None):
    if User.query.filter_by(eppn=eppn).first():
        logging.info("user %s already exists" % eppn)
        return None

    user = User(eppn, password, is_admin=is_admin, email_id=email_id)
    if not is_admin:
        add_user_to_default_workspace(user)
    db.session.add(user)
    db.session.commit()
    return user


def get_clusters():
    if 'TEST_MODE' not in current_app.config:
        cluster_config = load_cluster_config(load_passwords=False)
    else:
        # rig unit tests to use dummy data
        cluster_config = dict(clusters=[
            dict(name='dummy_cluster_1', driver='KubernetesLocalDriver'),
            dict(name='dummy_cluster_2', driver='KubernetesLocalDriver'),
        ])

    cluster_data = []
    for cluster in cluster_config['clusters']:
        driver_class = find_driver_class(cluster.get('driver'))
        if not driver_class:
            logging.warning('No class for driver %s found', cluster.get('driver'))
            continue
        driver_config = driver_class.get_configuration()
        logging.debug('adding cluster %s to cluster_data', cluster['name'])
        cluster_data.append(dict(
            name=cluster['name'],
            conf=driver_config,
            schema=driver_config['schema'],
            model=driver_config['model'],
            form=driver_config['form'],
        ))

    return cluster_data


def update_email(eppn, email_id=None):
    user = User.query.filter_by(eppn=eppn).first()
    if email_id:
        user.email_id = email_id
    db.session.add(user)
    db.session.commit()
    return user


# both eppn and email are the same
def invite_user(eppn=None, password=None, is_admin=False, expiry_date=None):
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(email_regex, eppn):
        raise RuntimeError("Incorrect email")
    user = User.query.filter_by(eppn=eppn).first()
    if user:
        logging.warning("user %s already exists" % user.eppn)
        return None

    user = User(eppn=eppn, password=password, is_admin=is_admin, email_id=eppn, expiry_date=expiry_date)
    db.session.add(user)
    db.session.commit()

    token = ActivationToken(user)
    db.session.add(token)
    db.session.commit()

    if not current_app.config['SKIP_TASK_QUEUE'] and not current_app.config['MAIL_SUPPRESS_SEND']:
        logging.warning('email sending not implemented')
    else:
        logging.warning(
            "email sending suppressed in config: SKIP_TASK_QUEUE:%s MAIL_SUPPRESS_SEND:%s" %
            (current_app.config['SKIP_TASK_QUEUE'], current_app.config['MAIL_SUPPRESS_SEND'])
        )
        activation_url = '%s/#/activate/%s' % (current_app.config['BASE_URL'], token.token)
        content = render_template('invitation.txt', activation_link=activation_url)
        logging.warning(content)

    return user


def create_system_workspaces(admin):
    system_default_workspace = Workspace('System.default')
    workspace_admin_obj = WorkspaceUserAssociation(workspace=system_default_workspace, user=admin, owner=True)
    system_default_workspace.users.append(workspace_admin_obj)
    db.session.add(system_default_workspace)
    db.session.commit()


def add_user_to_default_workspace(user):
    system_default_workspace = Workspace.query.filter_by(name='System.default').first()
    workspace_user_obj = WorkspaceUserAssociation(workspace=system_default_workspace, user=user)
    system_default_workspace.users.append(workspace_user_obj)
    db.session.add(system_default_workspace)
    db.session.commit()


def requires_workspace_manager_or_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user.is_admin and not g.user.is_workspace_owner and not is_workspace_manager(g.user):
            abort(403)
        return f(*args, **kwargs)

    return decorated


def is_workspace_manager(user, workspace=None):
    if workspace:
        match = WorkspaceUserAssociation.query.filter_by(
            user_id=user.id,
            workspace_id=workspace.id,
            manager=True
        ).first()
    else:
        match = WorkspaceUserAssociation.query.filter_by(user_id=user.id, manager=True).first()
    if match:
        return True
    return False


def match_cluster(cluster_name):
    clusters = get_clusters()
    if not clusters:
        logging.warning('No clusters found')
    for cluster in clusters:
        if cluster["name"] == cluster_name:
            return cluster
