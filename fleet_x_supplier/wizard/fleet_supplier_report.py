
from odoo import fields, models, api, _


class wizard_report_fleet_supplier(models.TransientModel):

    _name = 'wizard.report.fleet.supplier'
    _description = 'Wizard that opens supplier cost logs'

    vendor_id = fields.Many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]", required=True)
    choose_date = fields.Boolean('Choose a Particular Period')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    _defaults = {
        'choose_date': False,
        'date_to': fields.date.today()
    }

    @api.multi
    def open_table(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        ctx = context.copy()
        domain = [('vendor_id', '=', data['vendor_id'][0])]
        if data['choose_date']:
            from_date = data['date_from']
            to_date = data['date_to']
            domain = [('vendor_id', '=', data['vendor_id'][0]), ('date', '>=', from_date), ('date', '<=', to_date)]
        return {
            'domain': domain,
            'name': _('Cost Logs'),
            'view_type': 'form',
            'view_mode': 'tree,graph',
            'res_model': 'report.fleet.supplier',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }
