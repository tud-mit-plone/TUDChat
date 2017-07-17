## Script (Python) "tud_chat_additional_css"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##

# Additional css which is created programmatically on basis of the TUDChat object

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type','text/css')

css = """
/* Admin text color */
#chatAppendix .admin::before,
#chat .username.icon-view::before {
    color: %s;
}
#chatContent div.admin_message .message_content {
    border-left: 0.5em solid %s;
}
#chatContent div.admin_message.ownMessage .message_content {
    border-right: 0.5em solid %s;
    border-left: none;
}
""" % (context.adminColor, context.adminColor, context.adminColor)

return css