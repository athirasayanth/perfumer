from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError



class SaleOrderLineEstimation(models.Model):
    _name = "sale.order.line.estimation"
    _description = "Estimation Lines for Sale Order Line"

    sale_order_line_id = fields.Many2one(
        'sale.order.line', string="Sale Order Line", ondelete="cascade"
    )
    estimation_line_id = fields.Many2one(
        'cdx.estimation.line', string="Estimation Line", required=True, ondelete="cascade"
    )
    product_uom_qty = fields.Float(string="Selected Quantity", required=True, default=1)

    total_price = fields.Float(string="Total Price", compute="_compute_total_price", store=True,digits='Product Price')
    bom_id = fields.Many2one('mrp.bom', string="Bill of Material", required=True, ondelete="cascade")
    bom_line_id = fields.Many2one('mrp.bom.line', string="Bom Line", required=True, ondelete="cascade")
    @api.depends('estimation_line_id', 'product_uom_qty')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.estimation_line_id.price_subtotal * record.product_uom_qty

    # @api.constrains('product_uom_qty', 'estimation_line_id')
    # def _check_remaining_quantity(self):
    #     for record in self:
    #         if record.product_uom_qty > record.estimation_line_id.remaining_qty:
    #             raise UserError(
    #                 _("Cannot select more than the available remaining product_uom_qty (%s) for %s.") %
    #                 (record.estimation_line_id.remaining_qty, record.estimation_line_id.product_id.name)
    #             )