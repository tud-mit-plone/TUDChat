function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    var timeSpan = "";
    if(dateFrequency == "message") {
        timeSpan = "<span class='chatdate' data-time='"+message.date+"'></span>";
    }

    return "<div id=chatEntry"+message.id+" class='admin "+entry_classes+"'>"
        +"<span class='meta-information'><span class='username'>"+message.name+"</span>" + timeSpan + " <span class='adminActions'><a href='#' class='edit' data-mid="+message.id+" title='Nachricht bearbeiten'>&nbsp;</a> <a href='#' class='delete' data-mid="+message.id+" title='Nachricht l&ouml;schen'>&nbsp;</a></span></span>"
        +"<div class='message_content'><span>"+parsed_message+""+(additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"</span></div>"
        +"</div>";
}

function printNewUser(user, role) {
    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';

    if (user == ownUsername || role == 'admin')
        return "<li class='chatUser"+entry_classes+"'>"+user+"</li>";
    else
        return "<li class='chatUser"+entry_classes+"'>"+user+"<div class='adminActions'><a href='#' data-uname='"+user+"' class='ban' title='Benutzer aus Chat verbannen'>&nbsp;</a> <a href='#' data-uname='"+user+"' class='kick' title='Benutzer aus Chat entfernen'>&nbsp;</a> <a href='#' data-uname='"+user+"' class='warn' title='Benutzer verwarnen'>&nbsp;</a></div></li>";
}


$(document).ready(
    function(){

        $("body").delegate("a.edit", "click", function(e) {
            var oldMsg = $("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text();
            var mId = $(e.target).attr("data-mid");
            // Deselect all messages
            $("li.selected").removeClass("selected");
            // Select current message
            $("#chatEntry"+mId).addClass("selected");
            $.notification.warn("Nachricht bearbeiten <br/> <br/><form id='editMsgForm'><label for='newMsg'>Neue Nachricht:</label><br/><br/> <input type='text' id='newMsg' value='"+oldMsg+"' class='editBox'/></form>", false,
                                                                        [{"name" :"Bearbeiten",
                                                                            "click":function(){
                                                                              if (oldMsg != $("#newMsg").val()) {
                                                                                $.post(ajax_url, {'method': 'editMessage', 'message_id' :mId, 'message': $("#newMsg").val() } , function(data) { updateCheck(); });
                                                                              }
                                                                              $("#chatEntry"+mId).removeClass("selected");
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": function() { $.notification.clear(); $("#chatEntry"+mId).removeClass("selected");} },
                                                                         ]);
            e.preventDefault();
        });



        $("body").delegate("a.delete", "click", function(e) {
            var message = $("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text();
            message = ((message.length > 150) ? message.substr(0, 150) + "..." : message);
            $.notification.warn("Wollen Sie wirklich diese Nachricht löschen? <br/><br/>" + $("#chatEntry"+$(e.target).attr("data-mid")).children("span.username").text() + " " + message, false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.post(ajax_url, {'method': 'deleteMessage', 'message_id': $(e.target).attr("data-mid") }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("a.kick", "click", function(e) {
            user = $(e.target).attr("data-uname");
            $.notification.warn("Wollen Sie wirklich den Benutzer \"" + user + "\" aus dem Chat entfernen?", false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.post(ajax_url, {"method": "kickUser", "user": $(e.target).attr("data-uname") }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("a.ban", "click", function(e) {
            user = $(e.target).attr("data-uname");
            $.notification.warn("Wollen Sie wirklich den Benutzer \"" + user + "\" aus dem Chat verbannen? <br/> <br/><form id='banUserForm'><label for='ban_reason'>Banngrund:</label> <input type='text' id='ban_reason'/></form>", false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.post(ajax_url, {"method": "banUser", "user": $(e.target).attr("data-uname"), "reason": $("#ban_reason").val() }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("a.warn", "click", function(e) {
            user = $(e.target).attr("data-uname");
            $.notification.warn("Welche Verwarnung wollen Sie dem Benutzer \"" + user + "\" aussprechen? <br/> <br/><form id='warnUserForm'><label for='warning'>Warnung:</label> <input type='text' id='warning'/></form>", false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.post(ajax_url, {"method": "warnUser", "user": $(e.target).attr("data-uname"), "warning": $("#warning").val() }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

    }
);