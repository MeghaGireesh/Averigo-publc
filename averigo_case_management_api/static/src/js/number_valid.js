odoo.define('averigo_case_management_api.number_valid', function (require) {
    "use strict";    
    var basic_fields = require('web.basic_fields');
    var registry = require('web.field_registry');
    var FieldChar = basic_fields.FieldChar;
    var core = require('web.core');
    var _t = core._t;
  
    var NumValidation = FieldChar.extend({
        events: _.extend({},FieldChar.prototype.events,{
            'keydown': '_onKeyDown',
        }),
        init: function () {
            this._super.apply(this, arguments);
        },
        _onKeyDown: function (e) {
            var self = this;
            //e.keyCode: Enter 13
            //e.keyCode: BackSpace 8
            //e.keyCode: Delete 46
            //e.keyCode: + 187
            //e.keyCode: + 107
            //e.keyCode: - 189
            //e.keyCode: - 109
            //e.keyCode: Left Arrow 37
            //e.keyCode: Up Arrow 38
            //e.keyCode: Right Arrow 39
            //e.keyCode: Down Arrow 40

            if(e.shiftKey){ self.do_warn(_t('Error'),'Please enter valid number!');return false; }
            if (e.keyCode){
            if (!(e.keyCode ==8  || e.keyCode==13 || e.keyCode ==187 || e.keyCode ==189 || e.keyCode ==107 || e.keyCode ==109 || e.keyCode ==37 || e.keyCode ==38|| e.keyCode ==39|| e.keyCode ==40|| e.keyCode ==46 ))
            {
                if (!((e.keyCode >=48 && e.keyCode <=57) || (e.keyCode >=96 && e.keyCode <=105)))
                {
                    self.do_warn(_t('Error'),'Please enter valid number!');
                    return false;
                }
            }
            }
        },

    });
    registry.add('number_validation', NumValidation);
    return NumValidation;

});