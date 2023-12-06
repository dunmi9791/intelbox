# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

from datetime import date



class ExpenseRequest(models.Model):
    _name = 'expense.intelbox'
    _rec_name = 'exp_no'
    _description = 'staff expense request and reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    exp_no = fields.Char(string="Expense Number",
                         default=lambda self: _('New'),
                         requires=False, readonly=True, )
    date = fields.Date(string="Date", required=True, track_visibility='onchange',)
    memo_to = fields.Many2one(comodel_name="res.users", string="TO", required=True,
                              domain=lambda self: [( "groups_id", "=", self.env.ref( "intelbox.group_approverequest_group" ).id )])
    copy_to = fields.Many2many(comodel_name="res.users", string="CC")
    subject = fields.Char(string="Subject", required=False, track_visibility='onchange',)
    request_from = fields.Many2one(comodel_name="res.users", string="From", readonly=True, default=lambda self: self.env.user)
    expenses = fields.One2many(
        'exprequest.expline', 'exprequest_id', 'Expenses',
        copy=True, readonly=True, states={'draft': [('readonly', False)]}, )
    amount_total = fields.Float('Total Requested/Approved', compute='_amount_total', store=True, track_visibility='onchange',)
    state = fields.Selection(string="",
                             selection=[('draft', 'draft'), ('Requested', 'Requested'), ('Unit Head Approve', 'Unit Approval'),
                                        ('Fin Approve', 'Fin Approved'),
                                        ('disburse', 'disbursed'),
                                        ('Rejected', 'Rejected'),], required=False,
                             copy=False, default='draft', readonly=True, track_visibility='onchange', )

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    related_bill = fields.Many2one('account.move', string='Related Bill', domain=[('journal_id', '=', 2 ), ('state', '=', 'posted')],
                                   readonly=False, copy=False)
    # invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    @api.depends('expenses.price_subtotal', )
    def _amount_total(self):
        for expenses in self:
            expenses.amount_total = sum(expense.price_subtotal for expense in expenses.expenses)

    @api.depends('related_bill')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.related_bill)

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('related_bill.expense_id', '=', self.id)],
            'context': {'create': False},
        }


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

    @api.model
    def create(self, vals):
        record = super(ExpenseRequest, self).create(vals)
        record.add_user_as_follower()
        return record

    def write(self, vals):
        result = super(ExpenseRequest, self).write(vals)
        self.add_user_as_follower()
        return result

    def add_user_as_follower(self):
        for record in self:
            user = record.memo_to
            if user:
                record.message_subscribe(partner_ids=[user.id])

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.related_bill.ids,
                'expense_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('exp_no', _('New')) == _('New'):
                vals['exp_no'] = self.env['ir.sequence'].next_by_code('increment_expense') or _('New')
        return super().create(vals_list)

    # @api.model
    # def create(self, vals):
    #     if vals.get('state') == 'Fin Approve' and not vals.get('related_bill'):
    #         raise ValidationError("The Related Bill is required in the Financial Approval  state.")
    #     return super(ExpenseRequest, self).create(vals)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'Fin Approve' and not self.related_bill:
            raise ValidationError("The Related Bill is required in the Financial Approval  state.")
        return super(ExpenseRequest, self).write(vals)


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


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     expense_id = fields.Many2one('expense.intelbox', string='Expense Request', readonly=True, copy=False)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'

    expense_id = fields.Many2one('expense.intelbox', string='Expense Request', readonly=True, copy=False)

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': first_batch_result['lines'],
                'batch': first_batch_result,
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'payment_values': {
                                **batch_result['payment_values'],
                                'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                            },
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        self.expense_id.expense_paid()
        return payments

