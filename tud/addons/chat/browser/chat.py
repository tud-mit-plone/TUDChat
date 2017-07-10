from datetime import datetime

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

from tud.addons.chat.interfaces import IChatSession

class ChatView(BrowserView):
    """Default chat view
    """

    def getTitle(self):
        return self.context.getField('title').get(self.context)

    def getIntroduction(self):
        return self.context.getField('introduction').get(self.context)

    ## @brief this function generates a list of all chat sessions which were active
    #  @return list of chat session objects
    def getActiveChatSessions(self):
        """ Get a list of all active chat sessions. """
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': IChatSession.__identifier__,
            'path': '/'.join(self.context.getPhysicalPath()),
            'ChatSessionStartDate': {'query': datetime.now(), 'range': 'max'},
            'ChatSessionEndDate': {'query': datetime.now(), 'range': 'min'},
            'review_state': 'open'
            }
        return [brain.getObject() for brain in catalog(query)]

    ## @brief this function generates a list of all chat sessions which were planned
    #  @return list of chat session objects
    def getNextChatSessions(self):
        """ Get the next chat session, which will start. """
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': IChatSession.__identifier__,
            'path': '/'.join(self.context.getPhysicalPath()),
            'ChatSessionStartDate': {'query': datetime.now(), 'range': 'min'},
            'review_state': 'open'
            }
        return [brain.getObject() for brain in catalog(query)]

class ChatSessionsView(BrowserView):
    """Chat sessions view
    """

    def getSessions(self):
        """ Returns all chat sessions """
        return self.context.getChildNodes()

    def getState(self, obj):
        """ Returns current workflow state of given object """
        wftool = getToolByName(self, 'portal_workflow')
        return wftool.getInfoFor(obj, 'review_state')

    def getStateTitle(self, obj):
        """ Returns current workflow state title of given object """
        wftool = getToolByName(self, 'portal_workflow')
        state = wftool.getInfoFor(obj, 'review_state')
        workflows = wftool.getWorkflowsFor(obj)
        if workflows:
            for wf in workflows:
                if state in wf.states:
                    return wf.states[state].title or state
