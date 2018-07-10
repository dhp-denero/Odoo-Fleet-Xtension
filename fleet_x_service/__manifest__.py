# -*- coding: utf-8 -*-
{
    'name': "Fleet Xtenson - Vehicle Service management",
    'summary': "Provides more to vehicle service management",
    'author': "Salton Massally<smassally@idtlabs.sl>, DeneroTeam <dhaval@deneroteam.com>",
    'website': "https://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '10.0.2018.06.28.2',
    'depends': ['fleet_x', 'fleet_x_driver'],
    'data': [
        'views/fleet_service.xml',
        'views/res_config.xml',
        'data/fleet_service_data.xml',
        'reports/fleet_board_view.xml',
        'security/ir.model.access.csv',
        'security/fleet_service_security.xml',
    ],

    'installable': True

}
