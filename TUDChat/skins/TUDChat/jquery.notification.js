/* content from notification.js */

/*
 * notificaiton for jQuery
 * http://www.labs.aranox.de/
 *
 * Copyright (c) 2012 Frank Kubis
 *
 * Date: 02.04.2012
 * Version: 1.00
 */

(function($){
    /**
    * Set it up as an object under the jQuery namespace
    */
    $.notification = {};

    /**
    * Set up global options that the user can over-ride
    */
    $.notification.options = {
        style : { // css-classes for style
          error   : "notification notification_error",
          success : "notification notification_success",
          warn    : "notification notification_warn",
          general : "notification notification_general"
        },
        autoClose       : true,     // close message automaticly
        clickToClose    : false,
        autoCloseTime   : 3000,     // close it automatic in ... ms
        position        : '',
        fadeInSpeed     : 'fast', // how fast notifications fade in
        fadeOutSpeed    : 250,     // how fast the notices fade out
        time            : 6000,     // hang on the screen for...
        moveSpeed       : "fast",   // the messages moves ... up
        debug           : false      // debug mode, set true and error messages will write in console
    }
    /**
     * display an error message
     * @param message: @see notification._add
     * @param autoClose: @see notification._add
     * @param buttons: @see notification._add
     * @return @see notification._add
     */
    $.notification.error = function(message, autoClose, buttons){
        return notification._add(message, $.notification.options.style.error, autoClose, buttons);
    }
    /**
     * display an success message
     * @param message, @see notification._add
     * @param autoClose: @see notification._add
     * @param buttons: @see notification._add
     * @return @see notification._add
     */
    $.notification.success = function(message, autoClose, buttons){
        return notification._add(message, $.notification.options.style.success, autoClose, buttons);
    }
    /**
     * display an warn message
     * @param message: @see notification._add
     * @param autoClose: @see notification._add
     * @param buttons: @see notification._add
     * @return @see notification._add
     */
    $.notification.warn = function(message, autoClose, buttons){
        return notification._add(message, $.notification.options.style.warn, autoClose, buttons);
    }
    /**
     * display an general message
     * @param message, @see notification._add
     * @param autoClose: @see notification._add
     * @param buttons: @see notification._add
     * @return @see notification._add
     */
    $.notification.general = function(message, autoClose, buttons){
        return notification._add(message, $.notification.options.style.general, autoClose, buttons);
    }
    /**
     * delete all messages
     */
    $.notification.clear = function(){
        $.each(open_messages, function(i){
            notification._remove(open_messages[i], false);
        });
        open_messages = [];
        notification._overlay.hide();
    }
    /**
     * delete spezific message
     * @param id: id of message
     *
     */
    $.notification.close = function(id){
        for(i in open_messages)
            if(id == open_messages[i].attr('id')){
                notification._remove(open_messages[i]);
                return;
            }
    }
    $.notification.debug = function(i){
        console.log(open_messages[i]);
    }
    var overlay = null; // ovelay object
    var messages = null; // message container
    var open_messages = []; // open messages
    var notification = {
        /**
         * littel loger function
         */
        _log : function(){
            if($.notification.options.debug)
                for(i in notification._log.arguments)
                    console.log("NOTIFICATION: " +  notification._log.arguments[i]);
        },
        /**
         * some ovleray functions
         */
        _overlay : {
            /**
             * create the overlay
             */
            init : function(){
                overlay = $("<div/>").css({
                    "width"  : $(window).width() + "px",
                    "height" : $(window).height() + "px"
                }).attr({"id" : "notification_overlay"});
                $("body").append(overlay);
                $("#notification_overlay").append($("<div/>").addClass("transparency"));
                $(window).resize(function(){
                    overlay.css({
                        "width"  : $(window).width()  + "px",
                        "height" : $(window).height() + "px"
                    });
                    notification._center(messages);
                });
            },
            /**
             * display the overlay
             */
            display : function(){
                if(overlay == null)
                    this.init();
                overlay.fadeIn($.notification.options.fadeInSpeed);
            },
            /**
             * hide the overlay
             */
            hide : function(){
                overlay.fadeOut($.notification.options.fadeOutSpeed);

            }
        },
        _center : function(item){
                var top = ($(window).height() - item.height() ) / 2 ;
                var left  = ( ($(window).width()  - item.width()  ) / 2 );
                messages.css({"top" : top + "px", "left" : left + "px"});
        },
        _slide : function(){
            var childHeight = 0;
            var children = messages.children();
            children.each(function(i){
                if($(children[i]).css('visibility') == "hidden")
                    childHeight += $(children[i]).outerHeight();
            });
            var top = ($(window).height() - messages.outerHeight() + childHeight) / 2 + "px";
            messages.animate({top: top}, $.notification.options.moveSpeed);
        },
        /**
        * display an message
        * @param message: (String) the message
        * @param autoClose: (Boolean) should the message close after some seconds? Time can change by use $.notification.options
        * @param cssClass: (String) classname for css style
        * @param buttons: (Object) list of buttons [{"name":"foo", "click" : function(){//some code}},...]
        * @return (String) id of message
        */
        _add : function(message, cssClass, autoClose, buttons){

            if(typeof message == "undefined" || message == ""){
                this._log("ERROR: missing message parameter")
                return null;
            }

            buttons   = (typeof buttons == "undefined") ? [] : buttons;
            autoClose = (typeof autoClose == "undefined") ? $.notification.options.autoClose : autoClose;

            this._overlay.display();

            if(messages == null){
                messages = $("<div/>").attr("id", "notification_container");
                overlay.append(messages);
            }
            var id = 'message' + new Date().getTime();
            var item  = $("<div/>").css({"display" : "none"})
                                   .html(message)
                                   .attr({'id' : id,
                                          'class' : cssClass});
            if(buttons.length > 0)
                item.append("<hr/>");
            button_container = $("<div/>").addClass("notification_button_container");
            for(i in buttons){
                var button = $("<button/>").bind("click", buttons[i].click)
                                           .addClass("notification_button")
                                           .html(buttons[i].name);
                button_container.append(button);
            }
            item.append(button_container);

            if(($.notification.options.clickToClose && buttons.length == 0) || (!autoClose && button.length == 0)){
                item.css("cursor","pointer");
                item.click(function(){
                    $.notification.close(id);
                });                
            }
            messages.append(item);

            //correct height, little dirty hack ~~
            item.ready(function(){item.height(item.height());});
            if(open_messages.length > 0){
                this._slide();
            }else{
                this._center(item);
            }
            item.fadeIn($.notification.options.fadeInSpeed, function() {
              // Focus input field or if non-given first button
              if (item.children("input").length)
                item.children("input").focus();
              else
                item.find("button:first-child").focus();
            });

            open_messages.push(item);
            if(autoClose)
                window.setTimeout("$.notification.close('" + item.attr('id') + "')", $.notification.options.autoCloseTime);

            return id;
        },
        _remove : function(item, remove){
            if(typeof remove != "boolean" )
                remove = true;

            item.fadeOut($.notification.options.fadeOutSpeed, function(){
                item.css({'visibility':'hidden','display': "block"});
                notification._slide();
                item.slideUp("fast", function(){item.remove();});
            });
            if(remove)
                open_messages = $.grep(open_messages, function(elem, index) {
                    return elem.attr('id') != item.attr('id');
                })
            if(open_messages.length == 0)
                this._overlay.hide();
        }
    }
})(jQuery);

/* end of content from notification.js */

