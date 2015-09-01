# -*- coding: utf-8 -*-
## TUDChat
"""
    TUDChat
"""
__docformat__ = 'restructuredtext'

# Python imports
import re
import simplejson
import random, string
import os.path, time
from cStringIO import StringIO
import urlparse

# Zope imports
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.Permissions import manage_properties
from DateTime import DateTime

# CMF imports
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import CMFCorePermissions
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

# Archetypes imports
try:
    from Products.LinguaPlone.public import *
except ImportError:
    # No multilingual support
    from Products.Archetypes.public import *

# Product imports
from Products.TUDChat.config import *
from Products.TUDChat.core.schemata import TUDChatSchema
from Products.TUDChat.core.InteractionInterface import ITUDChatInteractionInterface
from Products.TUDChat.core.PersistenceInterface import ITUDChatStorage
from Products.TUDChat.core.TUDChatSqlStorage import TUDChatSqlStorage

# for Debugging only
from pprint import saferepr

import logging
logger = logging.getLogger('TUDChat')

class UserStatus:
    OK, NOT_AUTHORIZED, KICKED, BANNED, LOGIN_ERROR, WARNED, CHAT_WARN = range(7)

class BanStrategy:
    COOKIE, IP, COOKIE_AND_IP = ('COOKIE', 'IP', 'COOKIE_AND_IP')


