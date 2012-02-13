function filterAll() {
    $('.filter').attr('checked', true);
    filterHistory(true);
}

function filterNone() {
    $('.filter').attr('checked', false);
    filterHistory();
}

function filterHistory(showAll) {
    var transactions = $('div.transaction');
    var filters = $('.filter');
    var filterMap = Array();
    var MAPPING_PREFIX = "map";

    for (var i = 0; i < filters.length; i++) {
        var filter = filters[i];
        if (filter.checked) {
            filterMap[MAPPING_PREFIX + filter.name] = filter.checked;
        }
    }

    for (i = 0; i < transactions.length; i++) {
        var transaction = transactions[i];
        var diffs = $(transaction).children('div.diff').children('div.diffitem');
        var n_hidden = 0;
        for (var j = 0; j < diffs.length; j++) {
            var id = $($(diffs[j]).children()[0]).text();
            if (MAPPING_PREFIX + id in filterMap || showAll) {
                $(diffs[j]).show();
            } else {
                $(diffs[j]).hide();
                n_hidden += 1;
            }
        }
        var hidden_text = null;
        if (n_hidden == 1) {
            hidden_text = '1 item hidden';
        } else if (n_hidden) {
            hidden_text = n_hidden + ' items hidden';
        }
        $(transaction).children('.filtered').remove();
        if (hidden_text) {
            $(transaction).append('<div class="filtered">' + hidden_text + '</div>');
        }
    }
}

function collapseOrExpand() {
    // this is <div class="extender">
    // the following element is <div class="collapsible">
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

function hideItemsIfTooMany() {
    $('.items').each(function(){
        var expander = $(this).children('.expander')[0];
        var content = $(this).children('.collapsible')[0];
        // items are formatted using <br /> so the heuristic is very
        // approximate.
        if (content.childNodes.length > 100 && !$(content).is(':hidden')) {
            var icon = $(expander).children('img');
            $(icon).attr('src', $('#expandImg').attr('src'));
            $(content).hide();
        }
    });
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

function ajaxErrorHandler(XMLHttpRequest, textStatus, errorThrown) {
    errorMessage = "";
    if (textStatus == "parsererror") {
        errorMessage = "Server returned malformed data";
    } else if (textStatus == "error") {
        errorMessage = "Unknown error (maybe server is offline?)";
    } else if (textStatus == "timeout") {
        errorMessage = "Server timeout";
    } else if (textStatus == "notmodified") {
        errorMessage = "Server error (says resource not modified)";
    } else {
        errorMessage = "Unknown error";
    }

    errorMessage = '<span class="error"> ' + errorMessage + '</strong>';
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

function activateGoTo() {
    var path = $('#gotoInput').val();
    var api_url = '@@zodbbrowser_path_to_oid';
    $('#pathError').text("Loading...").slideDown();
    $.ajax({url: api_url, dataType: 'json', data: "path=" + path,
            timeout: 7000, success: ajaxSuccessHandler,
            error: ajaxErrorHandler});
}

function cancelRollback(e) {
    $('#confirmation').remove();
    $('div.transaction').removeClass('focus');
    $('input.rollbackbtn').show();
}

function pressRollback(e) {
    e.preventDefault();
    cancelRollback();
    $(e.target).hide();
    var transaction_div = $(e.target).closest('div.transaction');
    transaction_div.addClass('focus');
    $('<div id="confirmation">' +
        '<form action="" method="post">' +
          '<div class="message">' +
            'This is a dangerous operation that may break data integrity.'+
            ' Are you really sure you want to do this?' +
          '</div>' +
          '<input type="BUTTON" value="Really revert to this state" onclick="doRollback()">' +
          '<input type="BUTTON" value="Cancel" onclick="cancelRollback()">' +
        '</form>' +
      '</div>').appendTo(transaction_div);
}

function doRollback() {
    var transaction_div = $('#confirmation').closest('div.transaction');
    var rollback_form = transaction_div.find('form.rollback');
    rollback_form.find('input[name="confirmed"]').val('1');
    rollback_form.submit();
}

$(document).ready(function() {
    $('.expander').click(collapseOrExpand);
    hideItemsIfTooMany();
    $('#path a').click(function(event){event.stopPropagation();});
    $('#path').click(showGoTo);
    $('#gotoInput').blur(hideGoTo);
    $('#gotoInput').keypress(function(event){
        if (event.which == 13) { // enter
            activateGoTo();
        }
    });
    $('#gotoInput').keydown(function(event){
        if (event.keyCode == 27) { // escape
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
    $('input.rollbackbtn').click(pressRollback);
    $('span.truncated').click(function(event){
        event.preventDefault();
        var placeholder = $(this);
        var id = placeholder.attr('id');
        $.ajax({url: '@@zodbbrowser_truncated', data: 'id=' + id,
                success: function(data, status) {
                    placeholder.replaceWith(data);
                }});
    });
});
