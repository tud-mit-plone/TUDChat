function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    var timeSpan = "";
    if(dateFrequency == "message") {
        timeSpan = "<span class='chatdate' data-time='"+message.date+"'></span>";
    }

    var whisperSpan = "";
    var whisperIcon = "";
    if(changes.whisper) {
        entry_classes += " whisper";
        whisperSpan = "<span class='additional_content'>Private Nachricht</span>";
        // whisperIcon = (message.name == ownUsername) ? "<span class='whisper-icon'></span>" : "<a href='#' class='whisper-icon' title='Mit privater Nachricht antworten' data-uname='"+message.name+"'></a>";
        whisperIcon = "<span class='whisper-icon'></span>";
    }

    return "<div id=chatEntry"+message.id+" class='"+entry_classes+"'><span class='meta-information'><span class='username'>"+message.name+"</span>" + timeSpan + "</span> " + whisperIcon + "<div class='message_content'><span class='message'>"+whisperSpan+parsed_message + (additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"</span></div> </div>";
}

function printNewUser(user, role) {
    var liContent = user;

    if(
          whisper != "off"
      &&  user != ownUsername
      && (role == "admin" || whisper == "on")
    ) {
      liContent = "<a href='#' class='icon-mail' title='Nachricht an " + user + " schreiben' data-uname='"+user+"'>" + user + "</a>";
    }

    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';

    return "<li class='chatUser"+entry_classes+"'>"+liContent+"</li>";
}