class TUDChat(BaseContent):
    """TUDChat class"""

    __implements__ = (ITUDChatInteractionInterface,)
    meta_type                = 'TUDChat'
    archetype_name           = 'Chat'
    content_icon             = 'content_icon.gif'
    default_view             = 'TUDChat_view'
    schema                   = TUDChatSchema
    isPrincipiaFolderish     = False

    chat_storage             = None

    # Data
    ## @brief collection of timestamps to call methods in certain intervals
    timestamps               = {}
    ## @brief chat room container with userlist, kicked_users, banned_users and timestamps
    chat_rooms               = {}
    ## @brief define roles that have admin privileges
    admin_roles              = ['Admin','ChatModerator']
    ## @brief list of message ids sent from admins
    admin_messages           = []
    ## @brief for each connector_id the own prefixes in this database
    own_database_prefixes    = {}
    ## @brief replacements for special html chars (char "&" is in function included)
    htmlspecialchars         = {'"':'&quot;', '\'':'&#039;', '<':'&lt;', '>':'&gt;'} # {'"':'&quot;'} this comment is needed, because there is a bug in doxygen

    # Actions
    ## @brief describe the menu for the chat
    actions = (
        {'id'           : 'view',
         'name'         : 'View',
         'action'       : 'string:${object_url}/TUDChat_view',
         'permissions'  : (CMFCorePermissions.View, ),
         'category'     : 'object'
         },
        {'id'           : 'edit',
         'name'         : 'Chat-Einstellungen',
         'action'       : 'string:${object_url}/base_edit',
         'permissions'  : (CMFCorePermissions.ManageProperties, ),
         'category'     : 'object'
         },
        {'id'           : 'add_session',
         'name'         : 'Chat-Sitzung hinzufügen',
         'action'       : 'string:${object_url}/add_session',
         'permissions'  : (CMFCorePermissions.ManageProperties, ),
         'category'     : 'object'
         },
        {'id'           : 'edit_sessions',
         'name'         : 'Chat-Sitzungen verwalten',
         'action'       : 'string:${object_url}/edit_sessions',
         'permissions'  : (CMFCorePermissions.ManageProperties, ),
         'category'     : 'object'
         },
    )

    security = ClassSecurityInfo()

    # Page Templates
    security.declareProtected(manage_properties, 'add_session')
    add_session = PageTemplateFile('../skins/TUDChat/add_session.pt', globals())
    security.declareProtected(manage_properties, 'edit_sessions')
    edit_sessions = PageTemplateFile('../skins/TUDChat/edit_sessions.pt', globals())

    ## @brief class constructor which prepares the database connection
    #  @param id the identifier of the chat object
    def __init__(self, id):
        self.id = id
        logger.info("Initialised 'TUDChat Content'...")
        self.chat_storage = None
        self.own_database_prefixes = self.own_database_prefixes


    security.declarePrivate('_post_init')
    def _post_init(self):
        """
        _post_init(self) => Post-init method (being called AFTER the class has been set into the ZODB)
        """
        # We set the object creator as a Reviewer - as it won't be possible to do so
        # later because of permission restrictions
        obj = self
        member_id = getToolByName(self, 'portal_membership').getAuthenticatedMember().getId()
        roles = list(obj.get_local_roles_for_userid( userid=member_id ))
        if "Reviewer" not in roles:
            roles.append( "Reviewer" )
            obj.manage_setLocalRoles( member_id, roles )
        # We reindex the object
        self.reindexObject()
        logger.info("Postinit")

    ##########################################################################
    # General Utility methods
    ##########################################################################

    # override the default actions

    ## @brief check and apply admin settings
    #  @param error list of errors
    def post_validate(self, REQUEST, errors):
        """
        This function checks the edit form values in context.
        It's called after the field validation passes.
        """
        if not REQUEST.get('post_validated'):
            connector_id = REQUEST.get('connector_id')
            database_prefix = REQUEST.get('database_prefix')
            if not errors:
                self.chat_storage = TUDChatSqlStorage(connector_id, database_prefix) # Update chat_storage
                if self.chat_storage.createTables() or database_prefix in self.own_database_prefixes.get(connector_id, []): # check if the prefix is free or is it an already used prefix
                    if self.own_database_prefixes.get(connector_id):
                        self.own_database_prefixes[connector_id].add(database_prefix)
                    else:
                        self.own_database_prefixes[connector_id] = set([database_prefix])
                    logger.info("TUDChat: connector_id = %s" % (connector_id,))
                else:
                    errors['database_prefix'] = "Dieser Prefix wird in dieser Datenbank bereits verwendet. Bitte wählen Sie einen anderen Prefix."
            REQUEST.set('post_validated', True)

    security.declarePublic("getAllowedDbList")
    ## @brief get a list of for chat usage allowed database connections
    #  @return list list of allowed databases
    def getAllowedDbList(self):
        """
        Get a list of allowed Mysql_Connection_IDs
        """
        dl = DisplayList()
        portal_tud_chat_tool = getToolByName(self, 'portal_tud_chat')

        url=self.absolute_url()
        if url.count('/')<3:
            path = '/'
        else:
            path = '/'.join(url.split('/')[3:])

        for connection in portal_tud_chat_tool.getAllowedDbList(path):
            dl.add(connection, connection)
        return dl

    ## @brief this function checks if the domain in the url matches the chat domain
    #  @param url str complete url to check
    #  @return str url to redirect if domains don't match, otherwise empty string
    security.declarePublic("checkURL")
    def checkURL(self, url):
        """ chat domain check"""
        portal_tud_chat_tool = getToolByName(self, 'portal_tud_chat')
        chat_domain = portal_tud_chat_tool.chat_domain
        transfer_protocol = portal_tud_chat_tool.transfer_protocol

        domain = urlparse.urlparse(url)

        if domain[1].count(":") == 0:
            hostname = domain[1]
            port = ""
        elif domain[1].count(":") == 1:
            hostname, port = domain[1].split(":")
            port = ":"+port
        else:
            return ""

        if hostname != chat_domain:
            return urlparse.urlunparse((transfer_protocol, chat_domain+port, domain[2], domain[3], domain[4], domain[5]))
        else:
            return ""

    ## @brief this function checks for a valid utf-8 string
    #  @param url str string to check
    #  @return bool true for valid utf-8 otherwise false
    security.declarePublic("checkUTF8")
    def checkUTF8(self, string):
        """ utf-8 check"""
        try:
            string.decode("utf8")
        except:
            return False
        return True

    security.declarePublic("show_id")
    def show_id(self,):
        """
        Determine whether to show an id in an edit form

        show_id() used to be in a Python Script, but was removed from Plone 2.5,
        so we had to add the method here for compatability
        """

        if getToolByName(self, 'plone_utils').isIDAutoGenerated(self.REQUEST.get('id', None) or self.getId()):
            return not (self.portal_factory.isTemporary(self) or self.CreationDate() == self.ModificationDate())
        return

    security.declarePublic("getIp")
    ## @brief get IP address from a request
    #  @return string IP address as a string or None if not available
    def getIp(self, REQUEST): # see: http://dev.menttes.com/collective.developermanual/serving/http_request_and_response.html#request-client-ip
        """  Extract the client IP address from the HTTP request in a proxy compatible way.

        @return: IP address as a string or None if not available
        """

        if "HTTP_X_FORWARDED_FOR" in REQUEST.environ:
            # Virtual host
            ip = REQUEST.environ["HTTP_X_FORWARDED_FOR"]
        elif "HTTP_HOST" in REQUEST.environ:
            # Non virtual host
            ip = REQUEST.environ["REMOTE_ADDR"]
        else:
            # Unit test code?
            ip = None

        return ip

    def html_escape(self, text):
        """ Escape html characters """
        tmptext = text.replace('&','&amp;')
        for key in self.htmlspecialchars:
            tmptext = tmptext.replace(key, self.htmlspecialchars[key])
        return tmptext

    security.declarePrivate('getDefaultPloneSiteCharset')
    def getDefaultPloneSiteCharset(self):
        """ Get the default charset of this plone site."""
        return self.portal_properties.site_properties.getProperty('default_charset')

    ##########################################################################
    # Access management
    ##########################################################################

    ## @brief Check, if a user is registered to a chat session
    #  @return bool True, if user is registered, otherwise False
    def isRegistered(self, REQUEST = None):
        """ Check, if a user is registered to a chat session. """
        session=REQUEST.SESSION

        if session.get('user_properties'):
            chat_uid = session.get('user_properties').get('chat_room')
            if chat_uid in self.chat_rooms.keys():
                if self.hasUser(session.get('user_properties').get('name'), chat_uid):
                    return True
            else:
                session.clear()
        return False

    ## @brief check, if a user is admin for this chat
    #  @return bool True, if user is admin, otherwise False
    def isAdmin(self, REQUEST = None):
        """ Check, if a user is admin for this chat. """
        # use the existing security mechanism, look for admin roles on the context
        # this respects groups and acquires settings along the path
        user = getSecurityManager().getUser()
        return user.has_role(self.admin_roles, self)

    ## @brief check, if a user is banned from this chat
    #  @return bool True, if user is banned, otherwise False
    def isBanned(self, REQUEST = None):
        """ Check, if a user is banned.  """
        #ip_address = self.getIp(REQUEST)
        session=REQUEST.SESSION
        user_properties=session.get('user_properties')
        if user_properties:
            chat_uid=user_properties.get('chat_room')
        else:
            chat_uid=None

        # Existing cookie
        if BanStrategy.COOKIE in self.banStrategy and REQUEST.get('tudchat_is_banned') == 'true':
            return True

        """
        # Check by IP address in all chat rooms
        if BanStrategy.IP in self.banStrategy:
            for chat_uid in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_uid]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return True
        """

        if not session.get('user_properties'):
            return False

        # Is in ban list? Add cookie
        if BanStrategy.COOKIE in self.banStrategy and chat_uid and user_properties.get('name') in self.chat_rooms[chat_uid]['banned_chat_users'].keys():
            REQUEST.RESPONSE.setCookie('tudchat_is_banned', 'true', expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            REQUEST.RESPONSE.setCookie('tudchat_ban_reason', self.chat_rooms[chat_uid]['banned_chat_users'][user_properties.get('name')].get('reason'), expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            # Free that username to be used by others
            if not BanStrategy.IP in self.banStrategy:
                del self.chat_rooms[chat_uid]['banned_chat_users'][user_properties.get('name')]
            return True

        return False

    ## @brief tell the client the reason for the ban, if the client was banned
    #  @return str ban reason
    def getBanReason(self, REQUEST = None):
        """ Helper method to get ban reason """
        #ip_address = self.getIp(REQUEST)

        if BanStrategy.COOKIE in self.banStrategy:
            # Retrieve information from given cookies or just recently set cookies
            tudchat_is_banned = REQUEST.get('tudchat_is_banned') or (REQUEST.RESPONSE.cookies.get('tudchat_is_banned') and REQUEST.RESPONSE.cookies.get('tudchat_is_banned')['value'])
            tudchat_ban_reason = REQUEST.get('tudchat_ban_reason') or (REQUEST.RESPONSE.cookies.get('tudchat_ban_reason') and REQUEST.RESPONSE.cookies.get('tudchat_ban_reason')['value'])

            if tudchat_is_banned == 'true':
                return tudchat_ban_reason

        """
        if BanStrategy.IP in self.banStrategy:
            # Check by IP-Address in all chat rooms
            for chat_uid in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_uid]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return banEntry[banEntry.keys()[0]].get('reason')
            return 'Not banned'
        """
        return

    ## @brief this function returns information about the chat session of the requesting user
    #  @return dict with the following info: id,name,description,password,max_users,start,end,active
    def getChatInfo(self, REQUEST = None):
        """ Return all information about requesting users chat session """
        if REQUEST:
            session=REQUEST.SESSION
            user_properties=session.get('user_properties')
            if user_properties:
                chat_uid=user_properties.get('chat_room')
                session_info = self.chat_storage.getChatSession(chat_uid)
                session_info['start'] = session_info['start'].strftime('%d.%m.%Y, %H:%M Uhr')
                session_info['end'] = session_info['end'].strftime('%d.%m.%Y, %H:%M Uhr')
                return session_info
        return None

    ##########################################################################
    # Chat Session Management
    ##########################################################################

    ## @brief this function creates a chat session
    #  @param name str name of the chat session
    #  @param description str description of the chat session
    #  @param start str start time of the chat session (clients can't enter the chat before)
    #  @param end str end time of the chat session (Clients can't enter the chat after this time. All connected clients will be kicked after this time.)
    #  @param password str password to enter the chat room
    #  @param max_users int user limit for this chat room
    def createChatSession(self, name, description, start, end, password = None, max_users = None, REQUEST = None):
        """ Create a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.createChatSession(name, description, start, end, password, max_users)
        return True

    ## @brief this function modifies an existing chat session
    #  @param chat_uid int id of the chat which would be modified
    #  @param name str new name of the chat session
    #  @param description str new description of the chat session
    #  @param start str new start time of the chat session (clients can't enter the chat before)
    #  @param end str new end time of the chat session (Clients can't enter the chat after this time. All connected clients will be kicked after this time.)
    #  @param password str new password to enter the chat room
    #  @param max_users int new user limit for this chat room
    def editChatSession(self, chat_uid, name, description, start, end, password = None, max_users = None, REQUEST = None):
        """ Create a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.editChatSession(chat_uid, name, description, start, end, password, max_users)
        return True

    ## @brief this function deletes an existing chat session
    #  @param chat_uid int id of the chat which would be deleted
    def deleteChatSession(self, chat_uid, REQUEST = None):
        """ Delete a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.deleteChatSession(chat_uid)
        self.chat_storage.deleteActions(chat_uid)
        try:
            del self.chat_rooms[chat_uid]
        except:
            pass
        return True

    ## @brief this function generates a list of all existing chat sessions for this chat_content instance
    #  @return list of dictionaries, the following information are in every dict: id,name,description,password,max_users,start,end,status
    def getAllChatSessions(self, REQUEST = None):
        """ Get a list of all active, planned and closed chat sessions with their current state. """
        if not self.isAdmin(REQUEST):
            return

        result = []
        for x in self.chat_storage.getAllChatSessions():
            x['status'] = (x['start'] > DateTime().timeTime() and 'geplant') or (x['end'] < DateTime().timeTime() and 'abgelaufen') or 'aktiv'
            x['active'] = x['status'] == 'aktiv'
            result.append(x)

        return result

    ## @brief this function generates a list of all chat sessions which were active and planned
    #  @return list of dictionaries, the following information are in every dict: id,name,description,password,max_users,start,end
    def getChatSessions(self, REQUEST = None):
        """ Get a list of all active and planned chat sessions. This excludes closed ones. """
        if not self.isAdmin(REQUEST):
            return
        return self.chat_storage.getChatSessions()

    ## @brief this function generates a list of all chat sessions which were active
    #  @return list of dictionaries, the following information are in every dict: id,name,description,password,max_users,start,end
    def getActiveChatSessions(self, REQUEST = None):
        """ Get a list of all active chat sessions. """
        if self.chat_storage:
            return self.chat_storage.getActiveChatSessions()
        else:
            return None

    ## @brief this function generates a list of all chat sessions which were planned
    #  @return list of dictionaries, the following information are in every dict: id,name,start,end
    def getNextChatSessions(self, REQUEST = None):
        """ Get the next chat session, which will start. """
        if self.chat_storage:
            return self.chat_storage.getNextChatSessions()
        else:
            return None

    ## @brief this function returns information about a specific chat session
    #  @param chat_uid int id of the specific chat session
    #  @return dict with the following information: id,name,description,password,max_users,start,end,active
    def getChatSessionInfo(self, chat_uid, REQUEST = None):
        """ Get all information about a specific chat_session."""
        if not self.isAdmin(REQUEST):
            return
        session_info = self.chat_storage.getChatSession(chat_uid)
        session_info['start'] = session_info['start'].strftime('%d.%m.%Y, %H:%M Uhr')
        session_info['end'] = session_info['end'].strftime('%d.%m.%Y, %H:%M Uhr')
        return session_info

    ## @brief this function obfuscates user names of closed unlocked chat sessions and locks these chat sessions
    #  @return int count of locked chat sessions
    def lockClosedChatSessions(self):
        """
        Locks closed unlocked chat sessions and obfuscates user names of message senders and in messages.
        Only closed unlocked chat sessions that are closed for more than five minutes will be processed.
        
        """
        if not self.chat_storage:
            return 0
        
        chats = self.chat_storage.getClosedUnlockedChatSessions()
        now = DateTime().timeTime()
        locked = 0
        
        for chat in chats:
            #lock only chat sessions that are closed for more than five minutes
            if chat['end'] < now - 300:
                users = [user['user'] for user in self.chat_storage.getUsersBySessionId(chat['id'])]
                #replace long user names before short user names
                #this is import for user names that containing other user names (for example: "Max" and "Max Mustermann")
                users.sort(cmp = lambda a, b: len(a)-len(b), reverse = True)
                actions = self.chat_storage.getRawActionContents(chat['id'])
                i = 0
                
                #obfuscate user names
                for user in users:
                    old_name = user
                    
                    i += 1
                    new_name = "Benutzer "+str(i)
                    while new_name in users:
                        i += 1
                        new_name = "Benutzer "+str(i)
                    
                    self.chat_storage.updateUserName(chat['id'], old_name, new_name)
                    
                    old_name = re.compile(re.escape(old_name), re.IGNORECASE)
                    for action in actions:
                        action['content'] = old_name.sub(new_name, action['content'])
                
                for action in actions:
                    self.chat_storage.updateActionContent(action['id'], action['content'])
                
                self.chat_storage.lockChatSession(chat['id'])
                locked += 1
        
        return locked

    ## @brief this function returns all chat messages about a specific chat session
    #  @param chat_uid int id of the specific chat session
    #  @return list of dictionaries, the following information are in every dict: id, action, date, user, message, target, a_action, a_name
    def getLogs(self, chat_uid, REQUEST = None):
        """ Retrieve the whole and fully parsed chat log """
        if not self.isAdmin(REQUEST):
            return
        return self.chat_storage.getActions(chat_uid, 0, 0)[:-1]

    ##########################################################################
    # Form Handler
    ##########################################################################

    ## @brief this function is called from the chat session form to validate the input fields before creating or modifying chat sessions
    #  @param title str title of the chat session
    #  @param description str description of the chat session
    #  @param start_date time start date of the chat session
    #  @param end_date time end date of the chat session
    #  @param password str password of the chat session
    #  @param max_users int user limit of the chat session
    #  @param chat_uid int only used to modify an existing chat session
    def addSessionSubmit(self, title, description, start_date, end_date, password, max_users, chat_uid = None, REQUEST = None):
        """ Form Handler for adding or edit a session """

        errors = {}

        if not title:
            errors['title'] = "Pflichtfeld. Bitte geben Sie den Titel an."

        datetime_pattern = re.compile("(\d{2})\.(\d{2})\.(\d{4}), (\d{2}):(\d{2}) Uhr")

        match = datetime_pattern.match(start_date)
        sd = None
        if match:
            day, month, year, hours, minutes = [int(data) for data in match.groups()]
            try:
                sd = DateTime(year, month, day, hours, minutes)
            except DateTime.DateTimeError:
                errors['start_date'] = "Falsches Beginn-Datum! Bitte korrigieren Sie Ihre Eingabe."
        else:
            errors['start_date'] = "Falsches Beginn-Datum! Bitte korrigieren Sie Ihre Eingabe."

        match = datetime_pattern.match(end_date)
        ed = None
        if match:
            day, month, year, hours, minutes = [int(data) for data in match.groups()]
            try:
                ed = DateTime(year, month, day, hours, minutes)
            except Exception:
                errors['end_date'] = "Falsches Ende-Datum! Bitte korrigieren Sie Ihre Eingabe."
        else:
            errors['end_date'] = "Falsches Ende-Datum! Bitte korrigieren Sie Ihre Eingabe."

        if sd != None and ed != None and sd > ed:
            errors['start_date'] = "Beginn-Datum ist nach Ende-Datum! Bitte korrigierne Sie Ihre Eingabe."

        if len(password)>30:
            errors['password'] = "Das Passwort darf maximal 30 Zeichen lang sein."

        try:
            if max_users:
                int(max_users)
        except:
            errors['max_users'] = "Die maximale Benutzeranzahl darf nur Zahlen enthalten oder muss leer sein."
        if max_users and int(max_users)<0:
            errors['max_users'] = "Die maximale Benutzeranzahl darf nicht negativ sein."


        REQUEST['errors'] = errors

        if not errors:
            if chat_uid:
                success = self.editChatSession(chat_uid, title, description, sd, ed, password or None, max_users or None, REQUEST)
            else:
                success = self.createChatSession(title, description, sd, ed, password or None, max_users or None, REQUEST)
            if success == False:
                errors['database'] = 'Fehler in der Datenbank.'

        if not errors:
            REQUEST['portal_status_message'] = 'Änderungen wurden gespeichert.'
        else:
            REQUEST['portal_status_message'] = 'Bitte korrigieren Sie die angezeigten Fehler.'

        if chat_uid:
            return self.edit_session(request=REQUEST)
        else:
            return self.add_session(request=REQUEST)

    ## @brief this function deletes existing chat session
    #  @param REQUEST request contains a list named "delete" with the chat room ids to delete
    def editSessionsSubmit(self, REQUEST):
        """ Form Handler for editing sessions """

        delete = REQUEST.get('delete',[])

        for id in delete:
            self.deleteChatSession(id)

        if delete:
            REQUEST['portal_status_message'] = 'Chat-Sitzungen wurden gelöscht.'
        else:
            REQUEST['portal_status_message'] = 'Es wurden <em>keine</em> Chat-Sitzungen gelöscht.'

        return self.edit_sessions(request=REQUEST)

    ##########################################################################
    #  User Management
    ##########################################################################

    security.declarePrivate('addUser')
    ## @brief this function adds an user to an existing chat session
    #  @param user str user name to add
    #  @param chat_uid int id of the room, where the user want to join
    #  @param is_admin bool true if the user has admin privileges
    #  @return bool true on success or false if the user is already in the room
    def addUser(self, user, chat_uid, is_admin):
        """ Add yourself to the user list. """
        if not self.chat_rooms[chat_uid]['chat_users'].has_key(user):
            self.chat_rooms[chat_uid]['chat_users'][user] = {'date': DateTime().timeTime(), 'last_message_sent' : 0, 'is_admin' : is_admin }
            self._p_changed = 1
            return True
        return False

    security.declarePrivate('hasUser')
    ## @brief this function checks if an user is in a specific room
    #  @param user str user name to check
    #  @param chat_uid int id of the room to check
    #  @return bool true if the user in the room, otherwise false
    def hasUser(self, user, chat_uid):
        """ Check for the existence of a user. """
        return user in self.chat_rooms[chat_uid]['chat_users'].keys()

    security.declarePrivate('removeUser')
    ## @brief this function removes an user from a specific room
    #  @param user str user name to remove
    #  @param chat_uid int id of the room where the user is inside
    def removeUser(self, user, chat_uid):
        """ Remove a single user by its name. """
        if self.chat_rooms[chat_uid]['chat_users'].has_key(user):
            del self.chat_rooms[chat_uid]['chat_users'][user]
            self._p_changed = 1
        #remove chatroom if there no real entries
        if len(self.chat_rooms[chat_uid]['chat_users'])==0 and len(self.chat_rooms[chat_uid]['kicked_chat_users'])==0 and len(self.chat_rooms[chat_uid]['banned_chat_users'])==0:
            del self.chat_rooms[chat_uid]

    security.declarePrivate('clearUsers')
    ## @brief this function removes all users from a specific room
    #  @param chat_uid int id of the room
    def clearUsers(self, chat_uid):
        """ Clear the user list. """
        self.chat_rooms[chat_uid]['chat_users'].clear()
        self._p_changed = 1

    security.declarePrivate('getUsers')
    ## @brief this function returns all users of a specific room
    #  @param chat_uid int id of the room
    #  @return list users of the chat room
    def getUsers(self, chat_uid):
        """ Return the list of all user names in a chat room. """
        return self.chat_rooms[chat_uid]['chat_users'].keys()

    security.declarePrivate('addBannedUser')
    ## @brief this function returns all users of a specific room
    #  @param user str user name to be banned
    #  @param reason str reason for banning the user
    #  @param chat_uid int id of the room where the user is inside
    #  @return bool true if the user was banned succesfully, otherwise false
    def addBannedUser(self, user, reason, chat_uid):
        """ Ban a user with a given reason. """
        if not user in self.chat_rooms[chat_uid]['banned_chat_users'].keys() and user in self.chat_rooms[chat_uid]['chat_users'].keys():
            self.chat_rooms[chat_uid]['banned_chat_users'][user] = { 'reason': reason }
            self.removeUser(user, chat_uid)
            return True
        return False

    security.declarePrivate('removeBannedUser')
    ## @brief this function removes a user from the list of banned users
    #  @param user str user name to remove from the banned user list
    #  @param chat_uid int id of the room where the user was banned
    #  @return bool true if the user was removed from the banned user list, otherwise false (the user wasn't in the list of banned users of the given room)
    def removeBannedUser(self, user, chat_uid):
        """ Unban a user. """

        if user in self.chat_rooms[chat_uid]['banned_chat_users'].keys():
            del self.chat_rooms[chat_uid]['banned_chat_users'][user]
            return True
        return False

    security.declarePrivate('addWarnedUser')
    ## @brief this function stores a warning message for a given user in a given chat room
    #  @param user str user name to be warned
    #  @param warning str message which would send to the user
    #  @param chat_uid int id of the room where the user is inside
    #  @return bool true if the user was found in the given room and if there is no other warning message for the user, otherwise false
    def addWarnedUser(self, user, warning, chat_uid):
        """ Warn a user with a given text.
            The user gets the message after calling the getActions method. """
        if not user in self.chat_rooms[chat_uid]['warned_chat_users'].keys() and user in self.chat_rooms[chat_uid]['chat_users'].keys():
            self.chat_rooms[chat_uid]['warned_chat_users'][user] = { 'warning': warning }
            return True
        return False

    security.declarePrivate('removeWarnedUser')
    ## @brief this function removes a warning message for a given user in a given chat room
    #  @param user str user name of the warned user
    #  @param chat_uid int id of the room where the user is inside
    #  @return bool true if the warning message was found in the given room, otherwise false
    def removeWarnedUser(self, user, chat_uid):
        """ Remove the warning message for a given user.
            This is usually done in the message sending process. """

        if user in self.chat_rooms[chat_uid]['warned_chat_users'].keys():
            del self.chat_rooms[chat_uid]['warned_chat_users'][user]
            return True
        return False

    ## @brief this function removes all banned users in all chat rooms (this function is only for debugging)
    def clearBannedUsers(self):
        """ Clear the banned user list of all chat rooms. """
        for chat_uid in self.chat_rooms.keys():
            self.chat_rooms[chat_uid]['banned_chat_users'].clear()
        self._p_changed = 1

    ###################################
    # Exposed methods
    ###################################

    security.declareProtected(CMFCorePermissions.View, "registerMe")
    ## @brief this function registers an user to a chat room
    #  @param user str proposed name of the user
    #  @param chatroom int id of the room where the user want to enter
    #  @param password str optional password of the room
    #  @return bool true if the user was successfully added to the room, otherwise false
    def registerMe(self, user, chatroom, agreement="false", password=None, REQUEST = None):
        """ Register a user to a chat room.
            Before the user was added, this function will check the pre-conditions to enter the room (password, user limit, user name restrictions, banned users, room state)
            If the room does not exist in the room list, it will be created here. """
        REQUEST.SESSION.set('user_properties', None)
        chat_session = self.chat_storage.getChatSession(chatroom)
        user = user.strip()

        if agreement == "false":
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ohne Zustimmung zum Datenschutzhinweis kann der Chat nicht betreten werden.'}})
        if chat_session['password'] and chat_session['password'] != password:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das eingegebene Passwort ist nicht korrekt.'}})
        if chat_session['max_users'] and self.chat_rooms.get(chatroom) and chat_session['max_users'] <= len(self.chat_rooms[chatroom]['chat_users']):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das Benutzerlimit für diese Chat-Session ist bereits erreicht.'}})
        if len(re.findall(r"[a-zA-ZäöüÄÖÜ]",user))<3:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername muss mindestens drei Buchstaben enthalten.'}})
        if len(user) < 3:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu kurz. (Er muss mindestens 3 Zeichen lang sein.)'}})
        if len(user) > 20:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu lang. (Er darf maximal 20 Zeichen lang sein.)'}})
        if not self.checkUTF8(user):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername enthält ungültige Zeichen. (Es sind nur UTF-8-Zeichen erlaubt.)'}})
        if not chat_session['active']:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Der gewählte Chat-Raum ist zurzeit nicht aktiv.'}})
        if self.chat_rooms.has_key(chatroom) and user.lower() in [chat_user.lower() for chat_user in self.chat_rooms[chatroom]['chat_users'].keys()]:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Der Benutzername ist bereits belegt.'}})
        if self.isBanned(REQUEST):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Sie wurden dauerhaft des Chats verwiesen. <br/> <br/> Grund: ' + str(self.getBanReason(REQUEST))}})

        session = REQUEST.SESSION
        start_action_id = self.chat_storage.getLastChatAction(chatroom)
        self.checkForInactiveUsers()

        # Clean username
        user = self.html_escape(user)

        if chatroom not in self.chat_rooms.keys(): # TODO Check hinzufügen, ob der Raum verfügbar ist.
            self.chat_rooms[chatroom] = {'chat_users'  : {},
                                    'kicked_chat_users' : [],
                                    'warned_chat_users': {},
                                    'banned_chat_users' : {}
                                    }

        if not self.isBanned(REQUEST) and user and self.addUser(user, chatroom, self.isAdmin(REQUEST)):
            session.set('user_properties', {'name': user,
                                            'start_action' : start_action_id,
                                            'last_action': start_action_id,
                                            'user_list': [],
                                            'chat_room': chatroom,
                                            'chat_room_check': 0
                                            })
            return simplejson.dumps(True)
        return simplejson.dumps(False)

    security.declareProtected(CMFCorePermissions.View, "logout")
    ## @brief this function removes an user from a chat room
    #  @return bool true if the user was successfully removed from the room, otherwise false
    def logout(self, REQUEST = None):
        """ Logout yourself.
            The associated room will be retrieved from the user session. """
        session=REQUEST.SESSION
        if session.get('user_properties'):
            user = session.get('user_properties').get('name')
            chat_uid = session.get('user_properties').get('chat_room')
            session.set('user_properties', None)
            session.invalidate()

            self.removeUser(user, chat_uid)
        return simplejson.dumps(True)

    ###################################
    # Utility methods
    ###################################

    security.declarePrivate('userHeartbeat')
    ## @brief this function tells the system, that the user is active
    def userHeartbeat(self, REQUEST):
        """ Updates the activity timestamp of the user.
            The user information will be retrieved from the request """
        session = REQUEST.SESSION
        user_properties = session.get('user_properties')
        name = user_properties.get('name')
        chat_uid = user_properties.get('chat_room')
        self.chat_rooms[chat_uid]['chat_users'][name]['date'] = DateTime().timeTime()

    security.declarePrivate('checkForInactiveUsers')
    ## @brief this function removes users who doesn't call the heart beat method for a defined timeout time
    def checkForInactiveUsers(self):
        """ Check for inactive users and kick them. """
        now = DateTime().timeTime()
        if now - self.timestamps.setdefault('userHeartbeat', 0) > 5: # Perform this check every 5 seconds
            for chat_uid in self.chat_rooms.keys():
                for user in self.chat_rooms[chat_uid]['chat_users'].keys():
                    if now - self.chat_rooms[chat_uid]['chat_users'][user].get('date') > self.timeout: # timeout
                        self.removeUser(user, chat_uid)
            self.timestamps['userHeartbeat'] = now

    ##########################################################################
    # Public Message / Action methods
    ##########################################################################

    ## @brief this function adds a message to the chat room of the user
    #  @param message str message to send
    def sendMessage(self, message, REQUEST = None):
        """ Send a message to the chat room of the user.
            The chat chat room will be retrieved from the request.
            If the user sends to many messages in a pre-defined interval, the message will be ignored.
            The maximum message length will be also checked (if the message length is to high, it will be truncated). """

        if not self.isRegistered(REQUEST):
            return

        session=REQUEST.SESSION

        now = DateTime().timeTime()
        chat_uid = session.get('user_properties').get('chat_room')
        user = session.get('user_properties').get('name')

        self.userHeartbeat(REQUEST)
        if not message:
            return
        if (now - self.chat_rooms[chat_uid]['chat_users'][user].get('last_message_sent')) < self.blockTime: # Block spamming messages
            return
        else:
            self.chat_rooms[chat_uid]['chat_users'][user]['last_message_sent'] = now

        #filter invalid utf8
        if not self.checkUTF8(message):
            return

        if self.maxMessageLength:
            message = message[:self.maxMessageLength]
        msgid = self.chat_storage.sendAction(chat_uid = chat_uid,
                            user = user,
                            action = self.isAdmin(REQUEST) and 'mod_add_message' or 'user_add_message',
                            content = self.html_escape(message))

    ## @brief this function edits an already sent message
    #  @param message int id of the message to edit
    #  @param message str text of the new message
    def editMessage(self, message_id, message, REQUEST = None):
        """ Edit a message.
            This action can only performed by admins. """
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        self.userHeartbeat(REQUEST)
        if not message:
            return
        self.chat_storage.sendAction(chat_uid = session.get('user_properties').get('chat_room'),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_edit_message',
                                    content = self.html_escape(message),
                                    target = message_id)

    ## @brief this function deletes an already sent message
    #  @param message int id of the message to delete
    def deleteMessage(self, message_id, REQUEST = None):
        """ Delete a message by its id.
            This action can only performed by admins. """
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        self.userHeartbeat(REQUEST)

        self.chat_storage.sendAction(chat_uid = session.get('user_properties').get('chat_room'),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_delete_message',
                                    target = message_id)

    ## @brief this function returns all updates specific to the calling user since the last time this method was called
    #  @return dict special JSON dictonary that contains either a special state or message and user updates
    def getActions(self, REQUEST = None):
        """ This function returns all actions specific to the calling user since the last function call.
            Also performs several checks. """
        session=REQUEST.SESSION

        if self.isBanned(REQUEST):
            self.logout(REQUEST)
            return simplejson.dumps({'status': {'code': UserStatus.BANNED, 'message': self.getBanReason(REQUEST)}})

        if not self.isRegistered(REQUEST):
            return simplejson.dumps({'status': {'code': UserStatus.NOT_AUTHORIZED, 'message': 'NOT AUTHORIZED'}})


        user_properties = session.get('user_properties')
        old_user_properties = user_properties.copy()
        user = user_properties.get('name')
        chat_uid = user_properties.get('chat_room')

        if user in self.chat_rooms[chat_uid]['warned_chat_users']:
            warning = self.chat_rooms[chat_uid]['warned_chat_users'][user]['warning']
            self.removeWarnedUser(user, chat_uid)
            return simplejson.dumps({'status': {'code': UserStatus.WARNED, 'message': warning}})

        if user in self.chat_rooms[chat_uid]['kicked_chat_users']:
            self.chat_rooms[chat_uid]['kicked_chat_users'].remove(user)
            self.logout(REQUEST)
            return simplejson.dumps({'status': {'code': UserStatus.KICKED, 'message': ''}})

        self.userHeartbeat(REQUEST)
        self.checkForInactiveUsers()

        #check if the chat is still active
        now = DateTime().timeTime()
        if now - user_properties.get('chat_room_check') > 60: # Perform this check every 60 seconds
            user_properties['chat_room_check'] = now
            chat_session = self.chat_storage.getChatSession(chat_uid)
            end_time = DateTime(chat_session['end'])
            if not chat_session['active']:
                self.removeUser(user, chat_uid)
                session.set('user_properties', user_properties)
                return simplejson.dumps({'status': {'code': UserStatus.KICKED, 'message': 'Die Chat-Sitzung ist abgelaufen.'}})
            if not user_properties.get('chatInactiveWarning') and end_time.timeTime() - now < 300: # warn user 5 minutes before the chat will close
                user_properties['chatInactiveWarning'] = True
                session.set('user_properties', user_properties)
                return simplejson.dumps({'status': {'code': UserStatus.CHAT_WARN, 'message': 'Die Chat-Sitzung läuft in weniger als 5 Minuten ab.'}})

        # Lookup last action
        start_action = user_properties.get('start_action')
        last_action = user_properties.get('last_action')
        #limit message count for users who get normally all messages since start action
        if start_action==last_action:
            limit = 30
        else:
            limit = 0
        list_actions = self.chat_storage.getActions(chat_uid = chat_uid, last_action = last_action, start_action = start_action, limit = limit)
        # build a list of extra attributes
        for i in range(len(list_actions)):
            list_actions[i]['attr'] = []
            if list_actions[i]['a_action'] != '':
                list_actions[i]['attr'].append({'a_action':list_actions[i]['a_action'], 'a_name':list_actions[i]['a_name']})
            if list_actions[i]['action'] == 'mod_add_message' or list_actions[i]['u_action'] == 'mod_add_message':
                list_actions[i]['attr'].append({'admin_message':True})

        return_dict = {
                        'messages':
                            {
                                'new': [ {  'id': action['id'],
                                            'date': self.showDate and action['date'].strftime(self.chatDateFormat) or "",
                                            'name': action['user'],
                                            'message': action['message'],
                                            'attributes': action['attr'] } for action in list_actions if (action['action'] == "user_add_message" or action['action'] == "mod_add_message")],
                                'to_delete': [ { 'id': action['target'],
                                                  'date': self.showDate and action['date'].strftime(self.chatDateFormat) or "",
                                                  'name': action['user'],
                                                  'attributes': action['attr'] } for action in list_actions if action['action'] == "mod_delete_message" ],
                                'to_edit': [ {  'id': action['target'],
                                                'date': self.showDate and action['date'].strftime(self.chatDateFormat) or "",
                                                'name': action['user'],
                                                'message': action['message'],
                                                'attributes': action['attr'] } for action in list_actions if action['action'] == "mod_edit_message" ],
                            },
                        'users':
                            {
                                'new':       [ { 'name' : person,
                                                 'is_admin' :  self.chat_rooms[chat_uid]['chat_users'][person]['is_admin']} for person in self.getUsers(chat_uid) if person not in session.get('user_properties').get('user_list')],
                                'to_delete': [ person for person in session.get('user_properties').get('user_list') if person not in self.getUsers(chat_uid) ]
                            },
                        'status':
                            {
                                'code' : UserStatus.OK,
                                'message': 'OK'
                            }
                      }

        # Update last action
        if len(list_actions) > 1:
            user_properties['last_action'] = list_actions[len(list_actions)-1].get('id')
        # Update persons
        user_properties['user_list'] = self.getUsers(chat_uid)

        # Update session only if necessary
        if old_user_properties['last_action'] != user_properties['last_action'] or old_user_properties['user_list'] != user_properties['user_list'] or old_user_properties['chat_room_check'] != user_properties['chat_room_check']:
            session.set('user_properties', user_properties)

        return simplejson.dumps(return_dict)

    ## @brief this function removes an user from the chat room where the admin is inside
    #  @param user str name of the user to kick
    def kickUser(self, user, REQUEST = None):
        """ Kick a user. """
        user = self.html_escape(user)
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        # You can not kick yourself
        if session.get('user_properties').get('name') == user:
            return

        self.userHeartbeat(REQUEST)
        self.chat_rooms[session.get('user_properties').get('chat_room')]['kicked_chat_users'].append(user)

    ## @brief this function warns an user in the chat room where the admin is inside
    #  @param user str name of the user to warn
    #  @param warning str message text which will be send to the user
    #  @return bool true if the warning message is stored otherwise false
    def warnUser(self, user, warning = "", REQUEST = None):
        """ Warn a user. """
        user = self.html_escape(user)
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        # You can not warn yourself
        if session.get('user_properties').get('name') == user:
            return

        self.userHeartbeat(REQUEST)

        chat_uid = session.get('user_properties').get('chat_room')

        return simplejson.dumps(self.addWarnedUser(user, warning, chat_uid))

    ## @brief this function bans an user from the chat room where the admin is inside
    #  @param user str name of the user to ban
    #  @param reason str reason text which will be displayed additionally to the ban
    #  @return bool true if the ban is stored otherwise false
    def banUser(self, user, reason = "", REQUEST = None):
        """ Ban a user. """
        user = self.html_escape(user)
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        # You can not ban yourself
        if session.get('user_properties').get('name') == user:
            return

        self.userHeartbeat(REQUEST)

        chat_uid = session.get('user_properties').get('chat_room')

        return simplejson.dumps(self.addBannedUser(user, reason, chat_uid))

    ##########################################################################
    # Debugging
    ##########################################################################

    security.declareProtected(CMFCorePermissions.View, "status")
    ## @brief this function returns status information about all chat rooms and the session of the calling user
    #  @param asJSON bool set to true if you want JSON formatted response
    #  @return str status information in JSON or non-JSON format
    def status(self, REQUEST, asJSON = False):
        """ Get overall status. """
        self.checkForInactiveUsers()
        d = {
            'chat_rooms': self.chat_rooms,
            'session': REQUEST.SESSION.get('user_properties'),
            'isRegistered': self.isRegistered(REQUEST),
            'isAdmin': self.isAdmin(REQUEST),
            'db_prefixes': self.own_database_prefixes
        }
        if asJSON:
            return simplejson.dumps(d)
        else:
            return d

    security.declareProtected(CMFCorePermissions.View, "resetLastAction")
    ## @brief this function resets the last action to the start action of the user's chat room
    def resetLastAction(self, REQUEST = None):
        """ Reset last_action to get all messages from the beginning. """
        session = REQUEST.SESSION
        if session.get('user_properties'):
            user_properties = session.get('user_properties')
            user_properties['last_action'] = user_properties.get('start_action')
            user_properties['user_list'] = []
            session.set('user_properties', user_properties)

    security.declareProtected(CMFCorePermissions.View, "addPrefix")
    ## @brief this function adds a prefix to a given database
    #  @param db str database connector id
    #  @param prefix str prefix of the database
    def addPrefix(self, db, prefix, REQUEST = None):
        """ Add the prefix to the list of own db prefixes. """
        if not self.isAdmin(REQUEST):
            return

        already_exist = False
        if self.own_database_prefixes.get(db):
            already_exist = prefix in self.own_database_prefixes[db]
            self.own_database_prefixes[db].add(prefix)
        else:
            self.own_database_prefixes[db] = set([prefix])

        self._p_changed = 1

        return str(not already_exist)

    security.declareProtected(CMFCorePermissions.View, "myRequest")
    def myRequest(self, REQUEST = None):
        """ reset last_action to get all messages from the beginning """
        return REQUEST

registerType(TUDChat, PROJECTNAME)
