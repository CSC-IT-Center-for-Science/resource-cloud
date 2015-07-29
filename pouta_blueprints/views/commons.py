from flask.ext.restful import fields
from flask.ext.httpauth import HTTPBasicAuth
from flask import g, render_template
import logging
from pouta_blueprints.models import db, ActivationToken, SystemToken, User
from pouta_blueprints.server import app
from pouta_blueprints.tasks import send_mails

user_fields = {
    'id': fields.String,
    'email': fields.String,
    'credits_quota': fields.Float,
    'credits_spent': fields.Float,
    'is_active': fields.Boolean,
    'is_admin': fields.Boolean,
    'is_deleted': fields.Boolean,
}

auth = HTTPBasicAuth()
auth.authenticate_header = lambda: "Authentication Required"


@auth.verify_password
def verify_password(userid_or_token, password):
    # first check for system tokens
    if SystemToken.verify(userid_or_token):
        g.user = User('system', is_admin=True)
        return True

    g.user = User.verify_auth_token(userid_or_token, app.config['SECRET_KEY'])
    if not g.user:
        g.user = User.query.filter_by(email=userid_or_token).first()
        if not g.user or not g.user.check_password(password):
            return False
    return True


def create_worker():
    return create_user('worker@pouta_blueprints', app.config['SECRET_KEY'], is_admin=True)


def create_user(email, password, is_admin=False):
    if User.query.filter_by(email=email).first():
        raise RuntimeError("user %s already exists" % email)
    user = User(email, password, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()
    return user


def add_user(email, password=None, is_admin=False):
    user = User.query.filter_by(email=email).first()
    if user:
        logging.warn("user %s already exists" % email)
        return None

    user = User(email, password, is_admin)
    db.session.add(user)
    db.session.commit()

    token = ActivationToken(user)
    db.session.add(token)
    db.session.commit()

    if not app.dynamic_config['SKIP_TASK_QUEUE'] and not app.dynamic_config['MAIL_SUPPRESS_SEND']:
        send_mails.delay([(user.email, token.token)])
    else:
        logging.warn(
            "email sending suppressed in config: SKIP_TASK_QUEUE:%s MAIL_SUPPRESS_SEND:%s" %
            (app.dynamic_config['SKIP_TASK_QUEUE'], app.dynamic_config['MAIL_SUPPRESS_SEND'])
        )
        activation_url = '%s/#/activate/%s' % (app.config['BASE_URL'], token.token)
        content = render_template('invitation.txt', activation_link=activation_url)
        logging.warn(content)

    return user
