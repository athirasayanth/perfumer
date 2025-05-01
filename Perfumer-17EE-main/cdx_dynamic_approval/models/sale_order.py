from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    approval_state = fields.Selection(
        [('1st_approve', '1st Approve'), ('2nd_approve', '2nd Approve'), ('3rd_approve', '3rd Approve'),
         ('4th_approve', '4th Approve'), ('5th_approve', '5th Approve'), ('approved', 'Approved')],
        string='Approval State')

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.approval_state and self.approval_state != 'approved':
            raise UserError(_("Please approve first."))
        return res

    # @api.model
    # def default_get(self, default_fields):
    #     rec = super(SaleOrder, self).default_get(default_fields)
    #     model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
    #     approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
    #     if approval_config:
    #         title = "Sale Order Approval"
    #         approve_line = self.env['dynamic.approve.config.line'].search(
    #             [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '1')], limit=1)
    #         for user_id in approve_line.user_ids:
    #             message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
    #                       f"SO: {self.name}\n"
    #             self.button_send_notification(title, user_id.partner_id, message)
    #         rec['approval_state'] = '1st_approve'
    #     else:
    #         rec['approval_state'] = False
    #     return rec
    
    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].sudo().search([('model_id', '=', model_id.id)], limit=1)
        if approval_config:
            title = "Sale Order Approval"
            approve_line = self.env['dynamic.approve.config.line'].search(
                [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '1')], limit=1)
            for user_id in approve_line.user_ids:
                message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
                        f"SO: {res.name}\n"
                self.button_send_notification(title, user_id.partner_id, message,res.id)
            res.approval_state = '1st_approve'
        else:
            res.approval_state = False
        return res

    def action_1st_approve(self):
        model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
        if approval_config:
            approve_line = self.env['dynamic.approve.config.line'].search(
                [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '1')], limit=1)
            if approve_line and approve_line.user_ids and self.env.user.id not in approve_line.user_ids.ids:
                raise UserError(_("You can't approve this."))
            if int(approval_config.approval_levels) == 1:
                self.write({
                    'approval_state': 'approved'
                })
            else:
                title = "Sale Order Approval"
                approve_line = self.env['dynamic.approve.config.line'].search(
                    [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '2')], limit=1)
                for user_id in approve_line.user_ids:
                    message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
                              f"SO: {self.name}\n"
                    self.button_send_notification(title, user_id.partner_id, message,self.id)
                self.write({
                    'approval_state': '2nd_approve'
                })

    def action_2nd_approve(self):
        model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
        if approval_config:
            approve_line = self.env['dynamic.approve.config.line'].search(
                [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '2')], limit=1)
            if approve_line and approve_line.user_ids and self.env.user.id not in approve_line.user_ids.ids:
                raise UserError(_("You can't approve this."))
            if int(approval_config.approval_levels) == 2:
                self.write({
                    'approval_state': 'approved'
                })
            else:
                title = "Sale Order Approval"
                approve_line = self.env['dynamic.approve.config.line'].search(
                    [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '3')], limit=1)
                for user_id in approve_line.user_ids:
                    message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
                              f"SO: {self.name}\n"
                    self.button_send_notification(title, user_id.partner_id, message,self.id)
                self.write({
                    'approval_state': '3rd_approve'
                })

    def action_3rd_approve(self):
        model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
        if approval_config:
            approve_line = self.env['dynamic.approve.config.line'].search(
                [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '3')], limit=1)
            if approve_line and approve_line.user_ids and self.env.user.id not in approve_line.user_ids.ids:
                raise UserError(_("You can't approve this."))
            if int(approval_config.approval_levels) == 3:
                self.write({
                    'approval_state': 'approved'
                })
            else:
                title = "Sale Order Approval"
                approve_line = self.env['dynamic.approve.config.line'].search(
                    [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '4')], limit=1)
                for user_id in approve_line.user_ids:
                    message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
                              f"SO: {self.name}\n"
                    self.button_send_notification(title, user_id.partner_id, message,self.id)
                self.write({
                    'approval_state': '4th_approve'
                })

    def action_4th_approve(self):
        model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
        if approval_config:
            approve_line = self.env['dynamic.approve.config.line'].search(
                [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '4')], limit=1)
            if approve_line and approve_line.user_ids and self.env.user.id not in approve_line.user_ids.ids:
                raise UserError(_("You can't approve this."))
            if int(approval_config.approval_levels) == 4:
                self.write({
                    'approval_state': 'approved'
                })
            else:
                title = "Sale Order Approval"
                approve_line = self.env['dynamic.approve.config.line'].search(
                    [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '5')], limit=1)
                for user_id in approve_line.user_ids:
                    message = f"Hello {user_id.name},\n\nPlease Approve :\n\n" \
                              f"SO: {self.name}\n"
                    self.button_send_notification(title, user_id.partner_id, message,self.id)
                self.write({
                    'approval_state': '5th_approve'
                })

    def action_5th_approve(self):
        model_id = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1)
        approval_config = self.env['dynamic.approve.config'].search([('model_id', '=', model_id.id)], limit=1)
        approve_line = self.env['dynamic.approve.config.line'].search(
            [('approve_config_id', '=', approval_config.id), ('approval_levels', '=', '5')], limit=1)
        if approve_line and approve_line.user_ids and self.env.user.id not in approve_line.user_ids.ids:
            raise UserError(_("You can't approve this."))
        self.write({
            'approval_state': 'approved'
        })

    # def button_send_notification(self, title, partner_id, message,ID):
    #     if not self.env.user.deactivate:
    #         self.env['bus.bus']._sendone(partner_id, 'sale.order-' + str(ID), {
    #             'title': title,
    #             'message': message,
    #             'sticky': True
    #         })
            
    def button_send_notification(self, title, partner_id, message, ID):
        if not self.env.user.deactivate:
            self.env['bus.bus']._sendone(partner_id, 'my.notification', {
                'model_tech_name':self._name,
                'rec_id':ID,
                'title': title,
                'message': message,
                'sticky': True
            })
