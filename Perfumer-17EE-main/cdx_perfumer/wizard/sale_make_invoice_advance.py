# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import  models



class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    _description = "Sales Advance Payment Invoice"

  

    #=== ACTION METHODS ===#

    def create_invoices(self):
        res=super(SaleAdvancePaymentInv,self).create_invoices()
        invoice=self.env['account.move'].browse(res['res_id'])
        users = self.env.ref('account.group_account_manager').users
        title = "Sale Order Invoice"
        message = f"Sale invoice  {invoice.name} is created"
        for user in users:
            self.env['bus.bus'].send_notification(user.partner_id,invoice._name,invoice.id,title,message)
        return res