function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);    
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    return "<li id=chatEntry"+message.id+" class='admin "+entry_classes+"'><span class='username'>"+message.name+":</span> <span class='message_content'>"+parsed_message+"</span> "+(additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"<div class='adminActions hidden'><a href='#' class='edit' data-mid="+message.id+" title='Nachricht bearbeiten'>&nbsp;</a> <a href='#' class='delete' data-mid="+message.id+" title='Nachricht l&ouml;schen'>&nbsp;</a></div></li>";    
}

function printNewUser(user) {
    if (user == ownUsername)
        return "<li class='chatUser ownUsername'>"+user+"</li>";
    else
        return "<li class='chatUser'>"+user+"<div class='adminActions hidden'><a href='#' data-uname='"+user+"' class='ban' title='Benutzer aus Chat verbannen'>&nbsp;</a> <a href='#' data-uname='"+user+"' class='kick' title='Benutzer aus Chat entfernen'>&nbsp;</a> <a href='#' data-uname='"+user+"' class='warn' title='Benutzer verwarnen'>&nbsp;</a></div></li>";
}


$(document).ready(
	function(){
        $("body").delegate("a.edit", "click", function(e) {
            $("#chatMsgEdit").val($("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text());
            $("#chatMsgEditSave").attr("data-mid", $(e.target).attr("data-mid"));
            $("#message_edit").fadeIn();
            // Deselect all messages
            $("li.selected").removeClass("selected");            
            // Select current message
            $("#chatEntry"+$(e.target).attr("data-mid")).addClass("selected");            
            e.preventDefault();
        });
        $("body").delegate("a.delete", "click", function(e) {
            $.notification.warn("Wollen Sie wirklich diese Nachricht löschen? <br/><br/>" + $("#chatEntry"+$(e.target).attr("data-mid")).children("span.username").text() + " " + $("#chatEntry"+$(e.target).attr("data-mid")).children("span.message_content").text(), false,                
                                                                        [{"name" :"Ok",
                                                                            "click":function(){                                                                           
                                                                              $.get("deleteMessage", { 'message_id': $(e.target).attr("data-mid") }, function(data) { updateCheck(); });
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
                                                                              $.get("kickUser", { "user": $(e.target).attr("data-uname") }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("a.ban", "click", function(e) {
            user = $(e.target).attr("data-uname");
            $.notification.warn("Wollen Sie wirklich den Benutzer \"" + user + "\" aus dem Chat verbannen? <br/> <br/><label for='ban_reason'>Bangrund:</label> <input type='text' id='ban_reason'/>", false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.get("banUser", { "user": $(e.target).attr("data-uname"), "reason": $("#ban_reason").val() }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("a.warn", "click", function(e) {
            user = $(e.target).attr("data-uname");
            $.notification.warn("Welche Verwarnung wollen Sie dem Benutzer \"" + user + "\" aussprechen? <br/> <br/><label for='warning'>Warnung:</label> <input type='text' id='warning'/>", false,
                                                                        [{"name" :"Ok",
                                                                            "click":function(){
                                                                              $.get("warnUser", { "user": $(e.target).attr("data-uname"), "warning": $("#warning").val() }, function(data) { updateCheck(); });
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Abbrechen", "click": $.notification.clear },
                                                                         ]);
            e.preventDefault();
        });

        $("body").delegate("li", "mouseover mouseout", function(event) {
            if (event.type == 'mouseover') { 
                $(this).addClass("hovered");
                $(this).children(".adminActions").removeClass("hidden");
            } else if (event.type == 'mouseout') { 
                $(this).removeClass("hovered");
                $(this).children(".adminActions").addClass("hidden");
            }
        });
        
        $("#chatMsgEditSave").click(function(e){
            $.post("editMessage", { 'message_id' : $(e.target).attr("data-mid"), 'message': $("#chatMsgEdit").val() } , function(data) { updateCheck(); });
            $("#message_edit").fadeOut();
            $("#chatMsgEdit").val("");
            $("#chatEntry"+$(e.target).attr("data-mid")).removeClass("selected");
        });
        $("#chatMsgEditAbort").click(function(e){            
            $("#message_edit").fadeOut();
            $("#chatMsgEdit").val("");
            $("#chatEntry"+$("#chatMsgEditSave").attr("data-mid")).removeClass("selected");     
        });
	}
);