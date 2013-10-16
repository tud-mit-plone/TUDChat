# -*- coding: utf-8 -*-
## TUDChat
"""
Installation module for TUDChat
"""

# Python imports
from StringIO import StringIO

# CMF imports
from Products.CMFCore.utils import getToolByName

from Products.Archetypes import listTypes
from Products.Archetypes.Extensions.utils import installTypes, install_subskin

# Product imports
from Products.TUDChat.config import *

def setPermissions(self, out):
    """
    """
    pass

def install(self):
    """
    """
    out = StringIO()

    # install types
    typeInfo = listTypes(PROJECTNAME)
    installTypes(self, out, typeInfo, PROJECTNAME)
    
    # install skin
    install_subskin(self, out, GLOBALS)

    # Add portal types to use portal factory
    pftool = getToolByName(self, 'portal_factory')
    pftool.manage_setPortalFactoryTypes(listOfTypeIds=(PROJECTNAME,))
    
    # install tool
    portal_root = self.portal_url.getPortalObject()
    if not hasattr(portal_root, "portal_tud_chat"):
        portal_root.manage_addProduct['TUDChat'].manage_addTool('TUDChatTool')
    
    # add role for Chat Moderator
    portal_root = self.portal_url.getPortalObject()
    portal_root._addRole('ChatModerator')
    portal_root.manage_role('ChatModerator', ('Access contents information', 'Manage properties', 'Modify portal content', 'View'))

    out.write('Installation completed.\n')
    return out.getvalue()

def uninstall(self):
    """
    """
    out = StringIO()
    out.write('Uninstallation completed.\n')
    return out.getvalue()
