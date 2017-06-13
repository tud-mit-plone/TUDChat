# -*- coding: utf-8 -*-

# Python imports
import re
import simplejson
import logging

# Zope imports
from DateTime import DateTime
from AccessControl import ClassSecurityInfo, getSecurityManager
from zope.interface import implementer

# CMF imports
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, IntegerField, DateTimeField
from Products.Archetypes.public import StringWidget, IntegerWidget, CalendarWidget
from Products.validation.validators import ExpressionValidator, RegexValidator

try:
    from raptus.multilanguagefields import fields
    from raptus.multilanguagefields import widgets
except ImportError:
    from Products.Archetypes import Field as fields
    from Products.Archetypes import Widget as widgets

from tud.addons.chat.interfaces import IChatSession

logger = logging.getLogger('tud.addons.chat')

ChatSessionSchema = schemata.ATContentTypeSchema.copy() + Schema((
    fields.TextField('description',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = widgets.TextAreaWidget(
            label        = u"Beschreibung",
            description  = u"Bitte geben Sie eine Beschreibung fuer die Chat-Sitzung an."
        )
    ),
    DateTimeField('start_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = u"Beginn",
            description  = u"Bitte geben Sie den Beginn der Chat-Sitzung an."
        )
    ),
    DateTimeField('end_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = u"Ende",
            description  = u"Bitte geben Sie das Ende der Chat-Sitzung an."
        )
    ),
    StringField('password',
        required           = False,
        default            = '',
        validators         = (ExpressionValidator('python: len(value) <= 30', 'Das Passwort darf maximal 30 Zeichen lang sein.'), ),
        widget             = StringWidget(
            label        = u"Passwort",
            description  = u"Bitte geben Sie ein Passwort fuer die Chat-Sitzung an, falls Sie den Zugang beschraenken wollen."
        )
    ),
    IntegerField('max_users',
        required           = False,
        default            = 0,
        validators         = RegexValidator('checkNum', '^[0-9]+$', errmsg = 'Die maximale Benutzeranzahl muss eine Zahle groesser oder gleich 0 sein.'),
        widget             = IntegerWidget(
            label        = u"maximale Benutzer",
            description  = u"Bitte geben Sie die maximale Benutzerzahl ein, falls Sie die Anzahl der Chat-Benutzer limitieren moechten. (0 bedeutet keine Beschraenkung)"
        )
    ),
    IntegerField('chat_id',
        required           = True,
        default            = 0,
        validators         = RegexValidator('checkNum', '^[0-9]+$', errmsg = 'Die Chat-ID muss eine Zahl groesser oder gleich 0 sein.'),
        read_permission    = permissions.ManagePortal,
        write_permission   = permissions.ManagePortal,
        widget             = StringWidget(
            label        = u"Chat-ID",
            description  = u"Eindeutige Datenbank-ID dieser Chat-Sitzung (bei 0 wird die ID generiert, wenn die Sitzung angelegt wird)"
        )
    ),
),
)

schemata.finalizeATCTSchema(ChatSessionSchema, folderish=False, moveDiscussion=False)

class UserStatus:
    OK, NOT_AUTHORIZED, KICKED, BANNED, LOGIN_ERROR, WARNED, CHAT_WARN = range(7)

class BanStrategy:
    COOKIE, IP, COOKIE_AND_IP = ('COOKIE', 'IP', 'COOKIE_AND_IP')

