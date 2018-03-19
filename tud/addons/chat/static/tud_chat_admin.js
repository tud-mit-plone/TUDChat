$( document ).ready(function() {

    $("body").delegate("a.edit", "click", function(e) {
        var oldMsg = $("#chatEntry"+$(e.target).attr("data-mid")).find(".message_content .message").text();
        var mId = $(e.target).attr("data-mid");
        // Deselect all messages
        $("li.selected").removeClass("selected");
        // Select current message
        $("#chatEntry"+mId).addClass("selected");
        $.notification.warn(
            TudChat._('edit_message') + "<br/> <br/><form id='editMsgForm'><label for='newMsg'>" + TudChat._('new_message') + "</label><br/><br/> <input type='text' id='newMsg' value='"+oldMsg+"' class='editBox'/></form>",
            false,
            [
                {"name" : TudChat._('button_edit'),
                    "click":function(){
                        if (oldMsg != $("#newMsg").val()) {
                            $.post(TudChat.ajaxUrl, {'method': 'editMessage', 'message_id' :mId, 'message': $("#newMsg").val() } , function(data) { TudChat.updateCheck(); });
                        }
                        $.notification.clear();
                        $("#chatEntry"+mId).removeClass("selected");
                    }
                },
                {"name" : TudChat._('button_abort'),
                    "click": function(){
                        $.notification.clear();
                        $("#chatEntry"+mId).removeClass("selected");
                    }
                },
            ]
        );
        e.preventDefault();
    });

    $("body").delegate("a.delete", "click", function(e) {
        var message = $("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text();
        message = ((message.length > 150) ? message.substr(0, 150) + "..." : message);
        $.notification.warn(
            TudChat._('delete_confirmation') + "<br/><br/>" + $("#chatEntry"+$(e.target).attr("data-mid")).children("span.username").text() + " " + message,
            false,
            [
                {"name" : TudChat._('button_ok'),
                    "click":function(){
                        $.post(
                            TudChat.ajaxUrl,
                            {'method': 'deleteMessage', 'message_id': $(e.target).attr("data-mid") },
                            function(data) { TudChat.updateCheck(); }
                        );
                        $.notification.clear();
                    }
                },
                {"name" : TudChat._('button_abort'), "click": function() {
                    $.notification.clear();
                }
                }
            ]
        );
        e.preventDefault();
    });


    $("body").delegate("#chatMsgMoreButtons .moreButtonsExpand", "click", function(e) {
        e.preventDefault();
        $(e.target).toggleClass("icon-down icon-up");
        $("#chatMsgMoreButtons .buttonsWrapper").toggle();
    });

    $("body").delegate("#chatMsgMoreButtons button[type='submit']", "click", function(e) {
        $(e.target).toggleClass("icon-down icon-up");
        $("#chatMsgMoreButtons .buttonsWrapper").toggle();
    });

});