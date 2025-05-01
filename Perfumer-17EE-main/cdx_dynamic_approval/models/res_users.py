
from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    deactivate = fields.Boolean('Deactivate Notifications', default=False)