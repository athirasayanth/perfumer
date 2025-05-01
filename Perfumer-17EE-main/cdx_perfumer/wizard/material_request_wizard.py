from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CdxMaterialRequestWizard(models.Model):
    _name = 'cdx.material.request.wizard'
    _description = "Daily Material Request Wizard"

    @api.model
    def default_get(self, fields_list):
        res = super(CdxMaterialRequestWizard, self).default_get(fields_list)
        mrp_id = self.env["mrp.production"].browse(self._context.get("active_id"))
        material_request_line = mrp_id.move_raw_ids.filtered(lambda l: l.select_line)
        material_lines = [
        (0, 0, {
            'product_id': material.product_id.id,
            'quantity': material.product_uom_qty,
            'available_quantity':material.product_qty_available,
            'product_uom_id': material.product_id.uom_id.id,
            'mrp_material_line':material.id,
        })
        for material in material_request_line
    ]
        mrp_id.move_raw_ids.select_line=False
        res['material_line'] = material_lines
        res['material_request_id'] = mrp_id.id
        res['location_id'] = mrp_id.location_src_id.id
        return res

    def get_default_dest(self):
        location = self.env['stock.location'].sudo().search([('is_main', '=', True)],limit=1)
        if location:
            return location
        else:
            raise UserError(_("Please configure the master warehouse!"))

    type_of_request = fields.Selection([('material','Material Transfer'),('requisition','Purchase Request')], default='material', required=True,readonly=True)
    location_id = fields.Many2one('stock.location', "Requesting Location")
    dest_location_id = fields.Many2one('stock.location', "Master Location",default=get_default_dest)
    material_request_id = fields.Many2one('mrp.production', "Job")
    material_line = fields.One2many('cdx.material.request.wizard.line','request_wizard_id', string="Materials")

    #for multilocation request for a single product
    is_multi_location_request = fields.Boolean(string="Is multi location", default=False, store=True)
    product_id = fields.Many2one('product.product', string="Product")
    available_quantity = fields.Float(string="Demand/Remaining")
    origin  = fields.Char('Source Document',copy=False,readonly=True)


    def action_create_material_request(self, material_line):
        if self.is_multi_location_request:
            total_quantity = sum(self.material_line.mapped('quantity'))
            if total_quantity >self.available_quantity:
                raise UserError("Quantity exceeds actual requested quantity")
            for material in material_line:
                line_vals = [(0, 0, {
                                            'product_id': material.product_id.id,  # Ensure to use .id
                                            'quantity': material.quantity,
                                            'product_uom_id': material.product_id.uom_id.id
                                        })]
                material_request = self.env['material.request'].sudo().create({
                    'location_id': self.location_id.id,
                    'dest_location_id': material.dest_location_id.id,
                    'state': 'draft',
                    'material_ids': line_vals,
                    'company_id':material.dest_location_id.company_id.id,
                    'manual_creation':False,
                    'from_amr':True,
                    'origin':self.origin,
                    'job_id':self.material_request_id.id
                })
                self.material_request_id.material_request_id = material_request.id
                # if material_request.dest_location_id.is_main:
                #     material_request.action_request()
                # elif self.env.user.has_group('cdx_iec_material_req.group_manager_material_request'):
                #     material_request.action_request()                    

            mrp_material_line = self.material_line.mapped('mrp_material_line')[0]
            updated_quantity = mrp_material_line.available_quantity - total_quantity
            mrp_material_line.write({'available_quantity':updated_quantity})
            mrp_material_line.select_line = False


        else:
            material_request_line = []
            for material in material_line:
                line_vals = (0, 0, {
                            'product_id': material.product_id.id,  # Ensure to use .id
                            'quantity': material.quantity,
                            'product_uom_id': material.product_id.uom_id.id
                        })
                material_request_line.append(line_vals)
            if material_request_line:  # Only create if there are lines to add
                material_request = self.env['material.request'].sudo().create({
                    'location_id': self.location_id.id,
                    'dest_location_id': self.dest_location_id.id,
                    'state': 'draft',
                    'material_ids': material_request_line,
                    'company_id':self.dest_location_id.company_id.id,
                    'manual_creation':False,
                    'from_amr':True,
                    'origin':self.origin,
                    'job_id':self.material_request_id.id
                })
                # if material_request.dest_location_id.is_main:
                material_request.action_request()
                self.material_request_id.material_request_id = material_request.id
                # elif self.env.user.has_group('cdx_iec_material_req.group_manager_material_request'):
                #     material_request.action_request()  



    def action_create_request(self):
        material_line = self.material_line.filtered(lambda x: x.quantity != 0)
        if not material_line:
            raise UserError("Please set quantity to create a Material Request!")
        if self.type_of_request == 'material':
            self.action_create_material_request(material_line)
        else:
            self.action_create_requisition(material_line)


    def action_create_requisition(self, material_line):
        # Filter selected lines that are marked for creation
        material_line = self.material_line.filtered(lambda x: x.quantity != 0)
        
        if not material_line:
            raise UserError("Please set quantity to create a Material Requisition!")

        material_request_line = []
        for material in material_line:
            vendor_ids = material.product_id.seller_ids.ids
            partner_id = vendor_ids
            line_vals = (0, 0, {
                        'product_id': material.product_id.id,
                        'description':material.product_id.name,
                        'qty': material.quantity,
                        'uom': material.product_id.uom_id.id,
                        'partner_id':partner_id,
                    })
            material_request_line.append(line_vals)
        if material_request_line:  # Only create if there are lines to add
            requisition_id = self.env['cdx.material.purchase.requisition'].sudo().create({
                'requisition_line_ids': material_request_line,
                'company_id':self.material_request_id.company_id.id,
                'origin':self.origin,
                'material_request_id':self.material_request_id.id
            })
            # for requisition in requisition_id.requisition_line_ids:
            #     requisition.onchange_product_id()
            
            # for material in material_line:
                # updated_quantity = material.daily_material_line.available_quantity - material.quantity
                # material.daily_material_line.write({'available_quantity':updated_quantity})
                # material.daily_material_line.stock_line_id.write({'material_request_ids':[(4,material_request.id)]})
                # material.daily_material_line.select_line = False
            if requisition_id:
                self.material_request_id.requisition_id = requisition_id.id
                purchase_group=self.env.ref('purchase.group_purchase_user')
                title = "Purchase Requisition"
                activity_type=self.env.ref('cdx_perfumer.cdx_pur_req')                
                message = f"Purchase Request  {requisition_id.name} is created for you"
                for user in purchase_group.users:
                    notification = {
                    'activity_type_id': activity_type.id,
                    'res_id': requisition_id.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', '=', activity_type.res_model)],limit=1).id,
                    'icon': activity_type.icon,
                    'date_deadline': fields.Date.today(),
                    'user_id': user.id,
                    'note': 'Purchase Request Assigned to you'
                }
                    self.env['mail.activity'].create(notification)
                    self.env['bus.bus'].send_notification(user.partner_id[0],requisition_id._name,requisition_id.id,title,message)

