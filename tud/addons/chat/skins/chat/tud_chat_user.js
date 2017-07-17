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
    if(changes.whisper_target) {
        entry_classes += " whisper";
        whisperSpan = "<span class='additional_content'>" + getUnameLink(changes.whisper_target, { preText: "Private Nachricht an " }) + "</span>";
        whisperIcon = "<span class='whisper-icon'></span>";
    }

    var userNameString = getUnameLink(message.name, { checkOnline: true, toAdmin: changes.admin_message });

    return "<div id=chatEntry"+message.id+" class='"+entry_classes+"'>"
            + "<span class='meta-information'>" + userNameString + timeSpan + "</span> "+ whisperIcon
            + "<div><span class='message_content'>" + whisperSpan + "<span class='message'>" + parsed_message + "</span>" + (additional_content != '' ? "<span class='additional_content'>" + additional_content + "</span>" : "") + "</span></div>"
        + "</div>";
}

function printNewUser(user, role) {
    var liContent = getUnameLink(user, { afterStart: false, toAdmin: (role == "admin") });

    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';

    return "<li class='chatUser"+entry_classes+"'>"+liContent+"</li>";
}