# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class fleet_vehicle_type(models.Model):

    _name = "fleet.vehicle.type"

    name = fields.Char('Name', requried=True, selectable=False)


class fleet_vehicle_odometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    _order = 'value desc'

    def _get_neighbours(self):
        '''
        get the odometer reading
        @todo: since this field is stored, we should recompute in instances of
        another reading being inserted just before this
        '''
        previous = self.search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('id', '!=', self.id),
            ('date', '<=', self.date)],
            limit=1,
            order='date desc,value desc'
        )
        next = self.search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('id', '!=', self.id),
            ('date', '>=', self.date)],
            limit=1, order='date asc,value asc'
        )
        return previous, next

    @api.constrains('value')
    def _check_meter_value(self):
        '''
        let's ensure that odo value increases with every new one logged
        '''
        previous, next = self._get_neighbours()
        if len(previous) and previous.value > self.value:
            raise UserError('Odometer reading can not be lesser than the last recorded odometer reading for this vehicle')
        # if len(next) and next.value < self.value:
        #     raise UserError('Odometer reading can not be greater than the next recorded odometer reading for this vehicle')
        return True


class fleet_vehicle_location(models.Model):

    _name = "fleet.vehicle.location"

    name = fields.Char('Name', required=True)


class fleet_vehicle_department(models.Model):

    _name = 'fleet.vehicle.department'

    @api.one
    @api.depends("vehicle_ids")
    def _get_vehicle_count(self):
        self.vehicle_count = len(self.vehicle_ids)

    @api.one
    @api.depends('name', 'parent_id')
    def _dept_name_get_fnc(self):
        name = self.name
        if self.parent_id:
            name = self.parent_id.name + ' / ' + name
        self.display_name = name

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute='_dept_name_get_fnc', string='Name', store=True)
    vehicle_ids = fields.One2many('fleet.vehicle', 'department_id', 'Vehicles')
    vehicle_count = fields.Integer('Vehicle Count', compute="_get_vehicle_count")
    parent_id = fields.Many2one('fleet.vehicle.department', 'Parent Department', select=True)
    child_ids = fields.One2many('fleet.vehicle.department', 'parent_id', 'Child Departments')
    note = fields.Text('Note')

    @api.multi
    def name_get(self):
        result = []
        for department in self:
            result.append((department.id, department.display_name))
        return result

    @api.constrains('parent_id')
    @api.multi
    def _check_recursion(self):
        level = 100
        cr = self.env.cr
        while len(self.ids):
            cr.execute('select distinct parent_id from fleet_vehicle_department where id IN %s', (tuple(self.ids),))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True


class FleetVehicleStateInherit(models.Model):
    _inherit = 'fleet.vehicle.state'

    active = fields.Boolean('Active', default=True)


