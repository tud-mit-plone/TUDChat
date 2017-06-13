from plone.theme.interfaces import IDefaultPloneLayer

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
