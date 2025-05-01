{
    "name": "Dynamic Approval System",
    "summary": "Dynamic Approval System",
    "version": "17.0.0.0.0",
    "author": "Fahad Hassan",
    "license": "AGPL-3",
    'website': "https://www.codexitns.com/",
    "category": "approval",
    "depends": ["base", "sale","purchase",'bus'],
    "data": [
        'security/ir.model.access.csv',
        'views/dynamic_approve_config_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/res_users_view.xml',
    ],
     'assets': {
        'web.assets_backend': [
            'cdx_dynamic_approval/static/src/js/services/notification_service.js',
        ],
    },
    "installable": True,
    "auto_install":False,
}
