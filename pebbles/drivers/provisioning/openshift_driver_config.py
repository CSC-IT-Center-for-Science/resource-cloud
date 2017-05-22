CONFIG = {
    'schema': {
        'type': 'object',
        'title': 'Comment',
        'description': 'Description',
        'required': [
            'name',
            'image',
            'port',
            'openshift_cluster_id',
            'memory_limit',
        ],
        'properties': {
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'image': {
                'type': 'string',
            },
            'port': {
                'type': 'integer',
            },
            'volume_mount_point': {
                'type': 'string',
            },
            'openshift_cluster_id': {
                'type': 'string',
                'title': 'Cluster name (configured in credentials file)',
            },
            'memory_limit': {
                'type': 'string',
                'default': '512M',
            },
            'maximum_instances_per_user': {
                'type': 'integer',
                'title': 'Maximum instances per user',
                'default': 1,
            },
            'maximum_lifetime': {
                'type': 'string',
                'title': 'Maximum life-time (days hours mins)',
                'default': '1h 0m',
                'pattern': '^(\d+d\s?)?(\d{1,2}h\s?)?(\d{1,2}m\s?)?$',
                'validationMessage': 'Value should be in format [days]d [hours]h [minutes]m'
            },
            'cost_multiplier': {
                'type': 'number',
                'title': 'Cost multiplier',
                'default': 0.0,
            },
            'environment_vars': {
                'type': 'string',
                'title': 'environment variables for docker, separated by space',
                'default': '',
            },
            'autodownload_url': {
                'type': 'string',
                'title': 'Autodownload URL',
                'default': '',
            },
            'autodownload_filename': {
                'type': 'string',
                'title': 'Autodownload file name',
                'default': '',
            },
            'show_password': {
                'type': 'boolean',
                'title': 'Show the required password/token (if any), to the user',
                'default': True,
            },
        }
    },
    'form': [
        {
            'type': 'help',
            'helpvalue': '<h4>Docker instance config</h4>'
        },
        'name',
        'description',
        'image',
        'port',
        'volume_mount_point',
        'openshift_cluster_id',
        'environment_vars',
        'autodownload_url',
        'autodownload_filename',
        'show_password',
        'memory_limit',
        'maximum_instances_per_user',
        'maximum_lifetime',
        'cost_multiplier'
    ],
    'model': {
        'name': 'openshift_testing',
        'description': 'openshift testing template',
        'cost_multiplier': 0.0,
        'port': 8888,
        'image': '',
        'memory_limit': '512M',
    }
}
