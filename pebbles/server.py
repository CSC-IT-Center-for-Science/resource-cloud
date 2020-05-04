import logging
import uuid

from flask import render_template
import flask_restful as restful
try:
    from flask_sso import SSO
except:
    logging.info("flask_sso library is not installed, Shibboleth authentication will not work")

from pebbles.app import app
from pebbles.models import db, User

from pebbles.views.commons import create_user, is_group_manager, update_email
from pebbles.views.blueprint_templates import blueprint_templates, BlueprintTemplateList, BlueprintTemplateView, BlueprintTemplateCopy
from pebbles.views.blueprints import blueprints, BlueprintList, BlueprintView, BlueprintCopy
from pebbles.views.plugins import plugins, PluginList, PluginView
from pebbles.views.users import users, UserList, UserView, UserActivationUrl, UserBlacklist, UserGroupOwner, KeypairList, CreateKeyPair, UploadKeyPair
from pebbles.views.groups import groups, GroupList, GroupView, GroupJoin, GroupListExit, GroupExit, GroupUsersList, ClearUsersFromGroup
from pebbles.views.notifications import NotificationList, NotificationView
from pebbles.views.instances import instances, InstanceList, InstanceView, InstanceLogs, InstanceTokensList, InstanceTokensView
from pebbles.views.authorize_instances import authorize_instances, AuthorizeInstancesView
from pebbles.views.activations import activations, ActivationList, ActivationView
from pebbles.views.firstuser import firstuser, FirstUserView
from pebbles.views.myip import myip, WhatIsMyIp
from pebbles.views.quota import quota, Quota, UserQuota
from pebbles.views.sessions import sessions, SessionView
from pebbles.views.variables import variables, PublicVariableList
from pebbles.views.locks import locks, LockView
from pebbles.views.stats import stats, StatsList
from pebbles.views.export_stats import export_stats, ExportStatistics
from pebbles.views.import_export import import_export, ImportExportBlueprintTemplates, ImportExportBlueprints
from pebbles.views.namespaced_keyvalues import namespaced_keyvalues, NamespacedKeyValueList, NamespacedKeyValueView

