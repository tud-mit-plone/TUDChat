from plone.theme.interfaces import IDefaultPloneLayer
from plone.supermodel import model

from zope.interface import Interface


class IAddonInstalled(IDefaultPloneLayer):
    """Marker interface that defines a Zope 3 browser layer.
       Indicates that the add-on is actually installed.
    """

class IChat(Interface):
    """Marker interface for chat
    """

class IChatSession(Interface):
    """Marker interface for chat session
    """

class IDatabaseObject(Interface):
    """Interface for database communication
    """

    def __init__(chat):
        pass

    def validate(REQUEST):
        pass

    def prefixInUse():
        pass

    def createTables():
        pass

    def getMaxSessionId():
        pass

    def getLastAction(chat_id):
        pass

    def getStartAction(chat_id, old_messages_count = 0, old_messages_minutes = 0):
        pass

    def getActions(chat_id, last_action, start_action, start_action_whisper, user, limit = 0):
        pass

    def getRawActionContents(chat_id):
        pass

    def sendAction(chat_id, user, action, content = "", target = None, whisper_target = None):
        pass

    def getUsersBySessionId(chat_id):
        pass

    def updateUserName(chat_id, old_name, new_name):
        pass

    def updateActionContent(action_id, new_content):
        pass

    def deleteActions(chat_id):
        pass

class IChatModel(model.Schema, IChat):
    """Model for chat objects
    """
    model.load('models/Chat.xml')

class IChatSessionModel(model.Schema, IChatSession):
    """Model for chat session objects
    """
    model.load('models/ChatSession.xml')
