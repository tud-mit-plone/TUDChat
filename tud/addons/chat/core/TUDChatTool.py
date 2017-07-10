# -*- coding: utf-8 -*-
"""
  TUDChat tool
"""
"""
TUDChatTool - manages the database connection list for the chat contents
"""
# Python imports
import re
from datetime import datetime, timedelta

# Zope imports
from zope.interface import alsoProvides
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import manage_properties
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from plone.protect.interfaces import IDisableCSRFProtection
from plone import api

# CMF imports
from Products.CMFCore.utils import UniqueObject, getToolByName

# Product imports
from tud.addons.chat.config import *
from tud.addons.chat.interfaces import IChatSession

class TUDChatTool(UniqueObject, SimpleItem, PropertyManager):
    """ Tool for TUDChat """

    plone_tool = True
    id = TOOL_ID
    title = "%s Tool" % PROJECTNAME
    meta_type = "%sTool" % PROJECTNAME

    #data
    db_list = []
    allowed_db_list = []

    security = ClassSecurityInfo()

    manage_options = (
                      ({ 'label' : 'Chatübersicht'
                       , 'action' : 'chat_list'
                       },
                       { 'label' : 'Datenbankliste konfigurieren'
                       , 'action' : 'db_config'
                       },
                      )
                     ) + PropertyManager.manage_options

    security.declareProtected(manage_properties, 'db_config')
    db_config = PageTemplateFile('../skins_tool/db_config.pt', globals())
    security.declareProtected(manage_properties, 'chat_list')
    chat_list = PageTemplateFile('../skins_tool/chat_list.pt', globals())

    def pathCleaner(self, path):
        """
            This function remove slash groups and slashes at the beginning and at the end of the path.
            This function also removes the Sites/TUD prefix if it exist.
        """
        #remove group of slashes and if exist first and last slash
        path = re.sub(r"/+","/",path)
        path = re.sub(r"^/","",path)
        path = re.sub(r"/$","",path)
        #remove prefix 'Sites', 'TUD' and 'Sites/TUD'
        path = re.sub(r"^Sites/TUD[/]{0,1}","",path)
        path = re.sub(r"^Sites[/]{0,1}","",path)
        path = re.sub(r"^TUD[/]{0,1}","",path)

        return path

    def getChatList(self, withObjects = False):
        """
            This function search all TUDChats in the system, which are registered in the catalog.
            This function return a list of dictonaries with id and path.
        """
        results = []

        catalog = getToolByName(self, 'portal_catalog')
        brains = catalog.searchResults({'portal_type': 'TUDChat'})

        for brain in brains:
            dict = {}
            dict['id'] = brain['id']
            dict['path'] = brain.getPath()
            try:
                if withObjects:
                    dict['obj'] = brain.getObject()
                results.append(dict)
            except:
                pass

        return results

    def getSQLConnectionIDs(self, path):
        """
            Find SQL database connections in the current folder.
            This function return a list of ids.
        """
        portal = self.portal_url.getPortalObject()
        folder = portal.restrictedTraverse(path)
        if folder:
            olist = folder.objectValues()
            result = [o.getId() for o in olist if o.meta_type=='Z MySQL Database Connection']
        else:
            result = []

        return result

    def getDbList(self):
        """
            Get all registered dbs.
            This function return a list of dictonaries with path and in_use flag.
        """
        results = []


        for db in self.db_list:
            dict = {}
            dict['path'] = db
            dict['in_use'] = db in self.allowed_db_list
            results.append(dict)

        return results

    def addDbPath(self, path, REQUEST = None):
        """
            This function add all dbs to the db list for a given path.
            status = 0 means databasas are added
            status = 1 means no databasas are added
            status = 2 means no databases found at the given path
        """
        status = 1

        path = self.pathCleaner(path)

        db_id_list = self.getSQLConnectionIDs(path)
        if len(db_id_list)>0:
            for db_id in db_id_list:
                if path+'/'+db_id not in self.db_list:
                    self.db_list.append(path+'/'+db_id)
                    status = 0
        else:
            status = 2

        REQUEST.form['status'] = status

        #needed for persistence
        self.db_list = self.db_list

        return self.db_config(request=REQUEST)

    def updateDbs(self, REQUEST=None):
        """
            This function set the allowed state for all databases and can delete some databases.
        """
        nochange = True

        remove_list=[]
        for path in self.db_list:
            if REQUEST.get('active_'+path) and path not in self.allowed_db_list:
                self.allowed_db_list.append(path)
                nochange = False
            elif not REQUEST.get('active_'+path) and path in self.allowed_db_list:
                self.allowed_db_list.remove(path)
                nochange = False
            if REQUEST.get('delete_'+path):
                remove_list.append(path)
                nochange = False
        for path in remove_list:
            self.db_list.remove(path)
            if path in self.allowed_db_list:
                self.allowed_db_list.remove(path)

        #needed for persistence
        self.db_list = self.db_list
        self.allowed_db_list = self.allowed_db_list

        REQUEST.form['nochange'] = nochange

        return self.db_config(request=REQUEST)

    def getAllowedDbList(self, path):
        """
            This function return a list of allowes database ids for the given path.
        """
        path = self.pathCleaner(path)

        #build a allowed path list with all sub paths
        path_parts = path.split('/')
        path_list = []
        for i in range(2,len(path_parts)+1):
            path_list.append("/".join(path_parts[:i]))

        db_id_list = []
        for dbpath in self.allowed_db_list:
            if dbpath.startswith('/'):
                db_id_list.append(dbpath[1:])
                continue
            db_path_without_id = '/'.join(dbpath.split('/')[:-1])
            for path_prefix in path_list:
                if db_path_without_id == path_prefix:
                    db_id_list.append(dbpath.split('/')[-1])
                    break

        return db_id_list

    def lockClosedChatSessions(self):
        """
            This function calls in all chat session objects a method which obfuscates user names of closed unlocked chat sessions and locks these sessions after obfuscation.
            A cron should periodical call this function.
            The count of locked chats will be returned.
        """
        # disable CSRF-Protection to allow write access
        alsoProvides(self.REQUEST, IDisableCSRFProtection)

        catalog = getToolByName(self, 'portal_catalog')
        query = {
            'object_provides': IChatSession.__identifier__,
            'ChatSessionEndDate': {'query': datetime.now() - timedelta(minutes = 6), 'range': 'max'},
            'review_state': 'open'
            }
        session_brains = catalog(query)
        for session_brain in session_brains:
            session = session_brain.getObject()
            api.content.transition(obj=session, transition='lock')

        return str(len(session_brains))

InitializeClass(TUDChatTool)