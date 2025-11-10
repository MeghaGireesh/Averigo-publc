odoo.define('account_asset_management.FormRenderer', function (require) {
"use strict";
var FormRenderer = require('web.FormRenderer');
var dom = require('web.dom');
var core = require('web.core');
var _t = core._t;
var FormRenderernew = FormRenderer.include({
_renderButtonBox: function (node) {
        var self = this;
        var $result = $('<' + node.tag + '>', {class: 'o_not_full'});

        // The rendering of buttons may be async (see renderFieldWidget), so we
        // must wait for the buttons to be ready (and their modifiers to be
        // applied) before manipulating them, as we check if they are visible or
        // not. To do so, we extract from this.defs the promises corresponding
        // to the buttonbox buttons, and wait for them to be resolved.
        var nextDefIndex = this.defs.length;
        var buttons = _.map(node.children, function (child) {
            if (child.tag === 'button') {
                return self._renderStatButton(child);
            } else {
                return self._renderNode(child);
            }
        });

        // At this point, each button is an empty div that will be replaced by
        // the real $el of the button when it is ready (with replaceWith).
        // However, this only works if the empty div is appended somewhere, so
        // we here append them into a wrapper, and unwrap them once they have
        // been replaced.
        var $tempWrapper = $('<div>');
        _.each(buttons, function ($button) {
            $button.appendTo($tempWrapper);
        });
        var defs = this.defs.slice(nextDefIndex);
        Promise.all(defs).then(function () {
            buttons = $tempWrapper.children();
            var buttons_partition = _.partition(buttons, function (button) {
            if(!self.model == 'account.asset' && !self.model == 'case.management'){
                return $(button).is('.o_invisible_modifier');
                }
            else{
            return !$(button).is('.o_invisible_modifier');
            }
            });
            var invisible_buttons = buttons_partition[0];
            var visible_buttons = buttons_partition[1];

            // Get the unfolded buttons according to window size
            var nb_buttons = self._renderButtonBoxNbButtons();
            var unfolded_buttons = visible_buttons.slice(0, nb_buttons).concat(invisible_buttons);

            // Get the folded buttons
            var folded_buttons = visible_buttons.slice(nb_buttons);
            if (folded_buttons.length === 1) {
                unfolded_buttons = buttons;
                folded_buttons = [];
            }

            // Toggle class to tell if the button box is full (CSS requirement)
            var full = (visible_buttons.length > nb_buttons);
            $result.toggleClass('o_full', full).toggleClass('o_not_full', !full);

            // Add the unfolded buttons
            _.each(unfolded_buttons, function (button) {
                $(button).appendTo($result);
            });

            // Add the dropdown with folded buttons if any
            if (folded_buttons.length) {
                $result.append(dom.renderButton({
                    attrs: {
                        'class': 'oe_stat_button o_button_more dropdown-toggle',
                        'data-toggle': 'dropdown',
                    },
                    text: _t("More"),
                }));

                var $dropdown = $("<div>", {class: "dropdown-menu o_dropdown_more", role: "menu"});
                _.each(folded_buttons, function (button) {
                    $(button).addClass('dropdown-item').appendTo($dropdown);
                });
                $dropdown.appendTo($result);
            }
        });

        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
});
return FormRenderernew;
});

