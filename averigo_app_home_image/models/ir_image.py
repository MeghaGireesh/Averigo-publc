import logging

from odoo.exceptions import UserError
from datetime import datetime

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class IRImage(models.Model):
    _name = 'ir.image'
    _description = 'Hoe Screen Image'
    _order = 'create_date desc'

    name = fields.Char()
    image = fields.Binary(string='Image', required=True)
    active = fields.Boolean(string="Active", default=True)
    operator_id = fields.Many2many('res.company', 'ir_image_res_company_rel', 'image_id', 'company_id',
                                   domain=[('is_main_company', '!=', True)],
                                   string="Operator")
    location = fields.Many2many('res.partner', 'ir_image_res_partner_rel', 'image_id', 'partner_id',
                                domain=[('is_customer', '=', True)])
    micro_market_id = fields.Many2many('stock.warehouse', 'ir_image_stock_warehouse_rel', 'image_id', 'warehouse_id',
                                       domain=[('location_type', '=', 'micro_market')])
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="Stop Date")
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="Stop Time")
    banner_text = fields.Text(string="Banner Text")
    mm_ids = fields.Many2many('stock.warehouse', 'ir_image_stock_warehouse_rel2', 'image_id2', 'warehouse_id2')

    @api.onchange('operator_id')
    def operator_id_changed(self):
        partner_ids = self.env['res.partner'].search([('company_id', 'in', self.operator_id.ids)]).ids
        return {
            'domain': {'location': [('is_customer', '=', True),
                                    ('operator_id', 'in', self.operator_id.ids)] if self.operator_id.ids else [
                ('is_customer', '=', True)]},
            'micro_market_id': [('location_type', '=', 'micro_market'), ('partner_id', 'in', partner_ids)]}

    @api.onchange('location')
    def location_changed(self):
        return {
            'domain': {
                'micro_market_id': [('partner_id', 'in', self.location.ids)] if self.location.ids else [
                    ('location_type', '=', 'micro_market')]
            }
        }

    def get_featured_image(self, args):
        try:
            micro_market = self.env['stock.warehouse'].browse(args['micro_market'])
            time = args['time'].split(' ')[1]
            date = args['time'].split(' ')[0]
            hours = float(time.split(':')[0])
            minutes = float(time.split(':')[1]) / 60 * 100
            timed_images = self.env['ir.image'].search(
                [('start_time', '<=', hours + (minutes / 100)), ('end_time', '>=', hours + (minutes / 100))])
            dated_images = self.env['ir.image'].search([('start_date', '<=', date), ('end_date', '>=', date)])
            ids = []
            if dated_images and timed_images:
                ids = list(set(timed_images.ids) & set(dated_images.ids))
            elif timed_images:
                ids = timed_images.ids
            elif dated_images:
                ids = dated_images.ids
            mm_images = self.env['ir.image'].search([('mm_ids', 'in', [micro_market.id])]).ids
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            ids = list(set(ids) & set(mm_images))
            if ids:
                rec = self.env['ir.image'].browse(ids[0])
                return {'image_url': base_url + '/web/image_get?model=ir.image&id=' + str(
                    rec.id) + '&field=image',
                        'banner_text': rec.banner_text}
            else:
                return {'image_url': False,
                        'banner_text': False}
        except:
            return {'image_url': False,
                    'banner_text': False}

    @api.model
    def create(self, vals_list):
        if 'end_date' in vals_list and 'start_date' in vals_list \
                and vals_list['end_date'] < vals_list['start_date']:
            raise UserError(_("Inconsistent start and end dates! \n"
                              "Stop date should be above the start date. "
                              "Please check the date fields and try again."))

        if 'start_time' in vals_list and 'end_time' in vals_list \
                and vals_list['end_time'] < vals_list['start_time']:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Stop time should be above the start time. "
                              "Please check the time fields and try again."))
        if vals_list['start_time'] < 0 or vals_list['end_time'] < 0 or vals_list['start_time'] > 24.0 or vals_list[
            'end_time'] > 24.0:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Time should be 0 to 24.0! "
                              "Please check the time fields and try again."))
        if vals_list['start_time'] == vals_list['end_time']:
            raise UserError(_("Start and End Time Can not be the same."))
        if 'micro_market_id' in vals_list and vals_list['micro_market_id'][0][2]:
            vals_list['mm_ids'] = vals_list['micro_market_id']
        elif 'location' in vals_list and vals_list['location'][0][2]:
            location = vals_list['location'][0][2]
            location = self.env['stock.warehouse'].search([('partner_id', 'in', location)]).ids
            vals_list['mm_ids'] = [[6, False, location]]
        elif 'operator_id' in vals_list and vals_list['operator_id'][0][2]:
            operator_id = vals_list['operator_id'][0][2]
            operator_id = self.env['stock.warehouse'].search([('company_id', 'in', operator_id)]).ids
            vals_list['mm_ids'] = [[6, False, operator_id]]
        else:
            mm_ids = self.env['stock.warehouse'].search([]).ids
            vals_list['mm_ids'] = [[6, False, mm_ids]]
        res = super(IRImage, self).create(vals_list)
        cr = self._cr
        query = """
        SELECT id, start_time, end_time from ir_image WHERE (""" + ((
                                                                                            "('%s'::DATE,'%s'::DATE) OVERLAPS (start_date, end_date) and" % (
                                                                                        res.start_date,
                                                                                        res.end_date)) if res.start_date and res.end_date else "") + """ id != %s and ((start_time <= %s and end_time >= %s) or (start_time >= %s and end_time <= %s)))""" % (
                    res.id, res.start_time, res.start_time, res.end_time, res.end_time)
        cr.execute(query)
        data = cr.dictfetchall()
        if data:
            ops = list(
                set(self.env['ir.image'].browse([d['id'] for d in data]).mapped('mm_ids').ids) & set(res.mm_ids.ids))
            if len(ops) > 0:
                mm = res.env['stock.warehouse'].browse(ops[0])
                raise UserError(
                    _("This image time and date overlaps an existing image for Micro Market %s" % (mm.name)))
        return res

    def write(self, vals_list):
        start_date = vals_list['start_date'] if 'start_date' in vals_list else self.start_date
        end_date = vals_list['end_date'] if 'end_date' in vals_list else self.end_date
        if not start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if not end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        if end_date < start_date:
            raise UserError(_("Inconsistent start and end dates! \n"
                              "Stop date should be above the start date. "
                              "Please check the date fields and try again."))
        start_time = vals_list['start_time'] if 'start_time' in vals_list else self.start_time
        end_time = vals_list['end_time'] if 'end_time' in vals_list else self.end_time
        if start_time > 24 or end_time > 24:
            raise UserError(_("Time values should be less than 24"))
        if end_time < start_time:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Stop time should be above the start time. "
                              "Please check the time fields and try again."))
        if start_time < 0 or end_time < 0 or start_time > 24.0 or end_time > 24.0:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Time should be 0 to 24.0! "
                              "Please check the time fields and try again."))
        if end_time == start_time:
            raise UserError(_("Start and End Time Can not be the same."))
        if 'micro_market_id' in vals_list:
            vals_list['mm_ids'] = vals_list['micro_market_id']
        elif 'location' in vals_list:
            location = vals_list['location'][0][2]
            location = self.env['stock.warehouse'].search([('partner_id', 'in', location)]).ids
            vals_list['mm_ids'] = [[6, False, location]]
        else:
            mm_ids = self.env['stock.warehouse'].search([]).ids
            vals_list['mm_ids'] = [[6, False, mm_ids]]
        res = super(IRImage, self).write(vals_list)

        cr = self._cr
        query = """
        SELECT id, start_time, end_time from ir_image WHERE (""" + \
                (("('%s'::DATE,'%s'::DATE) OVERLAPS (start_date, end_date) and" %
                  (self.start_date, self.end_date)) if self.start_date and self.end_date else "") + \
                """ id != %s and ((start_time <= %s and end_time >= %s) or (start_time >= %s and end_time <= %s)))""" % \
                (self.id, self.start_time, self.start_time, self.end_time, self.end_time)

        cr.execute(query)
        data = cr.dictfetchall()
        if data:
            ops = list(set(self.browse(data[0]['id']).mm_ids.ids) & set(self.mm_ids.ids))
            if len(ops) > 0:
                image = self.browse(data[0]['id'])
                mm = self.env['stock.warehouse'].browse(ops[0])
                raise UserError(
                    _("This image time and date overlaps an existing image for Micro Market %s" % (mm.name)))
        return res
