# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class fleet_config_settings(models.TransientModel):
    _inherit = 'fleet.config.settings'

    default_repair_scheduling_interval = fields.Selection([
        ('odometer', 'Odometer'),
        ('time', 'Time'),
        ('both', 'Both')],
        string='Scheduling Interval',
        default="both"
    )
    default_repair_scheduling_time = fields.Integer(
        'Interval (Mnths)',
        help="Interval between each servicing in months",
        default=3
    )
    default_repair_scheduling_odometer = fields.Integer(
        'Interval (Odometer)',
        help="Interval between each servicing in months",
        default=5000
    )
    default_repair_scheduling_notice = fields.Integer(
        'Notice (days)',
        help="How many days before date of schedule should notices be generated",
        default=7
    )

    @api.model
    def get_default_repair_scheduling_interval(self, fields):
        IrConfigParam = self.env['ir.config_parameter']
        res = {
            'default_repair_scheduling_interval': safe_eval(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_interval', 'False') or False),
            'default_repair_scheduling_time': int(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_time', 0)) or 0,

            'default_repair_scheduling_odometer': int(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_odometer', 0)) or 0,
            'default_repair_scheduling_notice': int(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_notice', 0)) or 0
        }
        return res

    @api.multi
    def set_default_repair_scheduling_interval(self):
        self.ensure_one()
        IrConfigParam = self.env['ir.config_parameter']
        IrConfigParam.set_param(
            'fleet_x_service.default_repair_scheduling_interval',
            repr(self.default_repair_scheduling_interval or False)
        )
        IrConfigParam.set_param(
            'fleet_x_service.default_repair_scheduling_time',
            self.default_repair_scheduling_time or 0
        )
        IrConfigParam.set_param(
            'fleet_x_service.default_repair_scheduling_odometer',
            self.default_repair_scheduling_odometer or 0
        )
        IrConfigParam.set_param(
            'fleet_x_service.default_repair_scheduling_notice',
            self.default_repair_scheduling_notice or 0
        )
