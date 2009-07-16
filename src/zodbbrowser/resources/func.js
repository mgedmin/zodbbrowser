function filterHistory() {
    var transactions = $('div.transaction');
    var filters = $('.filter');
    var filterMap = Array();
    var MAPPING_PREFIX = "map";

    for (i = 0; i < filters.length; i++) {
        var filter = filters[i];
        if (filter.checked) {
            filterMap[MAPPING_PREFIX + filter.name] = filter.checked;
        }
    }

    for (i = 0; i < transactions.length; i++) {
        transaction = transactions[i];
        var diff = $($(transaction).children()[1]).children()
        hasSelectedAttributes = false;
        for (j = 0; j < diff.length; j++) {
            var id = $($(diff[j]).children()[0]).text();
            if (!(MAPPING_PREFIX + id in filterMap)) {
                $(diff[j]).hide();
            } else {
                $(diff[j]).show();
                hasSelectedAttributes = true;
            }
        }

        if (!hasSelectedAttributes) {
            $(transaction).hide();
        } else {
            $(transaction).show();
        }
    }
}

function collapseOrExpand() {
    var content = $(this).next();
    var icon = $(this).children('img');
    if (content.is(':hidden')) {
        $(icon).attr('src', $('#collapseImg').attr('src'));
        content.slideDown();
    } else {
        $(icon).attr('src', $('#expandImg').attr('src'));
        content.slideUp();
    }
}

function showGoTo() {
    $('#path').hide();
    $('#goto').show();
    $('#gotoInput').focus();
}

function hideGoTo() {
    $('#goto').hide();
    $('#path').show();
    // Don't hide #pathError right away, this blur event might have been the
    // result of the user clicking on a link inside the #pathError text and
    // hiding it will prevent that link from getting activated.
    setTimeout(function(){ $('#pathError').slideUp(); }, 50);
}

function activateGoTo() {
    var path = $('#gotoInput').val();
    var api = $('#api').val();
    $('#pathError').text("Loading...").slideDown();
    $.ajax({url: api, dataType:'json', data: "path=" + path,
            timeout: 7000, success: ajaxSuccessHandler,
            error: ajaxErrorHandler})
}

function ajaxErrorHandler(XMLHttpRequest, textStatus, errorThrown) {
    errorMessage = ""
    if (textStatus == "parsererror") {
        errorMessage = "Server returned malformed data"
    } else if (textStatus == "error") {
        errorMessage = "Unknown error (maybe server is offline?)"
    } else if (textStatus == "timeout") {
        errorMessage = "Server timeout"
    } else if (textStatus == "notmodified") {
        errorMessage = "Unknown error"
    } else {
        errorMessage = "Unknown error"
    }

    errorMessage = '<span class="error"> ' + errorMessage + '</strong>'
    $('#pathError').html(errorMessage);
}

function ajaxSuccessHandler(data, status) {
    if (data.url) {
        window.location = data.url;
        $('#pathError').text("Found.").slideDown().slideUp();
    } else if (data.error) {
        $('#pathError').text(data.error).show();
        if (data.partial_url) {
            $('#pathError').append(', would you like to ' +
                                   '<a href="' + data.partial_url + '">' +
                                   'go to ' + data.partial_path +
                                   '</a>' +
                                   ' instead?');
        }
    } else {
        $('#pathError').text(status).show();
    }
}

$(document).ready(function() {
    $('.expander').click(collapseOrExpand);
    $('#path a').click(function(event){event.stopPropagation();});
    $('#path').click(showGoTo);
    $('#gotoInput').blur(hideGoTo);
    $('#gotoInput').keypress(function(event){
        if (event.which == 13) {
            activateGoTo();
        }
    });
    $('#gotoInput').keydown(function(event){
        if (event.keyCode == 27) {
            hideGoTo();
        }
    });
    $(document).keypress(function(event){
        if (event.which == 103) { // lowercase g
            if ($('#goto').is(':hidden')) {
                showGoTo();
                event.preventDefault();
            }
        }
    });
});