api = restful.Api(app)
api_root = '/api/v1'
api.add_resource(FirstUserView, api_root + '/initialize')
api.add_resource(UserList, api_root + '/users', methods=['GET', 'POST', 'PATCH'])
api.add_resource(UserView, api_root + '/users/<string:user_id>')
api.add_resource(UserActivationUrl, api_root + '/users/<string:user_id>/user_activation_url')
api.add_resource(UserBlacklist, api_root + '/users/<string:user_id>/user_blacklist')
api.add_resource(UserGroupOwner, api_root + '/users/<string:user_id>/user_group_owner')
api.add_resource(KeypairList, api_root + '/users/<string:user_id>/keypairs')
api.add_resource(CreateKeyPair, api_root + '/users/<string:user_id>/keypairs/create')
api.add_resource(UploadKeyPair, api_root + '/users/<string:user_id>/keypairs/upload')
api.add_resource(GroupList, api_root + '/groups')
api.add_resource(GroupView, api_root + '/groups/<string:group_id>')
api.add_resource(GroupJoin, api_root + '/groups/group_join/<string:join_code>')
api.add_resource(GroupListExit, api_root + '/groups/group_list_exit')
api.add_resource(GroupExit, api_root + '/groups/group_exit/<string:group_id>')
api.add_resource(GroupUsersList, api_root + '/groups/<string:group_id>/users')
api.add_resource(ClearUsersFromGroup, api_root + '/groups/clear_users_from_group')
api.add_resource(NotificationList, api_root + '/notifications')
api.add_resource(NotificationView, api_root + '/notifications/<string:notification_id>')
api.add_resource(SessionView, api_root + '/sessions')
api.add_resource(ActivationList, api_root + '/activations')
api.add_resource(ActivationView, api_root + '/activations/<string:token_id>')
api.add_resource(BlueprintTemplateList, api_root + '/blueprint_templates')
api.add_resource(BlueprintTemplateView, api_root + '/blueprint_templates/<string:template_id>')
api.add_resource(BlueprintTemplateCopy, api_root + '/blueprint_templates/template_copy/<string:template_id>')
api.add_resource(BlueprintList, api_root + '/blueprints')
api.add_resource(BlueprintView, api_root + '/blueprints/<string:blueprint_id>')
api.add_resource(BlueprintCopy, api_root + '/blueprints/blueprint_copy/<string:blueprint_id>')
api.add_resource(InstanceList, api_root + '/instances')
api.add_resource(
    InstanceView,
    api_root + '/instances/<string:instance_id>',
    methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
api.add_resource(
    InstanceLogs,
    api_root + '/instances/<string:instance_id>/logs',
    methods=['GET', 'PATCH', 'DELETE'])
api.add_resource(InstanceTokensList, api_root + '/instance_tokens')
api.add_resource(
    InstanceTokensView,
    api_root + '/instance_tokens/<string:instance_id>',
    methods=['POST', 'DELETE'])
api.add_resource(AuthorizeInstancesView, api_root + '/authorize_instances')
api.add_resource(PluginList, api_root + '/plugins')
api.add_resource(PluginView, api_root + '/plugins/<string:plugin_id>')
api.add_resource(PublicVariableList, api_root + '/config')
api.add_resource(WhatIsMyIp, api_root + '/what_is_my_ip')
api.add_resource(Quota, api_root + '/quota')
api.add_resource(UserQuota, api_root + '/quota/<string:user_id>')
api.add_resource(LockView, api_root + '/locks/<string:lock_id>')
api.add_resource(ImportExportBlueprintTemplates, api_root + '/import_export/blueprint_templates')
api.add_resource(ImportExportBlueprints, api_root + '/import_export/blueprints')
api.add_resource(StatsList, api_root + '/stats')
api.add_resource(ExportStatistics, api_root + '/export_stats/export_statistics')
api.add_resource(NamespacedKeyValueList, api_root + '/namespaced_keyvalues')
api.add_resource(NamespacedKeyValueView, api_root + '/namespaced_keyvalues/<string:namespace>/<string:key>')

app.register_blueprint(blueprint_templates)
app.register_blueprint(blueprints)
app.register_blueprint(plugins)
app.register_blueprint(users)
app.register_blueprint(groups)
app.register_blueprint(instances)
app.register_blueprint(activations)
app.register_blueprint(firstuser)
app.register_blueprint(myip)
app.register_blueprint(sessions)
app.register_blueprint(variables)
app.register_blueprint(quota)
app.register_blueprint(locks)
app.register_blueprint(import_export)
app.register_blueprint(stats)
app.register_blueprint(export_stats)
app.register_blueprint(namespaced_keyvalues)
app.register_blueprint(authorize_instances)

admin_icons = ["Dashboard", "Users", "Groups", "Blueprints", "Configure", "Statistics", "Account"]
group_owner_icons = ["Dashboard", "", "Groups", "Blueprints", "", "", "Account"]
group_manager_icons = ["Dashboard", "", "", "Blueprints", "", "", "Account"]
user_icons = ["Dashboard", "", "", "", "", "", "Account"]

if app.config['ENABLE_SHIBBOLETH_LOGIN']:
    sso = SSO(app=app)

    @sso.login_handler
    def login(user_info):
        if user_info['authmethod'] == app.config['CSC_LOGIN_AUTH_METHOD']:
            if user_info['accountlock'] and user_info['accountlock'] == 'true':
                error_description = 'Your CSC account has been locked. \
                    You were not authorized to access. Contact the administrator'
                return render_template(
                    'error.html',
                    error_title='User not authorized',
                    error_description=error_description
                )
            else:
                """
                Previously csc-internal-idp returned "eppn@cscuserid". Now the csc logins
                through AAI proxy returns eppn as "eppn@csc.fi". The following manipulation
                is required to access older accounts who logged in with cscuserid".

                Check if csc account is linked to haka, then eppn user-attribute is returned.
                if csc account is linked to virtu, then vppn user-attribute is returned.
                For other cases use csc email_id for now and later user name attribute
                (which is unique).

                In any case no matter what/how the csc account is linked to, it is always
                treated as separate account.
                If csc account is linked to more than one idp (say haka and virtu), then eppn
                from haka will be used. This will lead to a migrated-accessibilty problem(from
                older customer-idp) if a user has first linked to haka and then revoked and
                linked to virtu/anyother.
                """
                if user_info['eppn']:
                    eppn = user_info['eppn'].split('@')[0] + '@cscuserid'
                elif user_info['vppn']:
                    eppn = user_info['vppn'].split('@')[0] + '@cscuserid'
                    """ this is not implemented in csc LDAP yet.
                    elif user_info['cscusername']:
                    eppn = user_info['cscusername'] + '@cscuserid'
                    """
                else:
                    eppn = user_info['email_id']
        elif user_info['authmethod'] == app.config['VIRTU_LOGIN_AUTH_METHOD']:
            """
            virtu login does not have eppn. Eppn is only for academics. virtu has custom
            attribute virtuPersonPrincipalname(VirtuLocalId+VirtuHomeOrg) which is lot like eppn.
            """
            eppn = user_info['vppn']
        elif user_info['authmethod'] == app.config['HAKA_LOGIN_AUTH_METHOD']:
            eppn = user_info['eppn']
        else:
            # block all other logins
            error_description = 'You were not authorized to access. Contact the administrator'
            return render_template(
                'error.html',
                error_title='User not authorized',
                error_description=error_description
            )

        user = User.query.filter_by(eppn=eppn).first()
        if not user:
            user = create_user(eppn, password=uuid.uuid4().hex, email_id=user_info['email_id'])
        if not user.email_id:
            user = update_email(eppn, email_id=user_info['email_id'])
        if not user.is_active:
            user.is_active = True
            db.session.commit()
        if user.is_blocked:
            error_description = 'You have been blocked, contact your administrator'
            return render_template(
                'error.html',
                error_title='User Blocked',
                error_description=error_description
            )
        if user.is_admin:
            icons = admin_icons
        elif user.is_group_owner:
            icons = group_owner_icons
        elif is_group_manager(user):
            icons = group_manager_icons
        else:
            icons = user_icons

        token = user.generate_auth_token(app.config['SECRET_KEY'])
        return render_template(
            'login.html',
            token=token,
            username=eppn,
            is_admin=user.is_admin,
            is_group_owner=user.is_group_owner,
            is_group_manager=is_group_manager(user),
            userid=user.id,
            icon_value=icons
        )

    @sso.login_error_handler
    def login_error(user_info):
        error_title = 'unknown error'
        error_description = ''
        if not user_info.get('eppn'):
            error_title = 'Login not available'
            error_description = (
                'Your home organization did not return us your login attributes which prevents '
                'you from logging in. Waiting a bit might resolve this.')

        return render_template(
            'error.html',
            error_title=error_title,
            error_description=error_description
        )
