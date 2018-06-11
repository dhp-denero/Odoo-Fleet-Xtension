# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.safe_eval import safe_eval


class fleet_config_settings(models.TransientModel):
    _inherit = 'fleet.config.settings'

    default_analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
    )
    default_account_debit = fields.Many2one(
        'account.account', 'Debit Account',
    )
    default_account_credit = fields.Many2one(
        'account.account', 'Credit Account',
    )
    default_journal_id = fields.Many2one('account.journal', 'Journal')

    @api.model
    def get_default_default_analytic_account_id(self, fields):
        # res = self.env["ir.config_parameter"].get_param("fleet_x_account.default_analytic_account_id")
        # self.default_analytic_account_id = res or None
        IrConfigParam = self.env['ir.config_parameter']
        res = {
            'default_analytic_account_id': safe_eval(IrConfigParam.get_param('fleet_x_account.default_analytic_account_id', 'False') or False),
            'default_account_debit': safe_eval(IrConfigParam.get_param('fleet_x_account.default_account_debit', 'False') or False),

            'default_account_credit': safe_eval(IrConfigParam.get_param('fleet_x_account.default_account_credit', 'False') or False),
            'default_journal_id': safe_eval(IrConfigParam.get_param('fleet_x_account.default_journal_id', 'False') or False)
        }
        return res

    @api.multi
    def set_default_analytic_account_id(self):
        self.env["ir.config_parameter"].set_param(
            "fleet_x_account.default_analytic_account_id",
            repr(self.default_analytic_account_id.id or False)
        )
        self.env["ir.config_parameter"].set_param(
            "fleet_x_account.default_account_debit",
            repr(self.default_account_debit.id or False)
        )
        self.env["ir.config_parameter"].set_param(
            "fleet_x_account.default_account_credit",
            repr(self.default_account_credit.id or False)
        )
        self.env["ir.config_parameter"].set_param(
            "fleet_x_account.default_journal_id",
            repr(self.default_journal_id.id or False)
        )
