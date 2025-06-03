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
    product_id = fields.Many2one('product.product', string="Producto detectado")
    quantity = fields.Float(string="Cantidad requerida", required=True, default=1.0)
    state = fields.Selection([
        ('to_review', 'Revisar'),
        ('accepted', 'Aceptado'),
        ('created', 'Creado'),
        ('discarded', 'Descartado'),
    ], string="Estado", default='to_review', index=True, readonly=True)
    processed = fields.Boolean(
        string="Procesado",
        help="True si ya está en estado distinto de 'to_review'",
        readonly=True
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

    def write(self, vals):
        """
        Antes de aplicar write, comprobamos si se intenta cambiar product_id o quantity
        cuando state != 'to_review'. Si es así, lanzamos UserError para que:
          1) Aparezca el mensaje de error.
          2) Tras cerrarlo, el campo vuelva automáticamente a su valor original.
        """
        for line in self:
            if line.state != 'to_review':
                # Si alguien intenta modificar product_id o quantity, lanzamos error
                if 'product_id' in vals or 'quantity' in vals:
                    raise UserError(_("Solo se puede modificar 'Producto' o 'Cantidad' cuando el estado es 'Revisar'."))
        return super(PrePresupuestoLine, self).write(vals)
    
    def unlink(self):
        """
        Solo permitir borrar la línea si está en estado 'to_review'.
        """
        for line in self:
            if line.state != 'to_review':
                raise UserError(_("Solo se pueden eliminar líneas en estado 'Revisar'."))
        return super(PrePresupuestoLine, self).unlink()


    def action_accept(self):
        """Aceptar producto que ya existe."""
        for line in self:
            if line.processed == True:
                raise UserError(_("La línea ya ha sido procesada."))
            if not line.product_id:
                raise UserError(_("No hay producto asociado para aceptar."))
            if line.state == 'discarded' or line.state == 'created' or line.state == 'accepted':
                raise UserError(_("La línea ya está en estado aceptado, creado o descartado."))
            line.state = 'accepted'
            line.processed = True
            line.user_action = self.env.user.id
            line.date_action = fields.Datetime.now()


    def action_discard(self):
        """Descartar este producto."""
        for line in self:
            if line.state != 'to_review':
                raise UserError(_("La línea debe estar en estado 'Revisar' para descartarla."))
            if line.processed == True:
                raise UserError(_("La línea ya ha sido procesada."))
            line.state = 'discarded'
            line.processed = True
            line.user_action = self.env.user.id
            line.date_action = fields.Datetime.now()


    def action_open_create_wizard(self):
        """Abrir un modal para crear producto nuevo."""
        self.ensure_one()
        if self.state != 'to_review':
            raise UserError(_("La línea debe estar en estado 'Revisar' para crear un nuevo producto."))
        return {
            'name': _("Crear nuevo producto"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pre.presupuesto.line.create.product.wizard',
            'target': 'new',
            'context': {'active_line_id': self.id},
        }
