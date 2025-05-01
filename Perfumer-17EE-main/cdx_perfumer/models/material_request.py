from datetime import date
from odoo import models, fields, api, _
from odoo.fields import Command
from odoo.exceptions import MissingError, ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)



class MaterialRequest(models.Model):
    _name = 'material.request'
    _description='Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def get_default_dest(self):
        location = self.env['stock.location'].sudo().search([('usage', '=', 'internal')])
        if location:
            return location
        else:
            raise UserError(_("Please configure the master warehouse!"))

    def get_default_loc(self):
        location = self.env['stock.location'].sudo().search([('usage', '=', 'internal')])
        if location:
            return location

    name = fields.Char(string="Reference Number", readonly=True,copy=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('requested', 'Requested'),
                              ('approved', 'Approved'),
                              ('received', 'Received'),
                              ('declined', 'Declined'),
                              ('done', 'Done')], string='Status', default='draft', required=True,tracking=True)
    location_id = fields.Many2one('stock.location', "Requesting Location", store=True, required=True,
                                  default=get_default_loc,readonly=True )
    dest_location_id = fields.Many2one('stock.location', "Master Location", store=True, required=True,
                                       default=get_default_dest, domain="[('id','!=',location_id)]")
    src_user_id = fields.Many2one('res.users', string="Requesting Location User")
    dest_user_id = fields.Many2one('res.users', string="Master Location User")
    material_ids = fields.One2many('material.request.line', 'request_id')
    to_transit_picking_id = fields.Many2one('stock.picking', string="To Transit")
    from_transit_picking_id = fields.Many2one('stock.picking', string="To Transit")
    type = fields.Selection([('manual', 'Manual'), ('auto', 'Auto')], default='manual', )
    company_id = fields.Many2one('res.company', string="Company")
    user_check_src = fields.Boolean(string="src check", compute="get_src_user_flag")
    user_check_dest = fields.Boolean(string="dest check", compute="get_dest_user_flag")
    manual_creation = fields.Boolean(string="Manual Creation", default=True,help="user will click this incase of  manual creation from MMR view ",)
    from_amr =  fields.Boolean(string="From AMR",)
    origin = fields.Char(string="Source Document", readonly=True,tracking=True)
    requisition_id = fields.Many2one('cdx.material.purchase.requisition',string='Requisitions', ondelete="cascade")
    requisition_ids = fields.One2many('cdx.material.purchase.requisition','material_id', string="Requisitions")
    job_id  = fields.Many2one('mrp.production',string='Job',readonly=True)
    def get_dest_user_flag(self):
        for rec in self:
            if rec.dest_user_id and rec.dest_user_id.id == self.env.user.id:
                rec.user_check_dest = True
            else:
                rec.user_check_dest = False
    
    def get_src_user_flag(self):
        for rec in self:
            if rec.src_user_id and rec.src_user_id.id == self.env.user.id:
                rec.user_check_src = True
            else:
                rec.user_check_src = False
                

    def action_request(self):
        if self.type == 'manual':
            transit_loc = self.env['stock.location'].sudo().search([('usage', '=', 'transit'),], limit=1)
            move_lines = []
            picking_type_id = self.env['stock.picking.type'].sudo().search([('code', '=', 'internal'), ('company_id', '=', self.dest_location_id.company_id.id)], limit=1)
            if not picking_type_id:
                raise UserError(_("Please configure the Picking type!"))

            if self.location_id.company_id != self.dest_location_id.company_id:
                intertransit_type = 'inter_company'
            else:
                intertransit_type = 'inter_branch'
            for line in self.material_ids.filtered(lambda x: x.product_id != False):
                vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': self.dest_location_id.id,
                    'location_dest_id': self.location_id.id,
                    'product_uom_qty': line.quantity,
                    'quantity': line.quantity,
                    'company_id': self.dest_location_id.company_id.id,
                }
                move_lines.append((0, 0, vals))
            to_transit_picking = self.env['stock.picking'].with_context(manual_creation=self.manual_creation).sudo().create({
                'location_id': self.dest_location_id.id,
                'location_dest_id': transit_loc.id,
                'picking_type_id': picking_type_id.id,
                'state': 'draft',
                'move_ids_without_package': move_lines,
                'request_id': self.id,
                'company_id': self.dest_location_id.company_id.id,
                'intertransit_type':intertransit_type,
                'origin':self.name
            })
            self.to_transit_picking_id = to_transit_picking.id
            # target_user = self.env.ref('stock.group_stock_manager').users
            target_user = self.env['res.users'].search([('is_manager','=',True)],limit=1)
            src_user = self.env.user.id
            activity_type=self.env.ref('cdx_perfumer.notification_to_user_material_request')
            title = "Material Request"
            message = f"Material Request  {self.name} Assigned to You"
            for user in target_user:
                notification = {
                    'activity_type_id': activity_type.id,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', '=', activity_type.res_model)],limit=1).id,
                    'icon': activity_type.icon,
                    'date_deadline': fields.Date.today(),
                    'user_id': user.id,
                    'note': 'Material Request Created'
                }
                self.env['mail.activity'].create(notification)
                self.env['bus.bus'].send_notification(user.partner_id,self._name,self.id,title,message)
            if len(target_user):
                self.write({'dest_user_id': target_user[0].id})

            self.write({'src_user_id': src_user})
        self.write({'state': 'requested'})

    def action_approve(self):
        if self.type == 'manual':
            self.to_transit_picking_id.button_validate()
            if self.to_transit_picking_id.state == 'done':
                # raise UserError(_("Please confirm the Product Transfer!"))
                transit_loc = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], limit=1)
                if not transit_loc:
                    raise UserError(_("Please configure the transit!"))
                picking_type_id = self.env['stock.picking.type'].sudo().search([('code', '=', 'internal'), ('company_id', '=', self.location_id.company_id.id)], limit=1)
                if not picking_type_id:
                    raise UserError(_("Please configure the Picking type location!"))
                move_lines = []
                for line in self.to_transit_picking_id.move_ids_without_package:
                    vals = {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'location_id': transit_loc.id,
                        'location_dest_id': self.location_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'quantity': line.quantity,
                        'company_id': self.location_id.company_id.id,
                    }
                    move_lines.append((0, 0, vals))

                if self.location_id.company_id != self.dest_location_id.company_id:
                    intertransit_type = 'inter_company'
                else:
                    intertransit_type = 'inter_branch'
                from_transit_picking = self.env['stock.picking'].with_context(from_amr=self.from_amr,manual_creation=self.manual_creation).sudo().create({
                    'location_id': transit_loc.id,
                    'location_dest_id': self.location_id.id,
                    'picking_type_id': picking_type_id.id,
                    'state': 'draft',
                    'move_ids_without_package': move_lines,
                    'request_id': self.id,
                    'company_id': self.location_id.company_id.id,
                    'intertransit_type':intertransit_type,
                    'origin':self.name
                })
                self.from_transit_picking_id = from_transit_picking.id
                self.write({'state': 'approved'})
                target_user = self.src_user_id
                title = "Material Request Approval Confirmation"
                message = _('Material Request %s is Approved ...', self.name)
                activity_type=self.env.ref('cdx_perfumer.notification_to_user_material_request')
                for user in target_user:
                    notification = {
                        'activity_type_id': activity_type.id,
                        'res_id': self.id,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', '=', activity_type.res_model)], limit=1).id,
                        'icon': 'fa-pencil-square-o',
                        'date_deadline': fields.Date.today(),
                        'user_id': user.id,
                        'note': 'Material Request Approved'
                    }
                    self.env['mail.activity'].create(notification)
                    self.env['bus.bus'].send_notification(user.partner_id,self._name,self.id,title,message)

    def action_done(self):
        self.write({'state': 'done'})
        if self.job_id:
            # users = self.env.ref('mrp.group_mrp_manager').users
            users = self.env['res.users'].search([('is_production_manager','=',True)])
            title = "Production Job"
            for user in users:
                message = f"Material Request and stock movement For production job  {self.job_id.name} is completed"
                self.env['bus.bus'].send_notification(user.partner_id,self.job_id._name,self.job_id.id,title,message)

    def action_decline(self):
        self.write({'state': 'declined'})

    def action_receive(self):
        # if self.from_transit_picking_id.state != 'done':
        #     raise UserError(_("Please confirm the Product Receive!"))
        self.from_transit_picking_id.button_validate()
        self.write({'state': 'received'})

    def open_entries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "domain": [['request_id', '=', self.id]],
            'name': _('Stock Entries'),
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('material.request') or '/'
            
        ctx=dict(self.env.context)
        ctx['bypass_access'] = True
        self.env.context = ctx
        res = super(MaterialRequest, self).create(vals_list)
        return res


    def write(self,vals_list):
        ctx=dict(self.env.context)
        ctx['bypass_access'] = True
        self.env.context = ctx
        res = super(MaterialRequest,self).write(vals_list)
        return res
    
    
    def action_create_purchase_requisition(self):
        """Create a Purchase Requisition from a Material Request"""
        for rec in self:
            # if rec.requisition_id:
            #     raise UserError(_("A Purchase Requisition is already linked to this Material Request."))

            if not rec.material_ids:
                raise UserError(_("Please add at least one material request line."))
            selected_lines = rec.material_ids.filtered(lambda x: x.select_line)
            requisition_vals = {
                'name': self.env['ir.sequence'].next_by_code('cdx.purchase.requisition.seq') or 'New',
                'request_date': fields.Date.today(),
                'requisiton_requested_id': self.env.user.id,
                'company_id': self.env.company.id,
                'origin':'Job Purchase Request -'+self.origin + ' - ' + self.name,
                'request_location_id':self.location_id.id,
                'requisition_line_ids': [(0, 0, {
                    'product_id': line.product_id.id,
                    'description': line.product_id.name,
                    'qty': line.quantity,
                    'uom': line.product_uom_id.id,
                    # 'partner_id': [(6, 0, line.partner_id.ids)],  # Keep the vendors
                }) for line in selected_lines],
            }

            requisition = self.env['cdx.material.purchase.requisition'].create(requisition_vals)
            rec.requisition_id = requisition.id
            rec.requisition_ids = [Command.link(requisition.id)]
            selected_lines.write({'select_line': False})
            # rec.state = 'done'  # Mark Material Request as done

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cdx.material.purchase.requisition',
                'domain': [('id','in',rec.requisition_ids.ids)],
                'view_mode': 'tree,form',
                'target': 'current',
            }
            
    def action_open_purchase_requisition(self):
        
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'cdx.material.purchase.requisition',
                'res_id': self.requisition_ids.ids,
                'view_mode': 'tree,form',
                'target': 'current',
            }
    
    def action_open_mrp_production(self):
        self.ensure_one()
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'res_id': self.job_id.id if self.job_id else False,
                'view_mode': 'form',
                'target': 'current',
            }
    @api.model
    def get_stock_availability(self, product_id):
        """Fetch stock details from locations where is_main=True"""
        StockQuant = self.env["stock.quant"]
        StockLocation = self.env["stock.location"]

        # Get locations where is_main=True
        main_locations = StockLocation.search([("is_main", "=", True)])

        if not main_locations:
            return {"stock_details": [], "total_qty": 0}

        # Fetch stock details from those locations
        quants = StockQuant.search([
            ("location_id", "in", main_locations.ids),
            ("product_id", "=", product_id),
        ])

        stock_details = []
        total_qty = 0

        for quant in quants:
            stock_details.append({
                "quantity": quant.available_quantity,
                "location_name": quant.location_id.complete_name,
            })
            total_qty += quant.available_quantity

        return {"stock_details": stock_details, "total_qty": total_qty}
class MaterialRequestLine(models.Model):
    _name = 'material.request.line'

    request_id = fields.Many2one('material.request', "material request", )
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Quantity", required=True,digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id',string='Unit of Measure',required=True,store=True,readonly=False)
    pro_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',related='product_id.uom_id' )
    uom_po_id = fields.Many2one('uom.uom', string='Unit of Measure',related='product_id.uom_po_id')
    on_hand = fields.Float(compute="_compute_onhand_check")
    received_qty = fields.Float(string="Received Qty", readonly=True)
    select_line = fields.Boolean(string="Select", default=False)
    @api.depends('product_id')
    def _compute_onhand_check(self):
        for line in self:
            line.on_hand = 0
            request_id = line.request_id
            quant_ids = self.env['stock.quant'].sudo().search([('product_id','=',line.product_id.id),
                        ('location_id.usage','=','internal'),
                        ('location_id.company_id','=',request_id.dest_location_id.company_id.id),('location_id','=',request_id.location_id.id)])
            on_hand = sum(quant.quantity - quant.reserved_quantity for quant in quant_ids)
            line.on_hand = on_hand