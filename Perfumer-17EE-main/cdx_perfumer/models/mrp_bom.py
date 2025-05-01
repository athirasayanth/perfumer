from odoo import models, fields, api, _
from odoo.exceptions import MissingError, ValidationError, UserError



class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpBom,self).create(vals_list)
        res._assign_routes_to_product()
        if self.env.context.get('default_sol'):
            sol = self.env['sale.order.line'].search([('id', '=', int(self.env.context.get('default_sol')))], limit=1)
            sol.cdx_bom_id=res.id
            sol.price_unit =res.total_sale_price
        return res
    
    total_sale_price = fields.Float(string="Total", compute="_compute_total_sale_price", store=True)

    @api.depends('bom_line_ids.product_id', 'bom_line_ids.product_qty')
    def _compute_total_sale_price(self):
        """Calculate the total sale price based on BoM lines"""
        for bom in self:
            total = sum(line.product_id.list_price * line.product_qty for line in bom.bom_line_ids)
            bom.total_sale_price = total
    
    

    def write(self, vals):
        result = super().write(vals)
        self._assign_routes_to_product()
        if self.env.context.get('default_sol'):
            sol = self.env['sale.order.line'].search([('id', '=', int(self.env.context.get('default_sol')))], limit=1)
            sol.cdx_bom_id=self.id
            sol.price_unit =self.total_sale_price
        return result

    def _assign_routes_to_product(self):
        # Fetch route references safely
        route_mto = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
        route_manufacture = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
        
        # Check sale order line from context
        sale_order_line = self.env.context.get('default_sol')
        sol = self.env['sale.order.line'].browse(int(sale_order_line)) if sale_order_line else False


        for bom in self:
            product_template = bom.product_tmpl_id or bom.product_id.product_tmpl_id
            if not product_template:
                continue

            # Determine product group based on condition
            if sol and product_template.id == sol.product_template_id.id:
                product_group_value = 'fg'
            else:
                product_group_value = 'sp'

            # Assign product group
            if product_template.product_group != product_group_value:
                product_template.write({'product_group': product_group_value})

            # Process routes for template and variants
            def process_routes(product_or_template):
                routes_to_add = []
                if route_mto and route_mto not in product_or_template.route_ids:
                    routes_to_add.append(route_mto.id)
                if route_manufacture and route_manufacture not in product_or_template.route_ids:
                    routes_to_add.append(route_manufacture.id)

                routes_to_remove = []
                if route_buy and route_buy in product_or_template.route_ids:
                    routes_to_remove.append(route_buy.id)

                if routes_to_add or routes_to_remove:
                    product_or_template.write({
                        'route_ids': (
                            [(3, route_id) for route_id in routes_to_remove] +
                            [(4, route_id) for route_id in routes_to_add]
                        )
                    })

            process_routes(product_template)
            for variant in product_template.product_variant_ids:
                process_routes(variant)

            # Link BOM to Sale Order Line if applicable
            if sol:
                sol.cdx_bom_id = bom.id



class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    
    bom_id_custom = fields.Many2one('mrp.bom', 'BoM',index=True, ondelete='cascade')
    def generate_bom_from_bom_line(self):
        self.ensure_one()
        context = {
                'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
                'default_bol':self.id
            }
        if not self.bom_id_custom:
            # If no custom BOM is linked, show the wizard
            return {
                'name': _("Generate BOM Confirmation"),
                'type': 'ir.actions.act_window',
                'res_model': 'generate.bom.confirmation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': context
            }
        else:
            return {
                "name": _("Components"),
                "view_type": "form",
                "view_mode": "form",
                "res_model": "mrp.bom",
                "type": "ir.actions.act_window",
                "target": "new",
                'context': context,
                'res_id': self.bom_id_custom.id,
            }


    
    
    
    