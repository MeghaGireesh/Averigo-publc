odoo.define('averigo_archive_address.add_archive', function (require) {
    "use strict";
    /**
        This Function is used to add Archive Button in FormViewDialog.
        Problem to add this :- If the user have 2 delivery address at that time the delivery address will not automatically
         selected in sale order.If we try to remove the delivery address will show a f_key issue.
         To solve this issue we need to add a Archive Button.
        Note :- We are including the FormeViewRender so the archive Button will Show in all FormViewDialog.
         So we will get an error.Some of the models does not have active(archive) field.
         At that time will show an error so we need to catch the exception.
    **/

    var core = require('web.core');
    var _t = core._t;
    var ViewDialogs = require('web.view_dialogs');
    var FormViewDialog = ViewDialogs.FormViewDialog;
    FormViewDialog.include({
        _setRemoveButtonOption(options, btnClasses) {

            const self = this;
            this._super.apply(this, arguments);
            options.buttons.push({
                text: _t("Archive"),
                classes: 'btn-secondary ' + btnClasses,
                click: function () {
                    var response = confirm("Do you really want to Archive this record..?");
                    if (response) {
                        self._archive().then(self.close.bind(self));
                    }
                }
            });
        },
        _archive: async function () {
            /*This function will archive the record.*/
            var self = this;
            if (self.res_id == 0) {
                return Promise.resolve();
            }
            if (self.recordID) {
                await self.model.actionArchive([self.recordID], self.parentID).then(self.close.bind(self));
            }
            /* We need to reload the window after archiving the record. */
            location.reload();
        }
    });

    return FormViewDialog;
});