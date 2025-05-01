from odoo import models, fields, api


class DynamicApproveConfig(models.Model):
    _name = 'dynamic.approve.config'

    name = fields.Char("Name")
    model_id = fields.Many2one('ir.model', "Model")
    approve_lines = fields.One2many('dynamic.approve.config.line', 'approve_config_id', string="Approve Levels")
    approval_levels = fields.Selection(
        [('1', '1 Approval'), ('2', '2 Approval'), ('3', '3 Approval'), ('4', '4 Approval'), ('5', '5 Approval')],
        string='Approval Level')

    _sql_constraints = [
        ('model_id_uniq', 'unique (model_id)', "Model already exists."),
    ]

    @api.onchange('approval_levels')
    def onchange_approval_levels(self):
        if self.approval_levels:
            for line in self.approve_lines:
                line.unlink()

            approval_levels = int(self.approval_levels)
            for approval_levels in range(1, approval_levels + 1):
                existing_line = self.env['dynamic.approve.config.line'].search(
                    [('approve_config_id', '=', self._origin.id), ('approval_levels', '=', str(approval_levels))])
                if not existing_line:
                    self.env['dynamic.approve.config.line'].create({
                        'approve_config_id': self._origin.id,
                        'approval_levels': str(approval_levels),
                        'model_id': self.model_id.id
                    })
            # for approval_level_del in range(approval_levels+1 , 6):
            #     print(approval_level_del,'approval_level_delapproval_level_del')
            #     existing_line = self.env['dynamic.approve.config.line'].search(
            #         [('approve_config_id', '=', self._origin.id), ('approval_levels', '=', str(approval_levels))],limit=1)
            #     if existing_line:
            #         existing_line.unlink()


class DynamicApproveConfigLines(models.Model):
    _name = 'dynamic.approve.config.line'

    approve_config_id = fields.Many2one('dynamic.approve.config', string="Approve Config",invisible=True)
    model_id = fields.Many2one('ir.model', string="Model",invisible=True)
    res_model = fields.Char("Res Model", related='model_id.model',invisible=True)
    approval_type = fields.Selection([('group', 'Group'), ('user', 'User')], 'Approval Type', default='user',invisible=True)
    domain = fields.Char("Domain",invisible=True)
    approval_levels = fields.Selection(
        [('1', '1 Approval'), ('2', '2 Approval'), ('3', '3 Approval'), ('4', '4 Approval'), ('5', '5 Approval')],
        string='Approval Level')
    groups_ids = fields.Many2many('res.groups', string='Groups',invisible=True)
    user_ids = fields.Many2many('res.users', string="Users")
