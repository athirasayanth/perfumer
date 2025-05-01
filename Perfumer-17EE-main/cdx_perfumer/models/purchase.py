from odoo import api, fields, models, _
from odoo.exceptions import  UserError


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    cdx_requisition_id = fields.Many2one('cdx.material.purchase.requisition', string="Requisition")
    
    def action_rfq_send_direct(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False

        if not template_id:
            raise UserError(_("Email template for RFQ or Purchase Order not found."))

        # Fetch the email template
        template = self.env['mail.template'].browse(template_id)
        if not template:
            raise UserError(_("Email template could not be loaded."))

        # Send the email
        template.send_mail(self.id, force_send=True)

        # Optionally mark RFQ as sent
        if self.state == 'draft':
            self.write({'state': 'sent'})

        return True
    
    def action_create_invoice(self):
        res =super(PurchaseOrderInherit,self).action_create_invoice()
        bill=self.env['account.move'].browse(res['res_id'])
        users = self.env.ref('account.group_account_manager').users
        title = "Purchase Bill"
        message = f"Purchase Bill  {bill.name} is created"
        for user in users:
            self.env['bus.bus'].send_notification(user.partner_id,bill._name,bill.id,title,message)
        return res

    def button_confirm(self):
        res = super(PurchaseOrderInherit, self).button_confirm()
        users = self.env.ref('account.group_account_manager').users
        title = "Purchase Order"
        message = f"Purchase order  {self.name} is generated of Amount {self.amount_total} {self.currency_id.name}"
        for user in users:
            self.env['bus.bus'].send_notification(user.partner_id,self._name,self.id,title,message)
        if self.cdx_requisition_id:
            self.cdx_requisition_id.state = 'purchase'
        return res
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    cdx_requisition_line_id = fields.Many2one('cdx.material.purchase.requisition.line',string='Requisitions Line',copy=False)