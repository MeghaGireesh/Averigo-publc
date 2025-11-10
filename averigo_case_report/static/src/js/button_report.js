odoo.define("averigo_service_management.button_report", function (require) {
  "use strict";
  var basic_fields = require("web.basic_fields");
  var FieldInteger = basic_fields.FieldChar;
  var registry = require("web.field_registry");
  var Dialog = require('web.Dialog');
  var AbstractField = require('web.AbstractField');
  var relational_fields = require('web.relational_fields');
  var rpc = require("web.rpc");
  var FieldHtml = require("web_editor.field.html");
  var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
  var ListRenderer = require('web.ListRenderer');
  var tmpl_id = false;
  var core = require('web.core');
  var _t = core._t;
  var DebouncedField = basic_fields.DebouncedField;

//Widget to disable the click. Doing with style showing some issues.
  var openFieldOne2Many = ListRenderer.extend({

        events: {
        'click':'_disableClick'
        },
        _disableClick:function(ev)
        {
            ev.stopPropagation();
            ev.preventDefault();
        },
  });

  var caseReportOne2many = FieldOne2Many.extend({
        _getRenderer: function () {
            if (this.view.arch.tag === 'tree') {
                return openFieldOne2Many;
            }
            return this._super.apply(this, arguments);
        },
    });
    registry.add('one2manyFieldClickReport', caseReportOne2many);

  var fieldIntegerClickable = FieldInteger.extend({
    className: 'o_field_number',
    supportedFieldTypes: ['integer'],
    template: "FieldInteger",
    events: _.extend({}, DebouncedField.prototype.events, {
        'click': 'onClick_case',
    }),
    start:function(){
        this._super.apply(this, arguments);
    },
    _renderReadonly: function () {
        console.log("_renderReadonly");
    },
    onClick_case: async function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
//      console.log("998844");
      var self = this;
      var view_id_list = "";
      var domain = [];
      var context = {};
      var view_type = "";
      var views = [];
      var target = "";
      var name = "";
      var res_model =""
      await self
        ._rpc({
          model: "case.management",
          method: "get_view_id",
          args: [0],
        })
        .then(function (result) {
          self.view_id_list = result;
        });
      if (self.name == "machine_cases") {
       if (self.recordData.partner_id){
        var domain_item = "";
        var secound_domain = "";
        var secound_domain = parseInt(self.recordData.partner_id.data.id)
        domain = [['partner_id.id','=', secound_domain],['id','!=', self
        .recordData.id]]
        context = {};
        view_type = "list,form";
        res_model = self.model;
        views = [
          [self.view_id_list["list_view_id"], "list"],
          [false, "form"],
        ];
        target = "current";
        name= self.recordData.partner_id.data.display_name;
        }
      }
//       else if (self.name == "case_history_count") {
//        domain = [['origin_id', '=', self.recordData.id]];
//        target = "new";
//        res_model = 'casemanagement.notes';
//        name = self.recordData.number;
//        views = [[self.view_id_list["form_view_id"], 'list'], [false, 'form']];
//        view_type = 'list';
//        target = 'new';
//      }
      self.do_action({
        name:name,
        type: "ir.actions.act_window",
        res_model: res_model,
        domain: domain,
        views: views ,
        view_type: view_type ,
        target: target,

      });
    },
    });
  registry.add("field_integer_clickable", fieldIntegerClickable);

//  Widget to show and hide the html field long text.
  var Notes = FieldHtml.extend({
    template: "averigo_case_report.html_field_show_more",
    events: _.extend({}, FieldHtml.prototype.events,
      {
        'click .show-more' : "showMore",
        'click .hide-more' : "hideMore",
        'click .text-div' : "disableOpen",
        'click .text-item': "disableOpen",
      }
    ),
    disableOpen:function(ev){
        ev.stopPropagation();
        ev.preventDefault();
    },
    start:function()
    {
        this._super.apply(this, arguments);
    },
    hideMore:function(ev){
        ev.stopPropagation();
        ev.preventDefault();
        $(this.$el.find('.text-div'))[0].style.height = "revert-layer";
        $(this.$el.find('.text-div'))[0].style.maxHeight = "revert-layer";
        $(this.$el.find('#icon'))[0].style.display = "block";
        $(this.$el.find('.hide-more'))[0].style.display = "none";
    },
     showMore:function(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        $(this.$el.find('.text-div'))[0].style.height = "auto";
        $(this.$el.find('.text-div'))[0].style.maxHeight = "auto";
        $(this.$el.find('#icon'))[0].style.display = "none";
        $(this.$el.find('.hide-more'))[0].style.display = "block";
    },
    _renderReadonly: function () {
        var self = this;
        var value = this._textToHtml(this.value);
        if (this.nodeOptions.wrapper) {
            value = this._wrap(value);
        }

        this.$el.empty();
        var resolver;
        var def = new Promise(function (resolve) {
            resolver = resolve;
        });
//            let display_content = this.extractContent(value)
            let display_content = value.trimStart();
            let display_hypertext = '<div class="text-item"><div class="text-div" style="pointer-events:none !important;">'+display_content+'</div>';
            if (display_content.length > 30)
            {
                display_hypertext+= '<span id="icon" class="show-more">Show More</span><span class="hide-more">Hide ..</span></div>';
            }
            display_hypertext+="</div>";
            this.$content = $('<div class="o_readonly text-container"/>').html(display_hypertext);
            this.$content.appendTo(this.$el);
            resolver();

    },
    extractContent:function (value){
        var div = document.createElement('div')
        div.innerHTML=value;
        var text= div.textContent;
        return text;
    }

  });
  registry.add("html_show_more", Notes);

  // Widget to open the Internal Comments..
  var DescriptionDialog = relational_fields.FieldX2Many.extend({
  supportedFieldTypes: ['many2many'],
  tag_template: "FieldMany2ManyDialog",
  className: 'description_dialog',
  events: _.extend({}, AbstractField.prototype.events, {
    'click .icon-show-dialog': 'open_internal_comment',
  }),

  open_internal_comment:async function(ev){
    ev.stopPropagation();
    ev.preventDefault();

    await rpc.query({
          model: "case.management",
          method: "get_case_internal_notes",
          res_id:this.res_id,
          args: [this.res_id],
        }).then((result)=>{
        this.internal_comments = result;
        });
        let html_vals =`<thead class="thead-light"><tr><th scope="col"
        class="field_comment">Comment</th ><th scope="col">User</th><th scope="col">Date</th></tr></thead>`;
        html_vals+= _.map(this.internal_comments, function (child) {
            return '<tr scope="row"><td>'+child.description+'</td><td>'+child
            .created+'</td><td>'+child.date+'</td><tr/>';
        });
        let table = $('<table class="table table-striped"/>').html(html_vals)
//        console.log("html_vals",table);
        let content ;
        let self= this;
        var dialog = new Dialog(self, {
                title: _t("Internal Comments"),
                $content: table,
            });
        dialog.open()
  },
  start:function(){
    this.internal_comments;
    this._super.apply(this, arguments);
  },
  _renderReadonly: function () {
//      console.log("_renderReadonly",this.record.data.internal_comment_count);
      this.$content = $('<div class="o_readonly description_many2many"/>').html
      ('<span class="icon-show-dialog icon-color">'+this.record.data
      .internal_comment_count+'</span>');
      this.$content.appendTo(this.$el);
  },
  });
  registry.add('many2many_description_dialog', DescriptionDialog);

// Widget to open the Resolution Comments..
  var ResolutionDialog = relational_fields.FieldX2Many.extend({
  supportedFieldTypes: ['many2many'],
  className: 'resolution_dialog',
  events: _.extend({}, AbstractField.prototype.events, {
    'click .icon-show-resolution': 'open_resolution_comment',
  }),
  open_resolution_comment:async function(ev){
    ev.stopPropagation();
    ev.preventDefault();
    await rpc.query({
          model: "case.management",
          method: "get_case_resolution_notes",
          res_id:this.res_id,
          args: [this.res_id],
        }).then((result)=>{
        this.internal_comments = result;
        });
        let html_vals =`<thead class="thead-light"><tr><th scope="col" class="field_comment">Comment</th ><th scope="col">User</th><th scope="col">Date</th></tr></thead>`;
        html_vals+= _.map(this.internal_comments, function (child) {
            return '<tr scope="row"><td>'+child.description+'</td><td>'+child
            .created+'</td><td>'+child.date+'</td><tr/>';
        });
        let table = $('<table class="table table-striped table-bordered"/>').html
        (html_vals)
//        console.log("html_vals",table);
        let content ;
        let self= this;
        var dialog = new Dialog(self, {
                title: _t("Resolution Comments"),
                $content: table,
            });

//        console.log("dialog",dialog);
        dialog.open()
  },
  start:function(){
    this.internal_comments;
    this._super.apply(this, arguments);
  },
  _renderReadonly: function () {
  this.$content = $('<div class="o_readonly description_many2many"/>').html
  ('<span class="icon-color icon-show-resolution">'+this.record.data
      .case_resolution_count+'</span>');
  this.$content.appendTo(this.$el);
//   resolver();

  },

  });
  registry.add('many2many_resolution_dialog',ResolutionDialog);

  return  Notes;
});
