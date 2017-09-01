# -*- coding: utf-8 -*-
"""
TUDChat product
"""
# CMF imports
from Products.CMFCore.DirectoryView import registerDirectory
from Products.CMFCore.utils import ContentInit

# AT imports
from Products.Archetypes.public import process_types, listTypes

# Product import
from tud.addons.chat.config import *
from tud.addons.chat.core import *

import logging
logger = logging.getLogger('tud.addons.chat')

# Initialization method
def initialize(context):
    logger.info('tud.addons.chat initalize')
    listOfTypes = listTypes('tud.addons.chat')
    content_types, constructors, ftis = process_types(listOfTypes, 'tud.addons.chat')
    logger.info('content_types, constructors, ftis : %s' % str((content_types, constructors, ftis,)))

    for atype, constructor, fti in zip(content_types, constructors, ftis):
        ret = ContentInit('%s: %s' % ('tud.addons.chat', atype.portal_type),
                          content_types=(atype,),
                          extra_constructors=(constructor,),
                          fti=(fti,),
                          permission=ADD_PERMISSIONS[atype.portal_type],
                         ).initialize(context)

        logger.info('return value of ContentInit: %s' % str(ret))
