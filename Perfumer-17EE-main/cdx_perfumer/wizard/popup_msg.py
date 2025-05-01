from odoo import models, fields, api
from odoo.exceptions import UserError

class GenerateBomConfirmationWizard(models.TransientModel):
    _name = 'generate.bom.confirmation.wizard'
    _description = 'Confirmation Wizard for BOM Generation'


    def action_generate_bom(self):
        context={}
        action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.bom',
                    'view_mode': 'form',
                    'view_id': self.env.ref('mrp.mrp_bom_form_view').id,  # Reference to the BOM form view
                    'res_id': False,  # Create a new BOM if there's no BOM associated
                    'target': 'new',  # Open in the current window
                    'context':{}
                }
        # Check if no BOM is set on the sale order line
        if self.env.context.get('default_sol'):
            sale_order_line = self.env['sale.order.line'].browse(self.env.context.get('default_sol'))
            if  sale_order_line.cdx_bom_id:
                action['res_id'] = sale_order_line.cdx_bom_id.id
                # Open the MRP BOM form view
            else:
                context = {
                    'default_so': sale_order_line.order_id.id,
                    'default_sol': sale_order_line.id,
                    'default_product_tmpl_id': sale_order_line.product_template_id.id,
                    'default_code': sale_order_line.order_id.name,
                }
                action['context'] = context
            return action
        
        if self.env.context.get('default_bol'):
            bom_line = self.env['mrp.bom.line'].browse(self.env.context.get('default_bol'))
           
            if  bom_line.bom_id_custom:
                action['res_id'] = bom_line.bom_id_custom.id
            else:
                context = {
                    'default_product_tmpl_id': bom_line.product_id.product_tmpl_id.id,
                }
                action['context'] = context
                # Open the MRP BOM form view
            return action
    
    
    def action_cancel(self):
        # Simply close the wizard without doing anything
        return {'type': 'ir.actions.act_window_close'}