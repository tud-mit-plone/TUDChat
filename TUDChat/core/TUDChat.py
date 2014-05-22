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
from AccessControl import ClassSecurityInfo
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
    timestamps               = {} # collection of timestamps to call methods in certain intervalls
    chat_rooms               = {} # chatroom container with userlist, kicked_users, banned_users and timestamps
    admin_roles              = ['Admin','ChatModerator']
    own_database_prefixes    = {} # for each connector_id the own prefixes in this database
    htmlspecialchars         = {'"':'&quot;', '\'':'&#039;', '<':'&lt;', '>':'&gt;'} # char "&" is in function included

    # Actions
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

    def __init__(self, id):
        self.id = id
        logger.info("Initialised 'TUDChat Content'...")
        self.chat_storage = None
        self.own_database_prefixes = self.own_database_prefixes


    security.declarePrivate('_post_init')
    def _post_init(self):
        """
        _post_init(self) => Post-init method (that is, method that is called AFTER the class has been set into the ZODB)
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

    security.declarePublic("show_id")
    def show_id(self,):
        """
        Determine whether to show an id in an edit form

        show_id.py used to be a Python Script, but was removed from Plone 2.5,
        so we have to add the method here for compatability
        """

        if getToolByName(self, 'plone_utils').isIDAutoGenerated(self.REQUEST.get('id', None) or self.getId()):
            return not (self.portal_factory.isTemporary(self) or self.CreationDate() == self.ModificationDate())
        return

    security.declarePublic("getIp")
    def getIp(self, REQUEST): # see: http://dev.menttes.com/collective.developermanual/serving/http_request_and_response.html#request-client-ip
        """  Extract the client IP address from the HTTP request in proxy compatible way.

        @return: IP address as a string or None if not available
        """

        if "HTTP_X_FORWARDED_FOR" in REQUEST.environ:
            # Virtual host
            ip = REQUEST.environ["HTTP_X_FORWARDED_FOR"]
        elif "HTTP_HOST" in REQUEST.environ:
            # Non-virtualhost
            ip = REQUEST.environ["REMOTE_ADDR"]
        else:
            # Unit test code?
            ip = None

        return ip

    def html_escape(self, text):
        """ escape html chars """
        tmptext = text.replace('&','&amp;')
        for key in self.htmlspecialchars:
            tmptext = tmptext.replace(key, self.htmlspecialchars[key])
        return tmptext

    security.declarePrivate('getDefaultPloneSiteCharset')
    def getDefaultPloneSiteCharset(self):
        """ """
        return self.portal_properties.site_properties.getProperty('default_charset')

    ##########################################################################
    # Access management
    ##########################################################################

    def isRegistered(self, REQUEST = None):
        """ """
        session=REQUEST.SESSION

        if session.get('user_properties'):
            chat_uid = session.get('user_properties').get('chat_room')
            if chat_uid in self.chat_rooms.keys():
                if self.hasUser(session.get('user_properties').get('name'), chat_uid):
                    return True
            else:
                session.clear()
        return False

    def isAdmin(self, REQUEST = None):
        """ """

        member = getToolByName(self, 'portal_membership').getAuthenticatedMember()
        member_roles = list(member.getRoles())
        local_roles = list(self.get_local_roles_for_userid( userid=member.getId() ))

        for role in member_roles + local_roles:
            if role in self.admin_roles:
                return True
        return False

    def isBanned(self, REQUEST = None):
        """ Checks if you are banned  """
        ip_address = self.getIp(REQUEST)
        session=REQUEST.SESSION
        user_properties=session.get('user_properties')
        if user_properties:
            chat_uid=user_properties.get('chat_room')
        else:
            chat_uid=None

        # Existing cookie
        if BanStrategy.COOKIE in self.banStrategy and REQUEST.get('tudchat_is_banned') == 'true':
            return True

        # Check by IP-Address in all chat rooms
        if BanStrategy.IP in self.banStrategy:
            for chat_uid in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_uid]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return True

        if not session.get('user_properties'):
            return False

        # Is in ban-list? Add cookie
        if BanStrategy.COOKIE in self.banStrategy and chat_uid and user_properties.get('name') in self.chat_rooms[chat_uid]['banned_chat_users'].keys():
            REQUEST.RESPONSE.setCookie('tudchat_is_banned', 'true', expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            REQUEST.RESPONSE.setCookie('tudchat_ban_reason', self.chat_rooms[chat_uid]['banned_chat_users'][user_properties.get('name')].get('reason'), expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            # Free that username to be used by others
            if not BanStrategy.IP in self.banStrategy:
                del self.chat_rooms[chat_uid]['banned_chat_users'][user_properties.get('name')]
            return True

        return False

    def getBanReason(self, REQUEST = None):
        """ Helper method to get ban reason """
        ip_address = self.getIp(REQUEST)

        if BanStrategy.COOKIE in self.banStrategy:
            # Retrieve information from given cookies or just recently set cookies
            tudchat_is_banned = REQUEST.get('tudchat_is_banned') or (REQUEST.RESPONSE.cookies.get('tudchat_is_banned') and REQUEST.RESPONSE.cookies.get('tudchat_is_banned')['value'])
            tudchat_ban_reason = REQUEST.get('tudchat_ban_reason') or (REQUEST.RESPONSE.cookies.get('tudchat_ban_reason') and REQUEST.RESPONSE.cookies.get('tudchat_ban_reason')['value'])

            if tudchat_is_banned == 'true':
                return tudchat_ban_reason

        if BanStrategy.IP in self.banStrategy:
            # Check by IP-Address in all chat rooms
            for chat_uid in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_uid]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return banEntry[banEntry.keys()[0]].get('reason')
            return 'Not banned'
        return

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

    def createChatSession(self, name, description, start, end, password = None, max_users = None, REQUEST = None):
        """ Create a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.createChatSession(name, description, start, end, password, max_users)
        return True

    def editChatSession(self, chat_uid, name, description, start, end, password = None, max_users = None, REQUEST = None):
        """ Create a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.editChatSession(chat_uid, name, description, start, end, password, max_users)
        return True

    def deleteChatSession(self, chat_uid, REQUEST = None):
        """ Delete a chat session """
        if not self.isAdmin(REQUEST):
            return
        self.chat_storage.deleteChatSession(chat_uid)
        return True

    def closeChatSession(self, REQUEST = None):
        """ Close the current chat session """
        session = REQUEST.SESSION
        if not self.isAdmin(REQUEST):
            return
        self.sendAction(chat_uid = session.get('user_properties').get('chat_room'),
                                    user = session.get('user_properties').get('name'),
                                    action = "close_chat")

    def getAllChatSessions(self, REQUEST = None):
        """ get a list of all active, planned and closed chat sessions with there current state """
        if not self.isAdmin(REQUEST):
            return

        result = []
        for x in self.chat_storage.getAllChatSessions():
            x['status'] = (x['start'] > DateTime().timeTime() and 'geplant') or (x['end'] < DateTime().timeTime() and 'abgelaufen') or 'aktiv'
            result.append(x)

        return result

    def getChatSessions(self, REQUEST = None):
        """ get a list of all active and planned chat sessions """
        if not self.isAdmin(REQUEST):
            return
        return self.chat_storage.getChatSessions()

    def getActiveChatSessions(self, REQUEST = None):
        """ get a list of all active chat sessions """
        if self.chat_storage:
            return self.chat_storage.getActiveChatSessions()
        else:
            return None

    def getNextChatSessions(self, REQUEST = None):
        """ get the next chat session, which will start """
        if self.chat_storage:
            return self.chat_storage.getNextChatSessions()
        else:
            return None

    def getChatSessionInfo(self, chat_uid, REQUEST = None):
        """ get all information about a specific chat_session"""
        if not self.isAdmin(REQUEST):
            return
        session_info = self.chat_storage.getChatSession(chat_uid)
        session_info['start'] = session_info['start'].strftime('%d.%m.%Y, %H:%M Uhr')
        session_info['end'] = session_info['end'].strftime('%d.%m.%Y, %H:%M Uhr')
        return session_info

    def getLogs(self, chat_uid, REQUEST = None):
        """ Retrieve the whole and fully parsed chat log """
        if not self.isAdmin(REQUEST):
            return
        return self.chat_storage.getActions(chat_uid, 0, 0)[:-1]

    ##########################################################################
    # Form Handler
    ##########################################################################

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
    def addUser(self, user, ip, chat_uid, is_admin):
        """ Add yourself to the userlist """
        if not self.chat_rooms[chat_uid]['chat_users'].has_key(user):
            self.chat_rooms[chat_uid]['chat_users'][user] = {'ip_address': ip, 'date': DateTime().timeTime(), 'last_message_sent' : 0, 'is_admin' : is_admin }
            self._p_changed = 1
            return True
        return False

    security.declarePrivate('hasUser')
    def hasUser(self, user, chat_uid):
        """ Check for the existence of a user """
        return user in self.chat_rooms[chat_uid]['chat_users'].keys()

    security.declarePrivate('removeUser')
    def removeUser(self, user, chat_uid):
        """ Remove a single user by its name """
        if self.chat_rooms[chat_uid]['chat_users'].has_key(user):
            del self.chat_rooms[chat_uid]['chat_users'][user]
            self._p_changed = 1
        #remove chatroom if there no real entries
        if len(self.chat_rooms[chat_uid]['chat_users'])==0 and len(self.chat_rooms[chat_uid]['kicked_chat_users'])==0 and len(self.chat_rooms[chat_uid]['banned_chat_users'])==0:
            del self.chat_rooms[chat_uid]

    security.declarePrivate('clearUsers')
    def clearUsers(self, chat_uid):
        """ Clear the user list """
        self.chat_rooms[chat_uid]['chat_users'].clear()
        self._p_changed = 1

    security.declarePrivate('getUsers')
    def getUsers(self, chat_uid):
        """ Returns the list of users """
        return self.chat_rooms[chat_uid]['chat_users'].keys()

    security.declarePrivate('addBannedUser')
    def addBannedUser(self, user, ip, reason, chat_uid):
        """ Bans a user with a given reason """
        if not user in self.chat_rooms[chat_uid]['banned_chat_users'].keys() and user in self.chat_rooms[chat_uid]['chat_users'].keys():
            self.chat_rooms[chat_uid]['banned_chat_users'][user] = { 'reason': reason, 'ip_address': ip }
            self.removeUser(user, chat_uid)
            return True
        return False

    security.declarePrivate('removeBannedUser')
    def removeBannedUser(self, user, chat_uid):
        """ """

        if user in self.chat_rooms[chat_uid]['banned_chat_users'].keys():
            del self.chat_rooms[chat_uid]['banned_chat_users'][user]
            return True
        return False

    security.declarePrivate('addWarnedUser')
    def addWarnedUser(self, user, warning, chat_uid):
        """ Warn a user with a given text """
        if not user in self.chat_rooms[chat_uid]['warned_chat_users'].keys() and user in self.chat_rooms[chat_uid]['chat_users'].keys():
            self.chat_rooms[chat_uid]['warned_chat_users'][user] = { 'warning': warning }
            return True
        return False

    security.declarePrivate('removeWarnedUser')
    def removeWarnedUser(self, user, chat_uid):
        """ """

        if user in self.chat_rooms[chat_uid]['warned_chat_users'].keys():
            del self.chat_rooms[chat_uid]['warned_chat_users'][user]
            return True
        return False

    # debug
    def clearBannedUsers(self):
        """ Clear the banned user list """
        for chat_uid in self.chat_rooms.keys():
            self.chat_rooms[chat_uid]['banned_chat_users'].clear()
        self._p_changed = 1

    ###################################
    # Exposed methods
    ###################################

    security.declareProtected(CMFCorePermissions.View, "registerMe")
    def registerMe(self, user, chatroom, password=None, REQUEST = None):
        """ Register yourself """
        REQUEST.SESSION.set('user_properties', None)
        chat_session = self.chat_storage.getChatSession(chatroom)

        if chat_session['password'] and chat_session['password'] != password:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das eingegebene Passwort ist nicht korrekt.'}})
        if chat_session['max_users'] and self.chat_rooms.get(chatroom) and chat_session['max_users'] <= len(self.chat_rooms[chatroom]['chat_users']):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das Benutzerlimit für diese Chat-Session ist bereits erreicht.'}})
        if len(user) < 3:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu kurz. (Er muss mindestens 3 Zeichen lang sein.)'}})
        if len(user) > 20:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu lang. (Er darf maximal 20 Zeichen lang sein.)'}})
        if re.findall(r"[a-zA-Z]äöüÄÖÜ+",user):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername muss mindestens einen Buchstaben enthalten.'}})
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

        if not self.isBanned(REQUEST) and user and self.addUser(user, self.getIp(REQUEST), chatroom, self.isAdmin(REQUEST)):
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
    def logout(self, REQUEST = None):
        """ Logout yourself """
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
    def userHeartbeat(self, REQUEST):
        """ Updates the activity timestamp of each user """
        session = REQUEST.SESSION
        user_properties = session.get('user_properties')
        name = user_properties.get('name')
        chat_uid = user_properties.get('chat_room')
        self.chat_rooms[chat_uid]['chat_users'][name]['date'] = DateTime().timeTime()

    security.declarePrivate('checkForInactiveUsers')
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

    def sendMessage(self, message, REQUEST = None):
        """ Send a message """

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

        if self.maxMessageLength:
            message = message[:self.maxMessageLength]
        msgid = self.chat_storage.sendAction(chat_uid = chat_uid,
                            user = user,
                            action = self.isAdmin(REQUEST) and 'mod_add_message' or 'user_add_message',
                            content = self.html_escape(message))

    def editMessage(self, message_id, message, REQUEST = None):
        """ Edit a message """
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

    def deleteMessage(self, message_id, REQUEST = None):
        """ Delete a message by its id """
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        self.userHeartbeat(REQUEST)

        self.chat_storage.sendAction(chat_uid = session.get('user_properties').get('chat_room'),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_delete_message',
                                    target = message_id)

    def getActions(self, REQUEST = None):
        """ Get a list of new actions beginning from start_action.
            Also perform several checks. """
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
            end_time = DateTime(chat_session['end'].utcdatetime())
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
        list_actions = self.chat_storage.getActions(chat_uid = chat_uid, last_action = last_action, start_action = start_action)
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

    def kickUser(self, user, REQUEST = None):
        """ Kick a user """
        user = self.html_escape(user)
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        # You can not kick yourself
        if session.get('user_properties').get('name') == user:
            return

        self.userHeartbeat(REQUEST)
        self.chat_rooms[session.get('user_properties').get('chat_room')]['kicked_chat_users'].append(user)

    def warnUser(self, user, warning = "", REQUEST = None):
        """ Warn a user """
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

    def banUser(self, user, reason = "", REQUEST = None):
        """ Ban a user """
        user = self.html_escape(user)
        session=REQUEST.SESSION

        if not self.isAdmin(REQUEST):
            return
        # You can not ban yourself
        if session.get('user_properties').get('name') == user:
            return

        self.userHeartbeat(REQUEST)

        chat_uid = session.get('user_properties').get('chat_room')
        ip = self.chat_rooms[chat_uid]['chat_users'][user]['ip_address']

        return simplejson.dumps(self.addBannedUser(user, ip, reason, chat_uid))

    ##########################################################################
    # Debugging
    ##########################################################################

    security.declareProtected(CMFCorePermissions.View, "status")
    def status(self, REQUEST, asJSON = False):
        """ get overall status """
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
    def resetLastAction(self, REQUEST = None):
        """ reset last_action to get all messages from the beginning """
        session = REQUEST.SESSION
        if session.get('user_properties'):
            user_properties = session.get('user_properties')
            user_properties['last_action'] = user_properties.get('start_action')
            user_properties['user_list'] = []
            session.set('user_properties', user_properties)

    security.declareProtected(CMFCorePermissions.View, "addPrefix")
    def addPrefix(self, db, prefix, REQUEST = None):
        """ add the prefix to the list of own db prefixes """
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