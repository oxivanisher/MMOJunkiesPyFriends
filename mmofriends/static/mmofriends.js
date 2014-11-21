// Make links klickable in flash messages
$('#flashMessages').ready(function(){
    // Get each div
    $('.flashMessage').each(function(){
        // Get the content
        var str = $(this).html();
        // Set the regex string
        var regex = /(https?:\/\/([-\w\.]+)+(:\d+)?(\/([\w\/_\.]*(\?\S+)?)?)?)/ig
        // Replace plain text links by hyperlinks
        var replaced_text = str.replace(regex, "<a href='$1' target='_blank'>link</a>");
        // Echo link
        $(this).html(replaced_text);
    });
});
