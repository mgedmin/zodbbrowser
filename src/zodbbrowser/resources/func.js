$(document).ready(
    function() {
        expand = function (caller) {
            content = $(caller).next()
            if (content.is(':hidden')) {
                content.show()
                $(caller).val('-')
            } else {
                content.hide()
                $(caller).val('+')
            }
        }
    }
);
