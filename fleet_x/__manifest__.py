# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtenson",
    'summary': "This is an extension of default Fleet Management module",
    'author': 'Salton Massally<smassally@idtlabs.sl>, DeneroTeam <dhaval@deneroteam.com>',
    'website': "http://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '10.0.2018.06.11.1',
    'depends': ['fleet', 'board'],
    'data': [
        'data/fleet_data.xml',
        'security/ir.model.access.csv',
        'views/fleet.xml',
        'views/res_config.xml',
        'views/fleet_board_view.xml',
    ],
    'installable': True

}
