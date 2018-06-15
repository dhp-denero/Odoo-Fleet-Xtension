# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

from datetime import datetime

# --------------
#  Vehicle Drivers
# --------------


class fleet_driver(models.Model):

    _name = 'fleet.driver'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['ir.needaction_mixin', 'mail.thread']

    partner_id = fields.Many2one('res.partner', required=True, ondelete="cascade")
    identification_no = fields.Char('Identification #')
    date_hired = fields.Date('Hire Date', help='Date when the driver is hired',
                             required=True, track_visibility='onchange')
    date_terminated = fields.Date('Terminated Date',
                                  help='Date when the driver is terminated from job',
                                  track_visibility='onchange', readonly=True)
    date_license_exp = fields.Date('License exp. Date', help='Date when license expires',
                                   required=False, track_visibility='onchange',
                                   inverse="_set_date_license_exp")
    dob = fields.Date('Date of Birth')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Vehicle", index=1,
        track_visibility='onchange'
    )
    state = fields.Selection([('draft', 'Draft'),
                              ('unassigned', 'Unassigned'),
                              ('assigned', 'Assigned'),
                              ('license_exp', 'License Expired'),
                              ('terminated', 'Terminated')], 'State',
                             default='draft')
    previous_assignment_ids = fields.One2many('fleet.driver.assignment', 'driver_id',
                                              "Previous Vehicles", readonly=True, inverse="_compute_vehicle")
    previous_assignment_count = fields.Integer('Assignment Count',
                                               compute='_get_assignment_count',
                                               readonly=True)
    attachment_count = fields.Integer(string='Number of Attachments',
                                      compute='_get_attachment_number')
    license_no = fields.Char('License Number', required=True)
    issue_ids = fields.One2many('fleet.vehicle.issue', 'driver_id', 'Issues',
                                readonly=True)
    issue_count = fields.Integer('Issue Count', compute='_get_issue_count',
                                 readonly=True)
    location_id = fields.Many2one('fleet.vehicle.location', 'Operational Location',
                                  related="vehicle_id.location_id", store=True)

    @api.multi
    @api.depends('previous_assignment_ids')
    def _get_assignment_count(self):
        for rec in self:
            rec.previous_assignment_count = len(rec.previous_assignment_ids)

    @api.multi
    def _get_attachment_number(self):
        '''
        returns the number of attachments attached to a record
        FIXME: not working well for classes that inherits from this
        '''
        for rec in self:
            rec.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', rec._name),
                ('res_id', '=', rec.id)]
            )

    @api.multi
    def action_get_attachment_tree_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'fleet.driver'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'fleet.driver', 'default_res_id': self.ids[0]}
        return res

    @api.multi
    @api.depends('issue_ids')
    def _get_issue_count(self):
        for rec in self:
            rec.issue_count = len(rec.issue_ids)

    @api.multi
    @api.depends('previous_assignment_ids')
    def _compute_vehicle(self):
        for rec in self:
            if rec.previous_assignment_ids:
                rec.vehicle_id = rec.previous_assignment_ids[0].vehicle_id
            else:
                rec.vehicle_id = False

    @api.multi
    def _set_date_license_exp(self):
        for rec in self:
            if rec.state == 'license_exp' and fields.Date.from_string(rec.date_license_exp) > datetime.now().date():
                if len(rec.vehicle_id):
                    rec.state = 'assigned'
                else:
                    rec.state = 'unassigned'

    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env['res.users'].has_group('fleet_x.fleet_group_manager'):
            domain = [('state', '=', 'license_exp')]
        return domain

    @api.multi
    def _cron_drvLic_update(self):
        """
        Updating all the drivers with expired license.
        --------,
        """
        # usage of self not working here. api.multi required?
        driver_obj = self.env['fleet.driver']
        recs = driver_obj.search([('date_license_exp', '<=', fields.Date.today())])
        recs.write({'state': 'license_exp'})
        return True

    @api.multi
    def action_unassign(self):
        for driver in self:
            driver.write({'state': 'unassigned'})
            driver.vehicle_id = False
            assignment_ids = self.env['fleet.driver.assignment'].search([('driver_id', '=', driver.id)])
            if assignment_ids:
                assignment_ids.unlink()
        return True

    @api.multi
    def action_assign_vehicle(self, vehicle_id, vtype=False):
        for driver in self:
            driver.action_assign()
            if vehicle_id:
                self.env['fleet.driver.assignment'].create({
                    'vehicle_id': vehicle_id.id,
                    'driver_id': driver.id,
                    'date_start': fields.Date.today(),
                    'type': vtype
                })
        return True

    @api.multi
    def action_unassign_vehicle(self):
        for driver in self:
            driver.action_unassign()
        return True

    @api.multi
    def action_confirm(self):
        for driver in self:
            if len(driver.vehicle_id) > 0:
                driver.state = 'assigned'
            else:
                driver.state = 'unassigned'

    @api.multi
    def action_assign(self):
        return self.write({'state': 'assigned'})

    @api.multi
    def action_license_exp(self):
        return self.write({'state': 'license_exp'})

    @api.multi
    def action_terminate(self):
        self.action_unassign()
        return self.write({'state': 'terminated', 'date_terminated': fields.Date.today(), 'active': False})

    @api.multi
    def action_reactivate(self):
        self.action_confirm()
        return self.write({'date_terminated': None, 'active': True})

    # def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
    #     fields_to_hide = []  # let's hide res parter field that we do not want
    #     res = super(fleet_driver, self).fields_get(cr, uid, fields, context)
    #     for field in fields_to_hide:
    #         res[field]['selectable'] = False
    #     return res


