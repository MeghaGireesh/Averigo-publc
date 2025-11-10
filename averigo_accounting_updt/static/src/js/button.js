odoo.define('averigo_accounting_updt.action_button', function(require) {
    "use strict";
    var FormController = require('web.FormController');

    FormController.include({
        init: function(parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this._reloadedForDoneState = false; // Used for virtual.location.transfer
        },

        renderButtons: function($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.on('click', '.oe_save_payment_receipt_button', this.savePaymentReceipt.bind(this));
                this.$buttons.on('click', '.oe_save_bill_payment_button', this.saveBillPayment.bind(this));
            }
        },

        autofocus: function() {
            this._super.apply(this, arguments);
            var self = this;

            if (self.$buttons) {
                var stateData = self.renderer.state.data || {};
                console.log(self.modelName, "model");

                if (stateData.state === 'done') {
                    if (self.modelName === 'invoice.receipt' || self.modelName === 'bill.payment') {
                        self.$buttons.find('.o_form_button_edit').hide();
                        self.$buttons.find('.oe_save_bill_payment_button').hide();
                    } else if (self.modelName === 'virtual.location.transfer') {
                        self.$buttons.find('.o_form_button_edit').hide();
                        self.$buttons.find('.o_form_button_save, .o_form_button_cancel').hide();

                        if (!this._reloadedForDoneState) {
                            this._reloadedForDoneState = true;
                            this.reload().then(function() {});
                        }
                    }
                } else {
                    self.$buttons.find('.o_form_button_edit').show();

                    if (self.modelName === 'invoice.receipt' || self.modelName === 'bill.payment') {
                        self.$buttons.find('.oe_save_bill_payment_button').show();
                    } else if (self.modelName === 'virtual.location.transfer') {
                        self.$buttons.find('.o_form_button_save, .o_form_button_cancel').show();
                        this._reloadedForDoneState = false;
                    }
                }
            }
        },

        savePaymentReceipt: function(ev) {
            ev.stopPropagation();
            var self = this;
            return self.saveRecord(self.handle, {
                stayInEdit: true,
            }).then(function() {
                $('.oe_payment_receipt_post').trigger("click");
                self._setMode('readonly');
            });
        },

        saveBillPayment: function(ev) {
            ev.stopPropagation();
            var self = this;
            return self.saveRecord(self.handle, {
                stayInEdit: true,
            }).then(function() {
                $('.bill_payment_post').trigger("click");

                // Safeguard _setMode execution
                setTimeout(function() {
                    try {
                        if (self && typeof self._setMode === 'function') {
                            self._setMode('readonly');
                        } else {
                            console.error('_setMode is not a function or self is undefined');
                        }
                    } catch (error) {
                        console.error('Error in _setMode:', error);
                    }
                }, 0);
            }).catch(function(error) {
                console.error('Error in saveBillPayment:', error);
            });
        },
    });
});