from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class AccountPaymentWizard(models.TransientModel):
    _name = 'account.payment.wizard'
    _description = 'Account Payment Wizard'

    # Define fields that you want to include in your wizard
    partner_id = fields.Many2one('res.partner', string='Receiving Partner', required=True)
    amount = fields.Float(string='Amount')
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today)
    payment_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')
    ], string='Payment Type', required=True, default='outbound')
    ref = fields.Char(
        string='Ref', 
        required=False)
    bank = fields.Many2one('account.journal', string='Paying Account', domain="[('type', 'in', ['bank', 'cash'])]",
                           help='Select the bank or cash journal for the payment.', required=True)
    expense_id = fields.Many2one(comodel_name="expense.intelbox", string="Expense Ref",
                                 default=lambda self: self._get_default_expense_intelbox())

    def _get_default_expense_intelbox(self):
        return self.env.context.get('default_expense_id', False)

    def create_payment(self):
        self.ensure_one()
        # Logic to create account.payment record
        payment_vals = {
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'payment_type': self.payment_type,
            'ref': self.ref,
            'journal_id': self.bank.id,
            # Add other necessary fields and values
        }
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()
        self.expense_id.expense_paid()

