// // Make links klickable in flash messages
// $('#flashMessages').ready(function(){
//     // Get each div
//     $('.flashMessage').each(function(){
//         // Get the content
//         var str = $(this).html();
//         // Set the regex string
//         var regex = /(https?:\/\/([-\w\.]+)+(:\d+)?(\/([\w\/_\.]*(\?\S+)?)?)?)/ig
//         // Replace plain text links by hyperlinks
//         //  target='_blank' to fight link error on battle net
//         var replaced_text = str.replace(regex, "<a href='$1'>link</a>");
//         // Echo link
//         $(this).html(replaced_text);
//     });
// });

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
        $(this).parents('.col').toggleClass('col-md-4 col-md-8', 200).promise().done(function(){
            var resizeFunction = window["resizeBox" + $(this).find( ".box" ).attr('id')];
            if (typeof resizeFunction == 'function') {
                resizeFunction();
            }
        });
    });

    // close dashboard box
    $(".fa-close").click(function(){
        hiddenBox = $(this).parents('.col');
        hiddenBox.toggle();
        // $('.status').css('visibility','visible').delay(10000).fadeTo(function(){
        //     $('.status').css("visibility", "hidden");
        //     // hiddenBox.remove();
        // });
        updateBoxesDropdownMenu();
    });
    
    // undo close dashboard box
    $(".undo").click(function(){
        hiddenBox.toggle();
    });

    updateBoxesDropdownMenu();
});
// Update Boxes Dropdown Menu
function updateBoxesDropdownMenu(){
    hide = true;
    $("#removedBoxesDropdown").empty();
    $(".box.dboard").each(function( index ) {
        if ($(this).is(":hidden")) {
            hide = false;
            $("#removedBoxesDropdown").append('<li><a href="javascript:showDashboardBox(' + index + ');">' + $(this).find(".dboardtitle").html() + '</a></li>');
        }
    })
    if (hide) {
        $("#removedBoxesDropdownMenu").css("visibility", "hidden");    
    } else {
        $("#removedBoxesDropdownMenu").css('visibility','visible');
    }
    // http://stackoverflow.com/questions/18238890/save-div-toggle-state-with-jquery-cookie
    // $.cookie('boxesState', 'value');
}
function showDashboardBox(targetIndex) {
    $(".box.dboard").each(function( index ) {
        if (index == targetIndex) {
            hiddenBox = $(this).parents('.col');
            hiddenBox.toggle();
        }
    });
    updateBoxesDropdownMenu();
}

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
// Some helper functions
function showWorking(element) {
    element.html('<button class="btn btn-sm"><span class="glyphicon glyphicon-refresh glyphicon-refresh-animate"></span> Working...</button>');
}