import datetime
import json
import logging

import flask_restful as restful
from flask import Blueprint as FlaskBlueprint
from flask import abort, g, current_app
from flask_restful import marshal, marshal_with, fields, reqparse

from pebbles import rules, utils
from pebbles.forms import InstanceForm
from pebbles.models import db, Environment, Instance, InstanceLog, User
from pebbles.rules import apply_rules_instances
from pebbles.utils import requires_admin, memoize
from pebbles.views.commons import auth, is_workspace_manager

instances = FlaskBlueprint('instances', __name__)

USER_INSTANCE_LIMIT = 5

instance_fields = {
    'id': fields.String,
    'name': fields.String,
    'created_at': fields.DateTime(dt_format='iso8601'),
    'provisioned_at': fields.DateTime(dt_format='iso8601'),
    'deprovisioned_at': fields.DateTime(dt_format='iso8601'),
    'lifetime_left': fields.Integer,
    'maximum_lifetime': fields.Integer,
    'state': fields.String,
    'to_be_deleted': fields.Boolean,
    'log_fetch_pending': fields.Boolean,
    'error_msg': fields.String,
    'username': fields.String,
    'user_id': fields.String,
    'environment': fields.String,
    'environment_id': fields.String,
    'provisioning_config': fields.Raw,
    'instance_data': fields.Raw,
    'logs': fields.Raw,
}

instance_log_fields = {
    'id': fields.String,
    'instance_id': fields.String,
    'log_type': fields.String,
    'log_level': fields.String,
    'timestamp': fields.Float,
    'message': fields.String
}


def query_environment(environment_id):
    return Environment.query.filter_by(id=environment_id).first()


def query_user(user_id):
    return User.query.filter_by(id=user_id).first()


def positive_integer(input_value):
    """Return input_value if valid, raise an exception in other case."""
    try:
        input_int = int(input_value)
    except:
        raise ValueError('{} is not a valid integer'.format(input_value))
    if input_int >= 0:
        return input_int
    else:
        raise ValueError('{} is not a positive integer'.format(input_value))


