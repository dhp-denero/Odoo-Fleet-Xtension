# -*- coding: utf-8 -*-
from odoo import models


class fleet_config_settings(models.TransientModel):
    _name = 'fleet.config.settings'
    _inherit = 'res.config.settings'


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
