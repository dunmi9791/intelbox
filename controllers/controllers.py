# -*- coding: utf-8 -*-
# from odoo import http


# class Intelbox(http.Controller):
#     @http.route('/intelbox/intelbox', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/intelbox/intelbox/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('intelbox.listing', {
#             'root': '/intelbox/intelbox',
#             'objects': http.request.env['intelbox.intelbox'].search([]),
#         })

#     @http.route('/intelbox/intelbox/objects/<model("intelbox.intelbox"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('intelbox.object', {
#             'object': obj
#         })
