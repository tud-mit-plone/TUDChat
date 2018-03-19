from datetime import datetime, timedelta

from zope.component import getAdapter
from zope.security import checkPermission

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from plone.dexterity.browser import add, edit
from plone import api

from tud.addons.chat.interfaces import IChatSession, IDatabaseObject
from tud.addons.chat import chatMessageFactory as _

class ChatView(BrowserView):
    """
    Default chat view
    """

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

class AddForm(add.DefaultAddForm):
    """
    Add form for dexterity chat objects
    """

    def createAndAdd(self, data):
        """
        Creates chat object and adds it to the container.
        If the configured prefix is in use, a warning is shown.
        The table creation step is also done here, because the "edited_handler" will not run for dexterity objects.

        :param data: validated form data
        :type data: dict
        :return: created chat object
        :rtype: plone.dexterity.content.Container
        """
        obj = super(AddForm, self).createAndAdd(data)
        adapter_name = obj.database_adapter

        dbo = getAdapter(getattr(self.context, obj.id), interface=IDatabaseObject, name=adapter_name)
        obj._v_db_adapter = dbo

        if obj._v_db_adapter.prefixInUse(self.context, {"connector_id": obj.connector_id, "database_prefix": obj.database_prefix}):
            api.portal.show_message(_(u'warning_prefix_in_use', default= u'The chosen prefix is already in use in this database. If you don\'t want use the already used prefix, please change it!'), self.request, 'warning')

        obj._v_db_adapter.createTables()

        return obj

class AddView(add.DefaultAddView):
    """
    Add view for dexterity chat objects
    """

    form = AddForm

class EditForm(edit.DefaultEditForm):
    """
    Edit form for dexterity chat objects
    """

    def applyChanges(self, data):
        """
        Applies changed fields to the chat object.
        If the configured prefix has changed and if the new prefix is in use, a warning is shown.

        :param data: validated form data
        :type data: dict
        :return: schema associated with changed fields
        :rtype: dict
        """

        if checkPermission('tud.addons.chat.ManageChat', self.context):
            dbo = getAdapter(self.context, IDatabaseObject, self.context.database_adapter)
            database_prefix_old = self.context.database_prefix
            database_prefix_new = data["database_prefix"]
            if database_prefix_old != database_prefix_new and dbo.prefixInUse(self.context, {"connector_id": self.context.connector_id, "database_prefix": database_prefix_new}):
                api.portal.show_message(_(u'warning_prefix_in_use', default= u'The chosen prefix is already in use in this database. If you don\'t want use the already used prefix, please change it!'), self.request, 'warning')

        return super(EditForm, self).applyChanges(data)
