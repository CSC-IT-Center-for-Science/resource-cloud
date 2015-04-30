import os
import yaml
import functools
from pouta_blueprints.models import Variable

CONFIG_FILE = '/etc/pouta_blueprints/config.yaml'
LOCAL_CONFIG_FILE = '/etc/pouta_blueprints/config.yaml.local'
EXPOSED_VARIABLES = (
    'SENDER_EMAIL', 'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD',
    'MAIL_USE_SSL', 'MAIL_USE_TLS', 'INSTANCE_NAME_PREFIX')


def resolve_configuration_value(key, default=None, skip_db=False, *args, **kwargs):
    def get_key_from_config(config_file, key):
        return yaml.load(open(config_file)).get(key)

    variable = Variable.query.filter_by(key=key).first()
    if variable:
        return variable.value

    # check environment
    pb_key = 'PB_' + key
    value = os.getenv(pb_key)
    if value is not None:
        return value

    # then check local config file and finally check system
    # config file and given default
    for config_file in (LOCAL_CONFIG_FILE, CONFIG_FILE):
        if os.path.isfile(config_file):
            value = get_key_from_config(config_file, key)
            if value is not None:
                return value

    if default is not None:
        return default


def fields_to_properties(cls):
    for k, default in vars(cls).items():
        if not k.startswith('_') and k.isupper():
            resolvef = functools.partial(resolve_configuration_value, k, default, cls._skip_db)
            setattr(cls, k, property(resolvef))
    return cls


@fields_to_properties
class BaseConfig(object):
    _skip_db = False
    DEBUG = True
    SECRET_KEY = "change_me"
    WTF_CSRF_ENABLED = False
    SSL_VERIFY = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/change_me.db'
    M2M_CREDENTIAL_STORE = '/var/run/pouta_blueprints_m2m'
    MESSAGE_QUEUE_URI = 'redis://www:6379/0'
    INSTANCE_DATA_DIR = '/var/spool/pb_instances'
    INTERNAL_API_BASE_URL = 'https://www/api/v1'
    BASE_URL = 'https://localhost:8888'
    MAX_CONTENT_LENGTH = 1024 * 1024
    FAKE_PROVISIONING = False
    SENDER_EMAIL = 'sender@example.org'
    MAIL_SERVER = 'smtp.example.org'
    MAIL_PORT = 25
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_SUPPRESS_SEND = True
    SKIP_TASK_QUEUE = False
    WRITE_PROVISIONING_LOGS = True
    INSTANCE_NAME_PREFIX = 'pb-'

    # enable access by []
    def __getitem__(self, item):
        return getattr(self, item)

    def get(self, key):
        return getattr(self, key)


class TestConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    MAIL_SUPPRESS_SEND = True
    FAKE_PROVISIONING = True
    SKIP_TASK_QUEUE = True
    WRITE_PROVISIONING_LOGS = False
