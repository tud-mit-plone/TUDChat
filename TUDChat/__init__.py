# -*- coding: utf-8 -*-
"""
TUDChat product
"""
# CMF imports
from Products.CMFCore.DirectoryView import registerDirectory
from Products.CMFCore.utils import ContentInit, ToolInit

# AT imports
from Products.Archetypes.public import process_types, listTypes

# Product import
from Products.TUDChat.config import *
from Products.TUDChat.core import *
registerDirectory(SKINS_DIR, GLOBALS)

# TUDChatTool import
from Products.TUDChat.core.TUDChatTool import TUDChatTool

import logging
logger = logging.getLogger('TUDChat')

# Initialization method
def initialize(context):
    logger.info('TUDChat initalize')
    listOfTypes = listTypes(PROJECTNAME)
    content_types, constructors, ftis = process_types(listOfTypes, PROJECTNAME)
    logger.info('content_types, constructors, ftis : %s' % str((content_types, constructors, ftis,)))
    
    ret = ContentInit('%s Content' % PROJECTNAME,
                content_types = tuple(content_types),
                extra_constructors = tuple(constructors),
                fti = ftis,
                ).initialize(context)

    logger.info('return value of ContentInit: %s' % str(ret))
    
    tool = ToolInit('%s Tool' % PROJECTNAME,
                    tools=(TUDChatTool,),
                    product_name=PROJECTNAME,
                    icon='tool_icon.gif',)
    tool.initialize(context)
