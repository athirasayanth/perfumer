import pandas as pd
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
class CdxEstimate(models.Model):
    _name = 'cdx.estimation'
    _inherit=['mail.thread']

    name = fields.Char(string="name")
    estimation_date = fields.Date(string="Date",tracking=True)
    confirmed_date = fields.Date(string="Quotation Date",tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=False,tracking=True)
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity", readonly=False,tracking=True)
    state = fields.Selection([('draft','Draft'),('confirm','Confirmed'),('quotation','Quotation')], string="State", default="draft")
    estimation_ids = fields.One2many('cdx.estimation.line','estimation_id', string="Estimation Lines")
    total = fields.Float(string="Total", compute="_compute_total_price")
    user_id = fields.Many2one('res.users', string="Salesperson",tracking=True)
    assign_user_id = fields.Many2one('res.users', string="Assigned salesperson",tracking=True)
    sale_id = fields.Many2one('sale.order', string="Sale Order",tracking=True)
    cdx_is_quotation_assigned = fields.Boolean(string="Is Quotation User Assigned")
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('estimation.code') or _("New")

        return super(CdxEstimate,self).create(vals_list)
    
    @api.depends('estimation_ids')
    def _compute_total_price(self):
        for total in self:
            total_price = 0 
            for line in total.estimation_ids:
                total_price += line.subtotal
            total.total = total_price
   
    def action_view_sale_order(self):
        self.ensure_one()

        if not self.sale_id:
            raise UserError('No sales order is linked to this estimation.')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('cdx_estimation_id', '=', self.id)],
            'target': 'current', 
        }
    def action_create_quotation(self):
        self.ensure_one()
        order_lines = []
        for line in self.estimation_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.unit_cost_fc,  # Use the price from estimation
                'cdx_estimation_line_id': line.id,  # Optionally link the line to the sale order line
                'cdx_estimation_id':self.id,
            }))
        sale_order = self.env['sale.order'].create({
                        'cdx_estimation_id':self.id,
                        'partner_id':self.partner_id.id,
                        # 'user_id':self.assign_user_id.id,
                        # 'order_line': order_lines
                        })
        title = "Quotation"
        message = f"Quotation  {sale_order.name} Assigned to You"
        self.env['bus.bus'].send_notification(self.assign_user_id.partner_id,sale_order._name,sale_order.id,title,message)
        self.write({'state':'quotation',
            'sale_id':sale_order.id,
            'confirmed_date':fields.Date.today()})
        return self.action_view_sale_order()
    
    def cdx_assign_user_to_quotation(self):

        self.sale_id.sudo().user_id = self.assign_user_id.id
        title = "Sale Quotation"
        message = f"Sale  {self.sale_id.name} Assigned to You"
        self.env['bus.bus'].send_notification(self.assign_user_id.partner_id,self.sale_id._name,self.sale_id.id,title,message)
        self.cdx_is_quotation_assigned = True
    
    def action_confirm(self):
        self.write({'state':'confirm'})
    
    def action_import_estimation_lines(self):
        file_upload = fields.Binary(string="Upload File")
   
    file_name = fields.Char(string="File Name")
    file_upload = fields.Binary(string="Upload File",attachment=True)
   
    def action_import_estimation_lines(self):
        """Processes the uploaded Excel file and updates estimation lines."""
        if not self.file_upload:
            raise UserError("Please upload a file before importing.")

        # Decode the uploaded file
        file_data = base64.b64decode(self.file_upload)
        df = pd.read_excel(BytesIO(file_data), sheet_name="Costing")
        df.columns = df.columns.str.replace("\n", " ", regex=True)
        # Ensure all required columns exist
        # required_cols = ["Sr. No", "Part Code", "Qty", "Unit Cost(FC)", "Total Selling Price(S.P)"]
        # missing_columns = [col for col in required_cols if col not in df.columns]
        # if missing_columns:
        #     raise UserError(f"Missing columns in file: {', '.join(missing_columns)}")

        # Process data and update estimation lines
        estimation_lines = []
        for _, row in df.iterrows():
            sr_value = str(row.get("Sr. No", "")).strip()  # Convert to string for checking
            if sr_value.isalpha():  # Section Heading (Alphabetic SR)
                estimation_lines.append((0, 0, {
                    'display_type': 'line_section',
                    'name': row.get("Product Description", ""),
                }))
            else:  # Normal Estimation Line
                # if pd.isna(row["Part Code"]):  # Skip empty part codes
                #     continue
                product_id = self.env['product.product'].sudo().search([('name','=',row.get("Product Description", ""))],limit=1)
                estimation_lines.append((0, 0, {
                    'name':row.get("Product Description", ""),
                    'product_id':product_id.id,
                    'part_code': row.get("Part Code", ""),
                    'product_uom_qty': row.get("Qty", 1) or 1,
                    'unit_cost_fc': row.get("Unit Cost (FC)", 0) or 0,
                    'unit_cost_usd':row.get("Unit Cost (USD)  ", 0),
                    'vendor_disc':row.get("Std Vendor  Discount %", 0),
                    'hw_sw':row.get("Hard Ware  or  Software", 0),
                    'unit_sale_price': row.get("Unit S.P", 0) or 0,
                    'handling_charges':row.get("Handling Charges % ",0) or 0,
                    'ins_warr':row.get("Insurance+Warranty %",0) or 0,
                    'freight_per':row.get("Freight %",0) or 0,
                    'cd_wh_tax_per':row.get("Customs Duty / Withholding Tax  %",0) or 0,
                    'finance_charges_per':row.get("Finance Charges %",0) or 0,
                    'delivery_charges_per':row.get("Delivery Charges %",0) or 0,
                    'other_costs_per':row.get("Other Costs %",0) or 0,
                    'markup':row.get('Markup %',0) or 0
                }))

        if estimation_lines:
            self.write({'estimation_ids': estimation_lines})
        else:
            raise UserError("No valid estimation lines foundd in the file.")

        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Estimation lines and sections imported successfully!",
                'type': 'rainbow_man',
            }
        }