# --------------
# Fleet Vehicle
# --------------
class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"

    @api.multi
    @api.depends('previous_assignment_ids')
    def _get_assignment_count(self):
        for rec in self:
            rec.previous_assignment_count = len(rec.previous_assignment_ids)

    @api.multi
    @api.constrains('vehicle_driver_id', 'alt_vehicle_driver_id')
    def _check_drivers(self):
        for rec in self:
            if rec.vehicle_driver_id and rec.alt_vehicle_driver_id and rec.vehicle_driver_id.id == rec.alt_vehicle_driver_id.id:
                raise UserError('Primary and Alternate drivers can not be the same')

    @api.multi
    def _set_driver(self):
        assignment_obj = self.env['fleet.driver.assignment']
        domain = [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'primary')]
        drivers = assignment_obj.search(domain)
        if len(self.vehicle_driver_id) == 0:
            if len(drivers) == 0:
                return
            else:
                drivers[0].date_end = fields.Date.today()
                drivers[0].odometer_end = self.odometer
                drivers[0].driver_id.state = 'unassigned'
            return
        if len(drivers):
            drivers[0].date_end = fields.Date.today()
            drivers[0].odometer_end = self.odometer

    @api.multi
    def _set_alt_driver(self):
        assignment_obj = self.env['fleet.driver.assignment']
        domain = [('vehicle_id', '=', self.id), ('date_end', 'in', (None, False)), ('type', '=', 'secondary')]
        drivers = assignment_obj.search(domain)
        if len(self.alt_vehicle_driver_id) == 0:
            if len(drivers) == 0:
                return
            else:
                drivers[0].date_end = fields.Date.today()
                drivers[0].odometer_end = self.odometer
            return

        if len(drivers):
            drivers[0].date_end = fields.Date.today()
            drivers[0].odometer_end = self.odometer

    vehicle_driver_id = fields.Many2one('fleet.driver', 'Primary Driver',
                                        help='Primary driver of the vehicle',
                                        track_visibility='onchange',
                                        inverse="_set_driver",
                                        domain=[('state', '=', 'unassigned')])
    alt_vehicle_driver_id = fields.Many2one('fleet.driver', 'Secondary Driver',
                                            help='Secondary driver of the vehicle',
                                            track_visibility='onchange',
                                            inverse="_set_alt_driver",
                                            domain=[('state', '=', 'unassigned')])
    driver_id = fields.Many2one('res.partner', 'Driver', help='Driver of the vehicle',
                                related='vehicle_driver_id.partner_id',
                                readonly=True, required=False, store=True)
    previous_assignment_ids = fields.One2many(
        'fleet.driver.assignment', 'vehicle_id',
        "Previous Drivers", readonly=True)
    previous_assignment_count = fields.Integer(string='Assignment History',
                                               compute='_get_assignment_count',
                                               readonly=True)

    @api.multi
    def write(self, vals):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        context = dict(self.env.context or {})
        for vehicle in self:
            if not context.get('assignment', False):
                if 'vehicle_driver_id' in vals:
                    if vehicle.vehicle_driver_id:
                        vehicle.vehicle_driver_id.action_unassign_vehicle()

                    if vals.get('vehicle_driver_id', False):
                        vehicle_driver_id = self.env['fleet.driver'].browse([vals.get('vehicle_driver_id')])
                        if vehicle_driver_id:
                            vehicle_driver_id.action_assign_vehicle(vehicle, 'primary')

                if 'alt_vehicle_driver_id' in vals:
                    if vehicle.alt_vehicle_driver_id:
                        vehicle.alt_vehicle_driver_id.action_unassign_vehicle()

                    if vals.get('alt_vehicle_driver_id', False):
                        alt_vehicle_driver_id = self.env['fleet.driver'].browse([vals.get('alt_vehicle_driver_id')])
                        if alt_vehicle_driver_id:
                            alt_vehicle_driver_id.action_assign_vehicle(vehicle, 'secondary')
        return super(fleet_vehicle, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(fleet_vehicle, self).create(vals)
        if 'vehicle_driver_id' in vals:
            if res.vehicle_driver_id:
                res.vehicle_driver_id.action_unassign_vehicle()

            if res.vehicle_driver_id:
                res.vehicle_driver_id.action_assign_vehicle(res, 'primary')

        if 'alt_vehicle_driver_id' in vals:
            if res.alt_vehicle_driver_id:
                res.alt_vehicle_driver_id.action_unassign_vehicle()

            if res.alt_vehicle_driver_id:
                res.alt_vehicle_driver_id.action_assign_vehicle(res, 'secondary')
        return res


class fleet_driver_assignment(models.Model):
    _name = 'fleet.driver.assignment'
    _order = 'date_start DESC, id DESC'

    vehicle_id = fields.Many2one(
        'fleet.vehicle', 'Vehicle', required=True,
    )
    driver_id = fields.Many2one(
        'fleet.driver', 'Driver', required=True,
        domain=[
            ('state', '=', 'unassigned')
        ]
    )
    date_start = fields.Date('Start Date', required=True, help='Vehicle assignment start-date')
    date_end = fields.Date('End Date', help='Vehicle assignment end-date', default=False)
    notes = fields.Text('Notes')
    odometer_start = fields.Float('Odometer at Start', readonly=True)
    odometer_end = fields.Float('Odometer at Finish', readonly=True)
    type = fields.Selection([('primary', 'Primary'), ('secondary', 'Secondary')], required=True, default='primary')

    @api.multi
    def write(self, vals):
        for assignment in self:
            if 'vehicle_id' in vals or 'driver_id' in vals or 'type' in vals:
                vehicle_id = vals.get('vehicle_id', assignment.vehicle_id and assignment.vehicle_id.id or False)
                driver_id = vals.get('driver_id', assignment.driver_id and assignment.driver_id.id or False)
                type = vals.get('type', assignment.type)
                vehicle_id = self.env['fleet.vehicle'].browse([vehicle_id])
                if vehicle_id:
                    if type == 'secondary':
                        vehicle_id.with_context({'assignment': True}).write({
                            'alt_vehicle_driver_id': driver_id,
                        })
                    else:
                        vehicle_id.with_context({'assignment': True}).write({
                            'vehicle_driver_id': driver_id,
                        })
            if vals.get('driver_id', False):
                driver_id = self.env['fleet.driver'].browse([driver_id])
                assignment.driver_id.write({'state': 'unassigned'})
                driver_id.action_assign()
            if vals.get('type', False):
                vehicle_id = vals.get('vehicle_id', assignment.vehicle_id and assignment.vehicle_id.id or False)
                driver_id = vals.get('driver_id', assignment.driver_id and assignment.driver_id.id or False)
                if driver_id:
                    driver_id = self.env['fleet.driver'].browse([driver_id])
                if vehicle_id:
                    vehicle_id = self.env['fleet.vehicle'].browse([vehicle_id])
                    if vals.get('type') == 'primary':
                        if vehicle_id.vehicle_driver_id:
                            raise UserError('Vehicle is already assigned to another driver of this same type')

                    if vals.get('type') == 'secondary':
                        if vehicle_id.alt_vehicle_driver_id:
                            raise UserError('Vehicle is already assigned to another driver of this same type')

                assignment.driver_id.write({'state': 'unassigned'})
                driver_id.action_assign()
                driver_id.vehicle_id = vals.get('vehicle_id', assignment.vehicle_id and assignment.vehicle_id.id or False)
        return super(fleet_driver_assignment, self).write(vals)

    @api.model
    def create(self, data):
        res = super(fleet_driver_assignment, self).create(data)
        res.odometer_start = res.vehicle_id and res.vehicle_id.odometer or 0.0
        vehicle_obj = self.env['fleet.vehicle'].browse(res.vehicle_id.id)
        if vehicle_obj:
            if not vehicle_obj.vehicle_driver_id and res.type == 'primary':
                vehicle_obj.with_context({'assignment': True}).write({'vehicle_driver_id': res.driver_id.id})
                res.driver_id.action_assign()
                res.driver_id.vehicle_id = res.vehicle_id.id or False
            if not vehicle_obj.alt_vehicle_driver_id and res.type == 'secondary':
                vehicle_obj.with_context({'assignment': True}).write({'alt_vehicle_driver_id': res.driver_id.id})
                res.driver_id.action_assign()
                res.driver_id.vehicle_id = res.vehicle_id.id or False
        return res

    @api.one
    @api.constrains('driver_id', 'vehicle_id')
    def _check_driver_assign(self):
        domain = [
            ('driver_id', '=', self.driver_id.id),
            ('id', '!=', self.id),
            ('vehicle_id', '!=', self.vehicle_id.id),
            '|',
            ('date_end', 'in', (False, None)),
            ('date_end', '>', self.date_start),
        ]
        if self.search_count(domain):
            raise UserError('Driver is already assigned to another vehicle')

        domain = [

            ('vehicle_id', '=', self.vehicle_id.id),
            ('id', '!=', self.id),
            ('driver_id', '!=', self.driver_id.id),
            ('type', '=', self.type),
            '|',
            ('date_end', 'in', (False, None)),
            ('date_end', '>', self.date_start),
        ]
        if self.search_count(domain):
            raise UserError('Vehicle is already assigned to another driver of this same type')


class fleet_vehicle_issue(models.Model):
    _inherit = 'fleet.vehicle.issue'

    driver_id = fields.Many2one('fleet.driver', 'Responsible',
                                required=True, readonly=True,
                                domain=[('state', 'not in', ('draft', 'terminated'))],
                                states={'draft': [('readonly', False)]})
