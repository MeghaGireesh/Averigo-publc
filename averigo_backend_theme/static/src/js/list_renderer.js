odoo.define('averigo_backend_theme.ListRenderer', function (require) {
'use strict';

var core = require('web.core');
var ListRenderer = require('web.ListRenderer');
var _t = core._t;

var listRenderer = ListRenderer.include({
_onSelectRecord: function (ev) {
        ev.stopPropagation();
        this._updateSelection();
        if($(ev.target)[0].checked){
        $($($($(ev.target)[0].parentNode)[0].parentNode)[0].parentNode).css('background-color', '#ededed');
        $($($($(ev.target)[0].parentNode)[0].parentNode)[0].parentNode).css('box-shadow','3px 3px #bebebe');
        }else{
        $($($($(ev.target)[0].parentNode)[0].parentNode)[0].parentNode).css('background-color', '#ffffff');
        $($($($(ev.target)[0].parentNode)[0].parentNode)[0].parentNode).css('box-shadow', 'none');
        }
    },
});
});