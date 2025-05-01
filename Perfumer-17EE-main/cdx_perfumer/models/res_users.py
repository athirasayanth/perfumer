from odoo import models, fields,api


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    is_manager  = fields.Boolean('Warehouse Manager')
    is_production_manager  = fields.Boolean('Production Manager')
    is_procurement_manager  = fields.Boolean('Procurement Manager')
    is_ce  = fields.Boolean('Chief Executive')
    is_salesperson  = fields.Boolean('Sales Person')

class Partner(models.Model):
    _inherit='res.partner'
    

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        for node in arch.xpath("//field[@name='vat']"):
            node.attrib["string"] = 'Customer TRN'
        return arch, view