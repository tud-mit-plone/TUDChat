import urlparse

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

class ChatView(BrowserView):
    """Default chat view
    """

    def getTitle(self):
        return self.context.getField('title').get(self.context)

    def getIntroduction(self):
        return self.context.getField('introduction').get(self.context)

    ## @brief this function checks if the domain in the url matches the chat domain
    #  @param url str complete url to check
    #  @return str url to redirect if domains don't match, otherwise empty string
    def checkURL(self, url):
        """ chat domain check"""
        portal_tud_chat_tool = getToolByName(self, 'portal_tud_chat')
        chat_domain = portal_tud_chat_tool.chat_domain
        transfer_protocol = portal_tud_chat_tool.transfer_protocol

        domain = urlparse.urlparse(url)

        if domain[1].count(":") == 0:
            hostname = domain[1]
            port = ""
        elif domain[1].count(":") == 1:
            hostname, port = domain[1].split(":")
            port = ":"+port
        else:
            return ""

        if hostname != chat_domain:
            return urlparse.urlunparse((transfer_protocol, chat_domain+port, domain[2], domain[3], domain[4], domain[5]))
        else:
            return ""

    ## @brief this function generates a list of all chat sessions which were active
    #  @return list of dictionaries, the following information are in every dict: id,name,description,password,max_users,start,end
    def getActiveChatSessions(self):
        """ Get a list of all active chat sessions. """
        if self.context.chat_storage:
            return self.context.chat_storage.getActiveChatSessions()
        else:
            return None

    ## @brief this function generates a list of all chat sessions which were planned
    #  @return list of dictionaries, the following information are in every dict: id,name,start,end
    def getNextChatSessions(self):
        """ Get the next chat session, which will start. """
        if self.context.chat_storage:
            return self.context.chat_storage.getNextChatSessions()
        else:
            return None