class CdxMaterialRequestWizardLine(models.Model):
    _name = 'cdx.material.request.wizard.line'
    _description = "Material Request Wizard Line"

    request_wizard_id = fields.Many2one('cdx.material.request.wizard', "material request",invisible=True)
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="Quantity")
    available_quantity = fields.Float(string="Remaining Quantity")
    on_hand = fields.Float(string="On Quantity",compute='_compute_on_hand')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    mrp_material_line = fields.Many2one('stock.move', string="Materials",invisible=True)

    #for multilocation request for a single product
    dest_location_id = fields.Many2one('stock.location', "Master Location", store=True)

    @api.depends('request_wizard_id.dest_location_id','dest_location_id')
    def _compute_on_hand(self):
        for rec in self:
            if rec.request_wizard_id.is_multi_location_request:
                domain = [('product_id', '=', rec.product_id.id),('location_id','=',rec.dest_location_id.id)]
            else:
                domain = [('product_id', '=', rec.product_id.id),('location_id','=',rec.request_wizard_id.dest_location_id.id)]
            on_hand = self.env['stock.quant'].sudo().search(domain).quantity
            rec.on_hand = on_hand

    @api.onchange('quantity')
    def check_available_qty(self):
        if self.quantity > self.available_quantity and not self.request_wizard_id.is_multi_location_request:
            raise UserError("Quantity exceeds actual requested quantity")

    @api.onchange('request_wizard_id')
    def _onchange_request_wizard(self):
        print(self, self.request_wizard_id)
        if self.request_wizard_id and self.request_wizard_id.product_id:
            self.product_id = self.request_wizard_id.product_id
            self.product_uom_id = self.product_id.uom_id.id

    def get_warehouse_data(self):
        warehouse_ids = []
        data_ids = self.env['stock.quant'].sudo().search([('product_id', '=', self.id)])
        for data_id in data_ids:
            if data_id.location_id.location_id.name =="Virtual Locations" or data_id.location_id.location_id.name =="Partners":
                continue
            else:
                if data_id.quantity > 0:
                    location = {}
                    location['min_qty'] = self.env['stock.warehouse.orderpoint'].search([('product_id','=',self.id),('location_id','=',data_id.location_id.id)]).product_min_qty,
                    location['location_id'] = data_id.location_id.id,
                    location['location_name'] = data_id.location_id.display_name,
                    location['company'] = data_id.location_id.company_id.name,
                    location['quantity'] = data_id.quantity,
                    warehouse_ids.append(location)
        return warehouse_ids

    
    