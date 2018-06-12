# -*- coding: utf-8 -*-
{
    'name': "Odoo Debranding",
    'version': "10.0.2018.06.12.1",
    'summary': """Debrand Odoo""",
    'description': """Debrand Odoo""",
    'author': "DeneroTeam",
    'company': "DeneroTeam",
    'website': "https://www.deneroteam.com",
    'category': 'Tools',
    'depends': ['base', 'im_livechat', 'web'],
    'data': [
        'views/views.xml'
    ],
    'demo': [],
    'qweb': ["static/src/xml/*.xml"],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': True,
    'application': True
}
