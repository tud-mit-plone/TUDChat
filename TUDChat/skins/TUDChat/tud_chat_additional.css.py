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
div#chatUser ul li.adminrole {
    color: %s;
}
#chatContent li.admin_message {
    color: %s
}
""" % (context.adminColor, context.adminColor)

return css