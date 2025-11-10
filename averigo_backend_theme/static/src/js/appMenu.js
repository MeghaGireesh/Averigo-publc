odoo.define('averigo_backend_theme.appMenu', function (require) {
    'use strict';

    var appsMenu = require("web.AppsMenu");
    appsMenu.include({
        init: function (parent, menuData) {
            this._super.apply(this, arguments);
            this._activeApp = undefined;
            this._apps = _.map(menuData.children, function (appMenuData) {
                var webIcon = false;
                if (appMenuData.web_icon) {
                    webIcon = appMenuData.web_icon.replace(',', '/');
                }
                return {
                    actionID: parseInt(appMenuData.action.split(',')[1]),
                    menuID: appMenuData.id,
                    name: appMenuData.name,
                    xmlID: appMenuData.xmlid,
                    webIcon: webIcon || '/base/static/description/icon.png',
                };
            });
        },
    });
    return appsMenu;
});