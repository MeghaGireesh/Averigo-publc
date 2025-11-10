$(document).ready(function() {
    window.logout_interval = setTimeout(function() {
        window.location.href = "/web/session/logout";
    }, 15*60*1000);
    window.logout_interval_warning = setTimeout(function() {
        $('body > div').prepend('<div class="alert alert-danger" id="auto_logout_warning">You will be logged out in 5 minutes.</div>');
        clearTimeout(window.logout_interval_warning);
    }, 10*60*1000);
    $(document).on('click', $(document), function() {
        $('#auto_logout_warning').remove();
        clearTimeout(window.logout_interval);
        clearTimeout(window.logout_interval_warning);
        window.logout_interval = setTimeout(function() {
            window.location.href = "/web/session/logout";
        }, 15*60*1000);
        window.logout_interval_warning = setTimeout(function() {
            $("body > div").prepend('<div class="alert alert-danger" id="auto_logout_warning">You will be logged out in 5 minutes.</div>');
            clearTimeout(window.logout_interval_warning);
        }, 10*60*1000);
    });
    $(document).on('keydown', $(document), function() {
        $('#auto_logout_warning').remove();
        clearTimeout(window.logout_interval);
        clearTimeout(window.logout_interval_warning);
        window.logout_interval = setTimeout(function() {
            window.location.href = "/web/session/logout";
        }, 15*60*1000);
        window.logout_interval_warning = setTimeout(function() {
            $("body > div").prepend('<div class="alert alert-danger" id="auto_logout_warning">You will be logged out in 5 minutes.</div>');
            clearTimeout(window.logout_interval_warning);
        }, 10*60*1000);
    });
    $(document).on('mousemove', $(document), function() {
        $('#auto_logout_warning').remove();
        clearTimeout(window.logout_interval);
        clearTimeout(window.logout_interval_warning);
        window.logout_interval = setTimeout(function() {
            window.location.href = "/web/session/logout";
        }, 15*60*1000);
        window.logout_interval_warning = setTimeout(function() {
            $("body > div").prepend('<div class="alert alert-danger" id="auto_logout_warning">You will be logged out in 5 minutes.</div>');
            clearTimeout(window.logout_interval_warning);
        }, 10*60*1000);
    });
});