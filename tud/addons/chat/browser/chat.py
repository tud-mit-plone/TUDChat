from datetime import datetime, timedelta

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

from tud.addons.chat.interfaces import IChatSession
from tud.addons.chat import chatMessageFactory as _

class ChatView(BrowserView):
    """
    Default chat view
    """

    def getTitle(self):
        """
        Returns chat title.

        :return: title of chat
        :rtype: str
        """
        return self.context.getField('title').get(self.context)

    def getIntroduction(self):
        """
        Returns chat introduction.

        :return: introduction of chat
        :rtype: str
        """
        return self.context.getField('introduction').get(self.context)

    def getWhisperOption(self):
        """
        Returns configured whisper option.

        :return: whisper option ('on', 'restricted' or 'off')
        :rtype: str
        """
        return self.context.getField('whisper').get(self.context)

    def getShowOldMessagesOptions(self):
        """
        Returns settings which define how many messages are shown when entering a chat session and how old these messages can be.

        :return: maximum count of old messages and maximum age of these messages
        :rtype: dict
        """
        return {'count' : self.context.getField('oldMessagesCount').get(self.context),
                'minutes' : self.context.getField('oldMessagesMinutes').get(self.context)}

    def getActiveChatSessions(self):
        """
        Generates a list of all active chat sessions.

        :return: chat sessions
        :rtype: list[tud.addons.chat.content.chat_session.ChatSession]
        """
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': IChatSession.__identifier__,
            'path': '/'.join(self.context.getPhysicalPath()),
            'ChatSessionStartDate': {'query': datetime.now(), 'range': 'max'},
            'ChatSessionEndDate': {'query': datetime.now(), 'range': 'min'},
            'review_state': 'editable'
            }
        return [brain.getObject() for brain in catalog(query)]

    def getNextChatSessions(self):
        """
        Generates a list of all chat sessions which were planned.

        :return: chat sessions
        :rtype: list[tud.addons.chat.content.chat_session.ChatSession]
        """
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': IChatSession.__identifier__,
            'path': '/'.join(self.context.getPhysicalPath()),
            'ChatSessionStartDate': {'query': datetime.now() + timedelta(minutes = 1), # addition is needed to filter sessions that have been active for less than one minute
                                     'range': 'min'},
            'review_state': 'editable',
            'sort_on': 'ChatSessionStartDate',
            'sort_order': 'ascending'
            }
        return [brain.getObject() for brain in catalog(query)]

    def getPortalMessage(self):
        """
        Returns different portal messages depending on flags in user session.
        If no flag exists, no message will be returned.
        In case of message delivery the corresponding flag will be removed.

        :return: portal message, if at least one corresponding flag exists in user session, otherwise None
        :rtype: str or None
        """
        session = self.request.SESSION

        if session.has_key("chat_kick_message"):
            message = self.context.translate(_(u'session_kicked', default = u'You have been kicked from the chat by a moderator!'))

            if session["chat_kick_message"]:
                message += "<br /><br />" + self.context.translate(_(u'session_kicked_reason', default = u'Reason: ${reason}', mapping={u'reason': session["chat_kick_message"]}))

            del session["chat_kick_message"]

            return message

        if session.has_key("chat_ban_message"):
            message = self.context.translate(_(u'session_banned', default = u'You have been banned from the chat by a moderator!'))

            if session["chat_ban_message"]:
                message += "<br /><br />" + self.context.translate(_(u'session_banned_reason', default = u'Reason: ${reason}', mapping={u'reason': session["chat_ban_message"]}))

            del session["chat_ban_message"]

            return message

        if session.has_key("chat_not_authorized_message"):
            message = session["chat_not_authorized_message"]

            del session["chat_not_authorized_message"]

            return message

        return None

class ChatSessionsView(BrowserView):
    """
    Chat sessions view
    """

    def getSessions(self):
        """
        Returns all chat sessions.

        :return: chat sessions
        :rtype: OFS.ZDOM.NodeList
        """
        return self.context.getChildNodes()

    def getState(self, obj):
        """
        Returns current workflow state of given session.

        :param obj: chat session
        :type obj: tud.addons.chat.content.chat_session.ChatSession
        :return: workflow state ('editable' or 'archived')
        :rtype: str
        """
        wftool = getToolByName(self, 'portal_workflow')
        return wftool.getInfoFor(obj, 'review_state')

    def getStateTitle(self, obj):
        """
        Returns translated title of current workflow state of given session.

        :param obj: chat session
        :type obj: tud.addons.chat.content.chat_session.ChatSession
        :return: translated title of workflow state
        :rtype: str
        """
        wftool = getToolByName(self, 'portal_workflow')
        state = wftool.getInfoFor(obj, 'review_state')
        workflows = wftool.getWorkflowsFor(obj)
        if workflows:
            for wf in workflows:
                if state in wf.states:
                    return self.context.translate(wf.states[state].title or state)