@implementer(IChatSession)
class ChatSession(base.ATCTContent):
    """Chat session content type

    """

    meta_type = 'ChatSession'
    portal_type = "ChatSession"
    archetype_name = 'ChatSession'
    isPrincipiaFolderish = False

    #: Archetype schema
    schema = ChatSessionSchema

    security = ClassSecurityInfo()

    # Data
    ## @brief collection of timestamps to call methods in certain intervals
    timestamps               = {}
    ## @brief chat room container with userlist, kicked_users, banned_users and timestamps
    chat_rooms               = {}
    ## @brief define roles that have admin privileges
    admin_roles              = ['Admin','ChatModerator']
    ## @brief list of message ids sent from admins
    admin_messages           = []
    ## @brief replacements for special html chars (char "&" is in function included)
    htmlspecialchars         = {'"':'&quot;', '\'':'&#039;', '<':'&lt;', '>':'&gt;'} # {'"':'&quot;'} this comment is needed, because there is a bug in doxygen

    def getChatStorage(self):
        chat = self.getParentNode()
        return chat.chat_storage

    ##########################################################################
    # General Utility methods
    ##########################################################################


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

    ##########################################################################
    # Access management
    ##########################################################################

    ## @brief Check, if a user is registered to a chat session
    #  @return bool True, if user is registered, otherwise False
    def isRegistered(self, REQUEST = None):
        """ Check, if a user is registered to a chat session. """
        session=REQUEST.SESSION

        if session.get('user_properties'):
            chat_id = session.get('user_properties').get('chat_room')
            if chat_id in self.chat_rooms.keys():
                if self.hasUser(session.get('user_properties').get('name'), chat_id):
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
            chat_id=user_properties.get('chat_room')
        else:
            chat_id=None

        # Existing cookie
        if BanStrategy.COOKIE in self.banStrategy and REQUEST.get('tudchat_is_banned') == 'true':
            return True

        """
        # Check by IP address in all chat rooms
        if BanStrategy.IP in self.banStrategy:
            for chat_id in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_id]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return True
        """

        if not self.chat_rooms.get(chat_id):
            return False

        # Is in ban list? Add cookie
        if BanStrategy.COOKIE in self.banStrategy and chat_id and user_properties.get('name') in self.chat_rooms[chat_id]['banned_chat_users'].keys():
            REQUEST.RESPONSE.setCookie('tudchat_is_banned', 'true', expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            REQUEST.RESPONSE.setCookie('tudchat_ban_reason', self.chat_rooms[chat_id]['banned_chat_users'][user_properties.get('name')].get('reason'), expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            # Free that username to be used by others
            if not BanStrategy.IP in self.banStrategy:
                del self.chat_rooms[chat_id]['banned_chat_users'][user_properties.get('name')]
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
            for chat_id in self.chat_rooms.keys():
                banEntry = dict((user,baninfo) for user,baninfo in self.chat_rooms[chat_id]['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return banEntry[banEntry.keys()[0]].get('reason')
            return 'Not banned'
        """
        return

    ##########################################################################
    # Chat Session Management
    ##########################################################################

    ## @brief this function returns all chat messages about a specific chat session
    #  @param chat_id int id of the specific chat session
    #  @return list of dictionaries, the following information are in every dict: id, action, date, user, message, target, a_action, a_name
    def getLogs(self, chat_id, REQUEST = None):
        """ Retrieve the whole and fully parsed chat log """
        if not self.isAdmin(REQUEST):
            return
        return self.getChatStorage().getActions(chat_id, 0, 0)[:-1]

    ##########################################################################
    #  User Management
    ##########################################################################

    security.declarePrivate('addUser')
    ## @brief this function adds an user to an existing chat session
    #  @param user str user name to add
    #  @param chat_id int id of the room, where the user want to join
    #  @param is_admin bool true if the user has admin privileges
    #  @return bool true on success or false if the user is already in the room
    def addUser(self, user, chat_id, is_admin):
        """ Add yourself to the user list. """
        if not self.chat_rooms[chat_id]['chat_users'].has_key(user):
            self.chat_rooms[chat_id]['chat_users'][user] = {'date': DateTime().timeTime(), 'last_message_sent' : 0, 'is_admin' : is_admin }
            self._p_changed = 1
            return True
        return False

    security.declarePrivate('hasUser')
    ## @brief this function checks if an user is in a specific room
    #  @param user str user name to check
    #  @param chat_id int id of the room to check
    #  @return bool true if the user in the room, otherwise false
    def hasUser(self, user, chat_id):
        """ Check for the existence of a user. """
        return user in self.chat_rooms[chat_id]['chat_users'].keys()

    security.declarePrivate('removeUser')
    ## @brief this function removes an user from a specific room
    #  @param user str user name to remove
    #  @param chat_id int id of the room where the user is inside
    def removeUser(self, user, chat_id):
        """ Remove a single user by its name. """
        if self.chat_rooms[chat_id]['chat_users'].has_key(user):
            del self.chat_rooms[chat_id]['chat_users'][user]
            self._p_changed = 1
        #remove chatroom if there no real entries
        if len(self.chat_rooms[chat_id]['chat_users'])==0 and len(self.chat_rooms[chat_id]['kicked_chat_users'])==0 and len(self.chat_rooms[chat_id]['banned_chat_users'])==0:
            del self.chat_rooms[chat_id]

    security.declarePrivate('clearUsers')
    ## @brief this function removes all users from a specific room
    #  @param chat_id int id of the room
    def clearUsers(self, chat_id):
        """ Clear the user list. """
        self.chat_rooms[chat_id]['chat_users'].clear()
        self._p_changed = 1

    security.declarePrivate('getUsers')
    ## @brief this function returns all users of a specific room
    #  @param chat_id int id of the room
    #  @return list users of the chat room
    def getUsers(self, chat_id):
        """ Return the list of all user names in a chat room. """
        return self.chat_rooms[chat_id]['chat_users'].keys()

    security.declarePrivate('addBannedUser')
    ## @brief this function returns all users of a specific room
    #  @param user str user name to be banned
    #  @param reason str reason for banning the user
    #  @param chat_id int id of the room where the user is inside
    #  @return bool true if the user was banned succesfully, otherwise false
    def addBannedUser(self, user, reason, chat_id):
        """ Ban a user with a given reason. """
        if not user in self.chat_rooms[chat_id]['banned_chat_users'].keys() and user in self.chat_rooms[chat_id]['chat_users'].keys():
            self.chat_rooms[chat_id]['banned_chat_users'][user] = { 'reason': reason }
            self.removeUser(user, chat_id)
            return True
        return False

    security.declarePrivate('removeBannedUser')
    ## @brief this function removes a user from the list of banned users
    #  @param user str user name to remove from the banned user list
    #  @param chat_id int id of the room where the user was banned
    #  @return bool true if the user was removed from the banned user list, otherwise false (the user wasn't in the list of banned users of the given room)
    def removeBannedUser(self, user, chat_id):
        """ Unban a user. """

        if user in self.chat_rooms[chat_id]['banned_chat_users'].keys():
            del self.chat_rooms[chat_id]['banned_chat_users'][user]
            return True
        return False

    security.declarePrivate('addWarnedUser')
    ## @brief this function stores a warning message for a given user in a given chat room
    #  @param user str user name to be warned
    #  @param warning str message which would send to the user
    #  @param chat_id int id of the room where the user is inside
    #  @return bool true if the user was found in the given room and if there is no other warning message for the user, otherwise false
    def addWarnedUser(self, user, warning, chat_id):
        """ Warn a user with a given text.
            The user gets the message after calling the getActions method. """
        if not user in self.chat_rooms[chat_id]['warned_chat_users'].keys() and user in self.chat_rooms[chat_id]['chat_users'].keys():
            self.chat_rooms[chat_id]['warned_chat_users'][user] = { 'warning': warning }
            return True
        return False

    security.declarePrivate('removeWarnedUser')
    ## @brief this function removes a warning message for a given user in a given chat room
    #  @param user str user name of the warned user
    #  @param chat_id int id of the room where the user is inside
    #  @return bool true if the warning message was found in the given room, otherwise false
    def removeWarnedUser(self, user, chat_id):
        """ Remove the warning message for a given user.
            This is usually done in the message sending process. """

        if user in self.chat_rooms[chat_id]['warned_chat_users'].keys():
            del self.chat_rooms[chat_id]['warned_chat_users'][user]
            return True
        return False

    ## @brief this function removes all banned users in all chat rooms (this function is only for debugging)
    def clearBannedUsers(self):
        """ Clear the banned user list of all chat rooms. """
        for chat_id in self.chat_rooms.keys():
            self.chat_rooms[chat_id]['banned_chat_users'].clear()
        self._p_changed = 1

    ###################################
    # Exposed methods
    ###################################

    security.declareProtected(permissions.View, "registerMe")
    ## @brief this function registers an user to a chat room
    #  @param user str proposed name of the user
    #  @param chatroom int id of the room where the user want to enter
    #  @param password str optional password of the room
    #  @return bool true if the user was successfully added to the room, otherwise false
    def registerMe(self, user, agreement="false", password=None, REQUEST = None):
        """ Register a user to a chat room.
            Before the user was added, this function will check the pre-conditions to enter the room (password, user limit, user name restrictions, banned users, room state)
            If the room does not exist in the room list, it will be created here. """
        REQUEST.SESSION.set('user_properties', None)

        chatroom = self.getField('chat_id').get(self)
        user = user.strip()

        if agreement == "false":
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ohne Zustimmung zum Datenschutzhinweis kann der Chat nicht betreten werden.'}})

        chat_password = self.getField('password').get(self)
        if chat_password and chat_password != password:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das eingegebene Passwort ist nicht korrekt.'}})

        chat_max_users = self.getField('max_users').get(self)
        if chat_max_users and self.chat_rooms.get(chatroom) and chat_max_users <= len(self.chat_rooms[chatroom]['chat_users']):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Das Benutzerlimit für diese Chat-Session ist bereits erreicht.'}})

        if len(re.findall(r"[a-zA-ZäöüÄÖÜ]",user))<3:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername muss mindestens drei Buchstaben enthalten.'}})

        if len(user) < 3:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu kurz. (Er muss mindestens 3 Zeichen lang sein.)'}})

        if len(user) > 20:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername ist zu lang. (Er darf maximal 20 Zeichen lang sein.)'}})

        if not self.checkUTF8(user):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Ihr Benutzername enthält ungültige Zeichen. (Es sind nur UTF-8-Zeichen erlaubt.)'}})

        if not self.isActive():
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Der gewählte Chat-Raum ist zurzeit nicht aktiv.'}})

        if self.chat_rooms.has_key(chatroom) and user.lower() in [chat_user.lower() for chat_user in self.chat_rooms[chatroom]['chat_users'].keys()]:
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Der Benutzername ist bereits belegt.'}})

        if self.isBanned(REQUEST):
            return simplejson.dumps({'status': {'code':UserStatus.LOGIN_ERROR, 'message':'Sie wurden dauerhaft des Chats verwiesen. <br/> <br/> Grund: ' + str(self.getBanReason(REQUEST))}})

        session = REQUEST.SESSION
        start_action_id = self.getChatStorage().getLastChatAction(chatroom)
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

    def isActive(self):
        chat_start = self.getField('start_date').get(self)
        chat_end = self.getField('end_date').get(self)
        now = DateTime()
        return now > chat_start and now < chat_end


    security.declareProtected(permissions.View, "logout")
    ## @brief this function removes an user from a chat room
    #  @return bool true if the user was successfully removed from the room, otherwise false
    def logout(self, REQUEST = None):
        """ Logout yourself.
            The associated room will be retrieved from the user session. """
        session=REQUEST.SESSION
        if session.get('user_properties'):
            user = session.get('user_properties').get('name')
            chat_id = session.get('user_properties').get('chat_room')
            session.set('user_properties', None)
            session.invalidate()

            self.removeUser(user, chat_id)
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
        chat_id = user_properties.get('chat_room')
        self.chat_rooms[chat_id]['chat_users'][name]['date'] = DateTime().timeTime()

    security.declarePrivate('checkForInactiveUsers')
    ## @brief this function removes users who doesn't call the heart beat method for a defined timeout time
    def checkForInactiveUsers(self):
        """ Check for inactive users and kick them. """
        now = DateTime().timeTime()
        if now - self.timestamps.setdefault('userHeartbeat', 0) > 5: # Perform this check every 5 seconds
            for chat_id in self.chat_rooms.keys():
                for user in self.chat_rooms[chat_id]['chat_users'].keys():
                    if now - self.chat_rooms[chat_id]['chat_users'][user].get('date') > self.timeout: # timeout
                        self.removeUser(user, chat_id)
            self.timestamps['userHeartbeat'] = now

    ##########################################################################
    # Public Message / Action methods
    ##########################################################################

    ## @brief this function adds a message to the chat room of the user
    #  @param message str message to send
    def sendMessage(self, message, REQUEST = None):
        """ Send a message to the chat room of the user.
            If the user sends to many messages in a pre-defined interval, the message will be ignored.
            The maximum message length will be also checked (if the message length is to high, it will be truncated). """

        if not self.isRegistered(REQUEST):
            return

        session=REQUEST.SESSION

        now = DateTime().timeTime()
        chat_id = self.getField('chat_id').get(self)
        user = session.get('user_properties').get('name')

        self.userHeartbeat(REQUEST)
        if not message:
            return
        if (now - self.chat_rooms[chat_id]['chat_users'][user].get('last_message_sent')) < self.blockTime: # Block spamming messages
            return
        else:
            self.chat_rooms[chat_id]['chat_users'][user]['last_message_sent'] = now

        #filter invalid utf8
        if not self.checkUTF8(message):
            return

        if self.maxMessageLength:
            message = message[:self.maxMessageLength]
        msgid = self.getChatStorage().sendAction(chat_id = chat_id,
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
        self.getChatStorage().sendAction(chat_id = self.getField('chat_id').get(self),
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

        self.getChatStorage().sendAction(chat_id = session.get('user_properties').get('chat_room'),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_delete_message',
                                    target = message_id)

    ## @brief this function returns all updates specific to the calling user since the last time this method was called
    #  @return dict special JSON dictonary that contains either a special state or message and user updates
    def getActions(self, REQUEST = None):
        """ This function returns all actions specific to the calling user since the last function call.
            Also performs several checks. """
        session=REQUEST.SESSION
        chat_storage = self.getChatStorage()

        if self.isBanned(REQUEST):
            self.logout(REQUEST)
            return simplejson.dumps({'status': {'code': UserStatus.BANNED, 'message': self.getBanReason(REQUEST)}})

        if not self.isRegistered(REQUEST):
            return simplejson.dumps({'status': {'code': UserStatus.NOT_AUTHORIZED, 'message': 'NOT AUTHORIZED'}})


        user_properties = session.get('user_properties')
        old_user_properties = user_properties.copy()
        user = user_properties.get('name')
        chat_id = self.getField('chat_id').get(self)

        if user in self.chat_rooms[chat_id]['warned_chat_users']:
            warning = self.chat_rooms[chat_id]['warned_chat_users'][user]['warning']
            self.removeWarnedUser(user, chat_id)
            return simplejson.dumps({'status': {'code': UserStatus.WARNED, 'message': warning}})

        if user in self.chat_rooms[chat_id]['kicked_chat_users']:
            self.chat_rooms[chat_id]['kicked_chat_users'].remove(user)
            self.logout(REQUEST)
            return simplejson.dumps({'status': {'code': UserStatus.KICKED, 'message': ''}})

        self.userHeartbeat(REQUEST)
        self.checkForInactiveUsers()

        #check if the chat is still active
        now = DateTime().timeTime()
        if now - user_properties.get('chat_room_check') > 60: # Perform this check every 60 seconds
            user_properties['chat_room_check'] = now
            if not self.isActive():
                self.removeUser(user, chat_id)
                session.set('user_properties', user_properties)
                return simplejson.dumps({'status': {'code': UserStatus.KICKED, 'message': 'Die Chat-Sitzung ist abgelaufen.'}})
            if not user_properties.get('chatInactiveWarning') and self.getField('end_date').get(self).timeTime() - now < 300: # warn user 5 minutes before the chat will close
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
        list_actions = chat_storage.getActions(chat_id = chat_id, last_action = last_action, start_action = start_action, limit = limit)
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
                                                 'is_admin' :  self.chat_rooms[chat_id]['chat_users'][person]['is_admin']} for person in self.getUsers(chat_id) if person not in session.get('user_properties').get('user_list')],
                                'to_delete': [ person for person in session.get('user_properties').get('user_list') if person not in self.getUsers(chat_id) ]
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
        user_properties['user_list'] = self.getUsers(chat_id)

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

        chat_id = session.get('user_properties').get('chat_room')

        return simplejson.dumps(self.addWarnedUser(user, warning, chat_id))

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

        chat_id = session.get('user_properties').get('chat_room')

        return simplejson.dumps(self.addBannedUser(user, reason, chat_id))

    ##########################################################################
    # Debugging
    ##########################################################################

    security.declareProtected(permissions.View, "status")
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
            'isAdmin': self.isAdmin(REQUEST)
        }
        if asJSON:
            return simplejson.dumps(d)
        else:
            return d

    security.declareProtected(permissions.View, "resetLastAction")
    ## @brief this function resets the last action to the start action of the user's chat room
    def resetLastAction(self, REQUEST = None):
        """ Reset last_action to get all messages from the beginning. """
        session = REQUEST.SESSION
        if session.get('user_properties'):
            user_properties = session.get('user_properties')
            user_properties['last_action'] = user_properties.get('start_action')
            user_properties['user_list'] = []
            session.set('user_properties', user_properties)

    security.declareProtected(permissions.View, "myRequest")
    def myRequest(self, REQUEST = None):
        """ reset last_action to get all messages from the beginning """
        return REQUEST

atapi.registerType(ChatSession, 'tud.addons.chat')
