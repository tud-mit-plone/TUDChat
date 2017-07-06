function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    return "<div id=chatEntry"+message.id+" class='"+entry_classes+"'><span class='meta-information'><span class='username'>"+message.name+"</span><span class='chatdate'>"+$.trim(message.date)+"</span></span> <div class='message_content'><span>"+parsed_message + (additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"</span></div> </div>";
}

function printNewUser(user, role) {
    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';
    return "<li class='chatUser"+entry_classes+"'>"+user+"</li>";
}