class InstanceList(restful.Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('show_only_mine', type=bool, default=False, location='args')
    parser.add_argument('offset', type=positive_integer, location='args')
    parser.add_argument('limit', type=positive_integer, location='args')

    @auth.login_required
    @marshal_with(instance_fields)
    def get(self):
        user = g.user
        args = self.parser.parse_args()
        q = apply_rules_instances(user, args)
        q = q.order_by(Instance.provisioned_at)
        instances = q.all()

        get_environment = memoize(query_environment)
        get_user = memoize(query_user)
        for instance in instances:
            instance_logs = get_logs_from_db(instance.id)
            instance.logs = marshal(instance_logs, instance_log_fields)

            user = get_user(instance.user_id)
            if user:
                instance.username = user.ext_id

            environment = get_environment(instance.environment_id)
            if not environment:
                logging.warning("instance %s has a reference to non-existing environment" % instance.id)
                continue

            age = 0
            if instance.provisioned_at:
                age = (datetime.datetime.utcnow() - instance.provisioned_at).total_seconds()
            instance.lifetime_left = max(environment.maximum_lifetime - age, 0)
            instance.maximum_lifetime = environment.maximum_lifetime
            instance.cost_multiplier = environment.cost_multiplier

            if instance.to_be_deleted and instance.state != Instance.STATE_DELETED:
                instance.state = Instance.STATE_DELETING

        return instances

    @auth.login_required
    def post(self):
        user = g.user

        form = InstanceForm()
        if not form.validate_on_submit():
            logging.warning("validation error on user login")
            return form.errors, 422

        environment_id = form.environment.data

        # fetch the environment using shared access rules
        environment = rules.apply_rules_environments(user, dict(environment_id=environment_id)).first()
        if not environment:
            logging.warning('instance creation failed, no environment found for id %s', environment_id)
            abort(404)

        # admins and workspace managers are allowed to test disabled environments
        if not environment.is_enabled and not (user.is_admin or is_workspace_manager(user, environment.workspace)):
            logging.warning('instance creation failed, environment %s is disabled', environment_id)
            abort(403)

        instances_for_user = Instance.query.filter_by(
            environment_id=environment.id,
            user_id=user.id
        ).filter(Instance.state != 'deleted').all()

        if instances_for_user:
            return {'error': 'ENVIRONMENT_INSTANCE_LIMIT_REACHED'}, 409

        # create the instance and assign provisioning config from current environment + template
        instance = Instance(environment, user)
        instance.provisioning_config = utils.get_full_environment_config(environment)

        # XXX: Choosing the name should be done in the model's constructor method
        # decide on a name that is not used currently
        existing_names = set(x.name for x in Instance.query.all())
        # Note: the potential race is solved by unique constraint in database
        while True:
            c_name = Instance.generate_name(prefix=current_app.config.get('INSTANCE_NAME_PREFIX'))
            if c_name not in existing_names:
                instance.name = c_name
                break
        db.session.add(instance)
        db.session.commit()

        return marshal(instance, instance_fields), 200


class InstanceView(restful.Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('state', type=str)
    parser.add_argument('public_ip', type=str)
    parser.add_argument('error_msg', type=str)
    parser.add_argument('client_ip', type=str)
    parser.add_argument('instance_data', type=str)
    parser.add_argument('to_be_deleted', type=bool)
    parser.add_argument('log_fetch_pending', type=bool)
    parser.add_argument('send_email', type=bool)

    @auth.login_required
    @marshal_with(instance_fields)
    def get(self, instance_id):
        user = g.user
        args = {'instance_id': instance_id}
        query = apply_rules_instances(user, args)
        instance = query.first()
        if not instance:
            abort(404)

        environment = Environment.query.filter_by(id=instance.environment_id).first()
        instance.environment_id = environment.id
        instance.username = instance.user
        instance_logs = get_logs_from_db(instance.id)
        instance.logs = marshal(instance_logs, instance_log_fields)

        if 'allow_update_client_connectivity' in environment.full_config \
                and environment.full_config['allow_update_client_connectivity']:
            instance.can_update_connectivity = True

        age = 0
        if instance.provisioned_at:
            age = (datetime.datetime.utcnow() - instance.provisioned_at).total_seconds()
        instance.lifetime_left = max(environment.maximum_lifetime - age, 0)
        instance.maximum_lifetime = environment.maximum_lifetime
        instance.cost_multiplier = environment.cost_multiplier

        return instance

    @auth.login_required
    def delete(self, instance_id):
        user = g.user
        query = Instance.query.filter_by(id=instance_id)
        if not user.is_admin and not is_workspace_manager(user):
            query = query.filter_by(user_id=user.id)
        instance = query.first()
        if not instance:
            abort(404)
        workspace = instance.environment.workspace
        if not user.is_admin and not is_workspace_manager(user, workspace) and instance.user_id != user.id:
            abort(403)
        instance.to_be_deleted = True
        instance.deprovisioned_at = datetime.datetime.utcnow()
        db.session.commit()

        # Action queued, return 202 Accepted
        return None, 202

    @auth.login_required
    @requires_admin
    def patch(self, instance_id):
        args = self.parser.parse_args()
        instance = Instance.query.filter_by(id=instance_id).first()
        if not instance:
            abort(404)

        if args.get('state'):
            state = args.get('state')
            if state not in Instance.VALID_STATES:
                abort(422)
            instance.state = args['state']
            if instance.state == Instance.STATE_RUNNING:
                if not instance.provisioned_at:
                    instance.provisioned_at = datetime.datetime.utcnow()
            if instance.state == Instance.STATE_FAILED:
                instance.errored = True
            if instance.state == Instance.STATE_DELETED:
                delete_logs_from_db(instance_id)
            db.session.commit()

        if args.get('to_be_deleted'):
            instance.to_be_deleted = args['to_be_deleted']
            instance.deprovisioned_at = datetime.datetime.utcnow()
            db.session.commit()

        if args.get('log_fetch_pending') is not None:
            instance.log_fetch_pending = args['log_fetch_pending']
            db.session.commit()

        if args.get('error_msg'):
            instance.error_msg = args['error_msg']
            db.session.commit()

        if args.get('public_ip'):
            instance.public_ip = args['public_ip']
            db.session.commit()

        if args.get('instance_data'):
            try:
                instance.instance_data = json.loads(args['instance_data'])
            except ValueError:
                logging.warning("invalid instance_data passed to view: %s" % args['instance_data'])
            db.session.commit()


class InstanceLogs(restful.Resource):

    @auth.login_required
    @marshal_with(instance_log_fields)
    def get(self, instance_id):
        user = g.user
        parser = reqparse.RequestParser()
        parser.add_argument('log_type', type=str, default=None, required=False, location='args')
        args = parser.parse_args()
        query = apply_rules_instances(user, dict(instance_id=instance_id))
        instance = query.first()
        if not instance:
            abort(404)

        instance_logs = get_logs_from_db(instance_id, args.get('log_type'))

        return instance_logs

    @auth.login_required
    @requires_admin
    def patch(self, instance_id):
        parser = reqparse.RequestParser()
        parser.add_argument('log_record', type=dict)
        parser.add_argument('log_type', type=str)
        args = parser.parse_args()
        instance = Instance.query.filter_by(id=instance_id).first()
        if not instance:
            abort(404)
        if args.get('log_record'):
            log_record = args['log_record']
            instance_log = process_logs(instance_id, log_record)
            db.session.add(instance_log)
            db.session.commit()

        return 'ok'

    @auth.login_required
    @requires_admin
    def delete(self, instance_id):
        parser = reqparse.RequestParser()
        parser.add_argument('log_type', type=str, default=None, required=False, location='args')
        args = parser.parse_args()
        delete_logs_from_db(instance_id, args.get('log_type'))


def get_logs_from_db(instance_id, log_type=None):
    logs_query = InstanceLog.query\
        .filter_by(instance_id=instance_id)
    if log_type:
        logs_query = logs_query.filter_by(log_type=log_type)
    logs_query = logs_query.order_by(InstanceLog.timestamp)
    logs = logs_query.all()
    return logs


def delete_logs_from_db(instance_id, log_type=None):
    instance_logs = get_logs_from_db(instance_id, log_type)
    if not instance_logs:
        logging.warning("There are no log entries to be deleted")

    for instance_log in instance_logs:
        db.session.delete(instance_log)
    db.session.commit()


def process_logs(instance_id, log_record):

    # in case of running logs, the whole message is replaced again (thus only 1 running log record with all info)
    if log_record['log_type'] == 'running':
        existing_runnings_logs = get_logs_from_db(instance_id, 'running')
        if existing_runnings_logs:
            instance_log = existing_runnings_logs[0]
            instance_log.timestamp = float(log_record['timestamp'])
            # replace the whole text (older text now appended with the new text)
            instance_log.message = log_record['message']
            return instance_log

    instance_log = InstanceLog(
        instance_id,
        log_record['log_level'],
        log_record['log_type'],
        log_record['timestamp'],
        log_record['message'],
    )

    return instance_log
