from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# <-----------> Workflow Equipment Activity <--------->
#
# -----------------------> install <---------------------------------
# Equipment  -----initial ---> Warehouse ---install---> Customer location. (Micromarket/Order)
#
# ----------------------> Remove <-----------------------------------
# Equipment --initial --> warehouse |--install--->|Customer location
#                                   |<---Remove---|
#
# -------------------------> Retire <--------------------------------
# Equipment --initial --> warehouse |--install--->|Customer location
#                            |      |<---Remove---|
#                            |
#                     |---Retire----|
#
# ----------------------> Exchange <---------------------------------
#                                         [1]
# Equipment --initial --> warehouse |--install--->|Customer location
#                             |           [2]
#                             |     |<---Remove---|
#                             |           [3]
# New Equipment --initial --> |---->|--install--->|Customer location


# class EquipemtActivityType(models.Model):
#     _name = 'equipment.activity.type'
#
#     name = fields.Char(string="Type name")
#

class AccountAssetTransfer(models.Model):
    _name = "account.asset.transfer"
    _description = "Equipment Transfer"
    _inherit = ['mail.thread']
    _order = 'start_date desc,id desc'

    name = fields.Char(string="Name", required=True, copy=False, default='New',
                       readonly=True)
    transferred_asset_id = fields.Many2one('account.asset',
                                           string="Equipment to be Transferred",
                                           required=True,
                                           states={
                                               'done': [('readonly', True)]})

    transferred_asset_serial_no = fields.Char('Serial No', copy=False,
                                              required=True,
                                              related='transferred_asset_id.serial_no')

    transferred_asset_name = fields.Char(string="Equipment Name",
                                         related="transferred_asset_id.name")
    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env.user.company_id,
                                 states={'done': [('readonly', True)]},
                                 required=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related="company_id.currency_id",
                                  states={'done': [('readonly', True)]})
    purchase_price = fields.Monetary(string="Purchase Price",
                                     related="transferred_asset_id.purchase_value",
                                     store=True)
    residual_value = fields.Monetary(string="Residual Value",
                                     related="transferred_asset_id.value_residual",
                                     store=True)
    source_location_id = fields.Many2one('stock.location',
                                         string="Source Location",
                                         states={'done': [('readonly', True)]})
    destination_location_id = fields.Many2one('stock.location',
                                              string="Area/POS", )
    destination_location_id_mm = fields.Many2one('stock.location',
                                                 string="Micro Market",
                                                 compute='_compute_destination_location_mm',
                                                 store=True,
                                                 states={'done': [
                                                     ('readonly', True)]})

    @api.depends('transfer_micro_market_id', 'transfer_location_type',
                 'transferred_asset_id')
    def _compute_destination_location_mm(self):
        """Function compute the location of micromarket"""
        for rec in self:
            if rec.transfer_location_type == 'micro_market' and rec.transfer_micro_market_id:
                locations = self.env['stock.location'].search(
                    [('warehouse_id', '=', rec.transfer_micro_market_id.id),
                     ('is_bin_location', '=', True),
                     ('company_id', '=', rec.env.company.id)]).id
                rec.destination_location_id_mm = locations
            else:
                rec.destination_location_id_mm = False

    user_id = fields.Many2one('res.users', string="Responsible Person",
                              states={'done': [('readonly', True)]})
    asset_operation_type_id = fields.Many2one('asset.transfer.type',
                                              string="Operation Type",
                                              states={
                                                  'done': [('readonly', True)]})
    asset_transfer_type = fields.Selection(
        [('wtl', 'Warehouse to Location'), ('wtw', 'Warehouse to Warehouse'),
         ('ltw', 'Location to Warehouse'),
         ('ltl', 'Location to Location'), ], 'Transfer Type',
        states={'done': [('readonly', True)]})
    reason = fields.Text(string="Reason",
                         states={'done': [('readonly', True)]})
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string="Analytic Account",
                                          states={'done': [('readonly', True)]})
    state = fields.Selection(selection=[('draft', 'Draft'), ('done', 'Done'),
                                        ('cancelled', 'Cancelled'), ],
                             string="Status", default='draft',
                             track_visibility="onchange")
    create_date = fields.Datetime(string="Create Date",
                                  default=fields.Datetime.now, readonly=True, )
    transferred_date = fields.Date(string="Transferred Date",
                                   states={'done': [('readonly', True)]})
    #        default=fields.Date.today(),
    transfer_user_id = fields.Many2one('res.users', 'Transfer By',
                                       readonly=True)
    asset_sequence_number = fields.Char(string="Equipment Sequence Number",
                                        related="transferred_asset_id.code", )
    asset_description = fields.Text(string="Asset Discription",
                                    related="transferred_asset_id.note")
    asset_date_purchased = fields.Date(string="Asset Date Purchased",
                                       related="transferred_asset_id.effective_date")
    asset_purchase_cost = fields.Monetary(string="Asset Purchase Cost",
                                          related="transferred_asset_id.value_residual")
    internal_note = fields.Text(string="Internal Note",
                                states={'done': [('readonly', True)]})
    transfer_location_type = fields.Selection([('micro_market', 'Micro '
                                                                'market'),
                                               ('order', 'Other')],
                                              string='Location Type',
                                              readonly=True,
                                              states={'draft': [
                                                  ('readonly', False)]})
    transfer_micro_market_id = fields.Many2one('stock.warehouse',
                                               string="Micro Market",
    domain=[
        ('location_type', '=', 'micro_market')],
                                               readonly=True,
                                               states={'draft': [
                                                   ('readonly', False)]})
    transfer_warehouse_id = fields.Many2one('stock.warehouse',string="Micro Market", domain=[
        ('location_type', '=', 'view')],
        readonly=True, states={
            'draft': [('readonly', False)]})
    transfer_machine_location_ids = fields.Many2many('stock.location',
                                                     compute='_compute_transfer_machine_location_ids',
                                                     store="true")
    transfer_machine_location_ids_mm = fields.Many2many('stock.location',
                                                        'transfer_location_rel',
                                                        compute='_compute_transfer_machine_location_ids',
                                                        store="true")
    type = fields.Many2one('case.management.type', string="Type",
                           states={'done': [('readonly', True)]})
    transfer_location_partner_id = fields.Many2one('res.partner',
                                                   string="Customer",
                                                   states={'done': [
                                                       ('readonly', True)]},
                                                   domain="[('operator_id', '=', company_id),('is_customer','=',True),('type','=','contact'),('parent_id','=',False)]")
    customer_ids = fields.Many2many('res.partner',
                                    compute='compute_transfer_location_partner_id',
                                    store="true")
    mm_ids = fields.Many2many('stock.warehouse',
                              compute='compute_transfer_location_partner_id',
                              store="true")
    area = fields.Char(string="Area of the machine")
    equipment_state = fields.Selection(
        selection=[("draft", "Active"), ("open", "In Service"),
                   ("removed", "Inactive"), ('archived', 'Archived'),
                   ('out_repair', 'OutSide Repair')],
        string="Status", )
    disable_transfer = fields.Boolean(string="Disable the transfer button")

    def _default_operator_location_id(self):
        """Function to set the operator location default from comapny"""
        return self.env.company.equipment_warehouse_id.id

    equipment_warehouse = fields.Many2one('stock.location',
                                          default=_default_operator_location_id)
    operator_locations_ids = fields.Many2many('stock.location',
                                              related='transferred_asset_id.operator_locations_ids')

    # Exchange section
    new_equipment = fields.Many2one('account.asset', string="New Equipment No/Name")
    new_equipment_serial_no = fields.Char('Serial No', copy=False,
                                          required=True,
                                          related='new_equipment.serial_no')
    new_location_type = fields.Selection([('micro_market', 'Micromarket'),
                                          ('order', 'Other')],
                                         string='Location Type',
                                         default="micro_market", readonly=True,
                                         states={
                                             'draft': [('readonly', False)]})
    new_transfer_micro_market_id = fields.Many2one('stock.warehouse',string="Micro Market",
                                                   domain=[('location_type', '=', 'micro_market')],
                                                   readonly=True, store=True,
                                                   states={'draft': [
                                                       ('readonly', False)]})
    new_transfer_machine_location_ids = fields.Many2many('stock.location',
                                                         'rel_new_transfer_machine_location_ids_stock_location',
                                                         compute='_compute_new_transfer_machine_location_ids',
                                                         store=True
                                                         )
    new_transfer_machine_location_ids_mm = fields.Many2many('stock.location',
                                                            'rel_new_transfer_machine_location_ids_mm_stock_location',
                                                            'transfer_location_stock_location_rel',
                                                            compute='_compute_new_transfer_machine_location_ids',
                                                            store=True)
    new_start = fields.Datetime(string="Start Date",
                                default=fields.Datetime.now)
    new_equipment_warehouse_id = fields.Many2one('stock.location',
                                                 string="New Equipment Warehouse")
    new_destination_location_id = fields.Many2one('stock.location',
                                                  string="Area/POS", )
    new_destination_location_id_mm = fields.Many2one('stock.location',
                                                     string="Micro Market",
                                                     compute='_compute_new_destination_location_id_mm',
                                                     store=True,
                                                     states={'done': [
                                                         ('readonly', True)]})
    new_initial_meter_reading = fields.Float(string="Initial Meter Reading")
    new_relative_commission_rate = fields.Float(
        string="Relative Commission Rate")
    destination_location = fields.Char('Location/ Area')
    customer_name = fields.Char('Customer Name')

    @api.depends('new_location_type', 'new_transfer_micro_market_id',
                 'new_equipment')
    def _compute_new_destination_location_id_mm(self):
        for rec in self:
            if rec.new_location_type == 'micro_market' and rec.new_transfer_micro_market_id:
                locations = self.env['stock.location'].search(
                    [('warehouse_id', '=', rec.new_transfer_micro_market_id.id),
                     ('is_bin_location', '=', True),
                     ('company_id', '=', self.env.company.id)]).id
                rec.new_destination_location_id_mm = locations
            else:
                rec.new_destination_location_id_mm = False

    @api.onchange('new_equipment')
    def _onchange_new_equipment(self):
        self.new_equipment_warehouse_id = self.new_equipment.machine_location_id

    @api.model
    def _get_valid_hours(self):
        # return [('install', 'Install'), ('remove', 'Remove'), ('exchange', 'Exchange'), ('retire', 'Retire')]

        equipment_state = self.env.context.get('default_equipment_state')
        print("equipment_state", equipment_state)
        if equipment_state == 'draft':
            return [('install', 'Install'), ('exchange', 'Exchange'),
                    ('retire', 'Retire')]
        elif equipment_state == 'open':
            return [('remove', 'Remove')]

    activity_type = fields.Selection(
        [('install', 'Install'), ('remove', 'Remove'), ('exchange', 'Exchange'),
         ('retire', 'Retire'), ('out_repair', 'OutSide Repair')],
        string="Activity Type", default='install')

    start_date = fields.Datetime(string="Start Date",
                                 default=fields.Datetime.now)
    initial_meter_reading = fields.Float(String="Initial Meter Reading")
    relative_commission_rate = fields.Float(String="Relative Commission Rate")
    disposition_date = fields.Date(string="Disposition Date",
                                   default=fields.Date.today)
    retired_reason = fields.Selection(
        [('damage', 'Damage'), ('junk', 'Junk'), ('scrap', 'Scrap'),
         ('sold', 'Sold')],
        string="Retired Date")
    equipment_location = fields.Char(string="Equipment Location",
                                     help="Used to save the location name",
                                     compute='_compute_equipment_location',
                                     store=True)

    @api.depends('destination_location_id', 'transfer_micro_market_id',
                 'transfer_location_type')
    def _compute_equipment_location(self):
        """Function is used to compute the name of the Equipment location . Why it's doing is
        MicroMarket is warehouse and ares/pos is a location.So We can use Reference field or char.
        So now using the char method."""
        for rec in self:
            if rec.transfer_location_type == 'micro_market':
                rec.equipment_location = f"""{rec.transfer_micro_market_id.name} - {rec.transfer_micro_market_id.partner_id.name}"""
            elif rec.destination_location_id:
                rec.equipment_location = rec.destination_location_id.name
            else:
                rec.equipment_location = rec.equipment_warehouse.complete_name

    @api.onchange('activity_type')
    def _onchange_activity_type(self):
        print("_onchange_activity_type")
        equipment_status = self.env.context.get('default_equipment_state')
        if (equipment_status == 'draft' and self.activity_type
                in ['remove', 'exchange']):
            self.disable_transfer = True
        elif (equipment_status == 'out_repair' and self.activity_type in [
            'remove', 'exchange', 'out_repair']):
            self.disable_transfer = True
        elif equipment_status == 'open' and self.activity_type in ['install',
                                                                   'retire',
                                                                   'out_repair']:
            self.disable_transfer = True
        else:
            self.disable_transfer = False
        if self.activity_type in ['remove', 'retire', 'exchange']:
            self.transfer_location_partner_id = self.transferred_asset_id.location_partner_id
            self.transfer_location_type = self.transferred_asset_id.location_type
            self.destination_location_id_mm = self.transferred_asset_id.machine_location_id
            self.destination_location_id = self.transferred_asset_id.machine_location_id
            self.transfer_micro_market_id = self.transferred_asset_id.micro_market_id
            print("--------------------------->---",
                  self.transfer_micro_market_id)
        else:
            self.destination_location_id_mm = False
            self.destination_location_id = False

    # @api.depends('transfer_location_type')

    # @api.depends('asset_transfer_type')
    # def _compute_destination_location_id(self):
    #     print("_compute_destination_location_id",self._origin.destination_location_id)
    #     for rec in self:
    #         rec._origin.asset_transfer_type = False
    #         if rec._origin.asset_transfer_type == 'wtl':
    #             rec._origin.destination_location_id = self.env['stock.location'].search(
    #                 [('id', 'in', rec.transfer_machine_location_ids_mm.ids),
    #                  ('id', 'not in', rec.source_location_id.id)],
    #                 limit=1)
    #         elif rec._origin.asset_transfer_type == 'ltw':
    #             rec._origin.destination_location_id = self.env['stock.location'].search(
    #                 [('id', 'in', rec.transfer_machine_location_ids.ids),
    #                  ('id', 'not in', rec.source_location_id.id)],
    #                 limit=1)

    # @api.onchange('asset_transfer_type')
    # def _onchange_asset_transfer_type(self):
    #     print("88888888")
    #     self.destination_location_id_mm = None
    #     self.destination_location_id = None
    #     # if self.location_partner_id:
    #
    #     if self.asset_transfer_type in ['wtw', 'ltl'] and self.asset_operation_type_id.code in ['incoming', 'outgoing']:
    #         raise UserError(_('Please choose operation type internal transfer to proceed'))

    @api.depends('transfer_location_partner_id')
    def compute_transfer_location_partner_id(self):
        for rec in self:
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.user.company_id.id)])
            partner_ids = warehouse.mapped('partner_id')
            rec.customer_ids = partner_ids.ids
            if rec.transfer_location_partner_id:
                mm_ids = warehouse.filtered(lambda
                                                s: s.partner_id.id == rec.transfer_location_partner_id.id)
                rec.mm_ids = mm_ids.ids
            else:
                rec.mm_ids = warehouse.ids

    @api.depends('new_transfer_micro_market_id', 'transfer_location_partner_id',
                 'new_location_type', 'new_equipment')
    def _compute_new_transfer_machine_location_ids(self):
        # TODO :- Need to Fix the issue. When changing the customer need to show the destination address.
        for rec in self:
            print("Momo1")
            rec.new_transfer_machine_location_ids_mm = False
            rec.new_transfer_machine_location_ids = False
            if rec.new_location_type == 'micro_market' and rec.transfer_location_partner_id:
                micro_markets = self.env['stock.warehouse'].search(
                    [('company_id', '=', self.env.company.id),
                     ('location_type', '=', 'micro_market'), (
                         'partner_id', '=',
                         rec.transfer_location_partner_id.id)])
                locations = self.env['stock.location'].search(
                    [('warehouse_id', 'in', micro_markets.ids),
                     ('is_bin_location', '=', True),
                     ('company_id', '=', self.env.company.id)])
                rec.new_transfer_machine_location_ids_mm = [
                    (6, 0, locations.ids)]
                # rec.new_transfer_machine_location_ids_mm = [(6, 0, locations.ids)]
                if not rec.new_transfer_machine_location_ids_mm:
                    rec._origin.new_transfer_machine_location_ids_mm = [
                        (6, 0, locations.ids)]
            if rec.new_location_type == 'order' and rec.transfer_location_partner_id:
                rec.new_transfer_machine_location_ids_mm = [(5, 0, 0)]
                # rec.new_transfer_machine_location_ids_mm = [(5, 0, 0)]
                pass

    @api.depends('transfer_warehouse_id', 'transfer_micro_market_id',
                 'transfer_location_partner_id',
                 'transfer_location_type')
    def _compute_transfer_machine_location_ids(self):
        # TODO :- Need to Fix the issue. When changing the customer need to show the destination address.
        for rec in self:

            if rec.transfer_location_type == 'micro_market' and rec.transfer_location_partner_id:
                print("self.env.company.id", self.env.company.id,
                      rec.transfer_location_partner_id.id)
                micro_markets = self.env['stock.warehouse'].search(
                    [('company_id', '=', self.env.company.id),
                     ('location_type', '=', 'micro_market'), (
                         'partner_id', '=',
                         rec.transfer_location_partner_id.id)])
                print("micromarket", micro_markets)
                locations = self.env['stock.location'].search(
                    [('warehouse_id', 'in', micro_markets.ids),
                     ('is_bin_location', '=', True),
                     ('company_id', '=', self.env.company.id)])
                rec.transfer_machine_location_ids_mm = [(6, 0, locations.ids)]
                # rec.new_transfer_machine_location_ids_mm = [(6, 0, locations.ids)]
            if rec.transfer_location_type == 'order' and rec.transfer_location_partner_id:
                rec.transfer_machine_location_ids_mm = [(5, 0, 0)]
                # rec.new_transfer_machine_location_ids_mm = [(5, 0, 0)]
                pass
            rec.transfer_machine_location_ids_mm = []

    @api.model
    def default_get(self, default_fields):
        res = super(AccountAssetTransfer, self).default_get(default_fields)
        if self._context.get('create_from_machine'):
            machine_id = self.env['account.asset'].browse(
                self._context.get('active_id', []))
            res.update({
                'transferred_asset_id': machine_id.id,
            })
        return res

    @api.model
    def create(self, vals):
        res = super(AccountAssetTransfer, self).create(vals)
        sequence = self.env.ref('account_asset_management.machine_transfer_seq')
        seq = sequence.with_context(
            force_company=res.company_id.id).next_by_code(
            "account.machine.transfer") or _(
            'New')
        res.name = seq
        return res

    @api.onchange('transferred_asset_id')
    def _onchange_transferred_asset_id(self):
        print("_onchange_transferred_asset_id")
        if self.transferred_asset_id:
            self.transfer_location_type = self.transferred_asset_id.location_type
            self.source_location_id = self.transferred_asset_id.machine_location_id.id
            self.transfer_warehouse_id = self.transferred_asset_id.warehouse_id.id
            self.transfer_micro_market_id = self.transferred_asset_id.micro_market_id.id
            self.transfer_location_partner_id = self.transferred_asset_id.location_partner_id.id
            print("self.transfer_micro_market_id",
                  self.transfer_micro_market_id)

    def act_done(self):
        for rec in self:
            rec.state = 'done'
            rec.write({'transferred_date': fields.Date.today(),
                       'transfer_user_id': self.env.uid})
            if rec.activity_type == 'install':
                if rec.destination_location_id:
                    rec.transferred_asset_id.write({
                        'machine_location_id': rec.destination_location_id.id,
                        'location_partner_id': rec.transfer_location_partner_id.id,
                        'micro_market_id': rec.transfer_micro_market_id.id,
                        'last_transfer_date': fields.Date.today(),
                        'area_or_pos': rec.area,
                        'location_type': rec.transfer_location_type,
                        'state': 'open',
                        'activity_type': rec.activity_type,
                    })
                    rec.destination_location = str(
                        rec.destination_location_id.name)
                    if rec.transfer_location_partner_id:
                        rec.transfer_location_partner_id.message_post(
                            body=_(
                                f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong> - Equipment is 
                            Installed in Area - {rec.destination_location_id.name} By - <strong>{rec.transfer_user_id.name}</strong>'''))

                else:
                    rec.transferred_asset_id.write({
                        'machine_location_id': rec.destination_location_id_mm.id,
                        'location_partner_id': rec.transfer_location_partner_id.id,
                        'micro_market_id': rec.transfer_micro_market_id.id,
                        'last_transfer_date': fields.Date.today(),
                        'area_or_pos': rec.area,
                        'location_type': rec.transfer_location_type,
                        'state': 'open',
                        'activity_type': rec.activity_type,
                    })
                    rec.destination_location = str(
                        rec.destination_location_id_mm.complete_name)
                    if rec.transfer_user_id and rec.transfer_micro_market_id:
                        rec.transfer_micro_market_id.message_post(
                            body=_(
                                f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong> - Equipment is 
                                Installed in this market By- <strong>{rec.transfer_user_id.name}</strong>'''))
                rec.customer_name = rec.transfer_location_partner_id.name

            elif rec.activity_type == 'remove':
                if rec.transferred_asset_id.micro_market_id and rec.transfer_user_id:
                    rec.transferred_asset_id.micro_market_id.message_post(
                        body=_(
                            f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong> - Equipment is 
                            Removed from this market By- <strong>{rec.transfer_user_id.name}</strong><br/><strong>Reason:-</strong>{rec.reason}'''))
                elif rec.transfer_user_id and rec.destination_location_id:
                    rec.transfer_location_partner_id.message_post(
                        body=_(
                            f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong>- Equipment is Removed 
                            from location - <strong> {rec.destination_location_id.name} </strong> By - <strong>{rec.transfer_user_id.name}</strong><br/><strong>Reason:-</strong>{rec.reason}'''))
                rec.transferred_asset_id.write({
                    'machine_location_id': rec.equipment_warehouse.id,
                    'location_partner_id': False,
                    'micro_market_id': False,
                    'last_transfer_date': fields.Date.today(),
                    'area_or_pos': False,
                    'location_type': False,
                    'state': 'draft',
                    'activity_type': rec.activity_type,
                })
                rec.equipment_location = str(
                    rec.equipment_warehouse.complete_name)
                rec.destination_location = str(
                    rec.equipment_warehouse.complete_name)
                rec.customer_name = False
            elif rec.activity_type == 'retire':
                print("partner", rec.transfer_location_partner_id)
                rec.transferred_asset_id.write({
                    'machine_location_id': rec.equipment_warehouse.id,
                    'location_partner_id': False,
                    'micro_market_id': False,
                    'last_transfer_date': fields.Date.today(),
                    'area_or_pos': False,
                    'location_type': False,
                    'state': 'removed',
                    'activity_type': rec.activity_type,
                })
                rec.destination_location = str(
                    rec.equipment_warehouse.complete_name)
                rec.equipment_location = str(
                    rec.equipment_warehouse.complete_name)
                rec.customer_name = False
            elif rec.activity_type == 'out_repair':
                rec.transferred_asset_id.write({
                    'state': 'out_repair'
                })
            else:
                """ Exchange :- first bring new equipment (adding customer,location etc..), second Removing the 
                Equipment(Removing the customer,location etc...), then we create the new equipment Transfer record(
                install). """
                # vals['last_transfer_date'] = fields.Date.today()
                if rec.new_location_type == 'micro_market':
                    rec.new_transfer_micro_market_id.message_post(
                        body=_(
                            f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong> - Equipment is 
                                                Exchanged with <strong>{rec.new_equipment.code}{rec.new_equipment.name}- </strong> By <strong>{rec.transfer_user_id.name}</strong>'''))

                    print("rec.new_transfer_micro_market_id.id",
                          rec.new_transfer_micro_market_id.id)
                    values = {
                        'machine_location_id': rec.new_destination_location_id_mm.id,
                        'location_partner_id': rec.transfer_location_partner_id.id,
                        'micro_market_id': rec.new_transfer_micro_market_id.id,
                        'area_or_pos': '',
                        'location_type': rec.new_location_type,
                        'state': 'open',
                        'activity_type': 'install',
                    }
                    print("==---->", values)
                    rec.new_equipment.write(values)

                    rec.destination_location = str(
                        rec.new_destination_location_id_mm.complete_name)
                else:
                    rec.new_equipment.write({
                        'machine_location_id': rec.new_destination_location_id.id,
                        'location_partner_id': rec.transfer_location_partner_id.id,
                        'micro_market_id': False,
                        'last_transfer_date': fields.Date.today(),
                        'area_or_pos': rec.area,
                        'location_type': rec.new_location_type,
                        'state': 'open',
                        'activity_type': 'install',
                    })
                    rec.location_partner_id = rec.transfer_location_partner_id.id,
                    # Removing the location and customer
                    rec.transfer_location_partner_id.message_post(
                        body=_(
                            f'''<strong>{rec.transferred_asset_id.code} {rec.transferred_asset_id.name}</strong> - Equipment is
                                                Exchanged with - <strong>{rec.new_equipment.code} {rec.new_equipment.name} </strong> By - <strong>{rec.transfer_user_id.name}</strong>'''))

                rec.transferred_asset_id.write({
                    'machine_location_id': rec.equipment_warehouse.id,
                    'location_partner_id': False,
                    'micro_market_id': False,
                    'last_transfer_date': fields.Date.today(),
                    'area_or_pos': False,
                    'location_type': False,
                    'state': 'draft',
                    'activity_type': 'exchange',
                })
                rec.new_equipment.equipment_trasfer_ids = [(4, rec.id)]
                rec.customer_name = rec.transfer_location_partner_id.name
            rec.transferred_asset_id.equipment_trasfer_ids = [(4, rec.id)]

    def _action_cancel(self):
        self.state = 'cancelled'

    def act_cancel_manager(self):
        for rec in self:
            rec._action_cancel()

    def act_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for transfer in self:
            if transfer.state not in ['draft', 'cancelled']:
                raise ValidationError("Only delete in draft or cancelled state")
        return super(AccountAssetTransfer, self).unlink()


class AssetTransferType(models.Model):
    _name = "asset.transfer.type"
    _rec_name = "name"

    sequence_code = fields.Char(string="Code", required=True)
    code = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'),
                             ('internal', 'Internal Transfer')],
                            'Type of Operation', required=True)
    name = fields.Text(string="Name", required=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 default=lambda self: self.env.company)


class ResCompany(models.Model):
    _inherit = 'res.company'

    operator_locations_ids = fields.Many2many('stock.location',
                                              compute='_compute_operator_locations_ids')

    equipment_warehouse_id = fields.Many2one('stock.location',
                                             string="Equipment Default Warehouse",
                                             domain="[('id', 'in',operator_locations_ids)]")

    def _compute_operator_locations_ids(self):
        for rec in self:
            rec.operator_locations_ids = False
            if rec.id:
                operator_locator = self.env['stock.warehouse'].search(
                    [('location_type', '=', 'view'),
                     ('company_id', '=', self.id)],
                    order='id asc').mapped('lot_stock_id')
                rec.operator_locations_ids = [(6, 0, operator_locator.ids)]
                if operator_locator:
                    rec.operator_location_id = operator_locator[0]


class CaseManagementType(models.Model):
    _name = "case.management.type"
    _description = "Case Management Type"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 default=lambda self: self.env.company)
    install = fields.Boolean('Install')
    removal = fields.Boolean('Removal')
    is_preventive = fields.Boolean('Preventive', copy=False)
