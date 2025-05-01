
from odoo import models, fields, api, _

class ImBus(models.Model):

    _inherit = 'bus.bus'
    _description = 'Communication Bus'
    
    
    
    def send_notification(self,partner_id,model_tech_name,rec_id,title,message):
        if not self.env.user.deactivate:
            self._sendone(partner_id, 'my.notification', {
                'model_tech_name':model_tech_name,
                'rec_id':rec_id,
                'title': title,
                'message': message,
                'sticky': True
            })
