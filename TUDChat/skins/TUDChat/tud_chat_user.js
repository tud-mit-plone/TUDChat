function printMessage(message) {

    changes = applyAttributes(message.message, message.attributes);
    parsed_message = hyperlink(changes.message_content);
    entry_classes = changes.entry_classes + ((message.name == ownUsername) ? ' ownMessage' : '');
    additional_content = changes.additional_content;

    return "<li id=chatEntry"+message.id+" class='"+entry_classes+"'><span class='chatdate'>"+message.date+"</span><span class='username'>"+message.name+":</span> <span class='message_content'>"+parsed_message+"</span> "+(additional_content != '' ? "<span class='additional_content'>"+additional_content+"</span>" : "")+"</li>";
}

function printNewUser(user, role) {
    entry_classes = '';
    if (user == ownUsername)
        entry_classes += ' ownUsername';
    entry_classes += ' ' + role + 'role';
    return "<li class='chatUser"+entry_classes+"'>"+user+"</li>";
}