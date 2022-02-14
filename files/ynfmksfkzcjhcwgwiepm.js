function initSearchJS() {
    if (typeof jQuery != 'undefined') {
        $(document).ready(function() {
            var submitIcon = $('.searchbox-icon');
            var inputBox = $('.searchbox-input');
            var searchBox = $('.searchbox');
            var searchContainer = $('.open-search');
            var searchBtn = $('.search a.jtop-nav-link');
            var closeLink = $('.close-link')
            var isOpen = false;
            var searchTimer;

            function hideSearch() {
                searchContainer.removeClass('show');
                clearTimeout(searchTimer);
            }

            searchBtn.click(function() {
                searchContainer.addClass('show');
                inputBox.focus();
                searchTimer = setTimeout(hideSearch, 20000);
            });

            closeLink.click(hideSearch);

            inputBox.on('input', function() {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(hideSearch, 20000);
            })

            submitIcon.click(function(){
                if(isOpen == false){
                    searchBox.addClass('searchbox-open');
                    inputBox.focus();
                    isOpen = true;
                } else {
                    searchBox.removeClass('searchbox-open');
                    inputBox.focusout();
                    isOpen = false;
                }
            });  
            submitIcon.mouseup(function(){
                return false;
            });
            searchBox.mouseup(function(){
                return false;
            });
            $(document).mouseup(function(){
                if(isOpen == true){
                    $('.searchbox-icon').css('display','block');
                    submitIcon.click();
                }
            });
        });
    }
    else {
        window.setTimeout( initSearchJS, 50 );
    }
}
  
initSearchJS();

function buttonUps(e){
    var inputVal = $(e.currentTarget).val();
    inputVal = $.trim(inputVal).length;
    if( inputVal !== 0){
        $('.searchbox-icon').css('display','none');
    } else {
        $(e.currentTarget).val('');
        $('.searchbox-icon').css('display','block');
    }
}