class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"

    def _get_default_state(self):
        state = self.env.ref('fleet.vehicle_state_active', raise_if_not_found=False)
        if not state:
            state = self.env['fleet.vehicle.state'].search([('name', '=', 'Active')])
        return state and state.id or False

    odometer_ids = fields.One2many(
        'fleet.vehicle.odometer', 'vehicle_id',
        'Odometers', readonly=1
    )
    cost_ids = fields.One2many(
        'fleet.vehicle.cost', 'vehicle_id',
        'Cost', readonly=1
    )
    department_id = fields.Many2one(
        'fleet.vehicle.department', 'Department',
        help='Department of the vehicle',
        index=1, track_visibility='onchange'
    )
    attachment_count = fields.Integer(
        string='Number of Attachments',
        compute='_get_attachment_number'
    )
    note = fields.Text('Internal Note')
    active = fields.Boolean('Active', default=True, index=True)

    odometer_date = fields.Date(
        'Odometer Date',
        readonly=True,
        compute='_get_odometer_date',
        store=False
    )

    # properties
    manufacture_year = fields.Char('Year of Manufacture', size=4)
    ownership = fields.Selection([
        ('owned', 'Owned'),
        ('private', 'Private (owned by employee)'),
        ('leased', 'Leased'),
        ('rented', 'Rented'),
    ], 'Ownership', required=False, default="owned")
    fueltankcap = fields.Float('Fuel Tank Capacity')
    acquisition_date = fields.Date(
        'Acquisition Date', required=True,
        help='Date of purchase',
        default=fields.Date.today())
    type_id = fields.Many2one('fleet.vehicle.type', 'Type', required=True)
    location_id = fields.Many2one(
        'fleet.vehicle.location',
        'Operational Location'
    )

    # statistics
    lmiles = fields.Float('Kilometers per year', compute="_compute_vehicle_stats",
                          readonly=True, store=True)
    distance = fields.Float('Distance covered since purchase',
                            compute="_compute_vehicle_stats", readonly=True, store=True)
    costpm = fields.Float('Cost/KM', compute="_compute_vehicle_stats",
                          readonly=True, store=True)
    costpmon = fields.Float('Cost/Mnth', compute="_compute_vehicle_stats",
                            readonly=True, store=True)
    costtotal = fields.Float('Total Cost', compute="_compute_vehicle_stats",
                             readonly=True, store=True)

    # purchase info
    ppartner = fields.Many2one('res.partner', 'Purchased From',
                               domain="[('supplier','=',True)]")
    car_value = fields.Float('Purchase Price', help='Value of the bought vehicle')
    podometer = fields.Integer('Odometer at Purchase',
                               inverse="_set_odometer_at_purchase")
    warrexp = fields.Date('Date', help="Expiry date of warranty")
    warrexpmil = fields.Integer('(or) Kilometer', help="Expiry Kilometer of warranty")
    state_id = fields.Many2one('fleet.vehicle.state', 'State', default=_get_default_state, help='Current state of the vehicle', ondelete="set null")

    _sql_constraints = [
        ('uniq_license_plate', 'unique(license_plate)', 'The registration # of the vehicle must be unique !'),
        ('uniq_vin', 'unique(vin_sn)', 'The Chassis # of the vehicle must be unique !')
    ]

    @api.multi
    def _get_odometer_date(self):
        # date of last odometer reading
        for rec in self:
            if len(rec.odometer_ids):
                rec.odometer_date = rec.odometer_ids.sorted(lambda r: r.value)[-1].date

    @api.multi
    @api.depends('acquisition_date', 'podometer', 'odometer', 'odometer_ids', 'cost_ids', 'cost_ids.amount')
    def _compute_vehicle_stats(self):
        for rec in self:
            if not isinstance(rec.id, int):
                return
            costpm = 0.0
            costpmon = 0.0
            costtotal = 0.0
            if not len(rec.odometer_ids):
                return
            # odoo_delta = rec.odometer - rec.odometer_ids.sorted(lambda r: r.value)[0].value
            odoo_delta = rec.odometer - rec.podometer
            if odoo_delta <= 0:
                return
            rec.distance = odoo_delta
            if not len(rec.cost_ids) or not rec.acquisition_date:
                return

            time_delta = relativedelta(datetime.now(), fields.Date.from_string(rec.acquisition_date))
            # distance traveled since the first odometer was logged

            for cost in rec.cost_ids:
                costtotal += cost.amount

            months = (time_delta.years * 12) + time_delta.months
            costpmon = months and costtotal / months or costtotal
            costpm = costtotal / odoo_delta

            rec.costpm = costpm
            rec.costpmon = costpmon
            rec.costtotal = costtotal
            rec.lmiles = (time_delta.years > 1) and odoo_delta / time_delta.years or odoo_delta

    @api.multi
    def _set_odometer_at_purchase(self):
        for rec in self:
            if not len(rec.odometer_ids):
                self.env['fleet.vehicle.odometer'].create({
                    'value': rec.podometer,
                    'vehicle_id': rec.id,
                    'date':  rec.acquisition_date
                })
            else:
                first = rec.odometer_ids[-1]
                first_dt = fields.Date.from_string(first.date)
                acquisition_dt = fields.Date.from_string(rec.acquisition_date)
                if first_dt <= acquisition_dt:
                    first.write({
                        'value': rec.podometer,
                        'date': rec.acquisition_date})
                else:
                    self.env['fleet.vehicle.odometer'].create({
                        'value': rec.podometer,
                        'vehicle_id': rec.id,
                        'date':  rec.acquisition_date
                    })

    @api.one
    def _get_attachment_number(self):
        '''
        returns the number of attachments attached to a record
        FIXME: not working well for classes that inherits from this
        '''
        self.attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', self._name),
                                                                        ('res_id', '=', self.id)])

    @api.multi
    def action_get_attachment_tree_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'fleet.vehicle'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'fleet.vehicle', 'default_res_id': self.ids[0]}
        return res


class fleet_vehicle_model(models.Model):
    _inherit = 'fleet.vehicle.model'
    vendors = fields.Many2many(
        'res.partner',
        'fleet_vehicle_model_vendors',
        'model_id',
        'partner_id',
        string='Vendors',
        domain="[('supplier','=',True)]"
    )

# --------------
# Vehicle Department
# --------------


class fleet_vehicle_cost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    ref = fields.Char(readonly=True)
    vehicle_type_id = fields.Many2one('fleet.vehicle.type', 'Vehicle Type', related='vehicle_id.type_id', readonly=True, store=True)
    vehicle_location_id = fields.Many2one('fleet.vehicle.location', 'Vehicle Location', related='vehicle_id.location_id', readonly=True, store=True)

    @api.model
    def create(self, data):
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(data['parent_id'])
            vehicle = parent.vehicle_id
            data['ref'] = '%s-%s' % (vehicle.license_plate, self.env['ir.sequence'].next_by_code('fleet.vehicle.cost.ref'))
            # vehicle = self.env['fleet.vehicle'].browse(data['vehicle_id'])
        return super(fleet_vehicle_cost, self).create(data)
