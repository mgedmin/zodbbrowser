$(document).ready(
    function() {
        expand = function (caller) {
            content = $(caller).parent().next()
            if (content.is(':hidden')) {
                content.show()
                $(caller).attr('src', '@@/collapse.png')
            } else {
                content.hide()
                $(caller).attr('src', '@@/expand.png')
            }
        }
    }
);
