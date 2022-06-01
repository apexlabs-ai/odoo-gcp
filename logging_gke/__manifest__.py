# -*- coding: utf-8 -*-
{
    'name': "logging_gke",

    'summary': """
        Odoo logging for Google Cloud Kubernetes / Google Cloud Container engine
    """,

    'description': """
        Load this module during with --load=logging_gke
    """,

    'author': "Alex Yushin, Apex Labs",
    'website': "https://apexlabs.ai",
    'category': 'Extra Tools',
    'version': '13.0.0.1',
    'depends': ['base'],
    'external_dependencies': {
        'python': ['google-cloud-logging'],
    },
    'data': [
    ],
    'installable': True,
}
