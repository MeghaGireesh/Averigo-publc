from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountLoanLine(models.Model):
    _name = "account.loan.line"
    _description = "Asset Loan Table Line"
    _order = "type, line_date"

    name = fields.Char(string="Loan Name", size=64, readonly=True)
    asset_id = fields.Many2one(comodel_name="account.asset", string="Equipment", required=True, ondelete="cascade")
    previous_id = fields.Many2one(comodel_name="account.loan.line", string="Previous Loan Line",
                                  readonly=True, )
    parent_state = fields.Selection(related="asset_id.state", string="State of Equipment", readonly=True)
    loan_base = fields.Float(related="asset_id.loan_base", string="Loan Base", readonly=True)
    amount = fields.Float(string="Loan Amount", digits="Account", required=True)
    remaining_value = fields.Float(compute="_compute_values", digits="Account", string="Next Period Depreciation",
                                   store=True, )
    loan_value = fields.Float(compute="_compute_values", digits="Account", string="Loan Already Paid", store=True)
    line_date = fields.Date(string="Date", required=True)
    line_days = fields.Integer(string="Days", readonly=True)
    move_id = fields.Many2one(comodel_name="account.move", string="Loan Entry", readonly=True)
    move_check = fields.Boolean(compute="_compute_move_check", string="Entry Posted", store=True)
    type = fields.Selection(
        selection=[("create", "Depreciation Base"), ("loan", "Loan"), ("remove", "Asset Removal"), ],
        readonly=True, default="loan")
    init_entry = fields.Boolean(string="Initial Balance Entry",
                                help="Set this flag for entries of previous fiscal years "
                                     "for which Odoo has not generated accounting entries.", )
    payment_id = fields.Many2one('account.payment')

    @api.depends("amount", "previous_id", "type")
    def _compute_values(self):
        dlines = self
        if self.env.context.get("no_compute_asset_line_ids"):
            # skip compute for lines in unlink
            exclude_ids = self.env.context["no_compute_asset_line_ids"]
            dlines = self.filtered(lambda l: l.id not in exclude_ids)
        for dline in dlines:
            if dline.type == 'loan':

                # Group depreciation lines per asset
                asset_id = dline.asset_id
                grouped_dlines = []
                if dline.asset_id.id == asset_id.id:
                    grouped_dlines.append(dline)

                for dlines in grouped_dlines:
                    loan_value = 0
                    remaining_value = 0
                    for i, dl in enumerate(dlines):
                        if i == 0:
                            loan_base = dl.loan_base
                            tmp = loan_base - dl.previous_id.remaining_value
                            loan_value = dl.previous_id and tmp or 0.0
                            remaining_value = loan_base - loan_value - dl.amount
                        else:
                            loan_value += dl.previous_id.amount
                            remaining_value -= dl.amount
                        dl.loan_value = loan_value
                        dl.remaining_value = remaining_value
            else:
                dline.loan_value = 0
                dline.remaining_value = 0

    @api.depends("move_id")
    def _compute_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    @api.onchange("amount")
    def _onchange_amount(self):
        if self.type == "loan":
            self.remaining_value = (self.loan_base - self.loan_value - self.amount)

    def write(self, vals):
        for dl in self:
            line_date = vals.get("line_date") or dl.line_date
            asset_lines = dl.asset_id.loan_line_ids
            if list(vals.keys()) == ["move_id"] and not vals["move_id"]:
                # allow to remove an accounting entry via the
                # 'Delete Move' button on the depreciation lines.
                if not self.env.context.get("unlink_from_asset"):
                    raise UserError(_("You are not allowed to remove an accounting entry "
                                      "linked to an asset."
                                      "\nYou should remove such entries from the asset."))
            elif list(vals.keys()) == ["asset_id"]:
                continue
            elif dl.move_id and not self.env.context.get("allow_asset_line_update") and not line_date:
                raise UserError(_("You cannot change a loan line "
                                  "with an associated accounting entry."))
            elif vals.get("init_entry"):
                check = asset_lines.filtered(
                    lambda l: l.move_check and l.type == "loan" and l.line_date <= line_date)
                if check:
                    raise UserError(_("You cannot set the 'Initial Balance Entry' flag "
                                      "on a loan line "
                                      "with prior posted entries."))
            elif vals.get("line_date"):
                if dl.type == "create":
                    check = asset_lines.filtered(lambda l: l.type != "create" and (
                            l.init_entry or l.move_check) and l.line_date < fields.Date.to_date(vals["line_date"]))
                    if check:
                        raise UserError(_("You cannot set the Asset Start Date "
                                          "after already posted entries."))
                else:
                    check = asset_lines.filtered(
                        lambda al: al != dl and (al.init_entry or al.move_check) and al.line_date > fields.Date.to_date(
                            vals["line_date"]))
                    if check:
                        raise UserError(_("You cannot set the date on a depreciation line "
                                          "prior to already posted entries."))
        return super().write(vals)

    def unlink(self):
        for dl in self:
            if dl.type == "create" and dl.amount:
                raise UserError(_("You cannot remove an asset line " "of type 'Depreciation Base'."))
            elif dl.move_id:
                raise UserError(_("You cannot delete a depreciation line with "
                                  "an associated accounting entry."))
            previous = dl.previous_id
            next_line = dl.asset_id.loan_line_ids.filtered(lambda l: l.previous_id == dl and l not in self)
            if next_line:
                next_line.previous_id = previous
        return super(AccountLoanLine, self.with_context(no_compute_asset_line_ids=self.ids)).unlink()

    def _setup_move_data(self, loan_date):
        asset = self.asset_id
        move_data = {
            "date": loan_date,
            "ref": "{} - {}".format(asset.name, self.name),
            "journal_id": asset.journal_id.id,
            "partner_id": asset.partner_id.id,
        }
        return move_data

    def _setup_move_line_data(self, loan_date, account, ml_type, move):
        asset = self.asset_id
        amount = self.amount
        analytic_id = False
        if ml_type == "loan":
            debit = amount < 0 and -amount or 0.0
            credit = amount > 0 and amount or 0.0
        elif ml_type == "expense":
            debit = amount > 0 and amount or 0.0
            credit = amount < 0 and -amount or 0.0
            analytic_id = asset.account_analytic_id.id
        move_line_data = {
            "name": asset.name,
            "ref": self.name,
            "move_id": move.id,
            "account_id": account.id,
            "credit": credit,
            "debit": debit,
            "journal_id": asset.journal_id.id,
            "partner_id": asset.partner_id.id,
            "analytic_account_id": analytic_id,
            "date": loan_date,
            "asset_id": asset.id, }
        return move_line_data

    def create_payment(self):
        for line in self:
            payment_method_id = self.env['account.payment.method'].search(
                [('payment_type', '=', 'outbound'), ('code', '=', 'manual')], limit=1)
            vals = {
                'invoice_ids': line.asset_id.move_id.ids,
                'partner_id': line.asset_id.move_id.partner_id.id,
                'communication': line.asset_id.move_id.name,
                'amount': line.amount,
                'journal_id': line.asset_id.move_id.journal_id.id,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'payment_reference': line.name,
                'payment_method_id': payment_method_id.id,
            }
            payment_id = self.env['account.payment'].create(vals)
            payment_id.post()
            move_line = payment_id.move_line_ids[0]
            line.with_context(allow_asset_line_update=True).write({
                "move_id": move_line.move_id.id,
                "payment_id": payment_id.id,
            })

    def create_move(self):
        created_move_ids = []
        asset_ids = set()
        ctx = dict(self.env.context, allow_asset=True, check_move_validity=False)
        for line in self:
            asset = line.asset_id
            loan_date = line.line_date
            am_vals = line._setup_move_data(loan_date)
            move = self.env["account.move"].with_context(ctx).create(am_vals)
            depr_acc = self.env['account.account'].search(
                [('name', '=', 'Bank'), ('internal_type', '=', 'liquidity'), ('internal_group', '=', 'asset')], limit=1)
            exp_acc = asset.account_loan_id
            aml_d_vals = line._setup_move_line_data(loan_date, depr_acc, "loan", move)
            self.env["account.move.line"].with_context(ctx).create(aml_d_vals)
            aml_e_vals = line._setup_move_line_data(loan_date, exp_acc, "expense", move)
            self.env["account.move.line"].with_context(ctx).create(aml_e_vals)
            move.post()
            line.with_context(allow_asset_line_update=True).write({"move_id": move.id})
            created_move_ids.append(move.id)
            asset_ids.add(asset.id)
        # we re-evaluate the assets to determine if we can close them
        for asset in self.env["account.asset"].browse(list(asset_ids)):
            if asset.company_currency_id.is_zero(asset.value_residual):
                asset.state = "close"
        return created_move_ids

    def open_move(self):
        self.ensure_one()
        return {
            "name": _("Journal Entry"),
            "view_mode": "tree,form",
            "res_model": "account.move",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": [("id", "=", self.move_id.id)],
        }

    def unlink_move(self):
        for line in self:
            # move = line.move_id
            payment = line.payment_id
            payment.action_draft()
            # move.with_context(force_delete=True, unlink_from_asset=True).unlink()
            # trigger store function
            line.with_context(unlink_from_asset=True).write({
                "move_id": False,
                "payment_id": False,
            })
            if line.parent_state == "close":
                line.asset_id.write({"state": "open"})
            elif line.parent_state == "removed" and line.type == "remove":
                line.asset_id.write({"state": "close", "date_remove": False})
                line.unlink()
        return True
