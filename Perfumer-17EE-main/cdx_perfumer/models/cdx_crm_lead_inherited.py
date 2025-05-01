from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    same_shipping_address = fields.Boolean('Same As Billing Address')

    # Custom shipping address fields
    shipping_street = fields.Char('Shipping Street')
    shipping_street2 = fields.Char('Shipping Street2')
    shipping_city = fields.Char('Shipping City')
    shipping_state_id = fields.Many2one('res.country.state', 'Shipping State')
    shipping_zip = fields.Char('Shipping Zip')
    shipping_country_id = fields.Many2one('res.country', 'Shipping Country')

    customer_type = fields.Selection([
        ('new', 'New'),
        ('existing', 'Existing'),
        ('lead', 'Lead'),
        ('prospect', 'Prospect'),
    ], string='Customer Type')

    industry_type = fields.Char('Industry Type')

    customer_segment = fields.Selection([
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('distributor', 'Distributor'),
        ('vip', 'VIP'),
    ], string='Customer Segment')

    lead_source = fields.Selection([
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('event', 'Event'),
        ('walk_in', 'Walk-in'),
    ], string='Lead Source')

    credit_limit = fields.Monetary('Credit Limit', currency_field='company_currency_id')

    vat_number = fields.Char('Tax ID / VAT Number')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.vat_number = self.partner_id.vat

    company_currency_id = fields.Many2one(
        'res.currency', string='Company Currency',
        default=lambda self: self.env.company.currency_id.id, readonly=True)

    preferred_contact_method = fields.Selection([
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp')
    ], string='Preferred Contact Method')

    marketing_opt_in = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO'),
    ], string='Marketing Opt-in Status')

    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms'
    )

    customer_id = fields.Char(string='Customer ID', readonly=True, copy=False, index=True, default=lambda self: 'New')

    first_contact_date = fields.Datetime(string='First Contact Date', readonly=True)

    last_contact_date = fields.Datetime(string='Last Contact Date', readonly=True)

    @api.onchange('same_shipping_address', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _onchange_same_shipping_address(self):
        if self.same_shipping_address:
            self.shipping_street = self.street
            self.shipping_street2 = self.street2
            self.shipping_city = self.city
            self.shipping_state_id = self.state_id
            self.shipping_zip = self.zip
            self.shipping_country_id = self.country_id
        else:
            self.shipping_street = ""
            self.shipping_street2 = ""
            self.shipping_city = ""
            self.shipping_state_id = ""
            self.shipping_zip = ""
            self.shipping_country_id = ""


    @api.onchange('same_shipping_address', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _onchange_same_shipping_address(self):
        if self.same_shipping_address:
            self.shipping_street = self.street
            self.shipping_street2 = self.street2
            self.shipping_city = self.city
            self.shipping_state_id = self.state_id
            self.shipping_zip = self.zip
            self.shipping_country_id = self.country_id
    #
    # def create(self, vals):
    #     if isinstance(vals, list):  # If vals is a list of dicts
    #         for val in vals:
    #             if val.get('customer_id', 'New') == 'New':
    #                 val['customer_id'] = self.env['ir.sequence'].next_by_code('crm.lead.customer.id') or 'New'
    #             if not val.get('first_contact_date'):
    #                 val['first_contact_date'] = fields.Datetime.now()
    #     else:  # Single dict
    #         if vals.get('customer_id', 'New') == 'New':
    #             vals['customer_id'] = self.env['ir.sequence'].next_by_code('crm.lead.customer.id') or 'New'
    #         if not vals.get('first_contact_date'):
    #             vals['first_contact_date'] = fields.Datetime.now()
    #
    #     return super(CrmLead, self).create(vals)
