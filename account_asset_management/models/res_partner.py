from odoo import api, fields, models, _


class ResPartnerMachine(models.Model):
    _inherit = "res.partner"

    machine_ids = fields.One2many('account.asset', 'location_partner_id', string="Equipment",
                                  domain=[('location_type', '=', 'order')])
    machine_count = fields.Integer(compute='_compute_machine_count')

    machine_activity_ids = fields.One2many('account.asset.transfer', 'transfer_location_partner_id',
                                           string="Equipment History")

    @api.depends('machine_ids')
    def _compute_machine_count(self):
        for rec in self:
            rec.machine_count = len(self.env['account.asset'].search([("location_partner_id", "=", rec.id)]))

    def equipment_history(self):
        """Function to show the Equipment history for the Account"""
        form = self.env.ref('account_asset_management.res_partner_equipment_activity').id
        return {
            "name": _("Equipment History"),
            "view_mode": "form",
            "res_model": "res.partner",
            "res_id":self.id,
            "type": "ir.actions.act_window",
            "views": [(form, 'form')],
            "target": "new"
        }

    def show_all_equipment(self):
        tree = self.env.ref('account_asset_management.account_machine_view_tree').id
        form = self.env.ref('account_asset_management.account_machine_view_form').id
        return {
            "name": _("Equipments"),
            "view_mode": "tree,form",
            "res_model": "account.asset",
            'views': [(tree, 'tree'), (form, 'form')],
            "type": "ir.actions.act_window",
            "domain": [("location_partner_id", "=", self.id)],
            "target": "current"
        }

    def name_get(self):
        res = []
        for partner in self:
            name = partner._get_name()
            res.append((partner.id, name))
        return res

    def _get_name(self):
        """Utility method to allow name_get to be overrided without re-browse the partner"""
        partner = self
        name = partner.name or ""
        if partner.nick_name:
            name+= f" ({ partner.nick_name or ''})"
        if partner.company_name or partner.parent_id:
            if not name and partner.type in ["invoice", "delivery", "other"]:
                name = dict(self.fields_get(["type"])["type"]["selection"])[
                    partner.type
                ]
            if not partner.is_company:
                name = self._get_contact_name(partner, name)
        if self._context.get("show_address_only"):
            name = partner._display_address(without_company=True)
        if self._context.get("show_address"):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace("\n\n", "\n")
        name = name.replace("\n\n", "\n")
        if self._context.get("address_inline"):
            name = name.replace("\n", ", ")
        if self._context.get("show_email") and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get("html_format"):
            name = name.replace("\n", "<br/>")
        if self._context.get("show_vat") and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        if self._context.get("show_address_averigo"):
            name = f"""{partner.name or ""}\n {partner.nick_name or ""} \n
            {partner._display_address(
                without_company=True)} \n"""
        return name
