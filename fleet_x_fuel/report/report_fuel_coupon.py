#-*- coding:utf-8 -*-

import time
from openerp.osv import osv
from openerp.report import report_sxw


class fuel_coupon_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(fuel_coupon_report, self).__init__(cr, uid, name, context=context)
        #lets scream if state is not right
        coupon_ids  = context.get('active_ids', False)
        if coupon_ids:
            for coupon in self.pool.get('fleet.fuel.coupon').read(cr, uid, coupon_ids, ['state'], context=context):
                if coupon['state'] != 'active':
                    raise osv.except_osv('Error', 'Only active coupons can be printed!')

        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        partner = user.company_id.partner_id

        self.localcontext.update({
            'time': time,
            'partner': partner or False,
            'user': user or False,
        })


class wrapped_report_fuel_coupon(osv.AbstractModel):
    _name = 'report.fleet_x_fuel.report_fuel_coupon'
    _inherit = 'report.abstract_report'
    _template = 'fleet_x_fuel.report_fuel_coupon'
    _wrapped_report_class = fuel_coupon_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
