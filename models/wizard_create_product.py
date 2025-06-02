# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PrePresupuestoLineCreateProductWizard(models.TransientModel):
    _name = "pre.presupuesto.line.create.product.wizard"
    _description = "Wizard para crear producto desde línea de Pre-Presupuesto"

    name     = fields.Char(string="Nombre", required=True)
    categ_id = fields.Many2one('product.category', string="Categoría", required=True)
    price_unit = fields.Float(string="Precio unitario", required=True)
    uom_id   = fields.Many2one(
        'uom.uom',
        string="Unidad medida",
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit')
    )
    line_id  = fields.Many2one('pre.presupuesto.line', string="Línea asociada", required=True)
    quantity = fields.Float(string="Cantidad requerida", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(PrePresupuestoLineCreateProductWizard, self).default_get(fields_list)
        active_line = self.env['pre.presupuesto.line'].browse(self.env.context.get('active_line_id'))
        if active_line:
            res.update({
                'name': active_line.name,
                'line_id': active_line.id,
                'quantity': active_line.quantity,
            })
        return res


    def action_create_product(self):
        self.ensure_one()
        line = self.line_id
        if not line or line.state != 'to_review':
            raise UserError(_("La línea no está disponible para crear producto."))
        # 1) Crear product.template y product.product
        product_tmpl = self.env['product.template'].create({
            'name': self.name,
            'categ_id': self.categ_id.id,
            'list_price': self.price_unit,
            'uom_id': self.uom_id.id,
            'uom_po_id': self.uom_id.id,
            # agrega aquí otros campos obligatorios...
        })
        product = self.env['product.product'].search([
            ('product_tmpl_id', '=', product_tmpl.id)], limit=1)
        # 2) Actualizar la línea
        line.write({
            'product_id': product.id,
            'state': 'created',
            'processed': True,
            'user_action': self.env.user.id,
            'date_action': fields.Datetime.now(),
        })
        # 3) Cerrar wizard
        return {'type': 'ir.actions.act_window_close'}
