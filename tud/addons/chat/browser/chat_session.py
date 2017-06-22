# -*- coding: utf-8 -*-
from AccessControl import getSecurityManager

from Products.Five import BrowserView

class ChatSessionBaseView(BrowserView):
    def getSessionInformation(self):
        result = {}
        for field in ('title', 'description', 'chat_id', 'password', 'max_users', 'start_date', 'end_date',):
            result[field] = self.context.getField(field).get(self.context)
        result['url'] = self.context.absolute_url()

        return result

class ChatSessionView(ChatSessionBaseView):
    """Default chat session view
    """
    def getChatInformation(self):
        chat = self.context.getParentNode()

        result = {}
        for field in ('refreshRate', 'blockTime', 'maxMessageLength',):
            result[field] = chat.getField(field).get(chat)
        result['url'] = chat.absolute_url()

        return result

    ## @brief check, if a user is admin for this chat
    #  @return bool True, if user is admin, otherwise False
    def isAdmin(self):
        """ Check, if a user is admin for this chat. """
        # use the existing security mechanism, look for admin roles on the context
        # this respects groups and acquires settings along the path
        user = getSecurityManager().getUser()
        return user.has_role(self.context.admin_roles, self)

class ChatSessionLogView(ChatSessionBaseView):
    """Chat session log view
    """

    ## @brief this function returns all chat messages about a specific chat session
    #  @return list of dictionaries, the following information are in every dict: id, action, date, user, message, target, a_action, a_name
    def getLogs(self, REQUEST = None):
        """ Retrieve the whole and fully parsed chat log """
        chat_id = self.context.getField('chat_id').get(self.context)
        return self.context.getChatStorage().getActions(chat_id, 0, 0)[:-1]
