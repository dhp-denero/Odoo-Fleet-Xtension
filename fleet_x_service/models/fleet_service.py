# -*- coding: utf-8 -*-
import operator

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from odoo.tools.safe_eval import safe_eval


class fleet_service_type(models.Model):
    _inherit = 'fleet.service.type'

    parent_id = fields.Many2one('fleet.service.type', 'Parent')
    display_name = fields.Char(compute='_service_name_get_fnc', string='Name', store=False)

    @api.one
    @api.depends('name', 'parent_id')
    def _service_name_get_fnc(self):
        name = self.name
        if self.parent_id:
            name = self.parent_id.name + ' / ' + name
        self.display_name = name

    @api.multi
    def name_get(self):
        result = []
        for service in self:
            result.append((service.id, service.display_name))
        return result

    @api.constrains('parent_id')
    @api.multi
    def _check_recursion(self):
        level = 100
        cr = self.env.cr
        while len(self.ids):
            cr.execute('select distinct parent_id from fleet_service_type where id IN %s', (tuple(self.ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True


class fleet_service_schedule(models.Model):
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _name = "fleet.service.schedule"
    _order = "date asc"

    @api.model
    def _get_date_deadline(self):
        IrConfigParam = self.env['ir.config_parameter']
        value = safe_eval(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_notice', 'False') or 0.0)
        scheduled_date = datetime.now().date() + timedelta(days=value or 10)
        return fields.Date.to_string(scheduled_date)

    name = fields.Char('Reference', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    date = fields.Datetime('Scheduled On', required=True, default=fields.Date.today())
    date_deadline = fields.Datetime('Deadline', required=True, default=_get_date_deadline)
    date_closed = fields.Datetime('Closed Date')
    state = fields.Selection([('open', 'Open'),
                              ('overdue', 'Overdue'),
                              ('done', 'Done'),
                              ('cancel', 'Cancel')], default='open')
    service_log_id = fields.Many2one('fleet.vehicle.log.services', 'Service Log', readonly=True, inverse='_set_service_id')
    note = fields.Text('Description')
    auto_generated = fields.Boolean()
    cost_subtype_id = fields.Many2one('fleet.service.type', 'Service Type', required=True)
    maintenance_id = fields.Many2one('fleet.service.maintenance', 'Maintenance',)

    @api.one
    @api.constrains('date_deadline', 'date')
    def _check_date(self):
        if self.date_deadline and self.date and \
                fields.Date.from_string(self.date_deadline) < fields.Date.from_string(self.date):
            raise UserError('Deadline cannot be before the date of creation')
        return True

    @api.model
    def _cron_update_overdue(self):
        res_ids = self.search([('state', '=', 'open'),
                               ('date_deadline', '<', fields.Date.today())])
        res_ids.write({'state': 'overdue'})

    @api.one
    def _set_service_id(self):
        if len(self.service_log_id):
            self.action_done()

    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.schedule.ref')
        return super(fleet_service_schedule, self).create(data)

    @api.model
    def _needaction_domain_get(self):
        """
        Getting a head count of all the drivers with expired license.
        This will be shown in the menu item for drivers,
        """
        domain = []
        if self.env.user.has_group('fleet.fleet_group_user'):
            domain = [('state', '=', 'open')]
        return domain

    @api.multi
    def action_done(self):
        for schedule in self:
            if not len(schedule.service_log_id):
                raise UserError('No associated service log found for this schedule and so cannot mark as closed')
            schedule.write({'state': 'done', 'date_closed': schedule.date_closed or fields.Date.today()})

    @api.multi
    def action_cancel(self):
        for schedule in self:
            schedule.write({'state': 'cancel', 'date_closed': schedule.date_closed or fields.Date.today()})

    @api.multi
    def action_log_service(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        compose_form = self.env.ref('fleet.fleet_vehicle_log_services_view_form', False)
        ctx = dict(
            default_schedule_id=self.id,
            default_vehicle_id=self.vehicle_id.id,
            default_odometer=self.vehicle_id.odometer,
            default_schedule_log_date=self.date,
            default_cost_subtype_id=self.cost_subtype_id.id,
        )
        if self.auto_generated:
            self.env['fleet.vehicle.log.services'].create({
                'schedule_id': self.id,
                'vehicle_id': self.vehicle_id.id,
                'odometer': self.vehicle_id.odometer,
                'schedule_log_date': self.date,
                'cost_subtype_id': self.cost_subtype_id.id,
            })
        else:
            return {
                'name': _('Log Service History'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'fleet.vehicle.log.services',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'context': ctx,
            }


class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"

    @api.model
    def _get_default_scheduling_interval(self):
        IrConfigParam = self.env['ir.config_parameter']
        value = safe_eval(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_interval', 'False') or 0.0)
        return value or 'odometer'

    @api.model
    def _get_default_scheduling_time(self):
        IrConfigParam = self.env['ir.config_parameter']
        value = safe_eval(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_time', 'False') or 0.0)
        return value or 3

    @api.model
    def _get_default_scheduling_odometer(self):
        IrConfigParam = self.env['ir.config_parameter']
        value = safe_eval(IrConfigParam.get_param('fleet_x_service.default_repair_scheduling_odometer', 'False') or 0.0)
        return value or 5000

    last_service_id = fields.Many2one('fleet.vehicle.log.services', 'Last Service Log',
                                      readonly=True, store=True, compute="_compute_last_service")
    last_service_date = fields.Date('Last Serviced On', readonly=True, store=True,
                                    related='last_service_id.date')
    last_service_odometer = fields.Float(
        'Last Service Odometer', readonly=True, store=True,
        related='last_service_id.odometer')
    next_service_date = fields.Date('Next Service On', readonly=True, store=True,
                                    compute='_compute_next_service_details')
    next_service_odometer = fields.Float(
        'Next Service Odometer', readonly=True, store=True,
        compute='_compute_next_service_details')

    repair_scheduling_interval = fields.Selection(
        [
            ('odometer', 'Odometer'),
            ('time', 'Time'),
            ('both', 'Both')
        ],
        'Scheduling Interval',
        default=_get_default_scheduling_interval)
    repair_scheduling_time = fields.Integer('Interval (Mnths)',
                                            help="Interval between each servicing in months",
                                            default=_get_default_scheduling_time)
    repair_scheduling_odometer = fields.Integer('Interval (odometer)',
                                                help="Interval between each servicing in months",
                                                default=_get_default_scheduling_odometer)
    schedule_ids = fields.Many2one('fleet.service.schedule', 'schedules', domain=[('state', '=', 'open')])
    schedule_count = fields.Integer('schedule Count', readonly=True, compute="_get_schedule_count")
    service_maintenance_ids = fields.One2many(
        'fleet.service.maintenance', 'vehicle_id', 'Service Maintenance'
    )

    @api.multi
    @api.depends('log_services', 'log_services.vehicle_id', 'log_services.date')
    def _compute_last_service(self):
        for rec in self:
            logs = rec.log_services.sorted(key=operator.itemgetter('date', 'odometer', 'id'))
            rec.last_service_id = logs and logs[-1] or False

    @api.multi
    @api.depends(
        'last_service_id',
        'log_services',
        'repair_scheduling_time',
        'repair_scheduling_odometer',
        'last_service_odometer'
    )
    def _compute_next_service_details(self):
        for rec in self:
            last_date = rec.last_service_date and fields.Date.from_string(rec.last_service_date) or date.today()
            last_odometer = rec.last_service_odometer or rec.odometer
            next_dt = last_date + relativedelta(months=rec.repair_scheduling_time)
            rec.next_service_date = fields.Date.to_string(next_dt)
            rec.next_service_odometer = last_odometer + rec.repair_scheduling_odometer

    @api.multi
    def _get_schedule_count(self):
        for rec in self:
            rec.schedule_count = rec.env['fleet.service.schedule'].search_count(
                [
                    ('vehicle_id', '=', rec.id),
                    ('state', 'in', ['open', 'overdue'])
                ]
            )

    @api.model
    def _cron_schedule_repairs(self):
        service_obj = self.env['fleet.vehicle.log.services']
        res_ids = []
        for vehicle in self.search([]):
            if vehicle.repair_scheduling_interval == 'odometer' and vehicle.odometer >= vehicle.next_service_odometer:
                res_ids.append(vehicle.id)
            elif vehicle.repair_scheduling_interval == 'time' and \
                    fields.Date.from_string(vehicle.next_service_date) <= date.today():
                res_ids.append(vehicle.id)
            elif vehicle.repair_scheduling_interval == 'both':
                res_ids.append(vehicle.id)
        if res_ids:
            vehicles = self.browse(res_ids)
            vehicles.schedule_services()

    @api.multi
    def schedule_services(self, note=None, auto=True):
        schedule_obj = self.env['fleet.service.schedule']
        for vehicle in self:
            # let's first see if we have an outstanding
            if schedule_obj.search_count([
                ('state', 'in', ('open',  'overdue')),
                ('vehicle_id', '=', vehicle.id)
            ]):
                continue
            schedule_obj.create({
                'vehicle_id': vehicle.id,
                'auto_generated': auto,
                'note': note or 'Periodic Maintennace'
            })


class fleet_vehicle_log_services(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    @api.one
    def _set_schedule_id(self):
        if len(self.schedule_id):
            self.schedule_id.service_log_id = self.id

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        super(fleet_vehicle_log_services, self)._onchange_vehicle()
        if self.schedule_id:
            self.cost_subtype_id = self.schedule_id.cost_subtype_id.id and self.schedule_id.cost_subtype_id.id or False

    name = fields.Char('Reference', readonly=True)
    schedule_id = fields.Many2one('fleet.service.schedule', 'Service schedule', inverse="_set_schedule_id")
    schedule_log_date = fields.Datetime('Scheduled On', required=True, default=fields.Date.today())

    @api.model
    def create(self, data):
        data['name'] = self.env['ir.sequence'].next_by_code('fleet.service.log.ref')
        return super(fleet_vehicle_log_services, self).create(data)


class fleet_service_maintenance(models.Model):
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _name = "fleet.service.maintenance"
    _rec_name = 'vehicle_id'
    _description = 'Maintenance Plan'

    desc = fields.Text('Description', required=True,)
    service_type = fields.Many2one(
        'fleet.service.type', 'Service Type', required=True,
    )
    odometer = fields.Float('Odometer', required=True)
    vehicle_id = fields.Many2one(
        'fleet.vehicle', 'Vehicle', required=True,
    )
    maintenance_date = fields.Datetime(
        'Maintenance Date',
        required=True, default=fields.Date.today()
    )
    odometer_unit = fields.Selection(
        [('kilometers', 'Kilometers'), ('miles', 'Miles')],
        'Odometer Unit', default='kilometers', help='Unit of the odometer ',
        required=True
    )
    schedule_id = fields.Many2one(
        'fleet.service.schedule', string="Service Schedule", readonly=True
    )
    state = fields.Selection(related='schedule_id.state', string="State", readonly=True)

    @api.model
    def _cron_schedule_service_maintenance(self):
        res_ids = []
        maintenance_ids = self.search([])
        for maintenance in maintenance_ids.filtered(lambda r: r.vehicle_id):
            if maintenance.odometer >= maintenance.vehicle_id.next_service_odometer:
                res_ids.append(maintenance)
        if res_ids:
            for maintenance in res_ids:
                maintenance.schedule_services()
        return True

    @api.multi
    def schedule_services(self):
        schedule_obj = self.env['fleet.service.schedule']
        for maintenance in self:
            # let's first see if we have an outstanding
            if schedule_obj.search_count([
                ('state', 'in', ('open',  'overdue')),
                ('maintenance_id', '=', maintenance.id),
            ]):
                continue
            schedule_id = schedule_obj.create({
                'maintenance_id': maintenance.id,
                'vehicle_id': maintenance.vehicle_id.id,
                'auto_generated': True,
                'note': maintenance.desc or '',
                'cost_subtype_id': maintenance.service_type.id,
            })
            maintenance.schedule_id = schedule_id and schedule_id.id or False
        return True

    @api.onchange('service_type')
    def onchange_service_type(self):
        if self.service_type and not self.desc:
            self.desc = self.service_type.display_name
