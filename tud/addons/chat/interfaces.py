
from plone.theme.interfaces import IDefaultPloneLayer


class IAddonInstalled(IDefaultPloneLayer):
    """Marker interface that defines a Zope 3 browser layer.
       Indicates that the add-on is actually installed.
    """
