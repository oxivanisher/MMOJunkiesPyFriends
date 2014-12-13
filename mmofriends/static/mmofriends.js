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
        // $(this).parents('.col').fadeOut( 200 );

        var boxVisibleStates = JSON.parse($.cookie('boxVisibleStates'));
        boxVisibleStates[$(this).parents('.box.dboard').attr('id')] = false;
        $.cookie('boxVisibleStates', JSON.stringify(boxVisibleStates));
        updateBoxesDropdownMenu();
    });
    
    // undo close dashboard box
    // $(".undo").click(function(){
    //     hiddenBox.toggle();
    // });

    updateBoxesDropdownMenu();
});
// Update Boxes Dropdown Menu
function updateBoxesDropdownMenu(){
    // load settings from cookie to variable
    var cookieInput =  $.cookie('boxVisibleStates');
    if (cookieInput == undefined) {
        var boxVisibleStates = {};
    } else {
        var boxVisibleStates = JSON.parse(cookieInput);
    } 

    console.log("loading state from cookie");
    $(".box.dboard").each(function( index ) {
        var state =  boxVisibleStates[$(this).attr('id')];
        if (state == undefined) { state = true; }
        console.log("state: " + state);
        if (state) {
            console.log("box " + index + " visible");
            $(this).css('visibility','visible');
            // $(this).parents('.col').fadeIn( 200 );
        } else {
            console.log("box " + index + " hidden");
            // $(this).css('visibility','hidden');
            $(this).parents('.col').fadeOut( 200 );
        }
    });
    // save the values to the cookie
    $.cookie('boxVisibleStates', JSON.stringify(boxVisibleStates));

    hide = true;
    $("#removedBoxesDropdown").empty();
    console.log(cookieInput);
    $(".box.dboard").each(function( index ) {
        if (! boxVisibleStates[$(this).attr('id')]) {
            hide = false;
            $("#removedBoxesDropdown").append('<li><a href="javascript:showDashboardBox(' + index + ');">' + $(this).find(".dboardtitle").html() + '</a></li>');
        }
        // boxVisibleStates[$(this).attr('id')] = $(this).is(':visible');
        // $.cookie('boxesState' + $(this).attr('id'), $(this).is(':visible'));
        // console.log("box " + index + " state save " + $(this).is(':visible'));
    })


    // show or hide the dropdown
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
            var boxVisibleStates = JSON.parse($.cookie('boxVisibleStates'));
            boxVisibleStates[$(this).attr('id')] = true;
            $.cookie('boxVisibleStates', JSON.stringify(boxVisibleStates));
            updateBoxesDropdownMenu();
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