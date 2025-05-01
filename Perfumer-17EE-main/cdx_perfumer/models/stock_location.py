from odoo import api, fields, models, _


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_main = fields.Boolean(string="Is Main?")