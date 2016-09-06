CONFIG = {
    'schema': {
        'type': 'object',
        'title': 'Comment',
        'description': 'Description',
        'required': [
            'name',
            'number_of_nodes',
        ],
        'properties': {
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'software': {
                'type': 'array',
                'title': 'Select software',
                'items': {
                    'type': 'string',
                    'enum': [
                        'Common',
                        'Cluster',
                        'Hadoop',
                        'Spark',
                        'Ganglia',
                    ]
                }
            },
            'frontend_flavor': {
                'type': 'string',
                'title': 'Frontend flavor',
                'enum': [
                ]
            },
            'frontend_image': {
                'type': 'string',
                'title': 'Frontend image',
                'enum': [
                ]
            },
            'frontend_volumes': {
                'type': 'array',
                'title': 'Frontend volumes',
                'items': {
                    "type": "object",
                    "title": "Volume",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "size": {
                            "type": "integer"
                        },
                        "device": {
                            "type": "string"
                        },
                    }
                }
            },
            'node_volumes': {
                'type': 'array',
                'title': 'Node volumes',
                'items': {
                    "type": "object",
                    "title": "Volume",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "size": {
                            "type": "integer"
                        },
                        "device": {
                            "type": "string"
                        },
                    }
                }
            },
            'node_flavor': {
                'type': 'string',
                'title': 'Node flavor',
                'enum': [
                ]
            },
            'node_image': {
                'type': 'string',
                'title': 'Node image',
                'enum': [
                ]
            },
            'number_of_nodes': {
                'type': 'integer',
                'title': 'Number of worker nodes',
                'default': 2,
            },
            'maximum_lifetime': {
                'type': 'string',
                'title': 'Maximum life-time (days hours mins)',
                'default': '1h 0m',
                'pattern': '^(\d+d\s?)?(\d{1,2}h\s?)?(\d{1,2}m\s?)?$',
                'validationMessage': 'Value should be in format [days]d [hours]h [minutes]m'
            },
            'maximum_instances_per_user': {
                'type': 'integer',
                'title': 'Maximum instances per user',
                'default': 1,
            },
            'cost_multiplier': {
                'type': 'number',
                'title': 'Cost multiplier (default 1.0)',
                'default': 1.0,
            },
            'firewall_rules': {
                'type': 'array',
                'title': 'Frontend firewall rules',
                'items': {
                    'type': 'string',
                    'title': 'Rules',
                }
            },
            "allow_update_client_connectivity": {
                "type": "boolean",
                "title": "Allow user to request instance firewall to allow access to user's IP address",
                "default": False,
            },
            'needs_ssh_keys': {
                'type': 'boolean',
                'title': "Needs ssh-keys to access",
                'default': True,
            },
        }
    },
    'form': [
        {
            'type': 'help',
            'helpvalue': '<h4>Pouta virtualcluster service config</h4>'
        },
        'name',
        'description',
        'number_of_nodes',
        'frontend_flavor',
        'frontend_image',
        {
            'key': 'frontend_volumes',
            'items': ['frontend_volumes[].name', 'frontend_volumes[].size', 'frontend_volumes[].device']
        },
        'node_flavor',
        'node_image',
        {
            'key': 'node_volumes',
            'items': ['node_volumes[].name', 'node_volumes[].size', 'node_volumes[].device']
        },
        'software',
        'maximum_lifetime',
        'maximum_instances_per_user',
        'cost_multiplier',
        'firewall_rules',
        'allow_update_client_connectivity',
    ],
    'model': {
        'name': 'pvc',
        'description': 'pvc blueprint',
        'software': ['Common', ],
        'frontend_flavor': 'standard.tiny',
        'frontend_image': 'Ubuntu-14.04',
        'frontend_volumes': [
            {'name': 'local_data', 'device': '/dev/vdc', 'size': 0},
            {'name': 'shared_data', 'device': '/dev/vdd', 'size': 0},
        ],
        'node_flavor': 'standard.tiny',
        'node_image': 'Ubuntu-14.04',
        'node_volumes': [
            {'name': 'local_data', 'device': '/dev/vdc', 'size': 0},
        ],
        'firewall_rules': ['tcp 22 22 192.168.1.0/24'],
        'needs_ssh_keys': True,
    }
}
