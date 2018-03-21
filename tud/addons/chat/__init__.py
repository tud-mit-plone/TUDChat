# -*- coding: utf-8 -*-
"""
TUDChat product
"""

from zope.i18nmessageid import MessageFactory

# CMF imports
from Products.CMFCore.DirectoryView import registerDirectory
from Products.CMFCore.utils import ContentInit

# AT imports
from Products.Archetypes.public import process_types, listTypes

# Product import
from tud.addons.chat.config import *

chatMessageFactory = MessageFactory('tud.addons.chat')

# Initialization method
def initialize(context):
    """
    Initializes content types.

    :param context: product context
    :type context: App.ProductContext.ProductContext
    """
    listOfTypes = listTypes('tud.addons.chat')
    content_types, constructors, ftis = process_types(listOfTypes, 'tud.addons.chat')

    for atype, constructor, fti in zip(content_types, constructors, ftis):
        ret = ContentInit('%s: %s' % ('tud.addons.chat', atype.portal_type),
                          content_types=(atype,),
                          extra_constructors=(constructor,),
                          fti=(fti,),
                          permission=ADD_PERMISSIONS[atype.portal_type],
                         ).initialize(context)
