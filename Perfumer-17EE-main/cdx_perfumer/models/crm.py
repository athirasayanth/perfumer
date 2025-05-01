from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import Command
from datetime import datetime

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    cdx_jobcard_user_id = fields.Many2one('res.users', string="Jobcard User",tracking=True)
    cdx_estimation_id = fields.Many2one('cdx.estimation', string="Estimation",tracking=True)
    cdx_is_jobcard_assigned = fields.Boolean(string="Is Estimation User Assigned")
    estimation_count = fields.Integer(compute='_compute_estimation_data', string="Number of Estimation")
    cdx_estimation_ids = fields.One2many('cdx.estimation','opportunity_id', string="Estimations")
    date_deadline_delivery = fields.Date('Expected Delivery', help="Estimate of the date on which the opportunity delivery will be done.")
    def cdx_assign_user_to_jobcard(self):
        if not self.cdx_jobcard_user_id:
            raise UserError("Please select Estimation User")
        
        self.cdx_estimation_id.sudo().user_id = self.cdx_jobcard_user_id.id
        title = "Estimation"
        activity_type=self.env.ref('cdx_perfumer.cdx_job_est')                
        notification = {
                    'activity_type_id': activity_type.id,
                    'res_id': self.cdx_estimation_id.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', '=', activity_type.res_model)],limit=1).id,
                    'icon': activity_type.icon,
                    'date_deadline': fields.Date.today(),
                    'user_id': self.cdx_jobcard_user_id.id,
                    'note': 'Estimation assigned to You'
                }
        self.env['mail.activity'].create(notification)
        message = f"Estimation  {self.cdx_estimation_id.name} Assigned to You"
        self.env['bus.bus'].send_notification(self.cdx_jobcard_user_id.partner_id,self.cdx_estimation_id._name,self.cdx_estimation_id.id,title,message)
        self.cdx_is_jobcard_assigned = True
    
    def action_new_quotation(self):
        action =super(CrmLead,self).action_new_quotation()
        if self.cdx_jobcard_user_id:
            action['context']['default_user_id'] = self.cdx_jobcard_user_id.id
        return action
    def create_estimation(self):
        estimation_id  = self.env['cdx.estimation'].sudo().create({'opportunity_id': self.id,'partner_id':self.partner_id.id,'user_id':self.env.user.id,'origin':self.name})
        self.cdx_estimation_id =estimation_id.id
        self.cdx_estimation_ids = [Command.link(estimation_id.id)]
        # [(6,0,estimation_id.id)]
    
    
    @api.depends('cdx_estimation_id')
    def _compute_estimation_data(self):
        for lead in self:
            lead.estimation_count = len(lead.cdx_estimation_ids)
            

    def action_view_estimations(self):
        self.ensure_one()
        ids = self.cdx_estimation_ids.filtered_domain([('user_id', '=', self.env.user.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'cdx.estimation',
            'view_mode': 'list,form',
            'domain': [('id', 'in', ids.ids)],
            'target': 'current', 
        }
    
    
    @api.model
    def create(self, vals):
        lead = super().create(vals)
        lead._schedule_initial_activities()
        return lead

    def _schedule_initial_activities(self):
        """When lead is created, create first activities."""
        Activity = self.env['mail.activity']
        user = self.env['res.users'].sudo().search([('is_salesperson','=',True)],limit=1)
        # Immediately: Create New Lead/Opportunity Activity
        if user:
            Activity.create({
                'res_model_id': self.env.ref('crm.model_crm_lead').id,
                'res_id': self.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,  # Or a custom one
                'summary': 'Create new Lead/Opportunity',
                'user_id': user.id,
                'date_deadline': fields.Date.today(),
            })
    

    task_timer = fields.Boolean(
        string='Timer', default=False,
        help="Field to indicate if the timer is active.")
    is_user_working = fields.Boolean(
        string='Is Current User Working', compute='_compute_is_user_working',
        help="Technical field indicating whether the current user is working.")
    duration = fields.Float(
        string='Real Duration', store=True, readonly=False,
        help="The actual duration of the project task.")
    timer_user_id = fields.Many2one('res.users', string="Timer User")
    show_timer = fields.Boolean(string="Timer", compute='_compute_show_timer',
                                help="Indicates whether the timer should be"
                                     " shown for the current user.")
    
    timesheet_ids = fields.One2many('account.analytic.line', 'opportunity_id', 'Associated Timesheets')
    
    
    
    @api.depends('timer_user_id')
    def _compute_show_timer(self):
        """Compute the value of the show_timer field based on the
        timer_user_id."""
        for rec in self:
            if rec.timer_user_id:
                rec.show_timer = self.env.user.id == rec.timer_user_id.id
            else:
                rec.show_timer = True

    def _compute_is_user_working(self):
        """ Compute if the current user is working on the task """
        for order in self:
            if order.timesheet_ids.filtered(
                    lambda x: (x.user_id.id == self.env.user.id) and (
                            not x.date_end)):
                order.is_user_working = True
            else:
                order.is_user_working = False

    def action_toggle_start(self, timer):
        """ Toggle the timer based on the given parameter """
        if timer:
            self.write({'is_user_working': True, 'task_timer': True,
                        'timer_user_id': self.env.user.id})
            time_line = self.env['account.analytic.line']
            for time_sheet in self:
                time_line.create({
                    'name': self.env.user.name + ': ' + time_sheet.name,
                    'opportunity_id': time_sheet.id,
                    'user_id': self.env.user.id,
                    # 'project_id': time_sheet.projeect_id.id,
                    'using_timer': True,
                    'date_start': fields.Datetime.now(),
                })
        else:
            self.write({'is_user_working': False, 'task_timer': False,
                        'timer_user_id': False})
            time_line_obj = self.env['account.analytic.line']
            domain = [('opportunity_id', 'in', self.ids), ('date_end', '=', False),
                      ('user_id', '=', self.env.user.id)]
            for time_line in time_line_obj.search(domain):
                if time_line.date_start:
                    time_line.write({'date_end': fields.Datetime.now()})
                    diff = fields.Datetime.from_string(
                        time_line.date_end) - fields.Datetime.from_string(
                        time_line.date_start)
                    time_line.timer_duration = round(
                        diff.total_seconds() / 60.0, 2)
                    time_line.unit_amount = round(
                        diff.total_seconds() / (60.0 * 60.0), 2)

    def get_working_duration(self):
        """Get the additional duration for 'open times' i.e. productivity
        lines with no date_end."""
        self.ensure_one()
        duration = 0
        for time in self.timesheet_ids.filtered(
                lambda time: not time.date_end and time.using_timer):
            if type(time.date_start) != datetime:
                time.date_start = datetime.now()
                duration = 0
            else:
                duration += ((datetime.now() - time.date_start).total_seconds()
                             / 60)
        return duration
    
    
    
class AccountAnalyticLine(models.Model):
    _inherit='account.analytic.line'
    
    
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity",tracking=True)
    sale_id = fields.Many2one('sale.order', string="sale")
    date_start = fields.Datetime(string='Start Date',
                                 help="Start date and time for the task.")
    date_end = fields.Datetime(string='End Date', readonly=True,
                               help="End date and time for the task.")
    timer_duration = fields.Float(invisible=1, string='Time Duration (Minutes)',
                                  help="Duration of the timer in minutes.")
    using_timer = fields.Boolean(string='Timer Used',
                                 help="Signifies whether the the timesheet"
                                      " created using timer")