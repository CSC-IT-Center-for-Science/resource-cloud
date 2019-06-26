from Crypto.PublicKey import RSA
import base64
import struct
import six
from functools import wraps
from flask import abort, g
import re


KEYPAIR_DEFAULT = {
    'bits': 2048,
}


def generate_ssh_keypair(bits=KEYPAIR_DEFAULT['bits']):
    new_key = RSA.generate(bits)
    public_key = new_key.publickey().exportKey(format="OpenSSH")
    private_key = new_key.exportKey(format="PEM")
    return private_key, public_key


def validate_ssh_pubkey(pubkey):
    """
    Check if the given string looks like a SSH public key.
    Based on https://github.com/jirutka/ssh-ldap-pubkey
    """
    if not pubkey:
        return False

    key_parts = pubkey.split()
    if len(key_parts) < 2:
        return False

    key_type, key_data = key_parts[0:2]
    if key_type not in ("ssh-rsa", "ssh-dss"):
        return False

    try:
        key_bytes = base64.decodestring(six.b(key_data))
    except base64.binascii.Error:
        return False

    int_len = 4
    str_len = struct.unpack('>I', key_bytes[:int_len])[0]
    if six.u(key_bytes[int_len:(int_len + str_len)]) != six.b(key_type):
        return False

    return True


def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def requires_group_owner_or_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user.is_admin and not g.user.is_group_owner:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def memoize(func):
    """
    Generic memoization implementation suitable for decorator use
    """
    cache = {}

    def inner(x):
        if x not in cache:
            cache[x] = func(x)
        return cache[x]
    return inner


def parse_maximum_lifetime(max_life_str):
    m = re.match(r'^(\d+d\s?)?(\d{1,2}h\s?)?(\d{1,2}m\s?)??$', max_life_str)
    if m:
        days = hours = mins = 0
        if m.group(1):
            days = int(m.group(1).strip()[:-1])
        if m.group(2):
            hours = int(m.group(2).strip()[:-1])
        if m.group(3):
            mins = int(m.group(3).strip()[:-1])

        maximum_lifetime = days * 86400 + hours * 3600 + mins * 60
        return maximum_lifetime
    else:
        raise ValueError


def parse_ports_string(ports_str):
    ports_list = []
    ports_str = ports_str.replace(',', ' ')
    ports = ports_str.split(' ')
    ports = filter(None, ports)
    for port in ports:
        if ':' in port:
            (from_port, to_port) = parse_port_range(port)
        else:
            try:
                from_port = int(port)
                to_port = int(port)
            except:
                raise ValueError('Port is not an integer')

        if 0 < from_port < 65536 and 0 < to_port < 65536:
            ports_list.append((from_port, to_port))
        else:
            raise ValueError('Error parsing the input port string')
    return ports_list


def parse_port_range(port_range):
    m = re.match(r'(\d+):(\d+)', port_range)
    if m:
        if int(m.group(1)) < int(m.group(2)):
            return (int(m.group(1)), int(m.group(2)))
        else:
            raise ValueError('Port range invalid')
    else:
        raise ValueError('No port range found')


def get_full_blueprint_config(blueprint):
    """Get the full config for blueprint from blueprint template for allowed attributes"""
    template = blueprint.template
    allowed_attrs = template.allowed_attrs
    allowed_attrs = ['name', 'description'] + allowed_attrs
    full_config = template.config
    bp_config = blueprint.config
    for attr in allowed_attrs:
        if attr in bp_config:
            full_config[attr] = bp_config[attr]
    return full_config


def get_blueprint_fields_from_config(blueprint, field_name):
    """Hybrid fields for Blueprint model which need processing"""
    full_config = get_full_blueprint_config(blueprint)

    if field_name == 'preallocated_credits':
        preallocated_credits = False  # Default value
        if 'preallocated_credits' in full_config:
            try:
                preallocated_credits = bool(full_config['preallocated_credits'])
            except:
                pass
        return preallocated_credits

    if field_name == 'maximum_lifetime':
        maximum_lifetime = 3600  # Default value of 1 hour
        if 'maximum_lifetime' in full_config:
            max_life_str = str(full_config['maximum_lifetime'])
            if max_life_str:
                maximum_lifetime = parse_maximum_lifetime(max_life_str)
        return maximum_lifetime

    if field_name == 'cost_multiplier':
        cost_multiplier = 1.0  # Default value
        if 'cost_multiplier' in full_config:
            try:
                cost_multiplier = float(full_config['cost_multiplier'])
            except:
                pass
        return cost_multiplier


def b64encode_string(content):
    """python2 and python3 compatibility wrapper function. Can be removed when support for python2 is gone"""
    if six.PY3:
        return base64.b64encode(content.encode('utf-8')).decode('utf-8')
    else:
        return base64.b64encode(content).decode('utf-8')
