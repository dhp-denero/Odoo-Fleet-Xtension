# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.safe_eval import safe_eval


class fleet_config_settings(models.TransientModel):
    _name = 'fleet.config.settings'
    _inherit = 'fleet.config.settings'

    default_coupon_creation = fields.Boolean(
        'Automatic Coupon Creation',
        help="Automatically create coupons based on fueling policy",
        default=False
    )
    default_price_per_lt = fields.Float('Fuel Price per Liter', default=3750.00)
    default_efficiency_alert_buffer = fields.Float('Fuel Efficiency Alert Buffer', help='Alerts managers to fuel log efficiency that if \
     this amount greater than or lesser than average')

    @api.model
    def get_default_coupon_creation(self, fields):
        IrConfigParam = self.env['ir.config_parameter']
        res = {
            'default_coupon_creation': safe_eval(IrConfigParam.get_param('fleet_x_driver.default_coupon_creation', 'False') or False),
            'default_price_per_lt': safe_eval(IrConfigParam.get_param('fleet_x_driver.default_price_per_lt', 'False') or 0.0),
            'default_efficiency_alert_buffer': safe_eval(IrConfigParam.get_param('fleet_x_driver.default_efficiency_alert_buffer', 'False') or 0.0),
        }
        return res

    @api.multi
    def set_default_coupon_creation(self):
        self.env["ir.config_parameter"].set_param(
            "fleet_x_driver.default_coupon_creation",
            repr(self.default_coupon_creation or False)
        )
        self.env["ir.config_parameter"].set_param(
            "fleet_x_driver.default_price_per_lt",
            self.default_price_per_lt or 0.0
        )
        self.env["ir.config_parameter"].set_param(
            "fleet_x_driver.default_efficiency_alert_buffer",
            self.default_efficiency_alert_buffer or 0.0
        )
