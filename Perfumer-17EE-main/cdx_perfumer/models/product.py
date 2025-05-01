from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_group = fields.Selection([('rm', 'RM'),('sp','SP',),('fg','FG')])
