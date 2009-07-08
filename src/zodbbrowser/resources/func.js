function expand(caller) {
    var content = $(caller).next();
    var icon = $(caller).children('img');
    if (content.is(':hidden')) {
        content.show();
        $(icon).attr('src', '@@/collapse.png');
    } else {
        content.hide();
        $(icon).attr('src', '@@/expand.png');
    }
}
