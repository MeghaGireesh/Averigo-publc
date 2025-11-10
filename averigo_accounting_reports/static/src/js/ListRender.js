odoo.define('averigo_accounting_reports.invoice_list_render', function (require) {

var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var fieldRegistry = require('web.field_registry');
var ListRenderer = require('web.ListRenderer');
var rpc = require('web.rpc');
var dom = require('web.dom');
var utils = require('web.utils');
var ControlPanelView = require('web.ControlPanelView');
var rpc = require('web.rpc');
var Pager = require('web.Pager');

var InvoiceListRender = ListRenderer.extend({
    _updateSelection: function () {
        console.log("_updateSelection");
        this.selection = [];
	        var self = this;
	        var $inputs = this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
	        var allChecked = $inputs.length > 0;
	        $inputs.each(function (index, input) {
	            if (input.checked) {
	                self.selection.push($(input).closest('tr').data('id'));
	            } else {
	                allChecked = false;
	            }
	        });
	        if(this.selection.length > 0){
	        	$('.button_preview_invoice_lines').show()
	        }else{
	        	$('.button_preview_invoice_lines').hide()
	        }
	        this.$('thead .o_list_record_selector input').prop('checked', allChecked);
	        this.trigger_up('selection_changed', { selection: this.selection });
	        this._updateFooter();
    },
    _onSelectRecord: function (ev) {
        console.log("_onSelectRecord");
        ev.stopPropagation();
        this._updateSelection();
    },
    _onRowClicked:function(ev){
        if (!ev.target.closest('.o_list_record_selector') && !$(ev.target).prop('special_click')) {
            var id = $(ev.currentTarget).data('id');
            if (id) {
                console.log("id",id);
//                this.trigger_up('open_record', { id: id, target: ev.target });
            }
        }
    },
    _renderHeader: function () {
        this.addTrashIcon = false;
        var $thead = this._super.apply(this, arguments);
        console.log("0000",$thead.find('.o_list_record_selector'));
        $thead.find('.o_list_record_selector')?.remove();
        $thead.find('tr').append(this._renderSelectorHeader('th').addClass('selection_all_header'));
        return $thead;
    },

    _renderRow: function (record, index) {
        this.addTrashIcon = false;
        this.addCreateLine = false;
        var $row = this._super.apply(this, arguments);
//        console.log("1122",$row.find('.custom-checkbox').closest('td'));
        $row.find('.custom-checkbox')?.closest('td')?.remove();
        $row.append(this._renderSelector('td', !record.res_id));
        return $row;

    },
    _renderSelectorHeader: function (tag, disableInput) {
        var $content = dom.renderCheckbox();
        return $('<' + tag + '>')
            .addClass('o_list_record_selector')
            .append("<strong>Preview</strong>")
            .append($content);
    },
    _renderSelector: function (tag, disableInput) {
        var $content = dom.renderCheckbox();
        return $('<' + tag + '>')
            .addClass('o_list_record_selector')
            .append($content);
    },
    _renderHeaderCell: function (node) {
        const { icon, name, string } = node.attrs;
        var field = this.state.fields[name];
        let nodes = this._super.apply(this, arguments);
        if (field.string == "Preview" && field.type == "boolean"){
            var $checkbox = $('<input type="checkbox" class="preview_select_all mr-2"/>');
            nodes.prepend($checkbox);
            nodes[0].classList?.remove("o_column_sortable");
        }
        return nodes;
    },
    _renderEmptyRow: function () {
        var $td = $('<td>&nbsp;</td>').attr('colspan', (this._getNumberOfCols()+1));
        return $('<tr>').append($td);
    },
//    _renderFooter:function(){
//        this.hasSelectors = true;
//        this._super.apply(this, arguments);
//
//    }

    // AV-3543 Invoice list report -- Updated to get the sum of the fields in the List view
    _renderFooter: function () {
        var aggregates = {};
        _.each(this.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        var $cells = this._renderAggregateCells(aggregates);
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        else{
            $cells.push($('<td>'));
        }
        return $('<tfoot>').append($('<tr>').append($cells));
    },
});

var InvoiceReportOne2many = FieldOne2Many.extend({
        events: _.extend({
        'click .button_preview_invoice_lines': '_previewInvoices',
    }, FieldOne2Many.prototype.events),
        _previewInvoices:function(event){
            let self = this;
            event.preventDefault();
            var selected_ids = self.get_selected_ids_one2many();
            console.log("selected_ids",selected_ids);
            rpc.query({
                    model: 'invoice.list.report',
                    method: 'action_view_preview',
                    args: [selected_ids],
                    }).then((result)=> {
                return this.do_action(result);
            });
        },
        _getRenderer: function () {
            if (this.view.arch.tag === 'tree') {
                return InvoiceListRender;
            }
            return this._super.apply(this, arguments);
        },
        get_selected_ids_one2many: function () {
            var self=this;
            var ids =[];
            $('div > table.o_list_table > tbody')?.find('td.o_list_record_selector input:checked')
                    .closest('tr').each(function () {
                    ids.push(parseInt(self._getResId($(this).data('id'))));
            });
            return ids;
        },
        _getResId: function (recordId) {
            var record;
            utils.traverse_records(this.recordData[this.name], function (r) {
                if (r.id === recordId) {
                    record = r;
                }
            });
            return record?.res_id;
        },
        _renderControlPanel: function () {
            if (!this.view) {
            return Promise.resolve();
        }
        var self = this;
        var defs = [];
        var controlPanelView = new ControlPanelView({
            template: 'X2ManyControlPanelInvoice',
            withSearchBar: false,
        });
        var cpDef = controlPanelView.getController(this).then(function (controlPanel) {
            self._controlPanel = controlPanel;
            return self._controlPanel.prependTo(self.$el);
        });
        this.pager = new Pager(this, this.value.count, this.value.offset + 1, this.value.limit, {
            single_page_hidden: true,
            withAccessKey: false,
            validate: function () {
                var isList = self.view.arch.tag === 'tree';
                // TODO: we should have some common method in the basic renderer...
                return isList ? self.renderer.unselectRow() : Promise.resolve();
            },
        });
        this.pager.on('pager_changed', this, function (new_state) {
            self.trigger_up('load', {
                id: self.value.id,
                limit: new_state.limit,
                offset: new_state.current_min - 1,
                on_success: function (value) {
                    self.value = value;
                    self._render();
                },
            });
        });
        this._renderButtons();
        defs.push(this.pager.appendTo($('<div>'))); // start the pager
        defs.push(cpDef);
        return Promise.all(defs).then(function () {
            self._controlPanel.updateContents({
                cp_content: {
                    $buttons: self.$buttons,
                    $pager: self.pager.$el,
                }
            });
        });
    },
    });
fieldRegistry.add('invoice_list_report_one2many', InvoiceReportOne2many);

});