from odoo import api, fields, models, _



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    request_id = fields.Many2one('material.request', string="material request")
    intertransit_type = fields.Selection([('inter_company','InterCompany'),('inter_branch','Inter Branch')])
    
    
    
    def button_validate(self):
        res = super().button_validate()
        if self.purchase_id and self.purchase_id.cdx_requisition_id:
            mr =self.env['material.request'].search([('requisition_id','=',self.purchase_id.cdx_requisition_id.id)])
            if mr:
                title = "Material Request"
                message = f"Material Request  {mr.name} is Ready to Approve"

                self.env['bus.bus'].send_notification(mr.dest_user_id.partner_id,mr._name,mr.id,title,message)
        if self.picking_type_code == 'incoming' and self.purchase_id:
            users = self.env['res.users'].search([('is_procurement_manager','=',True)])
            title = "Purchase Order"
            for user in users:
                message = f"Purchase Order  {self.purchase_id.name} is Ready to generate bill"
                self.env['bus.bus'].send_notification(user.partner_id,self.purchase_id._name,self.purchase_id.id,title,message)
        return res            