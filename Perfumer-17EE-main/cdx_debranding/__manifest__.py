# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Codex Odoo UI Debranding',
    'version': '17.0.0.0',
    'summary': 'Odoo UI Debranding add every customisation detail here with comma in description section',
    'author': 'Codex',
    'description': """1. Chatter position changer.""",
    'website': 'www.codexitns.com',
    'depends': ['web', 'mail'],
    'category': 'Extra Tools',
    'data': [
        'views/res_users.xml',
        'views/web.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/cdx_debranding/static/src/js/web_chatter_position.esm.js',
            '/cdx_debranding/static/src/scss/chatter_custom.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
