from odoo import models, fields, api, _
class EstimationLineWizard(models.TransientModel):
    _name = 'cdx.estimation.line.wizard'
    _description = 'Wizard to Select Estimation Lines'

    estimation_line_ids = fields.Many2many('cdx.estimation.line', string="Estimation Lines")
    selected_total = fields.Float(string="Total Selected", compute="_compute_total")

    @api.depends('estimation_line_ids')
    def _compute_total(self):
        for wizard in self:
            wizard.selected_total = sum(wizard.estimation_line_ids.mapped('price_subtotal'))

    def action_confirm_selection(self):
        """Apply the selected estimation lines to the Sale Order Line"""
        sale_order_line = self.env['sale.order.line'].browse(self.env.context.get('active_id'))
        sale_order_line.cdx_estimation_line_ids = [(6, 0, self.estimation_line_ids.ids)]
        sale_order_line._compute_estimation_total()
        return {'type': 'ir.actions.act_window_close'}