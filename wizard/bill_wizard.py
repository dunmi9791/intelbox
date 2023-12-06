from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class CreateVendorBillWizard(models.TransientModel):
    _name = 'create.vendor.bill.wizard'
    _description = 'Create Vendor Bill Wizard'

    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, )
    invoice_date = fields.Date(string='Invoice Date', required=True)
    amount = fields.Float(string='Amount', required=True)
    description = fields.Char(string='Description')
    journal_id = fields.Many2one('account.journal', string='Paying Account',)
    # expense_id = fields.Many2one(comodel_name="expense.intelbox", string="Expense Ref",
    #                              default=lambda self: self._get_default_expense_intelbox())

    # def _get_default_expense_intelbox(self):
    #     return self.env.context.get('default_expense_id', False)

    @api.model
    def create_bill(self, _):
        for record in self:
            bill = self.env['account.move'].create({
                'type': 'in_invoice',
                'partner_id': record.vendor_id.id,
                'journal_id': record.journal_id.id,
                'invoice_date': record.invoice_date,
                'invoice_line_ids': [(0, 0, {
                    'name': record.description,
                    'quantity': 1,
                    'price_unit': record.amount,
                    # 'expense_id': record.expense_id.id,
                })],
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bill',
                'res_model': 'account.move',
                'res_id': bill.id,
                'view_mode': 'form',
            }
