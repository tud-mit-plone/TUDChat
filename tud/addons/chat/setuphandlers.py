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
from tud.addons.chat.config import *

def setPermissions(self, out):
    """
    """
    pass

def setupVarious(context):
    '''
    Ordinarily, GenericSetup handlers check for the existence of XML files.
    Here, we are not parsing an XML file, but we use a text file as a
    flag to check that we actually meant for this import step to be run.
    The file is found in profiles/default.
    '''

    if context.readDataFile('tud.addons.chat-default.txt') is None:
        return

    site = context.getSite()

    out = StringIO()

    # install types
    typeInfo = listTypes(PROJECTNAME)
    installTypes(site, out, typeInfo, PROJECTNAME)

    # Add portal types to use portal factory
    pftool = getToolByName(site, 'portal_factory')
    pftool.manage_setPortalFactoryTypes(listOfTypeIds=(PROJECTNAME,))

    # install tool
    portal_root = site.portal_url.getPortalObject()
    if not hasattr(portal_root, "portal_tud_chat"):
        portal_root.manage_addProduct['tud.addons.chat'].manage_addTool('TUDChatTool')

    out.write('Installation completed.\n')
    return out.getvalue()

def uninstall(self):
    """
    """
    out = StringIO()
    out.write('Uninstallation completed.\n')
    return out.getvalue()
