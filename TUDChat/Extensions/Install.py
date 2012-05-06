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
    setPermissions(self) => Set standard permissions / roles
    """
    # As a default behavior, newly-created permissions are granted to owner and manager.
    # To change this, just comment this code and grab back the code commented below to
    # make it suit your needs.
    for perm in PERMS_LIST:
        self.manage_permission(perm, ('Manager', 'Owner'), acquire=1)

    # Set special permissions
    self.manage_permission(TUDChat_restrictedChatPermission, ('Member', 'Manager', 'Owner', ), acquire=1)
    self.manage_permission(TUDChat_moderatePermission, ('Reviewer', 'Manager', ), acquire=1)
    out.write("Reseted default permissions\n")

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

    out.write('Installation completed.\n')
    return out.getvalue()

def uninstall(self):
    """
    """
    out = StringIO()
    out.write('Uninstallation completed.\n')
    return out.getvalue()
