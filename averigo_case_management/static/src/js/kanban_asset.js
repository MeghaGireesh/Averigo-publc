    odoo.define('averigo_case_management.kanban_attachment', function(require) {
        var kanban = require('web.KanbanRecord')
        var registry = require("web.field_registry");
        var relational_fields = require('web.relational_fields');
        var FieldBinaryFile = require('web.basic_fields').FieldBinaryFile;
        var DocumentViewer = require('mail.DocumentViewer');
        var rpc = require('web.rpc');
        var FieldBinaryPreview = FieldBinaryFile.extend({
            events: _.extend({}, {
                'click': '_onAttachmentView',
            }),
             _renderReadonly: function () {
//              Function is used to Render the eye icon .Otherwise the download icon will show.
                this._super.apply(this, arguments);
                var visible = !!(this.value && this.res_id);
                this.$el.empty().css('cursor', 'not-allowed');
                this.do_toggle(visible);
                if (visible) {
                    this.$el.css('cursor', 'pointer')
                            .text(this.filename_value || '')
                            .prepend($('<span class="fa fa-eye"/>'), ' ');
                    }
            },
            _onAttachmentView: function(ev) {
                ev.stopPropagation();
                ev.preventDefault();
                var self = this;
                var fieldId = self.res_id;
                var attachments = "";
                var activeAttachmentID = self.res_id;
                var item_list = []
                var items = "";
                if ('state' in self.__parentedParent.__parentedParent) {
                    items = self.__parentedParent.__parentedParent.state.data
                } else {
                    item_list.push(self.record.data)
                }
                if (items.length >= 1) {
                    for (var i = 0; i < items.length; i++) {
                        item_list.push(items[i].data);
                    }
                } else {
                    item_list.push(self.record.data)
                }
                if (activeAttachmentID) {
                    var attachmentViewer = new DocumentViewer(this, item_list, activeAttachmentID);
//                    var attachmentViewer = new UrlPreview(this, item_list, activeAttachmentID);
                    attachmentViewer.appendTo($('body'));
                }
            },

        });
        registry.add("field_item_preview", FieldBinaryPreview);

        var FieldMany2One = relational_fields.FieldMany2One;



        var FieldSateWizard = FieldMany2One.extend({
            start:function(){
                let self = this;
                self.close_case_view_id = false;
                this._super.apply(this, arguments);
                console.log("start *********");


            },
            _onFieldChanged: async function (ev) {
                let self = this;

                console.log("FieldSateWizard",ev,self);
                if (ev.data.changes.stage_id.display_name === "Closed" && self.res_id)
                {

                    await self._rpc({
                    model: 'case.management',
                    method: 'get_case_close_view',
                    }).then(function (result) {
                        self.close_case_view_id = result;
                    });
                    console.log("+++++++++",self.close_case_view_id);
                    let value = {
                         type: 'ir.actions.act_window',
                         name:"Close Case",
                         res_model: 'case.employee',
                         target: 'new',
                         views: [[self.close_case_view_id, "form"]],
                         context:{'default_origin_id':self.res_id},
                         view_mode: 'form',
                    }
                    self.do_action(value,{on_close:()=>{ console.log("1111");}})
//                    .then(()=>{
//                        self._super.apply(self, arguments);
//                    });
                }
                else
                {
                    this._super.apply(this, arguments);
                }
            },

        })
        registry.add("employee_completion_wizard", FieldSateWizard);
        return FieldBinaryPreview;
    });