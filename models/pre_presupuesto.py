# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta

class PrePresupuesto(models.Model):
    _name = "pre.presupuesto"
    _description = "Pre-Presupuesto (validación previa de productos)"

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        default=lambda self: _('Pre-Presupuesto')
    )
    presupuesto_id = fields.Many2one(
        'sale.order',
        string="Presupuesto destino",
        required=True,
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string="Creado por",
        default=lambda self: self.env.user,
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente validación'),
        ('done', 'Procesado'),
    ], string="Estado", default='draft', readonly=True, copy=False)
    line_ids = fields.One2many(
        'pre.presupuesto.line',
        'pre_id',
        string="Líneas",
        copy=False
    )
    date_create = fields.Datetime(
        string="Fecha creación",
        default=lambda self: fields.Datetime.now(),
        readonly=True
    )

    @api.model
    def create_from_rpc(self, presupuesto_id, products_list):
        # 1) Verificar que exista el presupuesto destino
        presupuesto = self.env['sale.order'].browse(presupuesto_id)
        if not presupuesto.exists():
            raise UserError(_("El presupuesto con ID %s no existe.") % presupuesto_id)

        # 2) Crear el pre-presupuesto en estado 'pending'
        pre = self.create({
            'presupuesto_id': presupuesto_id,
            'name': _('Pre-Presupuesto %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'state': 'pending'
        })

        # 3) Por cada producto en la lista, crear línea
        for item in products_list:
            name = (item.get('name') or "").strip()
            prod_id = item.get('product_id')
            processed_flag = item.get('processed', False)
            qty = item.get('quantity', 1.0)

            vals = {
                'pre_id': pre.id,
                'name': name,
                'quantity': qty,
            }
            if prod_id:
                product = self.env['product.product'].browse(prod_id)
                if product.exists():
                    vals['product_id'] = prod_id
                    if processed_flag:
                        vals['state'] = 'accepted'
                        vals['processed'] = True
                        vals['user_action'] = self.env.user.id
                        vals['date_action'] = fields.Datetime.now()
                    else:
                        vals['state'] = 'to_review'
                        vals['processed'] = False
                else:
                    vals['state'] = 'to_review'
                    vals['processed'] = False
            else:
                vals['state'] = 'to_review'
                vals['processed'] = False

            self.env['pre.presupuesto.line'].create(vals)

        return pre

    def action_check_done(self):

        for record in self:
            if record.state != 'pending':
                raise UserError(_("Este Pre-Presupuesto ya ha sido procesado o no está en estado pendiente."))

        for record in self:
            if any(line.state == 'to_review' for line in record.line_ids):
                raise UserError(_("Aún hay líneas por revisar en este Pre-Presupuesto."))

            sale_order = record.presupuesto_id
            # 1) Calcular y asignar validity_date = hoy + 1 día
            hoy = fields.Date.context_today(self)
            fecha_validez = fields.Date.to_date(hoy) + timedelta(days=1)
            sale_order.write({'validity_date': fecha_validez})

            # 2) Crear líneas en el presupuesto real
            for line in record.line_ids.filtered(lambda l: l.state in ('accepted', 'created')):
                product = line.product_id
                if not product:
                    continue
                sale_order.order_line.create({
                    'order_id': sale_order.id,
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_uom_qty': line.quantity,
                    'price_unit': product.lst_price,
                })
            record.state = 'done'
        
        notif = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Presupuesto procesado",
                'message': "Se ha procesado el Pre-Presupuesto y se han creado las líneas en el presupuesto destino.",
                'type': 'success',
                'sticky': False,
            }
        }
        # 2) Abrir la vista tree de pre.presupuesto
        
        return notif

    def unlink(self):
        for pre in self:
            if pre.state == 'done':
                raise UserError(_("No puedes eliminar un Pre-Presupuesto ya procesado."))
        return super(PrePresupuesto, self).unlink()
