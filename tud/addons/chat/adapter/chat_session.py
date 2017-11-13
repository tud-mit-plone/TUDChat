import re

from zope.component import getAdapter
from DateTime import DateTime

from OFS.interfaces import IObjectClonedEvent
from plone.indexer.decorator import indexer

from tud.addons.chat.interfaces import IChat, IChatSession, IDatabaseObject
from tud.addons.chat import chatMessageFactory as _

@indexer(IChatSession)
def startDateIndexer(object, **kw):
    return object.start_date

@indexer(IChatSession)
def endDateIndexer(object, **kw):
    return object.end_date

def generate_chat_id(obj, event):
    """
    Generates chat id for new chat sessions if chat id is 0 or if a chat session was copied.

    :param obj: chat session, which was created or copied
    :type obj: tud.addons.chat.content.chat_session.ChatSession
    :param event: triggered event (used to detect a copy action)
    :type event: Products.Archetypes.event.ObjectInitializedEvent or OFS.event.ObjectClonedEvent
    """
    chat = obj.getParentNode()

    if not IChat.providedBy(chat):
        return

    dbo = getAdapter(chat, IDatabaseObject, chat.database_adapter)

    if obj.chat_id != 0 and not IObjectClonedEvent.providedBy(event):
        return

    max_id_content = max([int(session.chat_id) for session in chat.getChildNodes()])
    max_id_table = dbo.getMaxSessionId()
    max_id = max((max_id_content, max_id_table,))
    new_id = max_id + 1

    obj.chat_id = new_id
    return True

def removed_handler(obj, event):
    """
    Deletes all actions of removed session in action table.

    :param obj: chat session, which will be deleted
    :type obj: tud.addons.chat.content.chat_session.ChatSession
    :param event: triggered event
    :type event: zope.lifecycleevent.ObjectRemovedEvent
    """
    chat_id = obj.chat_id
    chat = obj.getParentNode()

    dbo = getAdapter(chat, IDatabaseObject, chat.database_adapter)
    dbo.deleteActions(chat_id)

def action_succeeded_handler(obj, event):
    """
    Obfuscates user names of message senders and in messages.
    Only a chat session that is not already archived and that is closed for more than five minutes will be processed.

    :param obj: respective chat session
    :type obj: tud.addons.chat.content.chat_session.ChatSession
    :param event: triggered event with information about workflow transition
    :type event: Products.CMFCore.WorkflowCore.ActionSucceededEvent
    :return: True, if session was archived, otherwise None
    :rtype: bool or None
    """
    if event.action == 'archive':
        chat = obj.getParentNode()
        chat_id = obj.chat_id

        dbo = getAdapter(chat, IDatabaseObject, chat.database_adapter)

        now = DateTime().timeTime()

        #archive only chat sessions that are closed for more than five minutes
        if obj.end_date < now - 300:
            users = [user['user'] for user in dbo.getUsersBySessionId(chat_id)]
            #replace long user names before short user names
            #this is import for user names that containing other user names (for example: "Max" and "Max Mustermann")
            users.sort(cmp = lambda a, b: len(a)-len(b), reverse = True)
            actions = dbo.getRawActionContents(chat_id)
            i = 0

            #obfuscate user names
            for user in users:
                old_name = user

                i += 1
                new_name = obj.translate(_(u'log_user', default = u'User ${user}', mapping = {u'user' : str(i)}))
                while new_name in users:
                    i += 1
                    new_name = obj.translate(_(u'log_user', default = u'User ${user}', mapping = {u'user' : str(i)}))

                dbo.updateUserName(chat_id, old_name, new_name)

                old_name = re.compile(re.escape(old_name), re.IGNORECASE)
                for action in actions:
                    action['content'] = old_name.sub(new_name, action['content'])

            for action in actions:
                dbo.updateActionContent(action['id'], action['content'])
        else:
            raise Exception("Chat session has to be closed for more than 5 minutes!")

        return True

class StartEndDateValidator(object):
    """
    Checks that start_date is before end_date.
    """

    def __init__(self, context):
        """
        Sets context.

        :param context: chat session
        :type context: tud.addons.chat.content.chat_session.ChatSession
        """
        self.context = context

    def __call__(self, request):
        """
        Validates date parts of given request.

        :param request: request with form data
        :type request: ZPublisher.HTTPRequest.HTTPRequest
        :return: field names associated with error messages, if at least one error exists, otherwise None
        :rtype: dict or None
        """
        start_date = request.form.get('start_date', None)
        end_date = request.form.get('end_date', None)

        errors = {}

        try:
            start = DateTime(start_date)
        except:
            errors['start_date'] = self.context.translate(_(u'validation_start_date_format_err', default = u'Start of the chat has no valid date format.'))

        try:
            end = DateTime(end_date)
        except:
            errors['end_date'] = self.context.translate(_(u'validation_end_date_format_err', default = u'End of the chat has no valid date format.'))

        if 'start_date' in errors or 'end_date' in errors:
            # No point in validating bad input
            return errors

        if start > end:
            errors['end_date'] = self.context.translate(_(u'validation_end_before_start', default = u'Start of the chat must be before its end.'))

        return errors and errors or None
