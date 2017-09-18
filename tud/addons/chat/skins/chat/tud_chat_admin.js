function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    var timeSpan = "";
    if(dateFrequency == "message") {
        timeSpan = "<span class='chatdate' data-time='"+message.date+"'></span>";
    }

    var adminSpan = "";
    var whisperSpan = "";
    var whisperIcon = "";
    if(changes.whisper_target) {
        entry_classes += " whisper";
        whisperSpan = "<span class='additional_content'>" + getUnameLink(changes.whisper_target, { preText: _('private_message_to') + " ", fromAdmin: true }) + "</span>";
        whisperIcon = "<span class='whisper-icon'></span>";
    } else {
        adminSpan = " <span class='adminActions'><a href='#' class='edit' data-mid="+message.id+" title='" + _('edit_message') + "'>&nbsp;</a> <a href='#' class='delete' data-mid="+message.id+" title='" + _('delete_message') + "'>&nbsp;</a></span>";
    }

    var userNameString = getUnameLink(message.name, { fromAdmin: true, checkOnline: true, toAdmin: changes.admin_message });

    return "<div id=chatEntry"+message.id+" class='admin "+entry_classes+"'>"
        +"<span class='meta-information'>" + userNameString + timeSpan + adminSpan + "</span>"
        + whisperIcon + "<div><span class='message_content'>"+whisperSpan+"<span class='message'>"+parsed_message+"</span>"+""+(additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"</span></div>"
        +"</div>";
}

function printNewUser(user, role) {
    var liContent = getUnameLink(user, { afterStart: false, fromAdmin: true, toAdmin: (role == "admin") });

    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';

    return "<li class='chatUser"+entry_classes+"'>"+liContent+"</li>";
}


$(document).ready(
    function(){

        $("body").delegate("a.edit", "click", function(e) {
            var oldMsg = $("#chatEntry"+$(e.target).attr("data-mid")).find(".message_content .message").text();
            var mId = $(e.target).attr("data-mid");
            // Deselect all messages
            $("li.selected").removeClass("selected");
            // Select current message
            $("#chatEntry"+mId).addClass("selected");
            $.notification.warn(_('edit_message') + "<br/> <br/><form id='editMsgForm'><label for='newMsg'>" + _('new_message') + "</label><br/><br/> <input type='text' id='newMsg' value='"+oldMsg+"' class='editBox'/></form>", false,
                                                                        [{"name" :_('button_edit'),
                                                                            "click":function(){
                                                                              if (oldMsg != $("#newMsg").val()) {
                                                                                $.post(ajax_url, {'method': 'editMessage', 'message_id' :mId, 'message': $("#newMsg").val() } , function(data) { updateCheck(); });
                                                                              }
                                                                              $("#chatEntry"+mId).removeClass("selected");
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :_('button_abort'), "click": function() { $.notification.clear(); $("#chatEntry"+mId).removeClass("selected");} },
                                                                         ]);
            e.preventDefault();
        });



        $("body").delegate("a.delete", "click", function(e) {
            var message = $("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text();
            message = ((message.length > 150) ? message.substr(0, 150) + "..." : message);
            $.notification.warn(_('delete_confirmation') + "<br/><br/>" + $("#chatEntry"+$(e.target).attr("data-mid")).children("span.username").text() + " " + message, false,
                                                                        [{"name" :_('button_ok'),
                                                                            "click":function(){
                                                                              $.post(ajax_url, {'method': 'deleteMessage', 'message_id': $(e.target).attr("data-mid") }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :_('button_abort'), "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });



        $("#chatMsgMoreButtons .moreButtonsExpand").click(function(e) {
            e.preventDefault();
            $(e.target).toggleClass("icon-down icon-up");
            $("#chatMsgMoreButtons .buttonsWrapper").toggle();
        });

        $("#chatMsgMoreButtons .chatMsgMoreButton").click(function(e) {
            e.preventDefault();
            var method = $(e.target).data("method");
            if(method) {
                // warnUser method is only allowed with text
                if(method == "warnUser" && $("#chatMsgValue").val().trim() == "") {
                    return;
                }
                sendMessage(method);
                $("#chatMsgMoreButtons .moreButtonsExpand").click();
            }
        });

    }
);