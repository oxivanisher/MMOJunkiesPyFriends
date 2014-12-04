// Make links klickable in flash messages
$('#flashMessages').ready(function(){
    // Get each div
    $('.flashMessage').each(function(){
        // Get the content
        var str = $(this).html();
        // Set the regex string
        var regex = /(https?:\/\/([-\w\.]+)+(:\d+)?(\/([\w\/_\.]*(\?\S+)?)?)?)/ig
        // Replace plain text links by hyperlinks
        //  target='_blank' to fight link error on battle net
        var replaced_text = str.replace(regex, "<a href='$1'>link</a>");
        // Echo link
        $(this).html(replaced_text);
    });
});

$(function() {
    // Load flash messages
    $( "#flashDialogSuccess" ).dialog({
        autoOpen: true,
        dialogClass: 'success',
        modal: true,
        open: function(event, ui) {
            setTimeout(function(){
            $('#dialog').dialog('close');                
            }, 5000);
        },
        buttons: {
            Close: function() {
                $(this).dialog("close");
            }
        }
    });
    $( "#flashDialogError" ).dialog({
        autoOpen: true,
        dialogClass: 'error',
        modal: true,
        // open: function(event, ui) {
        //     setTimeout(function(){
        //     $('#dialog').dialog('close');                
        //     }, 3000);
        // },
        buttons: {
            Close: function() {
                $(this).dialog("close");
            }
        }
    });
    $( "#flashDialogInfo" ).dialog({
        autoOpen: true,
        dialogClass: 'info',
        modal: true,
        open: function(event, ui) {
            setTimeout(function(){
            $('#dialog').dialog('close');                
            }, 5000);
        },
        buttons: {
            Close: function() {
                $(this).dialog("close");
            }
        }
    });
    // $( "#loadingOverlay" ).modal({
    //     modal: true
    // });
    // $('ul.nav li.dropdown').hover(function(){
    //        $(this).children('ul.dropdown-menu').slideDown(); 
    //     }, function(){
    //        $(this).children('ul.dropdown-menu').slideUp(); 
    // });

    /* 
        stoef stuff
    */

    // expand / compress dashboard box
    $('.fa-expand').click(function(){
        $(this).parents('.col').toggleClass('col-md-4 col-md-8', 200);
    });

    // close dashboard box
    $(".fa-close").click(function(){
        hiddenBox = $(this).parents('.col');
        hiddenBox.toggle();
        $('.status').css('visibility','visible').delay(10000).fadeTo(function(){
            $('.status').css("visibility", "hidden");
            hiddenBox.remove();
        });
    });
    
    // undo close dashboard box
    $(".undo").click(function(){
        hiddenBox.toggle();
    });

});
// Popup Images and text (will be replaced with a vcard)
function showImgPopup(imgSrc) {
    $('img#popupimg').attr( "src", imgSrc );
    $("#imgpopup").show();
}
function hideImgPopup() {
    $("#imgpopup").hide();
}
function showInfoPopup(infoContentURL) {
    $("#infopopup").load( infoContentURL );
    $("#infopopup").show();
}
function hideInfoPopup() {
    $("#infopopup").hide();
}
// Finally, load the popup modal dialog window
$(window).load(function(){
   $('#loadingOverlay').fadeOut();
   $('#loadingOverlay').modal('hide');
});
