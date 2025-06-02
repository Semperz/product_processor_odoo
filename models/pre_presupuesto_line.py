# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PrePresupuestoLine(models.Model):
    _name = "pre.presupuesto.line"
    _description = "Línea Pre-Presupuesto"

    pre_id = fields.Many2one(
        'pre.presupuesto',
        string="Pre-Presupuesto",
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string="Nombre a validar", required=True, readonly=True)
    product_id = fields.Many2one('product.product', string="Producto detectado", readonly=True)
    quantity = fields.Float(string="Cantidad requerida", required=True, default=1.0)
    state = fields.Selection([
        ('to_review', 'Revisar'),
        ('accepted', 'Aceptado'),
        ('created', 'Creado'),
        ('discarded', 'Descartado'),
    ], string="Estado", default='to_review', index=True, readonly=True)
    processed = fields.Boolean(
        string="Procesado",
        help="True si ya está en estado distinto de 'to_review'"
    )
    user_action = fields.Many2one('res.users', string="Validado por", readonly=True)
    date_action = fields.Datetime(string="Fecha validación", readonly=True)

    # Estos campos no son obligatorios hasta crear el producto nuevo
    new_product_name = fields.Char(string="Nombre nuevo")
    new_categ_id = fields.Many2one('product.category', string="Categoría")
    new_price_unit = fields.Float(string="Precio unitario")
    new_uom_id = fields.Many2one(
        'uom.uom',
        string="Unidad medida",
        default=lambda self: self.env.ref('uom.product_uom_unit')
    )


    def action_accept(self):
        """Aceptar producto que ya existe."""
        for line in self:
            if line.state != 'to_review':
                continue
            if not line.product_id:
                raise UserError(_("No hay producto asociado para aceptar."))
            line.state = 'accepted'
            line.processed = True
            line.user_action = self.env.user.id
            line.date_action = fields.Datetime.now()


    def action_discard(self):
        """Descartar este producto."""
        for line in self:
            if line.state != 'to_review':
                continue
            line.state = 'discarded'
            line.processed = True
            line.user_action = self.env.user.id
            line.date_action = fields.Datetime.now()


    def action_open_create_wizard(self):
        """Abrir un modal para crear producto nuevo."""
        self.ensure_one()
        if self.state != 'to_review':
            return {}
        return {
            'name': _("Crear nuevo producto"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pre.presupuesto.line.create.product.wizard',
            'target': 'new',
            'context': {'active_line_id': self.id},
        }
