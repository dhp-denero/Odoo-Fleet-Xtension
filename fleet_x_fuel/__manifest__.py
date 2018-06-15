# -*- coding: utf-8 -*-
{
    'name': "Fleet management Xtenson - Fuel management",
    'summary': "provides more comprehensive fuel management features to fleet addon",
    'author': "Salton Massally<smassally@idtlabs.sl>, DeneroTeam <dhaval@deneroteam.com>",
    'website': "http://idtlabs.sl",
    'category': 'Managing vehicles and contracts',
    'version': '10.0.2018.06.12.1',
    'depends': ['fleet_x', 'fleet_x_driver'],
    'data': [
        'views/fleet_fuel.xml',
        'data/fleet_fuel_data.xml',
        'report/fuel_board_view.xml',
        'views/fleet_fuel_report.xml',
        'views/res_config_views.xml',
        'security/ir.model.access.csv',
        'report/report_fuel_coupon.xml',
    ],
    'installable': True

}
