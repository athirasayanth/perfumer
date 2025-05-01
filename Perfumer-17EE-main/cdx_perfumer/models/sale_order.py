from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    
    cdx_estimation_id = fields.Many2one('cdx.estimation', string="Estimation", readonly=True)
    markup = fields.Float(string="Markup (%)",digits='Discount',)

    payment_line = fields.One2many(comodel_name="account.payment", inverse_name="sale_id")
    payment_count = fields.Integer(string="Payment Count", compute="compute_payment_count")
    cdx_payment_state = fields.Selection([('not_invoice', 'Not Invoiced'), ('not_paid', 'Not Paid'),('paid', 'Paid'), ('partial', 'Partially Paid')],string="Payment Status", compute="cdx_compute_payment_status")
    amount_due = fields.Float(string="Amount Due", compute="compute_amount_due", store=True)
    paid_amount = fields.Float(string="Amount Paid",compute="compute_amount_due", store=True)
    
    def action_confirm(self):
        if self.cdx_payment_state in ['not_invoice','not_paid']:
            raise ValidationError(_("Advance Payment is not received"))
        return super(SaleOrder,self).action_confirm()
    @api.depends('payment_line.amount','payment_line','amount_total','state')
    def compute_amount_due(self):
        for rec in self:
            rec.amount_due = rec.amount_total - sum(line.amount_signed for line in rec.payment_line)
            rec.paid_amount = sum(line.amount_signed for line in rec.payment_line)
    @api.depends('payment_line')      
    def cdx_compute_payment_status(self):
        for rec in self:
            payment_status = 'not_paid'
            invoice_ids = rec.invoice_ids.filtered(
                lambda x: x.state != 'cancel')
            # if not invoice_ids:
            #     payment_status = 'not_invoice'
            #if ncheck for sale's payments
            if rec.payment_line:
                # if rec.cdx_invoice_advance_payment_status == 'partial_paid':
                #     payment_status = 'partial'
                # if rec.cdx_invoice_advance_payment_status == 'paid':
                #     payment_status = 'paid'
                # else:
                #     rec.cdx_invoice_advance_payment_status == 'not_paid':
                #     payment_status = 'not_paid'
                if rec.amount_due == 0 :
                    payment_status = 'paid'
                elif rec.amount_due != rec.amount_total:
                    payment_status = 'partial'
                else:
                    payment_status = 'not_paid'


            elif not invoice_ids:
                payment_status = 'not_invoice'
            elif any(inv.payment_state == 'partial' for inv in invoice_ids):
                payment_status = 'partial'
            elif all(inv.payment_state == 'paid' for inv in invoice_ids):
                payment_status = 'paid'
            rec.cdx_payment_state = payment_status
            
    @api.depends("payment_line")
    def compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_line)

    def action_advance_payment(self):
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payment.wizard",
            "view_id": self.env.ref("cdx_perfumer.advance_payment_wizard_form_view").id,
            "type": "ir.actions.act_window",
            "target": "new"
        }
    
    def action_view_payment(self):
        payment_ids = self.payment_line
        context = {'default_sale_id':self.id,'default_partner_id':self.partner_id.id,'default_payment_type': 'inbound','default_partner_type': 'customer'}
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_account_payments')
        if len(payment_ids) > 1:
            result['domain'] = [('id', 'in', payment_ids.ids)]
        elif len(payment_ids) == 1:
            result['views'] = [(self.env.ref('account.view_account_payment_form', False).id, 'form')]
            result['res_id'] = payment_ids.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    timesheet_ids = fields.One2many('account.analytic.line', 'sale_id', 'Associated Timesheets')

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
    
    timesheet_ids = fields.One2many('account.analytic.line', 'sale_id', 'Associated Timesheets')
    
    
    
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
                    'sale_id': time_sheet.id,
                    'user_id': self.env.user.id,
                    # 'project_id': time_sheet.projeect_id.id,
                    'using_timer': True,
                    'date_start': fields.Datetime.now(),
                })
        else:
            self.write({'is_user_working': False, 'task_timer': False,
                        'timer_user_id': False})
            time_line_obj = self.env['account.analytic.line']
            domain = [('sale_id', 'in', self.ids), ('date_end', '=', False),
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
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    
    cdx_estimation_id = fields.Many2one('cdx.estimation', string="Estimation", readonly=True,related='order_id.cdx_estimation_id',store=True)
    cdx_estimation_line_id = fields.Many2one('cdx.estimation.line', string="Estimation line", readonly=True,)

    widget_field = fields.Char(string="Wdiget field")
    cdx_bom_id = fields.Many2one('mrp.bom', string="BOM",copy=False )
    
    def action_open_estimation_popup(self):
        self.ensure_one()
        if not self.cdx_estimation_id:
            raise UserError(_("No estimation is linked to this sale order."))
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_action_handler',
            'context': {'order_line_id': self.id},
            'path':''
        }
    cdx_estimation_line_ids = fields.One2many(
        'sale.order.line.estimation', 'sale_order_line_id', string="Estimation Lines",invisible=True
    )
    markup = fields.Float(string="Markup (%)",digits='Discount',tracking=True)
    
    @api.depends('markup', 'order_id.markup','cdx_bom_id.total_sale_price','price_unit')
    def _compute_price_unit(self):
        """Compute price_unit based on markup percentage."""
        for line in self:
            markup_value = line.markup if line.markup else line.order_id.markup
            temp = line.price_unit
            if not line.markup:  # Only set if empty
                line.markup = line.order_id.markup
            line.price_unit = ((markup_value / 100) * temp if markup_value else 0) + temp
    
    
    def generate_bom(self):
        context = {
                'default_so': self.order_id.id,
                'default_sol': self.id,
                'default_product_tmpl_id': self.product_template_id.id,
                'default_code': self.order_id.name,
            }
        if self.cdx_bom_id:
            # BOM is already linked, open directly
            return {
                "name": _("Components"),
                "view_type": "form",
                "view_mode": "form",
                "res_model": "mrp.bom",
                "type": "ir.actions.act_window",
                "target": "new",
                'context': context,
                'res_id': self.cdx_bom_id.id,
            }

        # If no BOM linked, show the confirmation wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'generate.bom.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }
        
    
    
    @api.model
    def update_line_data(self, sale_order_line_id, estimation_data):
        """
        estimation_data: List of dictionaries with estimation_line_id and quantity
        """
        estimation_line_ids=[]
        sale_order_line = self.browse(sale_order_line_id)
        self = sale_order_line
        if sale_order_line:
            # Remove existing records before updating
            # sale_order_line.cdx_estimation_line_ids.unlink()
            if not self.cdx_bom_id:
                bom = self.env['mrp.bom'].create({
                'product_tmpl_id': sale_order_line.product_id.product_tmpl_id.id,
                'product_id': sale_order_line.product_id.id,
                'type': 'normal',  # 'normal' for manufacturing BoM
                'code':sale_order_line.order_id.name
                })
                sale_order_line.cdx_bom_id = bom.id
            # Create new records
            for data in estimation_data:
                estimation_line = self.env['cdx.estimation.line'].browse(data['estimation_line_id'])

                if data['product_uom_qty'] > estimation_line.remaining_qty:
                    raise UserError(
                        _("Not enough quantity available for %s. Remaining: %s, Requested: %s.") %
                        (estimation_line.product_id.name, estimation_line.remaining_qty, data['product_uom_qty'])
                    )
                bom_line_id=self.env['mrp.bom.line'].create({
                    'bom_id': bom.id,
                    'product_id': estimation_line.product_id.id,
                    'product_qty': estimation_line.product_uom_qty,
                    'product_uom_id': estimation_line.product_id.uom_id.id,
                    })
                new_line=self.env['sale.order.line.estimation'].create({
                    'sale_order_line_id': sale_order_line.id,
                    'estimation_line_id': data['estimation_line_id'],
                    'product_uom_qty': data['product_uom_qty'],
                    'bom_line_id':bom_line_id.id,
                    'bom_id':sale_order_line.cdx_bom_id.id
                })
                estimation_line_ids.append(new_line.id)
            estimation_line_ids +=sale_order_line.cdx_estimation_line_ids.ids
            sale_order_line.write({'cdx_estimation_line_ids': [(6, 0, estimation_line_ids)]})
            sale_order_line.price_unit = sum(sale_order_line.cdx_estimation_line_ids.mapped('total_price'))
            
            return {"success": True, "message": "Sale Order Line updated"}

        return {"success": False, "message": "Sale Order Line not found"}
    
    
    def show_all_lines(self):
        self.ensure_one()
        view_id = self.env.ref('cdx_perfumer.view_sale_line_list_estimation_selection').id
        print(self.cdx_estimation_line_ids.ids)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order line estimations',
            'res_model': 'sale.order.line.estimation',
            'view_mode': 'list,form',
            'view_type':'list',
            'views': [(view_id, 'list')],
            'domain': [('id', 'in', self.cdx_estimation_line_ids.ids)],
            'domain': [('sale_order_line_id','=',self.id)],
            'target': 'new', 
        }