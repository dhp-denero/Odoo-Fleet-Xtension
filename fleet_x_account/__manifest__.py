#-*- coding:utf-8 -*-
{
    'name': 'Fleet Accounting',
    'version': '1.0',
    'category': 'Managing vehicles and drivers',
    'summary': "Fleet integration with accounting",
    'author': 'Salton Massally<smassally@idtlabs.sl>, DeneroTeam <dhaval@deneroteam.com>',
    'website': 'http://idtlabs.sl',
    'depends': [
        'account', 'fleet_x_service'
    ],
    'data': [
        'views/fleet_account.xml',
        'views/res_config.xml',
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
