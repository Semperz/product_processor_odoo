# -*- coding: utf-8 -*-
import json
from odoo import http, _
from odoo.http import request

class PrePresupuestoRPC(http.Controller):
    @http.route('/pre_presupuesto/process', type='json', auth='none', methods=['POST'])
    def process_pre_presupuesto(self, **payload):
        """
        Espera un JSON como:
        {
          "token": "...",
          "presupuesto_id": 42,
          "productos": [
            {"name": "Hoja A4 80g",    "product_id": 17, "processed": true,  "quantity": 10},
            {"name": "Cartulina Roja", "product_id": null, "processed": false, "quantity": 5},
            ...
          ]
        }
        """
        token_val = payload.get('token')
        cfg_token = request.env['ir.config_parameter'].sudo().get_param('pre_presupuesto.token')
        if token_val != cfg_token:
            return {'error': _("Token incorrecto")}

        presupuesto_id = payload.get('presupuesto_id')
        productos      = payload.get('productos') or []
        if not presupuesto_id or not isinstance(productos, list):
            return {'error': _("Faltan datos obligatorios (presupuesto_id o lista de productos).")}

        try:
            # Llama al método del modelo que crea el pre-presupuesto
            pre = request.env['pre.presupuesto'].sudo().create_from_rpc(presupuesto_id, productos)
        except Exception as e:
            return {'error': str(e)}

        return {'ok': True, 'pre_presupuesto_id': pre.id}

