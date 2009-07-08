function collapseOrExpand(item) {
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
    // XXX: our callback is not called if server returns malformed JSON
    $('#pathError').text("Loading...").slideDown();
    $.getJSON(api, {'path': path}, function(data, status) {
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
    });
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
