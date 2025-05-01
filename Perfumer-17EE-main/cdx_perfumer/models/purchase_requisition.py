# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import  UserError

class CdxMaterialPurchaseRequisition(models.Model):
    _name = 'cdx.material.purchase.requisition'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']      
    _order = 'id desc'
    
    #@api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete Purchase Requisition which is not in draft or cancelled or rejected state.'))
#                raise Warning(_('You can not delete Purchase Requisition which is not in draft or cancelled or rejected state.'))
        return super(CdxMaterialPurchaseRequisition, self).unlink()
    
    name = fields.Char(
        string='Number',
        index=True,
        readonly=1,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('purchase', 'Purchase Order Created'),
        # ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ],
        default='draft',
        track_visibility='onchange',
    )
    request_date = fields.Date(
        string='Requisition Date',
        default=fields.Date.today(),
        required=True,
    )

    requisiton_requested_id = fields.Many2one(
        'res.users',
        string='Requisition Requested',
        copy=True,default=lambda self: self.env.user.id,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        required=True,
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        'cdx.material.purchase.requisition.line',
        'requisition_id',
        string='Purchase Requisitions Line',
        copy=True,
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'cdx_requisition_id',
        string='Purchase Ordes',
    )
    request_location_id = fields.Many2one('stock.location', string="Request Location")
    material_request_id = fields.Many2one('mrp.production', "Job")
    material_id = fields.Many2one('material.request', "material")
    count_rfq = fields.Integer("", compute='_compute_purchase_rfq')
    count_po = fields.Integer("", compute='_compute_purchase_po')
    count_mr = fields.Integer("", compute='_compute_material_request')
    origin  = fields.Char('Source Document',copy=False,readonly=True)
    @api.depends('purchase_order_ids','purchase_order_ids.state')
    def _compute_purchase_rfq(self):
        for order in self:
            order.count_rfq = len(order.purchase_order_ids.filtered(lambda x:x.state in ['draft','sent']))
    
        count_rfq = fields.Integer("", compute='_compute_purchase_rfq')

    @api.depends('purchase_order_ids','purchase_order_ids.state')
    def _compute_purchase_po(self):
        for order in self:
            order.count_po = len(order.purchase_order_ids.filtered(lambda x:x.state in ['purchase','purchase_send','done']))

    def _compute_material_request(self):
        for order in self:
            order.count_mr = len(self.env['material.request'].search([('requisition_id','=',order.id)]))
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('cdx.purchase.requisition.seq') or _("New")
        res = super(CdxMaterialPurchaseRequisition, self).create(vals_list)
        return res

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        po_line_vals = {
                 'product_id': line.product_id.id,
                 'name':line.product_id.name,
                 'product_qty': line.qty,
                 'product_uom': line.uom.id,
                 'date_planned': fields.Date.today(),
                 'price_unit': line.product_id.standard_price,
                 'order_id': purchase_order.id,
                 'cdx_requisition_line_id': line.id
        }
        return po_line_vals

    def create_rfq(self):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))

            po_dict = {}
            title = "Purchase Quotation"
            users = self.env.ref('purchase.group_purchase_manager').users
            for line in rec.requisition_line_ids:
                if not line.partner_id:
                        raise UserError(_('Please enter atleast one vendor on Requisition Lines for Requisition Action Purchase'))
                for partner in line.partner_id:
                    if partner not in po_dict:
                        po_vals = {
                            'partner_id':partner.id,
                            'currency_id':rec.env.user.company_id.currency_id.id,
                            'date_order':fields.Date.today(),
                            'company_id':rec.company_id.id,
                            'cdx_requisition_id':rec.id,
                            'origin': rec.name,
                        }
                        purchase_order = purchase_obj.create(po_vals)
                        po_dict.update({partner:purchase_order})
                        po_line_vals = rec._prepare_po_line(line, purchase_order)
                        purchase_line_obj.sudo().create(po_line_vals)
                        message = f"Purchase Quotation  {purchase_order.name} is created"
                        for user in users:
                            self.env['bus.bus'].send_notification(user.partner_id,purchase_order._name,purchase_order.id,title,message)
                        purchase_order.action_rfq_send_direct()
                    else:
                        purchase_order = po_dict.get(partner)
                        po_line_vals = rec._prepare_po_line(line, purchase_order)
                        purchase_line_obj.sudo().create(po_line_vals)
                rec.state = 'purchase'
                rec.state = 'sent'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_show_qo(self):
        for rec in self:
            purchase_action = self.env.ref('purchase.purchase_rfq').sudo()
            purchase_action = purchase_action.read()[0]
            purchase_action['domain'] = str([('cdx_requisition_id','=',rec.id),('state','in',['draft','sent'])])
        return purchase_action

    def action_show_po(self):
        for rec in self:
            purchase_action = self.env.ref('purchase.purchase_rfq').sudo()
            purchase_action = purchase_action.read()[0]
            purchase_action['domain'] = str([('cdx_requisition_id','=',rec.id),('state','not in',['draft','sent'])])
        return purchase_action

    def action_show_mr(self):
        self.ensure_one()
        mr=self.env['material.request'].search([('requisition_id','=',self.id)])
        return {
            "name": _("Material Request"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "material.request",
            "type": "ir.actions.act_window",
            "target": "current",
            "res_id":mr.id if mr else False
        }


class MaterialPurchaseRequisitionLine(models.Model):
    _name = "cdx.material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'

    
    requisition_id = fields.Many2one(
        'cdx.material.purchase.requisition',
        string='Requisitions', ondelete="cascade"
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )

    description = fields.Char(
        string='Description',
        required=True,
    )
    qty = fields.Float(
        string='Quantity',
        default=1,
        required=True,
    )
    uom = fields.Many2one(
        'uom.uom',#product.uom in odoo11
        string='Unit of Measure',
        required=True,
    )
    partner_id = fields.Many2many(
        'res.partner',
        string='Vendors',
    )
    on_hand = fields.Float()
    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            rec.uom = rec.product_id.uom_id.id

        """ Update the partner_id field with the vendor_ids of the product's brand. """
        if self.product_id:

            self.partner_id = self.product_id.seller_ids.ids
        else:
            # If no brand is set, clear the partner_id field
            self.partner_id = [(5, 0, 0)]  # Clear the Many2many field


