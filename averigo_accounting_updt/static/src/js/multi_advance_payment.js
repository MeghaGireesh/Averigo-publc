odoo.define("averigo_accounting_updt.multi_advance_payment", function(require) {
    "use strict";
    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    FormController.include({
        _onFieldChanged: function(event) {
            var self = this;
            this._super.apply(this, arguments);
             if (event.data.changes.partner_id && self.modelName == 'invoice.receipt'){
                rpc.query({
                    model: "invoice.receipt",
                    method: "get_advance_balance",
                    args: ['', event.data.changes.partner_id],
                }).then(function (result) {
                    console.log(result,"qqqqqqqqqqqqq")
                    self.advance_balance = result;
                });
            }
            if (event.data.changes.payment_mode_id) {
                if (event.data.changes.payment_mode_id.display_name == 'Advance' && self.advance_balance != 0)  {
                    $('.temp_btn').trigger("click");
                }
            }
            if (event.data.changes.partner_id && self.modelName == 'bill.payment'){
                rpc.query({
                    model: "bill.payment",
                    method: "get_credit_balance",
                    args: ['', event.data.changes.partner_id],
                }).then(function (result) {
                    console.log(result,"jjjjjjjjjjjjj")
                    self.credit_balance = result;
                });
            }
            if (event.data.changes.payment_type == 'advance' && self.credit_balance != 0) {
                $('.btn_temporary').trigger("click");

            }
        },
    });
});