class CdxEstimateLine(models.Model):
    _name = 'cdx.estimation.line'

    
    is_selected  = fields.Boolean("Select")
    estimation_id = fields.Many2one('cdx.estimation', string="Estimation")
    sequence = fields.Integer(string="Sequence")
    product_id = fields.Many2one('product.product', string="Product")
    name = fields.Char(string="Description")
    part_code = fields.Char(string="Part Code")
    product_uom_qty = fields.Float(string="Quantity")
    hw_sw = fields.Selection([('',''),('HW', 'HW'), ('SW', 'SW')],string='HW or SW',default="HW")
    product_uom_id = fields.Many2one('uom.uom', string="UoM")
    for_currency_id = fields.Many2one('res.currency', string="Foreign Currency")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal")
    display_type = fields.Selection([('line_section', "Section"),('line_note', "Note")], default=False)
    markup = fields.Float(string="Markup(%)")
    unit_cost_usd = fields.Float(string="Unit Cost (USD)")
    unit_cost_fc = fields.Float(string="Unit Cost (FC)")
    vendor_addl_disc = fields.Float(string="Addl Vendor Disc %")
    unit_cost_after_addl_disc = fields.Float(string="Unit Cost After Addl disc",compute="_compute_total_cost_after_disc")
    vendor_disc = fields.Float(string="Std Vendor Disc %")
    total_cost = fields.Float(string="Total Cost",compute="_compute_total_cost")
    handling_charges = fields.Float(string="Handling Charges %")
    handling_charges_amt = fields.Float(string="Handling Charges Amount",compute="_compute_handling_charges")
    markup_cost = fields.Float(string="Markup Cost", compute="_compute_markup_cost") 
    negotiation = fields.Float(string="Negotiation(%)")
    negotiation_amount = fields.Float(string="Negotiation Amount", compute="_compute_negotiation_amount")    
    ins_warr  = fields.Float("Insur + Wnty %")
    ins_warr_amt  = fields.Float("Insur + Wnty Amount",compute="_compute_ins_warr_amount")
    freight_per = fields.Float(string="Freight(%)")
    freight_amount = fields.Float(string="Freight Amount",compute="_compute_freight_amount")
    cd_wh_tax_per = fields.Float(string="CD / WH Tax(%)")
    cd_wh_tax_amt = fields.Float(string="CD / WH Tax Amount",compute="_compute_tax_amount")
    finance_charges_per = fields.Float(string="Finance Charges (%)")
    finance_charges_amt = fields.Float(string="Finance Amount",compute="_compute_finance_charges")
    delivery_charges_per = fields.Float(string="Delivery Charges (%)")
    delivery_charges_amt = fields.Float(string="Delivery Charges Amount",compute="_compute_delivery_charges")
    other_costs_per = fields.Float(string="Other Cost  (%)")
    other_costs_amt = fields.Float(string="Other Cost  Amount",compute="_compute_other_cost_charges")
    unit_landed_cost = fields.Float(string="Unit Landed Cost",compute="_compute_unit_landed_cost")
    total_landed_cost = fields.Float(string="Total Landed Cost Amount",compute="_compute_total_landed_cost")
    unit_sale_price = fields.Float(string="Unit S.P",compute="_compute_unit_sale_price",digits='Product Price')
    price_subtotal = fields.Float(string="Total Selling Price",compute="_compute_total_sale_price",digits='Product Price')
    
    
    @api.depends('vendor_disc','unit_cost_fc')
    def _compute_total_cost_after_disc(self):
        for line in self:
            line.unit_cost_after_addl_disc = line.unit_cost_fc-(line.unit_cost_fc * line.vendor_disc)
    
    @api.depends('product_uom_qty','unit_cost_after_addl_disc')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.product_uom_qty * line.unit_cost_after_addl_disc
            
    
    @api.depends('handling_charges','total_cost')
    def _compute_handling_charges(self):
        for line in self:
            line.handling_charges_amt = line.handling_charges * line.total_cost

    @api.depends('ins_warr','handling_charges_amt','total_cost')
    def _compute_ins_warr_amt(self):
        for line in self:
            line.ins_warr_amt = (line.total_cost + line.handling_charges_amt) * line.ins_warr
    
    
    @api.depends('freight_per','ins_warr_amt','handling_charges_amt','total_cost')
    def _compute_freight_amount(self):
        for line in self:
            line.freight_amount = (line.ins_warr_amt + line.total_cost + line.handling_charges_amt) * line.freight_per
   
    
    @api.depends('ins_warr_amt','handling_charges_amt','total_cost')
    def _compute_ins_warr_amount(self):
        for line in self:
            line.ins_warr_amt = (line.freight_amount + line.total_cost + line.handling_charges_amt) * line.ins_warr_amt
   
    @api.depends('cd_wh_tax_per','ins_warr_amt','handling_charges_amt','freight_amount','total_cost')
    def _compute_tax_amount(self):
        for line in self:
            line.cd_wh_tax_amt = (line.ins_warr_amt + line.total_cost + line.handling_charges_amt + line.freight_amount) * line.cd_wh_tax_per
   

    @api.depends('finance_charges_per','cd_wh_tax_amt','ins_warr_amt','handling_charges_amt','freight_amount','total_cost')
    def _compute_finance_charges(self):
        for line in self:
            line.finance_charges_amt = (line.cd_wh_tax_amt + line.ins_warr_amt + line.total_cost + line.handling_charges_amt + line.freight_amount) * line.finance_charges_per
   
    @api.depends('delivery_charges_per','finance_charges_amt','cd_wh_tax_amt','ins_warr_amt','freight_amount','total_cost')
    def _compute_delivery_charges(self):
        for line in self:
            line.delivery_charges_amt = (line.cd_wh_tax_amt + line.ins_warr_amt + line.total_cost + line.finance_charges_amt + line.freight_amount) * line.delivery_charges_per
   
   
    @api.depends('other_costs_per','delivery_charges_amt','handling_charges_amt','finance_charges_amt','cd_wh_tax_amt','ins_warr_amt','freight_amount','total_cost')
    def _compute_other_cost_charges(self):
        for line in self:
            line.other_costs_amt = (line.delivery_charges_amt + line.handling_charges_amt + line.cd_wh_tax_amt + line.ins_warr_amt + line.total_cost + line.finance_charges_amt + line.freight_amount) * line.other_costs_per
    
    
    
    @api.depends('product_uom_qty','other_costs_amt','delivery_charges_amt','handling_charges_amt','finance_charges_amt','cd_wh_tax_amt','ins_warr_amt','freight_amount','total_cost')
    def _compute_unit_landed_cost(self):
        for line in self:
            line.unit_landed_cost = (line.other_costs_amt + line.delivery_charges_amt + line.handling_charges_amt + line.cd_wh_tax_amt + line.ins_warr_amt + line.total_cost + line.finance_charges_amt + line.freight_amount) * line.product_uom_qty
    
    
    @api.depends('unit_landed_cost','product_uom_qty')
    def _compute_total_landed_cost(self):
        for line in self:
            line.total_landed_cost = line.unit_landed_cost * line.product_uom_qty
   
    
    
    @api.depends('markup','unit_landed_cost')
    def _compute_unit_sale_price(self):
        for line in self:
            line.unit_sale_price = line.unit_landed_cost /(1- line.markup)
    
    
    @api.depends('unit_sale_price','product_uom_qty')
    def _compute_total_sale_price(self):
        for line in self:
            line.price_subtotal = line.unit_sale_price  * line.product_uom_qty
   
   
   
    remaining_qty = fields.Float(string="Remaining Quantity",compute="_compute_remaining_qty",store=True)

    sale_order_line_estimation_ids = fields.One2many('sale.order.line.estimation', 'estimation_line_id', string="Used in Sale Orders")

    @api.depends('product_uom_qty', 'sale_order_line_estimation_ids.product_uom_qty')
    def _compute_remaining_qty(self):
        for record in self:
            used_qty = sum(record.sale_order_line_estimation_ids.mapped('product_uom_qty'))
            record.remaining_qty = record.product_uom_qty - used_qty
   
   
    # ----------------------------------------------
            
    @api.depends('markup','total_cost')
    def _compute_markup_cost(self):
        for line in self:
            markup_per_qty = line.total_cost * line.markup/100
            line.markup_cost = markup_per_qty
    
    @api.depends('total_cost','negotiation')
    def _compute_negotiation_amount(self):
        for line in self:
            neg_per_qty = line.total_cost * line.negotiation/100
            line.negotiation_amount =neg_per_qty
    
    @api.depends('total_cost','product_uom_qty')
    def _compute_subtotal(self):
        for line in self:
            total_cost = line.total_cost + line.markup_cost - line.negotiation_amount
            line.subtotal = total_cost * line.product_uom_qty
    @api.onchange('product_id')
    def _onchange_description(self):
        for line in self:
            if line.product_id:
                if line.product_id.description_sale:
                    line.name = line.product_id.display_name + '\n' + line.product_id.description_sale
                else:
                    line.name = line.product_id.display_name
                    line.product_uom_id = line.product_id.uom_id.id

    @api.onchange('product_id')
    def onchange_unit_price(self):
        for line in self:
            if line.product_id:
                line.total_cost = line.product_id.standard_price
    @api.model_create_multi
    def create(self,vals_list):
        estimation_lines = super(CdxEstimateLine,self).create(vals_list)
        # for lines in estimation_lines:
        #     if not lines.name:
        #         raise UserError(_("Please set the description..."))
        return estimation_lines
    
    
    def action_add_estimation_line(self):
        """Add the selected estimation line to the sale order."""
        sale_order = self.env['sale.order'].search([('cdx_estimation_id', '=', self.estimation_id.id)], limit=1)
        if not sale_order:
            raise UserError(_("No related Sale Order found for this estimation."))

        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_id.id,
            'name': self.name,
            'product_uom_qty': self.product_uom_qty,
            'price_unit': self.unit_cost_fc,  # Use the estimation price
            'cdx_estimation_id': self.estimation_id.id,
        })

        return {'type': 'ir.actions.act_window_close'}
    
    
    
