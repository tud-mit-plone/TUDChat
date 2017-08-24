import re

from DateTime import DateTime

from OFS.interfaces import IObjectClonedEvent
from plone.indexer.decorator import indexer

from tud.addons.chat.interfaces import IChat, IChatSession

@indexer(IChatSession)
def startDateIndexer(object, **kw):
    return object.start_date

@indexer(IChatSession)
def endDateIndexer(object, **kw):
    return object.end_date

def generate_chat_id(obj, event):
    """
    Generates chat_id for chat sessions if chat_id is 0 or if a chat session was copied
    """
    chat = obj.getParentNode()

    if not IChat.providedBy(chat) or not chat.chat_storage:
        return

    if obj.getField('chat_id').get(obj) != 0 and not IObjectClonedEvent.providedBy(event):
        return

    max_id_content = max([int(session.getField('chat_id').get(session)) for session in chat.getChildNodes()])
    max_id_table = chat.chat_storage.getMaxSessionId()
    max_id = max((max_id_content, max_id_table,))
    new_id = max_id + 1

    obj.getField('chat_id').set(obj, new_id)
    return True

def removed_handler(obj, event):
    """
    Deletes actions of removed chat in action table
    """
    chat_id = obj.getField('chat_id').get(obj)
    chat_storage = obj.getChatStorage()
    chat_storage.deleteActions(chat_id)

## @brief this function obfuscates user names of closed and not already archived chat sessions
#  @return bool True
def action_succeeded_handler(obj, event):
    """
    Obfuscates user names of message senders and in messages.
    Only a chat session that is closed for more than five minutes will be processed.
    """
    if event.action == 'archive':
        chat = obj.getParentNode()
        chat_storage = chat.chat_storage
        chat_id = obj.getField('chat_id').get(obj)

        if not chat_storage:
            raise Exception("Can't archive without storage!")

        now = DateTime().timeTime()

        #archive only chat sessions that are closed for more than five minutes
        if obj.getField('end_date').get(obj) < now - 300:
            users = [user['user'] for user in chat_storage.getUsersBySessionId(chat_id)]
            #replace long user names before short user names
            #this is import for user names that containing other user names (for example: "Max" and "Max Mustermann")
            users.sort(cmp = lambda a, b: len(a)-len(b), reverse = True)
            actions = chat_storage.getRawActionContents(chat_id)
            i = 0

            #obfuscate user names
            for user in users:
                old_name = user

                i += 1
                new_name = "Benutzer "+str(i)
                while new_name in users:
                    i += 1
                    new_name = "Benutzer "+str(i)

                chat_storage.updateUserName(chat_id, old_name, new_name)

                old_name = re.compile(re.escape(old_name), re.IGNORECASE)
                for action in actions:
                    action['content'] = old_name.sub(new_name, action['content'])

            for action in actions:
                chat_storage.updateActionContent(action['id'], action['content'])
        else:
            raise Exception("Chat session has to be closed for more than 5 minutes!")

        return True

class StartEndDateValidator(object):
    """
    Checks that start_date is before end_date.
    """

    def __init__(self, context):
        self.context = context

    def __call__(self, request):
        start_date = request.form.get('start_date', None)
        end_date = request.form.get('end_date', None)

        errors = {}

        try:
            start = DateTime(start_date)
        except:
            errors['start_date'] = 'Falsches Beginn-Datum! Bitte korrigieren Sie Ihre Eingabe.'

        try:
            end = DateTime(end_date)
        except:
            errors['end_date'] = 'Falsches Ende-Datum! Bitte korrigieren Sie Ihre Eingabe.'

        if 'start_date' in errors or 'end_date' in errors:
            # No point in validating bad input
            return errors

        if start > end:
            errors['end_date'] = 'Beginn-Datum ist nach Ende-Datum! Bitte korrigieren Sie Ihre Eingabe.'

        return errors and errors or None
