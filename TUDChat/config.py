# -*- coding: utf-8 -*-
"""
    Configuration for this product
"""

import os
 
from Products.CMFCore.CMFCorePermissions import setDefaultRoles

GLOBALS = globals()
PROJECTNAME = 'TUDChat'
SKINS_DIR = 'skins'
TOOL_ID = 'portal_tud_chat'

# Permissions
TUDChat_addPermission = "TUDChat: Add TUDChat objects"
TUDChat_editPermission = "TUDChat: Edit TUDChat"
TUDChat_moderatePermission = "TUDChat: Moderate TUDChat"

PERMS_LIST = (TUDChat_addPermission,
              TUDChat_editPermission,
              TUDChat_moderatePermission)

for perm in PERMS_LIST:
    setDefaultRoles(perm, ('Manager', 'Owner',))