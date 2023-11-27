# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import date



class ExpenseRequest(models.Model):
    _name = 'expense.intelbox'
    _rec_name = 'exp_no'
    _description = 'staff expense request and reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    exp_no = fields.Char(string="Expense Number",
                         default=lambda self: _('New'),
                         requires=False, readonly=True, )
    date = fields.Date(string="Date", required=True, )
    memo_to = fields.Many2one(comodel_name="res.users", string="TO", required=True,
                              domain=lambda self: [( "groups_id", "=", self.env.ref( "intelbox.group_approverequest_group" ).id )])
    copy_to = fields.Many2many(comodel_name="res.users", string="CC")
    subject = fields.Char(string="Subject", required=False,)
    request_from = fields.Many2one(comodel_name="res.users", string="From", readonly=True, default=lambda self: self.env.user)
    expenses = fields.One2many(
        'exprequest.expline', 'exprequest_id', 'Expenses',
        copy=True, readonly=True, states={'draft': [('readonly', False)]}, )
    amount_total = fields.Float('Total Requested/Approved', compute='_amount_total', store=True)
    state = fields.Selection(string="",
                             selection=[('draft', 'draft'), ('Requested', 'Requested'), ('Unit Head Approve', 'Unit Approval'),
                                        ('Fin Approve', 'Fin Approved'),
                                        ('disburse', 'disbursed'),
                                        ('Rejected', 'Rejected'),], required=False,
                             copy=False, default='draft', readonly=True, track_visibility='onchange', )

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)





    @api.depends('expenses.price_subtotal', )
    def _amount_total(self):
        for expenses in self:
            expenses.amount_total = sum(expense.price_subtotal for expense in expenses.expenses)


    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'Requested'),
                   ('Requested', 'Unit Head Approve'),
                   ('Requested', 'Rejected'),
                   ('Requested', 'draft'),
                   ('Unit Head Approve', 'Fin Approve'),
                   ('Unit Head Approve', 'Rejected'),
                   ('Fin Approve', 'Rejected'),
                   ('Fin Approve', 'disburse'),
                   ('disburse', 'disburse'),
                   ]
        return (old_state, new_state) in allowed


    def change_state(self, new_state):
        for request in self:
            if request.is_allowed_transition(request.state, new_state):
                request.state = new_state
            else:
                msg = _('Moving from %s to %s is not allowed') % (request.state, new_state)
                raise UserError(msg)

    def expense_request(self):
        self.change_state('Requested')

    def unit_expense_approve(self):
        self.change_state('Unit Head Approve')

    def expense_fin_approve(self):
        self.change_state('Fin Approve')

    def expense_paid(self):
        self.change_state('disburse')

    def expense_reject(self):
        self.change_state('Rejected')

    def expensefin_reject(self):
        self.change_state('Rejected')



    def reset_draft(self):
        self.change_state('draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('exp_no', _('New')) == _('New'):
                vals['exp_no'] = self.env['ir.sequence'].next_by_code('increment_expense') or _('New')
        return super().create(vals_list)




class ExpenserequestLine(models.Model):
    _name = 'exprequest.expline'

    _description = 'Expense line items'

    name = fields.Char()
    exprequest_id = fields.Many2one(comodel_name="expense.intelbox", index=True, ondelete="cascade")
    item_id = fields.Many2one(comodel_name="expense.item", string="Item", required=True, ondelete="restrict", index=True)
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", required=False, default=1.0, )
    cost = fields.Float(string=" Unit Cost", required=False, )
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    date = fields.Date(string="Date", required=False, )

    @api.depends('cost', 'exprequest_id', 'quantity', 'name', )
    def _compute_price_subtotal(self):
        for expense in self:
            expense.price_subtotal = expense.cost * expense.quantity



class ExpenseItem(models.Model):
    _name = 'expense.item'
    _rec_name = 'name'
    _description = 'Items'

    name = fields.Char(string="Item")
    active = fields.Boolean('active', default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Item already exist')
    ]
