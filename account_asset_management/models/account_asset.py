import calendar
import logging
from datetime import date
from functools import reduce
from sys import exc_info
from traceback import format_exception

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class DummyFy(object):
    def __init__(self, *args, **argv):
        for key, arg in argv.items():
            setattr(self, key, arg)


class AccountAsset(models.Model):
    _name = "account.asset"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Equipment"
    _check_company_auto = True
    _order = "date_start desc, code, name"
    _rec_name = 'combine_name'

    account_move_line_ids = fields.One2many(comodel_name="account.move.line",
                                            inverse_name="asset_id",
                                            string="Entries", readonly=True,
                                            copy=False, )
    move_line_check = fields.Boolean(compute="_compute_move_line_check",
                                     string="Has accounting entries")
    name = fields.Char(string="Name",
                       related='equipment_name_id.name',
                       track_visibility="onchange")
    code = fields.Char(string="Equipment Code", size=32,
                       default=lambda self: _('New'), readonly=True)
    purchase_value = fields.Monetary(string="Purchase Value", readonly=True,
                                     states={"draft": [("readonly", False)]},
                                     help="This amount represent the initial value of the asset."
                                          "\nThe Depreciation Base is calculated as follows:"
                                          "\nPurchase Value - Salvage Value.",
                                     currency_field='company_currency_id',
                                     track_visibility="onchange")
    salvage_value = fields.Monetary(string="Salvage Value", digits="Account",
                                    readonly=True,
                                    states={"draft": [("readonly", False)]},
                                    help="The estimated value that an asset will realize upon "
                                         "its sale at the end of its useful life.\n"
                                         "This value is used to determine the depreciation amounts.")
    depreciation_base = fields.Monetary(compute="_compute_depreciation_base",
                                        digits="Account",
                                        string="Depreciation Base", store=True,
                                        help="This amount represent the depreciation base "
                                             "of the asset (Purchase Value - Salvage Value.", )
    value_residual = fields.Monetary(compute="_compute_depreciation",
                                     digits="Account",
                                     string="Residual Value",
                                     store=True)
    value_depreciated = fields.Monetary(compute="_compute_depreciation",
                                        digits="Account",
                                        string="Depreciated Value",
                                        store=True, )
    note = fields.Text("Note")
    profile_id = fields.Many2one(comodel_name="account.asset.profile",
                                 string="Asset Profile",
                                 change_default=True,
                                 states={"draft": [("readonly", False)]})
    group_ids = fields.Many2many(comodel_name="account.asset.group",
                                 relation="account_asset_group_rel",
                                 column1="asset_id", column2="group_id",
                                 string="Asset Groups", )
    date_start = fields.Date(string="Purchase Date", readonly=True,
                             required=True, default=fields.Date.today,
                             states={"draft": [("readonly", False)]},
                             help="You should manually add depreciation lines "
                                  "with the depreciations of previous fiscal years "
                                  "if the Depreciation Start Date is different from the date "
                                  "for which accounting entries need to be generated.", )
    date_remove = fields.Date(string="Asset Removal Date", readonly=True)
    state = fields.Selection(
        selection=[("draft", "Active"), ("open", "In Service"),
                   ("removed", "Inactive"), ('archived', 'Archived'),
                   ('out_repair', 'OutSide Repair')],
        string="Status",
        track_visibility="onchange",
        required=True, default="draft", copy=False, readonly=True,
        help="When an Equipment is created, the status is 'Active'.\n"
             "If the Equipment is Transfer to customer location the status will be 'In Service'.\n"
             "If the Equipment is Retire the status will be 'In Active' \n", )
    active = fields.Boolean(default=True)
    partner_id = fields.Char(string="Distributor", readonly=True,
                             track_visibility="onchange")
    method = fields.Selection(selection=lambda self: self.env[
        "account.asset.profile"]._selection_method(),
                              string="Computation Method", required=True,
                              readonly=True,
                              states={"draft": [("readonly", False)]},
                              default="linear",
                              help="Choose the method to use to compute "
                                   "the amount of depreciation lines.\n"
                                   "  * Linear: Calculated on basis of: "
                                   "Gross Value / Number of Depreciations\n"
                                   "  * Degressive: Calculated on basis of: "
                                   "Residual Value * Degressive Factor"
                                   "  * Degressive-Linear (only for Time Method = Year): "
                                   "Degressive becomes linear when the annual linear "
                                   "depreciation exceeds the annual degressive depreciation")
    method_number = fields.Integer(string="Number of Years", readonly=True,
                                   default=5,
                                   states={"draft": [("readonly", False)]},
                                   help="The number of years needed to depreciate your asset", )
    method_period = fields.Selection(
        selection=lambda self: self.env[
            "account.asset.profile"]._selection_method_period(),
        string="Period Length", required=True, readonly=True, default="year",
        states={"draft": [("readonly", False)]},
        help="Period length for the depreciation accounting entries")
    method_end = fields.Date(string="Ending Date", readonly=True,
                             states={"draft": [("readonly", False)]})
    method_progress_factor = fields.Float(string="Degressive Factor",
                                          readonly=True,
                                          states={
                                              "draft": [("readonly", False)]},
                                          default=0.3, )
    method_time = fields.Selection(selection=lambda self: self.env[
        "account.asset.profile"]._selection_method_time(),
                                   string="Time Method", required=True,
                                   readonly=True, default="year",
                                   states={"draft": [("readonly", False)]},
                                   help="Choose the method to use to compute the dates and "
                                        "number of depreciation lines.\n"
                                        "  * Number of Years: Specify the number of years "
                                        "for the depreciation.\n"
                                   # "  * Number of Depreciations: Fix the number of "
                                   # "depreciation lines and the time between 2 depreciations.\n"
                                   # "  * Ending Date: Choose the time between 2 depreciations "
                                   # "and the date the depreciations won't go beyond."
                                   )
    days_calc = fields.Boolean(string="Calculate by days", default=False,
                               help="Use number of days to calculate depreciation amount", )
    use_leap_years = fields.Boolean(string="Use leap years", default=False,
                                    help="If not set, the system will distribute evenly the amount to "
                                         "amortize across the years, based on the number of years. "
                                         "So the amount per year will be the "
                                         "depreciation base / number of years.\n "
                                         "If set, the system will consider if the current year "
                                         "is a leap year. The amount to depreciate per year will be "
                                         "calculated as depreciation base / (depreciation end date - "
                                         "start date + 1) * days in the current year.")
    prorata = fields.Boolean(string="Prorata Temporis", readonly=True,
                             states={"draft": [("readonly", False)]},
                             help="Indicates that the first depreciation entry for this asset "
                                  "have to be done from the depreciation start date instead "
                                  "of the first day of the fiscal year.", )
    depreciation_line_ids = fields.One2many(comodel_name="account.asset.line",
                                            inverse_name="asset_id",
                                            string="Depreciation Lines",
                                            copy=False, readonly=True,
                                            states={
                                                "draft": [("readonly", False)]})
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 required=True, readonly=True,
                                 default=lambda
                                     self: self._default_company_id())
    company_currency_id = fields.Many2one(comodel_name="res.currency",
                                          related="company_id.currency_id",
                                          string="Company Currency", store=True,
                                          readonly=True, )
    account_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Analytic account")
    asset_no = fields.Char('Asset No', track_visibility="onchange")
    manufacture = fields.Char('Manufacture', track_visibility="onchange")
    model_no = fields.Char('Model No', track_visibility="onchange",
                           related='equipment_model_no_id.name')
    warranty = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                string="warranty",
                                default="no",
                                required=True,
                                track_visibility="onchange")
    route_id = fields.Many2one('route.route', string="Route",
                               related='machine_location_id.warehouse_id.route')
    commission = fields.Float('Relative Commission Rate')
    meter_reading = fields.Char('Initial Meeter Reading')
    vandalism = fields.Float('Vandalism Escrow %')
    management_fee = fields.Float('Management Fee %')
    marketing_fee = fields.Float('Marketing Fee %')
    fuel_surcharge = fields.Float('Fuel Surcharge %')
    model = fields.Char('Model', track_visibility="onchange",
                        related='equipment_model_id.name')
    model_redable = fields.Boolean('Model Readable', default=False)

    serial_no = fields.Char('Serial No', copy=False, required=True,
                            track_visibility="onchange")
    serial_readable = fields.Boolean('Serial Readable', default=False)
    effective_date = fields.Date('Effective Date',
                                 default=fields.Date.context_today,
                                 required=True,
                                 help="Date at which the Equipment became effective. This date will be used to compute "
                                      "the Mean Time Between Failure.")
    warranty_date = fields.Date('Warranty Expiration Date',
                                track_visibility="onchange")
    color = fields.Integer(string='Color Index', default=1)
    scrap_date = fields.Date('Scrap Date')
    machine_type_id = fields.Many2one('account.asset.type',
                                      string="Equipment Type",
                                      ondelete='restrict',
                                      track_visibility="onchange")
    vending_type = fields.Selection([('machine_style', 'Def. Equipment Style')],
                                    string="Vending/Non Vending TYpe")
    management_style = fields.Selection(
        [('machine_style', 'Def. Equipment Style'),
         ('non_commerce', 'Non Commerce')],
        string="Equipment Style", default='machine_style')
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920,
                              track_visibility="onchange")
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    location_type = fields.Selection(
        [('micro_market', 'Micromarket'), ('order', 'Order')],
        string='Location Type',
        default="micro_market", readonly=True,
        states={'draft': [('readonly', False)]})
    micro_market_id = fields.Many2one('stock.warehouse', domain=[
        ('location_type', '=', 'micro_market')], readonly=True,
                                      states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse',
                                   domain=[('location_type', '=', 'view')],
                                   readonly=True,
                                   states={'draft': [('readonly', False)]})
    location_partner_id = fields.Many2one('res.partner', string="Customer",
                                          domain="[('is_customer', '=', True),('parent_id', '=', False),('type', '=', 'contact')]")
    activity_type = fields.Selection(
        [('install', 'Install'), ('remove', 'Remove'), ('exchange', 'Exchange'),
         ('retire', 'Retire')],
        string="Activity Type", default='install')
    equipment_name_id = fields.Many2one('equipment.name',
                                        string="Equipment Name",
                                        track_visibility="onchange")
    equipment_model_id = fields.Many2one('equipment.model.name',
                                         string="Equipment Model",
                                         track_visibility="onchange")
    equipment_model_no_id = fields.Many2one('equipment.model.number',
                                            string="Equipment Model No",
                                            track_visibility="onchange")

    # @api.depends('equipment_name')
    # def _compute_name(self):
    #     for rec in self:
    #         rec.name = False
    #         if rec.equipment_name:
    #             rec.name = rec.equipment_name.name
    #
    # @api.depends('equipment_model')
    # def _compute_model(self):
    #     for rec in self:
    #         rec.name = False
    #         if rec.equipment_model:
    #             rec.name = rec.equipment_model.name

    def _get_default_location(self):
        """To set the default location for the Equipment"""
        return self.env['stock.warehouse'].search(
            [('location_type', '=', 'view'),
             ('company_id', '=', self.env.company.id)], limit=1,
            order='id asc').lot_stock_id.id

    machine_location_id = fields.Many2one('stock.location',
                                          string="Equipment Location",
                                          ondelete='restrict',
                                          default=_get_default_location)
    machine_location_ids = fields.Many2many('stock.location',
                                            compute='_compute_machine_location_ids')
    attachment_number = fields.Integer('Number of Attachments',
                                       compute='_compute_attachment_number')
    finance_type = fields.Selection(
        [('own', 'Own'), ('loan', 'Loan'), ('lease', 'Lease')], default='own')
    loan_year = fields.Integer(string="Loan/Lease", readonly=True,
                               default=1,
                               states={"draft": [("readonly", False)]})
    loan_period = fields.Selection(
        selection=lambda self: self.env[
            "account.asset.profile"]._selection_method_period(),
        string="Period Length", readonly=True, default="year",
        states={"draft": [("readonly", False)]},
        help="Period length for the loan accounting entries")
    loan_line_ids = fields.One2many(comodel_name="account.loan.line",
                                    inverse_name="asset_id",
                                    string="Loan Lines", copy=False,
                                    readonly=True,
                                    states={"draft": [("readonly", False)]})
    loan_base = fields.Float(digits="Account", string="Loan Base",
                             readonly=True,
                             states={"draft": [("readonly", False)]},
                             help="This amount represent the loan base of the Equipment")
    account_loan_id = fields.Many2one(comodel_name="account.account",
                                      string="Loan Account",
                                      domain="[('internal_type', '=', 'payable'),('deprecated', '=', False)]")
    journal_id = fields.Many2one(comodel_name="account.journal",
                                 domain=[('type', '=', 'general')],
                                 string="Journal")
    loan_paid = fields.Float(compute="_compute_loan", digits="Account",
                             string="Loan Paid", store=True)
    loan_to_pay = fields.Float(compute="_compute_loan", digits="Account",
                               string="Loan To Pay", store=True)
    loan_prorata = fields.Boolean(string="Prorata Temporis", readonly=True,
                                  states={"draft": [("readonly", False)]},
                                  default=True,
                                  help="Indicates that the first depreciation entry for this asset "
                                       "have to be done from the depreciation start date instead "
                                       "of the first day of the fiscal year.")
    installed_date = fields.Date(string="Installed Date", readonly=1)
    last_transfer_date = fields.Date(string="Install Date", readonly=1)
    removed_date = fields.Date(string="Removal Date", readonly=1)
    move_id = fields.Many2one('account.move')
    parts_line_ids = fields.One2many('parts.line', 'machine_id', string="Parts",
                                     ondelete='cascade')

    # Extra Added Fields
    serviced_by = fields.Selection(
        [('branch', 'Branch'), ('operator', 'Operator')],
        string='Serviced By', )

    service_date = fields.Date(string="Service Date")
    out_service_date = fields.Date(string="Out Service Date")
    disposition_date = fields.Date(string="Disposition Date")
    disposition_reason = fields.Char(string="Disposition Reason")

    machine_age = fields.Char(string="Equipment Age",
                              compute="_compute_machine_age")
    opt_health = fields.Integer(string="OPT Healthy %", default=0,
                                track_visibility="onchange")
    is_inventory = fields.Boolean(string="Inventory", default=False,
                                  track_visibility="onchange")
    is_telemetry = fields.Boolean(string="Telemetry", default=False,
                                  track_visibility="onchange")
    is_credit_Card_reader = fields.Boolean(string="Credit Card Reader",
                                           default=False,
                                           track_visibility="onchange")
    is_energy_star = fields.Boolean(string="Energy Star", default=False,
                                    track_visibility="onchange")
    is_healt_wellness = fields.Boolean(string="Health & Wellness",
                                       default=False,
                                       track_visibility="onchange")
    machine_frontage = fields.Selection(
        [('stack', 'Stack'), ('glass_front', 'Glass Front')],
        string="Equipment Frontage", track_visibility="onchange")

    area_or_pos = fields.Char(string="Area/POS")
    access_type = fields.Char(string="Access Type")

    first_reported_period = fields.Char(string="First Reported Period")
    last_reported_period = fields.Char(string="Last Reported Period")

    contract_expiration = fields.Date(string="Contract Expiration")

    full_address = fields.Char(string="Full Address",
                               compute="_compute_full_address", store=True)
    asset_message_ids = fields.One2many('machine.notes', 'asset_id', 'Message')

    # def _get_operator_location_id(self):
    #     """This method is used to write the operator location id . We need this field to transfer the equipment"""
    #     print("self.company_id.id", self.company_id.id)
    #     print('_compute_operator_location_id', self.operator_location_id,
    #           self.env['stock.warehouse'].search([('location_type', '=', 'view'),
    #                                               ('company_id', '=', self.company_id.id)],
    #                                              limit=1,
    #                                              order='id asc').lot_stock_id.id)
    #     # for rec in self:
    #     #     rec.operator_location_id = False
    #     #     if rec.company_id:
    #     self.operator_location_id = self.env['stock.warehouse'].search([('location_type', '=', 'view'),
    #                                                                     ('company_id', '=', self.company_id.id)],
    #                                                                    limit=1,
    #                                                                    order='id asc').lot_stock_id.id
    def _default_operator_location_id(self):
        """Function to set the operator location default from comapny"""
        if self.env.company.equipment_warehouse_id:
            return self.env.company.equipment_warehouse_id.id

    operator_locations_ids = fields.Many2many('stock.location',
                                              compute='_compute_operator_locations_ids',
                                              store=True, )
    operator_location_id = fields.Many2one('stock.location',
                                           string="Warehouse",
                                           domain="[('id', 'in',operator_locations_ids)]",
                                           default=_default_operator_location_id)
    is_customer_location = fields.Boolean(string="Is Customer Location")
    equipment_trasfer_ids = fields.Many2many('account.asset.transfer',
                                             string='Equipment Location History')
    """This is_customer_location boolean field is used to identify the equipment is in customer location or in 
    operator warehouse"""

    equipment_location = fields.Char(string="Equipment Location",
                                     help="Used to save the location name",
                                     compute='_compute_equipment_location',
                                     store=True, readonly=True)

    combine_name = fields.Char(string="name", compute='_compute_combine_name',
                               store=True)

    notes_count = fields.Integer(string="Notes Count",
                                 compute='_compute_notes_count', store=True)
    activity_count = fields.Integer(string="Activity Count",
                                    compute='_compute_activity_count',
                                    store=True)

    archived_date = fields.Datetime(string="Equipment Archive Date")

    @api.depends('equipment_trasfer_ids')
    def _compute_activity_count(self):
        for rec in self:
            rec.activity_count = len(rec.equipment_trasfer_ids.ids)

    @api.depends('asset_message_ids')
    def _compute_notes_count(self):
        for rec in self:
            rec.notes_count = len(rec.asset_message_ids.ids)

    @api.depends('code', 'name')
    def _compute_combine_name(self):
        for rec in self:
            rec.combine_name = str(rec.code) + " - " + str(rec.name)

    @api.depends('micro_market_id', 'machine_location_id', 'location_type',
                 'operator_location_id')
    def _compute_equipment_location(self):
        """Function is used to compute the name of the Equipment location . Why it's doing is
        MicroMarket is warehouse and ares/pos is a location.So We can use Reference field or char.
        So now using the char method."""
        for rec in self:
            if rec.location_type == 'micro_market' and rec.state != 'draft':
                rec.equipment_location = rec.micro_market_id.name
            elif rec.state == 'draft':
                rec.equipment_location = rec.operator_location_id.complete_name
            else:
                rec.equipment_location = rec.machine_location_id.name

    @api.constrains('active')
    def _check_active(self):
        if self.active == False:
            date = fields.Datetime.now()
            vals = {'state': 'archived', 'archived_date': date}
            self.write(vals)

    def action_archive(self):
        """Function is overrided to check the state of the equipment and also need to change the status to archived."""
        for rec in self:
            if rec.state != 'removed':
                raise ValidationError(
                    _("You can only archive equipment that is in the 'Inactive' status."))
        res = super().action_archive()

        return res

    def action_unarchive(self):
        res = super().action_unarchive()
        [rec.write({'state': 'removed'}) for rec in
         self.search([('state', "=", 'archived'), ('active', '=', True)])]
        return res

    #
    # def unlink(self):
    #     for rec in self:
    #         if rec.state == 'open':
    #             raise ValidationError(_("You cannot Delete equipment that is in the 'In Service' status."))
    #         else:
    #             res = super().unlink()

    @api.depends('company_id')
    def _compute_operator_locations_ids(self):
        for rec in self:
            rec.operator_locations_ids = False
            if rec.company_id:
                operator_locator = self.env['stock.warehouse'].search(
                    [('location_type', '=', 'view'),
                     ('company_id', '=', self.company_id.id)],
                    order='id asc').mapped('lot_stock_id')
                print("operator", operator_locator)
                rec.operator_locations_ids = [(6, 0, operator_locator.ids)]
                # if operator_locator:
                #     rec.operator_location_id = operator_locator[0]
                if rec.company_id.equipment_warehouse_id:
                    rec.operator_locations_id = rec.company_id.equipment_warehouse_id.id

    @api.constrains('operator_location_id', 'machine_location_id')
    def _check_customer_location(self):
        for rec in self:
            if rec.machine_location_id.id != rec.operator_location_id.id:
                rec.is_customer_location = True
            else:
                rec.is_customer_location = False

    @api.constrains('purchase_value', 'salvage_value', 'method_number',
                    'finance_type')
    def check_purchase_value(self):
        if not self.purchase_value > 0 and self.finance_type == 'own':
            raise UserError(_("Please provide a valid purchase value."))
        if self.purchase_value < 0:
            raise UserError(_("Please provide a valid purchase value."))
        if self.salvage_value and not self.salvage_value > 0:
            raise UserError(_("Salvage Value Cannot be Negative"))
        if self.method_number and not self.method_number > 0:
            raise UserError(_("Number of Year Cannot be Negative"))

    @api.model
    # @api.depends('machine_location_id')
    def _compute_full_address(self):
        # Saving the full address in the field
        for record in self:
            if record.machine_location_id:
                record.full_address = str(
                    record.machine_location_id.warehouse_id.street if record.machine_location_id.warehouse_id.street else " ") + ' ' + str(
                    record.machine_location_id.warehouse_id.street2 if record.machine_location_id.warehouse_id.street2 else "") + ' ' + str(
                    record.machine_location_id.warehouse_id.city if record.machine_location_id.warehouse_id.city else "") + ' ' + str(
                    record.machine_location_id.warehouse_id.state_id.name if record.machine_location_id.warehouse_id.state_id.name else "") + ' ' + str(
                    record.machine_location_id.warehouse_id.county if record.machine_location_id.warehouse_id.county else "") + ' (' + str(
                    record.machine_location_id.warehouse_id.zip if record.machine_location_id.warehouse_id.zip else "") + ')'

    @api.model
    @api.constrains('model', 'serial_no')
    def _check_model(self):
        for rec in self:
            if rec.model:
                rec.model_redable = True
            else:
                rec.model_redable = False
            if rec.serial_no:
                rec.serial_readable = True
            else:
                rec.serial_readable = False

    @api.constrains('state')
    def _check_state(self):
        # Checking the machine state if the state is removed then the cases should be cancelled
        # If we were cancelling any Equipment then the system will automatically cancel the related case too.
        # Also we are saving the equipment state change report.
        if self.state == 'removed':
            stage = self.env['case.management.stage'].search(
                [('name', 'not in', ['Closed', 'Cancelled'])])
            cases = self.env['case.management'].search(
                [('machine_ids', '=', self.id),
                 ('state_id', 'not in', stage.ids)])
            cancel = self.env['case.management.stage'].search(
                [('name', '=', 'Cancelled')], limit=1).id
            for rec in cases:
                rec.stage_id = cancel

    # @api.constrains('machine_location_id')
    # def _check_machine_location_id(self):
    #     """This function will work when we change the machine location.The hiatory of machine transfer will be
    #     recorded. source location and destination location is char becase they need to enter anything in area field."""
    # trasfer_ids =
    # self.equipment_trasfer_ids = [(4,)]
    # for rec in self:
    #     print("data")
    #     previous_data = self.env['machine.placement.history'].sudo().search([('machine_id', '=', rec.id)],
    #                                                                         limit=1,
    #                                                                         order='date desc')
    #     previous_data.sudo().write({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    #     self.env['machine.placement.history'].sudo().create({
    #         'location_id': rec.machine_location_id.id,
    #         'machine_id': rec.id,
    #         'operator_id': rec.company_id.id,
    #         'in_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #         'date': False,
    #         'activity_type': rec.activity_type,
    #         'source_location_id': previous_data.location_id.id,
    #         'source_location': previous_data.destination_location,
    #         'destination_location': rec.machine_location_id.complete_name or rec.area_or_pos,
    #         'customer_id': rec.location_partner_id.id,
    #     })

    @api.constrains('date_start')
    def _check_start_date(self):
        today = fields.date.today()
        if self.date_start > today:
            raise UserError(_('Purchase date must be less than today'))

    @api.depends('date_start')
    def _compute_machine_age(self):
        """Computing the machine age."""
        # Calculating machine age
        today = fields.date.today()
        for rec in self:
            if rec.date_start and rec.date_start > today:
                raise UserError(_('Purchase date must be less than today'))
            rec.machine_age = False
            if rec.date_start:
                year = today.year - rec.date_start.year
                month = abs(today.month - rec.date_start.month)
                day = abs(today.day - rec.date_start.day)
                rec.machine_age = "%d Years %d Months %d Days" % (
                    year, month, day)

    _sql_constraints = [
        ('serial_no', 'UNIQUE(company_id, serial_no)',
         "Another machine already exists with this serial number!"),
    ]

    def _compute_attachment_number(self):
        """Used to show the number of attachment in the smart button."""
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'account.asset'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attachment = dict(
            (data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    def action_get_attachment_view(self):
        """This function is used to get the attachment id.This function will be used for the attachment showing
        wizard"""
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base',
                                                           'action_attachment')
        res['domain'] = [('res_model', '=', 'account.asset'),
                         ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'account.asset',
                          'default_res_id': self.id}
        return res

    def action_open_customer_form(self):
        """Used as a button function. In the kanban view we have customer field. When we click on that will open the
        customer form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.location_partner_id.id,
            'views': [[False, 'form']]
        }

    @api.depends('warehouse_id', 'micro_market_id', 'location_type')
    def _compute_machine_location_ids(self):
        for rec in self:
            rec.machine_location_ids = self.env['stock.location'].sudo().search(
                [('is_machine_location', '=', True),
                 ('warehouse_id', '=', rec.warehouse_id.id),
                 ('company_id', '=', self.env.company.id)], order='id asc')

    @api.onchange('location_type')
    def _onchange_location_type(self):
        """If the trasfer type is order then we need to remove the location from the field. otherwise it will belong
        to the location"""
        if self.location_type == 'order':
            self.location_partner_id = None
            self.micro_market_id = not None
            self.machine_location_id = None

    """Removed Below code on 16-03-2023 for no use. Not sure this will helpful in future"""

    # @api.onchange('warehouse_id')
    # def _onchange_warehouse_id(self):
    #     bin_locations = self.env['stock.location'].sudo().search(
    #         [('is_bin_location', '=', True), ('warehouse_id', '=', self.warehouse_id.id),
    #          ('company_id', '=', self.env.company.id)], order='id', limit=1)
    #     # self.machine_location_id = bin_locations.id

    # @api.onchange('micro_market_id')
    # def _onchange_micro_market_id(self):
    #     self.location_partner_id = self.micro_market_id.partner_id.id

    # def action_view_asset_transfer(self):
    #     transferred_asset_ids = self.env['account.asset.transfer'].search([
    #         ('transferred_asset_id', '=', self.id)])
    #     action = self.env.ref('account_asset_management.action_account_asset_transfer').read()[0]
    #     action['context'] = {'create': True}
    #     action['domain'] = [('id', 'in', transferred_asset_ids.ids)]
    #     return action

    def action_view_asset_transfer_to_warehouse(self):
        """Showing the asset transfer view wizard."""
        print("move to wh")
        self.write({
            'machine_location_id': self.operator_location_id,
            'last_transfer_date': fields.Date.today(),
            'area_or_pos': '',
            'location_partner_id': False,
            'micro_market_id': False,
            'location_type': 'micro_market'
        })
        # return {
        #     'name': _('Equipment Transfer'),
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'account.asset.transfer',
        #     'view_id': self.env.ref('action_view_asset_transfer_to_warehouse'),
        #     'type': 'ir.actions.act_window',
        #     'target': 'new',
        #     # 'res_id': move_ids[0],
        # }

    def action_view_asset_transfer(self):
        """Showing the asset transfer view wizard."""
        return {
            'name': _('Equipment Activity'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.asset.transfer',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_equipment_warehouse': self.operator_location_id.id,
                'default_equipment_state': self.state},
        }

    def _get_disposal_moves(self):

        move_ids = []
        for asset in self:
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(
                lambda x: not x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in
                            unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(
                    unposted_depreciation_line_ids) + 1
                today = fields.Datetime.today()
                vals = {
                    'amount': asset.value_residual,
                    'asset_id': asset.id,
                    # 'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': asset.depreciation_base - asset.salvage_value,
                    # the asset is completely depreciated
                    'line_date': today,
                }
                commands.append((0, False, vals))
                asset.write(
                    {'depreciation_line_ids': commands, 'method_end': today,
                     'method_number': sequence})
                tracked_fields = self.env['account.asset'].fields_get(
                    ['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(
                    tracked_fields, old_values)
                if changes:
                    asset.message_post(
                        subject=_(
                            'Equipment sold or disposed. Accounting entry awaiting for validation.'),
                        tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move()

        return move_ids

    def set_to_close(self):
        move_ids = self._get_disposal_moves()
        if move_ids:
            return self._return_disposal_view(move_ids)
        # Fallback, as if we just clicked on the smartbutton
        return self.open_entries()

    def _return_disposal_view(self, move_ids):
        name = _('Disposal Move')
        view_mode = 'form'
        if len(move_ids) > 1:
            name = _('Disposal Moves')
            view_mode = 'tree,form'
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': view_mode,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': move_ids[0],
        }

    def open_entries(self):
        move_ids = []
        for asset in self:
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    move_ids.append(depreciation_line.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'asset.journal.wizard',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }

    @api.model
    def _default_company_id(self):
        return self.env.company

    def _compute_move_line_check(self):
        for asset in self:
            move_line_check = False
            for line in asset.depreciation_line_ids:
                if line.move_id:
                    move_line_check = True
                    break
            asset.move_line_check = move_line_check

    @api.depends("purchase_value", "salvage_value", "method")
    def _compute_depreciation_base(self):
        for asset in self:
            if asset.method in ["linear-limit", "degr-limit"]:
                asset.depreciation_base = asset.purchase_value
            else:
                asset.depreciation_base = asset.purchase_value - asset.salvage_value

    @api.onchange('purchase_value')
    def _onchange_loan_base(self):
        self.loan_base = self.purchase_value

    @api.depends("loan_base", "loan_line_ids.type", "loan_line_ids.amount",
                 "loan_line_ids.previous_id",
                 "loan_line_ids.init_entry", "loan_line_ids.move_check")
    def _compute_loan(self):
        for asset in self:
            lines = asset.loan_line_ids.filtered(
                lambda l: l.type in ("loan", "remove") and (
                        l.init_entry or l.move_check))
            value_depreciated = sum([line.amount for line in lines])
            residual = asset.loan_base - value_depreciated
            depreciated = value_depreciated
            asset.update({"loan_to_pay": residual, "loan_paid": depreciated})

    @api.depends("depreciation_base", "depreciation_line_ids.type",
                 "depreciation_line_ids.amount",
                 "depreciation_line_ids.previous_id",
                 "depreciation_line_ids.init_entry",
                 "depreciation_line_ids.move_check")
    def _compute_depreciation(self):
        for asset in self:
            lines = asset.depreciation_line_ids.filtered(
                lambda l: l.type in ("depreciate", "remove") and (
                        l.init_entry or l.move_check))
            value_depreciated = sum([line.amount for line in lines])
            residual = asset.depreciation_base - value_depreciated
            depreciated = value_depreciated
            asset.update(
                {"value_residual": residual, "value_depreciated": depreciated})

    @api.constrains("method", "method_time")
    def _check_method(self):
        for asset in self:
            if asset.method == "degr-linear" and asset.method_time != "year":
                raise UserError(
                    _("Degressive-Linear is only supported for Time Method = " "Year."))

    @api.constrains("date_start", "method_end", "method_time")
    def _check_dates(self):
        for asset in self:
            if asset.method_time == "end":
                if asset.method_end <= asset.date_start:
                    raise UserError(
                        _("The Start Date must precede the Ending Date."))

    @api.onchange("purchase_value", "salvage_value", "date_start", "method")
    def _onchange_purchase_salvage_value(self):
        if self.method in ["linear-limit", "degr-limit"]:
            self.depreciation_base = self.purchase_value or 0.0
        else:
            purchase_value = self.purchase_value or 0.0
            salvage_value = self.salvage_value or 0.0
            self.depreciation_base = purchase_value - salvage_value

    # @api.onchange("profile_id")
    # def _onchange_profile_id(self):
    #     for line in self.depreciation_line_ids:
    #         if line.move_id:
    #             raise UserError(_("You cannot change the profile of an asset "
    #                               "with accounting entries."))
    #     profile = self.profile_id
    #     if profile:
    #         self.update({
    #             "method": profile.method,
    #             "method_number": profile.method_number,
    #             "method_time": profile.method_time,
    #             "method_period": profile.method_period,
    #             "days_calc": profile.days_calc,
    #             "use_leap_years": profile.use_leap_years,
    #             "method_progress_factor": profile.method_progress_factor,
    #             "prorata": profile.prorata,
    #             "account_analytic_id": profile.account_analytic_id,
    #             "group_ids": profile.group_ids, })

    @api.onchange("method_time")
    def _onchange_method_time(self):
        if self.method_time != "year":
            self.prorata = True

    @api.onchange("method_number")
    def _onchange_method_number(self):
        if self.method_number and self.method_end:
            self.method_end = False

    @api.onchange("method_end")
    def _onchange_method_end(self):
        if self.method_end and self.method_number:
            self.method_number = 0

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'account.asset') or _('New')
        if vals.get("method_time") != "year" and not vals.get("prorata"):
            vals["prorata"] = True
        asset = super().create(vals)
        if self.env.context.get("create_asset_from_move_line"):
            # Trigger compute of depreciation_base
            asset.salvage_value = 0.0
        asset._create_first_asset_line()
        # Below code is used to confirm the Equipment at the time of record creation.
        # asset.with_context(asset_validate_from_write=True).validate()
        return asset

    def write(self, vals):
        if vals.get("method_time"):
            if vals["method_time"] != "year" and not vals.get("prorata"):
                vals["prorata"] = True
        res = super().write(vals)
        for asset in self:
            if self.env.context.get("asset_validate_from_write"):
                continue
            asset._create_first_asset_line()
            # if asset.profile_id.open_asset and self.env.context.get("create_asset_from_move_line"):
            #     asset.compute_depreciation_board()
            #     # extra context to avoid recursion
            #     asset.with_context(asset_validate_from_write=True).validate()
        return res

    def _create_first_asset_line(self):
        self.ensure_one()
        if self.depreciation_base and not self.depreciation_line_ids:
            asset_line_obj = self.env["account.asset.line"]
            line_name = self._get_depreciation_entry_name(0)
            asset_line_vals = {
                "amount": self.depreciation_base,
                "asset_id": self.id,
                "name": line_name,
                "line_date": self.date_start,
                "init_entry": True,
                "type": "create", }
            asset_line = asset_line_obj.create(asset_line_vals)
            if self.env.context.get("create_asset_from_move_line"):
                asset_line.move_id = self.env.context["move_id"]

    def unlink(self):
        for asset in self:
            transfer = self.env['account.asset.transfer'].search(
                [('transferred_asset_id', '=', asset.id)]).ids
            case = self.env['case.management'].search(
                [('machine_ids', '=', asset.id)]).ids
            if asset.state != "draft":
                raise UserError(
                    _("You can only delete Equipment that in Active state."))
            if len(transfer) or len(case):
                raise UserError(
                    _("You cannot delete an Equipment that has activity."))
        # if asset.depreciation_line_ids.filtered(lambda r: r.type == "depreciate" and r.move_check):
        #     raise UserError(_("You cannot delete an asset that contains "
        #                       "posted depreciation lines."))
        # update accounting entries linked to lines of type 'create'
        # amls = self.with_context(allow_asset_removal=True).mapped("account_move_line_ids")
        # amls.write({"asset_id": False})
        return super().unlink()

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", "=ilike", name + "%"),
                      ("name", operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ["&", "!"] + domain[1:]
        assets = self.search(domain + args, limit=limit)
        return assets.name_get()

    @api.depends("name", "code", "serial_no")
    def name_get(self):
        result = []
        for asset in self:
            name = asset.name
            if asset.code and asset.name:
                name = f"{asset.code} - {name} ({asset.serial_no})"
            result.append((asset.id, name))
        return result

    def validate(self):
        for asset in self:
            if asset.company_currency_id.is_zero(asset.value_residual):
                asset.state = "close"
            else:
                asset.state = "open"
                if not asset.depreciation_line_ids.filtered(
                        lambda l: l.type != "create"):
                    asset.compute_depreciation_board()
        return True

    def remove(self):
        self.ensure_one()
        ctx = dict(self.env.context, active_ids=self.ids, active_id=self.id)
        early_removal = False
        if self.method in ["linear-limit", "degr-limit"]:
            if self.value_residual != self.salvage_value:
                early_removal = True
        elif self.value_residual:
            early_removal = True
        if early_removal:
            ctx.update({"early_removal": True})

        return {
            "name": _("Generate Asset Removal entries"),
            "view_mode": "form",
            "res_model": "account.asset.remove",
            "target": "new",
            "type": "ir.actions.act_window",
            "context": ctx, }

    def set_to_draft(self):
        return self.write({"state": "draft"})

    def open_location_history(self):
        # This function will work when we click on the location history smart button.
        #     machine.placement.history
        # context = {"default_machine_placement_ids": self.env["machine.placement.history"].search(
        #     [('machine_id', '=', self.id)]).ids}
        # context = {'default_equipment_trasfer_ids':self.}
        # view_id = self.env.ref('account_asset_management.note_wizard_view').id
        # print("self.id", self.id)
        return {
            "name": _("Equipment Activity History"),
            "view_mode": "form",
            "res_model": "account.asset",
            "view_id": self.env.ref(
                'account_asset_management.account_asset_view_form_history_placement').id,
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def open_note(self):
        # Wizard action to show all the notes of the machine
        view_id = self.env.ref('account_asset_management.note_wizard_view').id
        return {
            "name": _("Notes"),
            "view_mode": "form",
            "res_model": "account.asset",
            "view_id": view_id,
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "target": "new", }

    def open_activities(self):
        # Opening the activities smart button.
        context = {"default_activity_ids": self.activity_ids.ids}
        view_id = self.env.ref(
            'account_asset_management.account_asset_activity_wizard').id
        return {
            "name": _("Activities"),
            "view_mode": "form",
            "res_model": "account.asset",
            "view_id": view_id,
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new", }

    def _group_lines(self, table):
        """group lines prior to depreciation start period."""

        def group_lines(x, y):
            y.update({"amount": x["amount"] + y["amount"]})
            return y

        depreciation_start_date = self.date_start
        lines = table[0]["lines"]
        lines1 = []
        lines2 = []
        flag = lines[0]["date"] < depreciation_start_date
        for line in lines:
            if flag:
                lines1.append(line)
                if line["date"] >= depreciation_start_date:
                    flag = False
            else:
                lines2.append(line)
        if lines1:
            lines1 = [reduce(group_lines, lines1)]
            lines1[0]["depreciated_value"] = 0.0
        table[0]["lines"] = lines1 + lines2

    def _compute_loan_line(self, loan_value_posted, table_i_start, line_i_start,
                           table, last_line,
                           posted_lines):
        digits = self.env["decimal.precision"].precision_get("Account")
        seq = len(posted_lines)
        depr_line = last_line
        last_date = table[-1]["lines"][-1]["date"]
        loan_value = loan_value_posted
        for entry in table[table_i_start:]:
            for line in entry["lines"][line_i_start:]:
                seq += 1
                name = self._get_depreciation_entry_name(seq)
                amount = line["amount"]
                if line["date"] == last_date:
                    # ensure that the last entry of the table always
                    # depreciates the remaining value
                    amount = self.loan_base - loan_value
                if amount:
                    vals = {
                        "previous_id": depr_line.id,
                        "amount": round(amount, digits),
                        "asset_id": self.id,
                        "name": name,
                        "line_date": line["date"],
                        "line_days": line["days"],
                        "init_entry": entry["init"],
                    }
                    loan_value += round(amount, digits)
                    depr_line = self.env["account.loan.line"].create(vals)
                else:
                    seq -= 1
            line_i_start = 0

    def _compute_depreciation_line(self, depreciated_value_posted,
                                   table_i_start, line_i_start, table,
                                   last_line,
                                   posted_lines):
        digits = self.env["decimal.precision"].precision_get("Account")

        seq = len(posted_lines)
        depr_line = last_line
        last_date = table[-1]["lines"][-1]["date"]
        depreciated_value = depreciated_value_posted
        for entry in table[table_i_start:]:
            for line in entry["lines"][line_i_start:]:
                seq += 1
                name = self._get_depreciation_entry_name(seq)
                amount = line["amount"]
                if line["date"] == last_date:
                    # ensure that the last entry of the table always
                    # depreciates the remaining value
                    amount = self.depreciation_base - depreciated_value
                    if self.method in ["linear-limit", "degr-limit"]:
                        amount -= self.salvage_value
                if amount:
                    vals = {
                        "previous_id": depr_line.id,
                        "amount": round(amount, digits),
                        "asset_id": self.id,
                        "name": name,
                        "line_date": line["date"],
                        "line_days": line["days"],
                        "init_entry": entry["init"],
                    }
                    depreciated_value += round(amount, digits)
                    depr_line = self.env["account.asset.line"].create(vals)
                else:
                    seq -= 1
            line_i_start = 0

    def compute_loan_board(self):
        if not self.account_loan_id:
            raise ValidationError(_("Please select loan account to compute."))
        if not self.journal_id:
            raise ValidationError(_("Please select loan journal  to compute."))

        line_obj = self.env["account.loan.line"]
        digits = self.env["decimal.precision"].precision_get("Account")

        for asset in self:
            if asset.value_residual == 0.0:
                continue
            domain = [("asset_id", "=", asset.id), ("type", "=", "loan"), "|",
                      ("move_check", "=", True),
                      ("init_entry", "=", True), ]
            posted_lines = line_obj.search(domain, order="line_date desc")
            if posted_lines:
                last_line = posted_lines[0]
            else:
                last_line = line_obj
            domain = [("asset_id", "=", asset.id), ("type", "=", "loan"),
                      ("move_id", "=", False),
                      ("init_entry", "=", False)]
            old_lines = line_obj.search(domain)
            if old_lines:
                old_lines.unlink()

            table = asset._compute_loan_table()
            if not table:
                continue

            asset._group_lines(table)

            # check table with posted entries and
            # recompute in case of deviation
            loan_value_posted = loan_value = 0.0
            if posted_lines:
                last_loan_date = last_line.line_date
                last_date_in_table = table[-1]["lines"][-1]["date"]
                if last_date_in_table <= last_loan_date:
                    raise UserError(
                        _("The duration of the asset conflicts with the ""posted depreciation table entry dates."))

                for _table_i, entry in enumerate(table):
                    residual_amount_table = entry["lines"][-1][
                        "remaining_value"]
                    if (entry["date_start"] <= last_loan_date <= entry[
                        "date_stop"]):
                        break

                if entry["date_stop"] == last_loan_date:
                    _table_i += 1
                    _line_i = 0
                else:
                    entry = table[_table_i]
                    date_min = entry["date_start"]
                    for _line_i, line in enumerate(entry["lines"]):
                        residual_amount_table = line["remaining_value"]
                        if date_min <= last_loan_date <= line["date"]:
                            break
                        date_min = line["date"]
                    if line["date"] == last_loan_date:
                        _line_i += 1
                table_i_start = _table_i
                line_i_start = _line_i

                # check if residual value corresponds with table
                # and adjust table when needed
                loan_value_posted = loan_value = sum(
                    [posted_line.amount for posted_line in posted_lines])
                residual_amount = asset.loan_base - loan_value
                amount_diff = round(residual_amount_table - residual_amount,
                                    digits)
                if amount_diff:
                    # compensate in first depreciation entry
                    # after last posting
                    line = table[table_i_start]["lines"][line_i_start]
                    line["amount"] -= amount_diff

            else:  # no posted lines
                table_i_start = 0
                line_i_start = 0

            asset._compute_loan_line(loan_value_posted, table_i_start,
                                     line_i_start, table, last_line,
                                     posted_lines)
        return True

    def compute_depreciation_board(self):
        line_obj = self.env["account.asset.line"]
        digits = self.env["decimal.precision"].precision_get("Account")

        for asset in self:
            if asset.value_residual == 0.0:
                continue
            domain = [("asset_id", "=", asset.id), ("type", "=", "depreciate"),
                      "|", ("move_check", "=", True),
                      ("init_entry", "=", True), ]
            posted_lines = line_obj.search(domain, order="line_date desc")
            if posted_lines:
                last_line = posted_lines[0]
            else:
                last_line = line_obj
            domain = [("asset_id", "=", asset.id), ("type", "=", "depreciate"),
                      ("move_id", "=", False),
                      ("init_entry", "=", False)]
            old_lines = line_obj.search(domain)
            if old_lines:
                old_lines.unlink()

            table = asset._compute_depreciation_table()
            if not table:
                continue

            asset._group_lines(table)

            # check table with posted entries and
            # recompute in case of deviation
            depreciated_value_posted = depreciated_value = 0.0
            if posted_lines:
                last_depreciation_date = last_line.line_date
                last_date_in_table = table[-1]["lines"][-1]["date"]
                if last_date_in_table <= last_depreciation_date:
                    raise UserError(
                        _("The duration of the asset conflicts with the ""posted depreciation table entry dates."))

                for _table_i, entry in enumerate(table):
                    residual_amount_table = entry["lines"][-1][
                        "remaining_value"]
                    if (entry["date_start"] <= last_depreciation_date <= entry[
                        "date_stop"]):
                        break

                if entry["date_stop"] == last_depreciation_date:
                    _table_i += 1
                    _line_i = 0
                else:
                    entry = table[_table_i]
                    date_min = entry["date_start"]
                    for _line_i, line in enumerate(entry["lines"]):
                        residual_amount_table = line["remaining_value"]
                        if date_min <= last_depreciation_date <= line["date"]:
                            break
                        date_min = line["date"]
                    if line["date"] == last_depreciation_date:
                        _line_i += 1
                table_i_start = _table_i
                line_i_start = _line_i

                # check if residual value corresponds with table
                # and adjust table when needed
                depreciated_value_posted = depreciated_value = sum(
                    [posted_line.amount for posted_line in posted_lines])
                residual_amount = asset.depreciation_base - depreciated_value
                amount_diff = round(residual_amount_table - residual_amount,
                                    digits)
                if amount_diff:
                    # compensate in first depreciation entry
                    # after last posting
                    line = table[table_i_start]["lines"][line_i_start]
                    line["amount"] -= amount_diff

            else:  # no posted lines
                table_i_start = 0
                line_i_start = 0

            asset._compute_depreciation_line(depreciated_value_posted,
                                             table_i_start, line_i_start, table,
                                             last_line,
                                             posted_lines)
        return True

    def _get_fy_duration(self, fy, option="days"):
        """Returns fiscal year duration.

        @param option:
        - days: duration in days
        - months: duration in months,
                  a started month is counted as a full month
        - years: duration in calendar years, considering also leap years
        """
        fy_date_start = fy.date_from
        fy_date_stop = fy.date_to
        days = (fy_date_stop - fy_date_start).days + 1
        months = ((fy_date_stop.year - fy_date_start.year) * 12 + (
                fy_date_stop.month - fy_date_start.month) + 1)
        if option == "days":
            return days
        elif option == "months":
            return months
        elif option == "years":
            year = fy_date_start.year
            cnt = fy_date_stop.year - fy_date_start.year + 1
            for i in range(cnt):
                cy_days = calendar.isleap(year) and 366 or 365
                if i == 0:  # first year
                    if fy_date_stop.year == year:
                        duration = (fy_date_stop - fy_date_start).days + 1
                    else:
                        duration = (date(year, 12, 31) - fy_date_start).days + 1
                    factor = float(duration) / cy_days
                elif i == cnt - 1:  # last year
                    duration = (fy_date_stop - date(year, 1, 1)).days + 1
                    factor += float(duration) / cy_days
                else:
                    factor += 1.0
                year += 1
            return factor

    def _get_fy_duration_factor(self, entry, firstyear):
        """
        localization: override this method to change the logic used to
        calculate the impact of extended/shortened fiscal years
        """
        duration_factor = 1.0
        fy = entry["fy"]
        if self.prorata:
            if firstyear:
                depreciation_date_start = self.date_start
                fy_date_stop = entry["date_stop"]
                first_fy_asset_days = (
                                              fy_date_stop - depreciation_date_start).days + 1
                first_fy_duration = self._get_fy_duration(fy, option="days")
                first_fy_year_factor = self._get_fy_duration(fy, option="years")
                duration_factor = (float(
                    first_fy_asset_days) / first_fy_duration * first_fy_year_factor)
            else:
                duration_factor = self._get_fy_duration(fy, option="years")
        else:
            fy_months = self._get_fy_duration(fy, option="months")
            duration_factor = float(fy_months) / 12
        return duration_factor

    def _get_depreciation_start_date(self, fy):
        """
        In case of 'Linear': the first month is counted as a full month
        if the fiscal year starts in the middle of a month.
        """
        if self.prorata:
            depreciation_start_date = self.date_start
        else:
            depreciation_start_date = fy.date_from
        return depreciation_start_date

    def _get_loan_stop_date(self, loan_start_date):
        loan_stop_date = loan_start_date + relativedelta(years=self.loan_year,
                                                         days=-1)
        return loan_stop_date

    def _get_depreciation_stop_date(self, depreciation_start_date):
        if self.method_time == "year" and not self.method_end:
            depreciation_stop_date = depreciation_start_date + relativedelta(
                years=self.method_number, days=-1)
        elif self.method_time == "number":
            if self.method_period == "month":
                depreciation_stop_date = depreciation_start_date + relativedelta(
                    months=self.method_number, days=-1)
            elif self.method_period == "quarter":
                m = [x for x in [3, 6, 9, 12] if
                     x >= depreciation_start_date.month][0]
                first_line_date = depreciation_start_date + relativedelta(
                    month=m, day=31)
                months = self.method_number * 3
                depreciation_stop_date = first_line_date + relativedelta(
                    months=months - 1, days=-1)
            elif self.method_period == "year":
                depreciation_stop_date = depreciation_start_date + relativedelta(
                    years=self.method_number, days=-1)
        elif self.method_time == "year" and self.method_end:
            depreciation_stop_date = self.method_end
        return depreciation_stop_date

    def _get_first_loan_period_amount(self, table, entry, loan_start_date,
                                      line_dates):
        """
        Return prorata amount for Time Method 'Year' in case of
        'Prorata Temporis'
        """
        amount = entry.get("period_amount")
        if self.loan_prorata:
            dates = [x for x in line_dates if x <= entry["date_stop"]]
            full_periods = len(dates) - 1
            amount = entry["fy_amount"] - amount * full_periods
        return amount

    def _get_first_period_amount(self, table, entry, depreciation_start_date,
                                 line_dates):
        """
        Return prorata amount for Time Method 'Year' in case of
        'Prorata Temporis'
        """
        amount = entry.get("period_amount")
        if self.prorata and self.method_time == "year":
            dates = [x for x in line_dates if x <= entry["date_stop"]]
            full_periods = len(dates) - 1
            amount = entry["fy_amount"] - amount * full_periods
        return amount

    def _get_loan_amount_linear(self, loan_start_date, loan_stop_date, entry):
        """
        Override this method if you want to compute differently the
        yearly amount.
        """
        if self.loan_year:
            return self.loan_base / self.loan_year
        year = entry["date_stop"].year
        cy_days = calendar.isleap(year) and 366 or 365
        days = (loan_stop_date - loan_start_date).days + 1
        return (self.loan_base / days) * cy_days

    def _get_amount_linear(self, depreciation_start_date,
                           depreciation_stop_date, entry):
        """
        Override this method if you want to compute differently the
        yearly amount.
        """
        if not self.use_leap_years and self.method_number:
            return self.depreciation_base / self.method_number
        year = entry["date_stop"].year
        cy_days = calendar.isleap(year) and 366 or 365
        days = (depreciation_stop_date - depreciation_start_date).days + 1
        return (self.depreciation_base / days) * cy_days

    def _compute_loan_year_amount(self, residual_amount, loan_start_date,
                                  loan_stop_date, entry):
        """
        Localization: override this method to change the degressive-linear
        calculation logic according to local legislation.
        """
        year_amount_linear = self._get_loan_amount_linear(loan_start_date,
                                                          loan_stop_date, entry)
        return year_amount_linear

    def _compute_year_amount(self, residual_amount, depreciation_start_date,
                             depreciation_stop_date, entry):
        """
        Localization: override this method to change the degressive-linear
        calculation logic according to local legislation.
        """
        if self.method_time != "year":
            raise UserError(
                _("The '_compute_year_amount' method is only intended for ""Time Method 'Number of Years."))
        year_amount_linear = self._get_amount_linear(depreciation_start_date,
                                                     depreciation_stop_date,
                                                     entry)
        if self.method == "linear":
            return year_amount_linear
        if self.method == "linear-limit":
            if (residual_amount - year_amount_linear) < self.salvage_value:
                return residual_amount - self.salvage_value
            else:
                return year_amount_linear
        year_amount_degressive = residual_amount * self.method_progress_factor
        if self.method == "degressive":
            return year_amount_degressive
        if self.method == "degr-linear":
            if year_amount_linear > year_amount_degressive:
                return min(year_amount_linear, residual_amount)
            else:
                return min(year_amount_degressive, residual_amount)
        if self.method == "degr-limit":
            if (residual_amount - year_amount_degressive) < self.salvage_value:
                return residual_amount - self.salvage_value
            else:
                return year_amount_degressive
        else:
            raise UserError(
                _("Illegal value %s in asset.method.") % self.method)

    def _compute_loan_line_dates(self, table, start_date, stop_date):
        """
        The posting dates of the accounting entries depend on the
        chosen 'Period Length' as follows:
        - month: last day of the month
        - quarter: last of the quarter
        - year: last day of the fiscal year

        Override this method if another posting date logic is required.
        """
        line_dates = []

        if self.loan_period == "month":
            line_date = start_date + relativedelta(day=31)
        if self.loan_period == "quarter":
            m = [x for x in [3, 6, 9, 12] if x >= start_date.month][0]
            line_date = start_date + relativedelta(month=m, day=31)
        elif self.loan_period == "year":
            line_date = table[0]["date_stop"]

        i = 1
        while line_date < stop_date:
            line_dates.append(line_date)
            if self.loan_period == "month":
                line_date = line_date + relativedelta(months=1, day=31)
            elif self.loan_period == "quarter":
                line_date = line_date + relativedelta(months=3, day=31)
            elif self.loan_period == "year":
                line_date = table[i]["date_stop"]
                i += 1

        # last entry
        if len(line_dates) == self.loan_year:
            line_dates.append(line_date)
            # if self.days_calc:
            #     line_dates.append(stop_date)
            # else:
            #     line_dates.append(line_date)
        return line_dates

    def _compute_line_dates(self, table, start_date, stop_date):
        """
        The posting dates of the accounting entries depend on the
        chosen 'Period Length' as follows:
        - month: last day of the month
        - quarter: last of the quarter
        - year: last day of the fiscal year

        Override this method if another posting date logic is required.
        """
        line_dates = []

        if self.method_period == "month":
            line_date = start_date + relativedelta(day=31)
        if self.method_period == "quarter":
            m = [x for x in [3, 6, 9, 12] if x >= start_date.month][0]
            line_date = start_date + relativedelta(month=m, day=31)
        elif self.method_period == "year":
            line_date = table[0]["date_stop"]

        i = 1
        while line_date < stop_date:
            line_dates.append(line_date)
            if self.method_period == "month":
                line_date = line_date + relativedelta(months=1, day=31)
            elif self.method_period == "quarter":
                line_date = line_date + relativedelta(months=3, day=31)
            elif self.method_period == "year":
                line_date = table[i]["date_stop"]
                i += 1

        # last entry
        if not (self.method_time == "number" and len(
                line_dates) == self.method_number):
            if self.days_calc:
                line_dates.append(stop_date)
            else:
                line_dates.append(line_date)
        return line_dates

    def _compute_loan_amount_per_fiscal_year(self, table, line_dates,
                                             loan_start_date, loan_stop_date):
        digits = self.env["decimal.precision"].precision_get("Account")
        fy_residual_amount = self.loan_base
        i_max = len(table) - 1
        asset_sign = self.loan_base >= 0 and 1 or -1
        day_amount = 0.0
        # if self.days_calc:
        #     days = (loan_stop_date - loan_start_date).days + 1
        #     day_amount = self.loan_base / days

        for i, entry in enumerate(table):
            year_amount = self._compute_loan_year_amount(fy_residual_amount,
                                                         loan_start_date,
                                                         loan_stop_date,
                                                         entry, )
            if self.loan_period == "year":
                period_amount = year_amount
            elif self.loan_period == "quarter":
                period_amount = year_amount / 4
            elif self.loan_period == "month":
                period_amount = year_amount / 12
            if i == i_max:
                fy_amount = fy_residual_amount
            else:
                firstyear = i == 0 and True or False
                fy_factor = self._get_fy_duration_factor(entry, firstyear)
                fy_amount = year_amount * fy_factor
            if asset_sign * (fy_amount - fy_residual_amount) > 0:
                fy_amount = fy_residual_amount
            period_amount = round(period_amount, digits)
            fy_amount = round(fy_amount, digits)
            entry.update({
                "period_amount": period_amount,
                "fy_amount": fy_amount,
                "day_amount": day_amount, })
            fy_residual_amount -= fy_amount
            if round(fy_residual_amount, digits) == 0:
                break
        i_max = i
        table = table[: i_max + 1]
        return table

    def _compute_depreciation_amount_per_fiscal_year(self, table, line_dates,
                                                     depreciation_start_date,
                                                     depreciation_stop_date):
        digits = self.env["decimal.precision"].precision_get("Account")
        fy_residual_amount = self.depreciation_base
        i_max = len(table) - 1
        asset_sign = self.depreciation_base >= 0 and 1 or -1
        day_amount = 0.0
        if self.days_calc:
            days = (depreciation_stop_date - depreciation_start_date).days + 1
            day_amount = self.depreciation_base / days

        for i, entry in enumerate(table):
            if self.method_time == "year":
                year_amount = self._compute_year_amount(fy_residual_amount,
                                                        depreciation_start_date,
                                                        depreciation_stop_date,
                                                        entry, )
                if self.method_period == "year":
                    period_amount = year_amount
                elif self.method_period == "quarter":
                    period_amount = year_amount / 4
                elif self.method_period == "month":
                    period_amount = year_amount / 12
                if i == i_max:
                    if self.method in ["linear-limit", "degr-limit"]:
                        fy_amount = fy_residual_amount - self.salvage_value
                    else:
                        fy_amount = fy_residual_amount
                else:
                    firstyear = i == 0 and True or False
                    fy_factor = self._get_fy_duration_factor(entry, firstyear)
                    fy_amount = year_amount * fy_factor
                if asset_sign * (fy_amount - fy_residual_amount) > 0:
                    fy_amount = fy_residual_amount
                period_amount = round(period_amount, digits)
                fy_amount = round(fy_amount, digits)
            else:
                fy_amount = False
                if self.method_time == "number":
                    number = self.method_number
                else:
                    number = len(line_dates)
                period_amount = round(self.depreciation_base / number, digits)
            entry.update({
                "period_amount": period_amount,
                "fy_amount": fy_amount,
                "day_amount": day_amount, })
            if self.method_time == "year":
                fy_residual_amount -= fy_amount
                if round(fy_residual_amount, digits) == 0:
                    break
        i_max = i
        table = table[: i_max + 1]
        return table

    def _compute_loan_table_lines(self, table, loan_start_date, loan_stop_date,
                                  line_dates):
        digits = self.env["decimal.precision"].precision_get("Account")
        asset_sign = 1 if self.loan_base >= 0 else -1
        i_max = len(table) - 1
        remaining_value = self.loan_base
        loan_value = 0.0

        for i, entry in enumerate(table):

            lines = []
            fy_amount_check = 0.0
            fy_amount = entry["fy_amount"]
            li_max = len(line_dates) - 1
            prev_date = max(entry["date_start"], loan_start_date)
            for li, line_date in enumerate(line_dates):
                line_days = (line_date - prev_date).days + 1
                if round(remaining_value, digits) == 0.0:
                    break

                if line_date > min(entry["date_stop"], loan_stop_date) and not (
                        i == i_max and li == li_max):
                    prev_date = line_date
                    break
                else:
                    prev_date = line_date + relativedelta(days=1)

                if (asset_sign * (fy_amount - fy_amount_check) < 0):
                    break

                if i == 0 and li == 0:
                    if entry.get("day_amount") > 0.0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = self._get_first_loan_period_amount(table,
                                                                    entry,
                                                                    loan_start_date,
                                                                    line_dates)
                        amount = round(amount, digits)
                else:
                    if entry.get("day_amount") > 0.0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = entry.get("period_amount")
                # last year, last entry
                # Handle rounding deviations.
                if i == i_max and li == li_max:
                    amount = remaining_value
                    remaining_value = 0.0
                else:
                    remaining_value -= amount
                fy_amount_check += amount
                line = {
                    "date": line_date,
                    "days": line_days,
                    "amount": amount,
                    "loan_value": loan_value,
                    "remaining_value": remaining_value, }
                lines.append(line)
                loan_value += amount

            # Handle rounding and extended/shortened FY deviations.
            #
            # Remark:
            # In account_asset_management version < 8.0.2.8.0
            # the FY deviation for the first FY
            # was compensated in the first FY depreciation line.
            # The code has now been simplified with compensation
            # always in last FT depreciation line.
            if not entry.get("day_amount"):
                if round(fy_amount_check - fy_amount, digits) != 0:
                    diff = fy_amount_check - fy_amount
                    amount = amount - diff
                    remaining_value += diff
                    lines[-1].update(
                        {"amount": amount, "remaining_value": remaining_value})
                    loan_value -= diff

            if not lines:
                table.pop(i)
            else:
                entry["lines"] = lines
            line_dates = line_dates[li:]

        for entry in table:
            if not entry["fy_amount"]:
                entry["fy_amount"] = sum(
                    [line["amount"] for line in entry["lines"]])

    def _compute_depreciation_table_lines(self, table, depreciation_start_date,
                                          depreciation_stop_date, line_dates):
        digits = self.env["decimal.precision"].precision_get("Account")
        asset_sign = 1 if self.depreciation_base >= 0 else -1
        i_max = len(table) - 1
        remaining_value = self.depreciation_base
        depreciated_value = 0.0

        for i, entry in enumerate(table):

            lines = []
            fy_amount_check = 0.0
            fy_amount = entry["fy_amount"]
            li_max = len(line_dates) - 1
            prev_date = max(entry["date_start"], depreciation_start_date)
            for li, line_date in enumerate(line_dates):
                line_days = (line_date - prev_date).days + 1
                if round(remaining_value, digits) == 0.0:
                    break

                if line_date > min(entry["date_stop"],
                                   depreciation_stop_date) and not (
                        i == i_max and li == li_max):
                    prev_date = line_date
                    break
                else:
                    prev_date = line_date + relativedelta(days=1)

                if (self.method == "degr-linear" and asset_sign * (
                        fy_amount - fy_amount_check) < 0):
                    break

                if i == 0 and li == 0:
                    if entry.get("day_amount") > 0.0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = self._get_first_period_amount(table, entry,
                                                               depreciation_start_date,
                                                               line_dates)
                        amount = round(amount, digits)
                else:
                    if entry.get("day_amount") > 0.0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = entry.get("period_amount")
                # last year, last entry
                # Handle rounding deviations.
                if i == i_max and li == li_max:
                    amount = remaining_value
                    remaining_value = 0.0
                else:
                    remaining_value -= amount
                fy_amount_check += amount
                line = {
                    "date": line_date,
                    "days": line_days,
                    "amount": amount,
                    "depreciated_value": depreciated_value,
                    "remaining_value": remaining_value, }
                lines.append(line)
                depreciated_value += amount

            # Handle rounding and extended/shortened FY deviations.
            #
            # Remark:
            # In account_asset_management version < 8.0.2.8.0
            # the FY deviation for the first FY
            # was compensated in the first FY depreciation line.
            # The code has now been simplified with compensation
            # always in last FT depreciation line.
            if self.method_time == "year" and not entry.get("day_amount"):
                if round(fy_amount_check - fy_amount, digits) != 0:
                    diff = fy_amount_check - fy_amount
                    amount = amount - diff
                    remaining_value += diff
                    lines[-1].update(
                        {"amount": amount, "remaining_value": remaining_value})
                    depreciated_value -= diff

            if not lines:
                table.pop(i)
            else:
                entry["lines"] = lines
            line_dates = line_dates[li:]

        for entry in table:
            if not entry["fy_amount"]:
                entry["fy_amount"] = sum(
                    [line["amount"] for line in entry["lines"]])

    def _get_fy_info(self, date):
        """Return an homogeneus data structure for fiscal years."""
        fy_info = self.company_id.compute_fiscalyear_dates(date)
        if "record" not in fy_info:
            fy_info["record"] = DummyFy(date_from=fy_info["date_from"],
                                        date_to=fy_info["date_to"])
        return fy_info

    def _compute_loan_table(self):
        table = []
        if (not self.loan_year):
            return table
        company = self.company_id
        asset_date_start = self.date_start
        fiscalyear_lock_date = company.fiscalyear_lock_date or fields.Date.to_date(
            "1901-01-01")
        loan_start_date = self.date_start
        loan_stop_date = self._get_loan_stop_date(loan_start_date)
        fy_date_start = asset_date_start
        while fy_date_start <= loan_stop_date:
            fy_info = self._get_fy_info(fy_date_start)
            table.append({
                "fy": fy_info["record"],
                "date_start": fy_info["date_from"],
                "date_stop": fy_info["date_to"],
                "init": fiscalyear_lock_date >= fy_info["date_from"], })
            fy_date_start = fy_info["date_to"] + relativedelta(days=1)
        # Step 1:
        # Calculate depreciation amount per fiscal year.
        # This is calculation is skipped for method_time != 'year'.
        line_dates = self._compute_loan_line_dates(table, loan_start_date,
                                                   loan_stop_date)
        table = self._compute_loan_amount_per_fiscal_year(table, line_dates,
                                                          loan_start_date,
                                                          loan_stop_date)
        # Step 2:
        # Spread depreciation amount per fiscal year
        # over the depreciation periods.
        self._compute_loan_table_lines(table, loan_start_date, loan_stop_date,
                                       line_dates)

        return table

    def _compute_depreciation_table(self):
        table = []
        if (self.method_time in ["year",
                                 "number"] and not self.method_number and not self.method_end):
            return table
        company = self.company_id
        asset_date_start = self.date_start
        fiscalyear_lock_date = company.fiscalyear_lock_date or fields.Date.to_date(
            "1901-01-01")
        depreciation_start_date = self._get_depreciation_start_date(
            self._get_fy_info(asset_date_start)["record"])
        depreciation_stop_date = self._get_depreciation_stop_date(
            depreciation_start_date)
        fy_date_start = asset_date_start
        while fy_date_start <= depreciation_stop_date:
            fy_info = self._get_fy_info(fy_date_start)
            table.append({
                "fy": fy_info["record"],
                "date_start": fy_info["date_from"],
                "date_stop": fy_info["date_to"],
                "init": fiscalyear_lock_date >= fy_info["date_from"], })
            fy_date_start = fy_info["date_to"] + relativedelta(days=1)
        # Step 1:
        # Calculate depreciation amount per fiscal year.
        # This is calculation is skipped for method_time != 'year'.
        line_dates = self._compute_line_dates(table, depreciation_start_date,
                                              depreciation_stop_date)
        table = self._compute_depreciation_amount_per_fiscal_year(table,
                                                                  line_dates,
                                                                  depreciation_start_date,
                                                                  depreciation_stop_date)
        # Step 2:
        # Spread depreciation amount per fiscal year
        # over the depreciation periods.
        self._compute_depreciation_table_lines(table, depreciation_start_date,
                                               depreciation_stop_date,
                                               line_dates)

        return table

    def _get_depreciation_entry_name(self, seq):
        """ use this method to customise the name of the accounting entry """
        return (self.code or str(self.id)) + "/" + str(seq)

    def _compute_entries(self, date_end, check_triggers=False):
        # TODO : add ir_cron job calling this method to
        # generate periodical accounting entries
        result = []
        error_log = ""
        if check_triggers:
            recompute_obj = self.env["account.asset.recompute.trigger"]
            recomputes = recompute_obj.sudo().search([("state", "=", "open")])
            if recomputes:
                trigger_companies = recomputes.mapped("company_id")
                for asset in self:
                    if asset.company_id.id in trigger_companies.ids:
                        asset.compute_depreciation_board()

        depreciations = self.env["account.asset.line"].search(
            [("asset_id", "in", self.ids), ("type", "=", "depreciate"),
             ("init_entry", "=", False),
             ("line_date", "<=", date_end), ("move_check", "=", False), ],
            order="line_date", )
        for depreciation in depreciations:
            try:
                with self.env.cr.savepoint():
                    result += depreciation.create_move()
            except Exception:
                e = exc_info()[0]
                tb = "".join(format_exception(*exc_info()))
                asset_ref = depreciation.asset_id.name
                if depreciation.asset_id.code:
                    asset_ref = "[{}] {}".format(depreciation.asset_id.code,
                                                 asset_ref)
                error_log += _("\nError while processing asset '%s': %s") % (
                    asset_ref, str(e),)
                error_msg = _("Error while processing asset '%s': \n\n%s") % (
                    asset_ref, tb,)
                _logger.error("%s, %s", self._name, error_msg)

        if check_triggers and recomputes:
            companies = recomputes.mapped("company_id")
            triggers = recomputes.filtered(
                lambda r: r.company_id.id in companies.ids)
            if triggers:
                recompute_vals = {
                    "date_completed": fields.Datetime.now(),
                    "state": "done", }
                triggers.sudo().write(recompute_vals)

        return (result, error_log)


class AccountAssetType(models.Model):
    _name = 'account.asset.type'

    name = fields.Char('Equipment Type', required=True)
    beverage = fields.Boolean()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 ondelete='cascade')

    _sql_constraints = [
        ('company_equipment_type_number_unique', 'UNIQUE(company_id, name)',
         'Equipment Type Already exist.')
    ]


class EquipmentName(models.Model):
    _name = 'equipment.name'
    _description = 'Equipment Name'
    """Model is used to save the Equipment names in model.To make the name 
    field dropdown"""
    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string='Name', help='Name of the equipment',required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 ondelete='cascade')

    _sql_constraints = [
        ('company_equipment_name_unique', 'UNIQUE(company_id, name)',
         'Equipment Name Already exist.')
    ]


class EquipmentModel(models.Model):
    _name = 'equipment.model.name'
    _description = 'Equipment Model'
    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string='Model', help='Name of the equipment Model')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 ondelete='cascade')

    _sql_constraints = [
        ('company_equipment_model_unique', 'UNIQUE(company_id, name)',
         'Equipment Model Already exist.')
    ]


class EquipmentModelNumber(models.Model):
    _name = 'equipment.model.number'
    _description = 'Equipment Model Number'
    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string='Model', help='Equipment Model Number')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 ondelete='cascade')

    _sql_constraints = [
        ('company_equipment_model_number_unique', 'UNIQUE(company_id, name)',
         'Equipment Model Already exist.')
    ]
