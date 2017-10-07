$('h1').each(function(index, element) {
    $(this).click(function() {
        $(this).next('div').toggle();
    });
});

$('.event-title').each(function(index, element) {
    $(this).parent('.event-heading').next('.event-prep').hide();
    $(this).click(function() {
        $(this).parent('.event-heading').next('.event-prep').toggle();
    });
});

$('.todo').each(function(index, element) {
    $(this).prop('checked', localStorage.getItem($(this).attr('id')) == 'true');
    $(this).change(function() {
        localStorage.setItem($(this).attr('id'), $(this).prop('checked'));
    });
});

$('.event-prep a').each(function(index, element) {
    $(this).attr('target', '_blank');
});
