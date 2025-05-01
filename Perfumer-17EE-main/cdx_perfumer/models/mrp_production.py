from odoo import models, fields, api, _
from odoo.exceptions import  UserError
from odoo.tools import float_compare
from odoo.tools.misc import format_date

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    
    
    material_request_id  = fields.Many2one('material.request',string='Material Request',readonly=True)
    receive_stock =  fields.Boolean(string="Receive Stock",compute='action_check_mr')
    requisition_id = fields.Many2one('cdx.material.purchase.requisition',string='Requisitions', ondelete="cascade")
    # def action_confirm(self):
    #     if self.material_request_id and self.material_request_id.state == 'done':
    #         res=super(MrpProduction,self).action_confirm()
    #     else:
    #         res=False
            
    #     return res
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'origin' in vals and 'product_id' in vals:
                sale_order = self.env['sale.order'].search([('name', '=', vals['origin'])], limit=1)
                if sale_order:
                    sale_line = sale_order.order_line.filtered(lambda l: l.product_id.id == vals['product_id'])
                    if sale_line and sale_line.cdx_bom_id:
                        vals['bom_id'] = sale_line.cdx_bom_id.id  # Assign correct BoM
        res = super(MrpProduction,self).create(vals_list)
        users = self.env['res.users'].search([('is_production_manager','=',True)])
        # users = self.env.ref('mrp.group_mrp_manager').users
        activity_type=self.env.ref('cdx_perfumer.cdx_job_card')                
        title = "Job Card"
        for rec in res:
            for user in users:
                notification = {
                    'activity_type_id': activity_type.id,
                    'res_id': rec.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', '=', activity_type.res_model)],limit=1).id,
                    'icon': activity_type.icon,
                    'date_deadline': fields.Date.today(),
                    'user_id': user.id,
                    'note': 'Job Card Created'
                }
                self.env['mail.activity'].create(notification)
                message = f"Job Card  {rec.name} is created"
                self.env['bus.bus'].send_notification(user.partner_id,rec._name,rec.id,title,message)
        return res
    
    def button_mark_done(self):
        res = super(MrpProduction,self).button_mark_done()
        sale_order = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
        if sale_order:
            title = "Job Card Completed for Sale Order"
            message = f"Sale Order {sale_order.name}  Job Card {self.name}  Production process is completed"
            self.env['bus.bus'].send_notification(sale_order.user_id.partner_id,sale_order._name,sale_order.id,title,message)
        return res
    def action_create_material_request_wizard(self):
    #     # Filter selected lines that are marked for creation
        material_request_line = self.move_raw_ids.filtered(lambda x: x.select_line)
        if not material_request_line:
            raise UserError("Please select lines to create a Request!")
        location_ids = material_request_line.mapped('location_id')
        location_ids = list(set(location_ids))
        if len(location_ids) >1:
            raise UserError("Please select product of same request location!!")

    #     # Prepare to create material request lines
        material_lines = [
            (0, 0, {
                'product_id': material.product_id.id,
                'quantity': material.product_uom_qty,
                'available_quantity':material.product_qty_available,
                'product_uom_id': material.product_id.uom_id.id,
                'mrp_material_line':material.id,
            })
            for material in material_request_line
        ]
        context = {'default_material_request_id':self.id,'default_material_line':material_lines,'default_origin':self.name,}
    
        return {
            "name": _("Material Request"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "cdx.material.request.wizard",
            "type": "ir.actions.act_window",
            "target": "new",
            "context":context
        }
        
    def action_view_material_request(self):
        return {
            "name": _("Material Request"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "material.request",
            "type": "ir.actions.act_window",
            "target": "current",
            "res_id":self.material_request_id.id
        }
        
    
    def action_view_purchase_request(self):
      return {
                'type': 'ir.actions.act_window',
                'res_model': 'cdx.material.purchase.requisition',
                'res_id': self.requisition_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    
    @api.depends('picking_type_id')
    def _compute_locations(self):
        location=self.env['stock.location'].search([('is_main','=',True)],limit=1)
        for production in self:
            if not production.picking_type_id.default_location_src_id or not production.picking_type_id.default_location_dest_id:
                company_id = production.company_id.id if (production.company_id and production.company_id in self.env.companies) else self.env.company.id
                fallback_loc = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
            production.location_src_id = location.id if location else production.picking_type_id.default_location_src_id.id
            production.location_dest_id = production.picking_type_id.default_location_dest_id.id or fallback_loc.id
    
    # @api.depends('state', 'reservation_state', 'date_start', 'move_raw_ids', 'move_raw_ids.forecast_availability', 'move_raw_ids.forecast_expected_date','material_request_id','material_request_id.state')
    # def _compute_components_availability(self):
    #     productions = self.filtered(lambda mo: mo.state not in ('cancel', 'done'))
    #     productions.components_availability_state = 'available'
    #     productions.components_availability = _('Available')

    #     other_productions = self - productions
    #     other_productions.components_availability = False
    #     other_productions.components_availability_state = False

    #     all_raw_moves = productions.move_raw_ids
    #     # Force to prefetch more than 1000 by 1000
    #     all_raw_moves._fields['forecast_availability'].compute_value(all_raw_moves)
    #     for production in productions:
    #         if any(float_compare(move.forecast_availability, 0 if move.state == 'draft' else move.product_qty, precision_rounding=move.product_id.uom_id.rounding) == -1 for move in production.move_raw_ids) and not production.material_request_id or production.material_request_id.state !='done':
    #             production.components_availability = _('Not Available')
    #             production.components_availability_state = 'unavailable'
    #         else:
    #             forecast_date = max(production.move_raw_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
    #             if forecast_date:
    #                 production.components_availability = _('Exp %s', format_date(self.env, forecast_date))
    #                 if production.date_start:
    #                     production.components_availability_state = 'late' if forecast_date > production.date_start else 'expected'

    
    @api.depends('material_request_id','material_request_id.state')
    def action_check_mr(self):
        for rec in self:
            if not rec.material_request_id or rec.material_request_id.state =='approve' and rec.state =='draft':
                rec.receive_stock = True
            else:
                rec.receive_stock = False
            print(rec.receive_stock)
                
    def action_receive_material_request_stock(self):
        self.material_request_id.action_receive()
    class MRPRawLines(models.Model):
        _inherit = 'stock.move'
        
        
        select_line = fields.Boolean(string="Select", default=False)

    
    
    
    
    
