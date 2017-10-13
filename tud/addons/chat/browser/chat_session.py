# -*- coding: utf-8 -*-
import re
import json
import urllib

from zope.component import getUtility, getAdapter
from zope.security import checkPermission
from DateTime import DateTime

from Products.Five import BrowserView

from plone.uuid.interfaces import IUUID

from collective.beaker.interfaces import ICacheManager

from tud.addons.chat import chatMessageFactory as _
from tud.addons.chat.interfaces import IDatabaseObject

marker = object()

class UserStatus:
    OK, NOT_AUTHORIZED, KICKED, BANNED, LOGIN_ERROR, WARNED = range(6)

class BanStrategy:
    COOKIE, IP, COOKIE_AND_IP = ('COOKIE', 'IP', 'COOKIE_AND_IP')

class ChatSessionBaseView(BrowserView):

    def __init__(self, context, request):
        super(ChatSessionBaseView, self).__init__(context, request)

        cacheManager = getUtility(ICacheManager)

        cache_name = "chat_{}".format(IUUID(self.context))
        self.cache = cacheManager.get_cache(cache_name, expire=18000)

        if not self.cache.has_key('chat_users'):
            self.cache.set_value('chat_users', {})
        if not self.cache.has_key('kicked_chat_users'):
            self.cache.set_value('kicked_chat_users', {})
        if not self.cache.has_key('warned_chat_users'):
            self.cache.set_value('warned_chat_users', {})
        if not self.cache.has_key('banned_chat_users'):
            self.cache.set_value('banned_chat_users', {})
        if not self.cache.has_key('check_timestamp'):
            self.cache.set_value('check_timestamp', DateTime().timeTime())

        self._dbo = self.getDatabaseObject()

    def getDatabaseObject(self):
        chat = self.context.getParentNode()
        dbo = getattr(chat, '_v_db_adapter', marker)
        if dbo != marker:
            return dbo
        else:
            dbo = getAdapter(chat, IDatabaseObject, chat.getField('database_adapter').get(chat))
            chat._v_db_adapter = dbo
            return dbo

    def getSessionInformation(self):
        result = {}
        for field in ('title', 'description', 'chat_id', 'password', 'max_users', 'start_date', 'end_date',):
            result[field] = self.context.getField(field).get(self.context)
        result['url'] = self.context.absolute_url()

        return result

    ## @brief check, if a user is admin for this chat
    #  @return bool True, if user is admin, otherwise False
    def isAdmin(self):
        """ Check, if a user is admin for this chat. """
        return checkPermission('tud.addons.chat.ModerateChat', self.context)

    ## @brief this function checks if an user is in a specific room
    #  @param user str user name to check
    #  @return bool true if the user in the room, otherwise false
    def hasUser(self, user):
        """ Check for the existence of a user. """
        return user in self.cache['chat_users'].keys()

    ## @brief Check, if a user is registered to a chat session
    #  @return bool True, if user is registered, otherwise False
    def isRegistered(self):
        """ Check, if a user is registered to a chat session. """
        session = self.request.SESSION

        if session.get('user_properties'):
            if self.hasUser(session.get('user_properties').get('name')):
                return True
            else:
                session.clear()
        return False

    def isActive(self):
        chat_start = self.context.getField('start_date').get(self.context)
        chat_end = self.context.getField('end_date').get(self.context)
        now = DateTime()
        return now > chat_start and now < chat_end

class ChatSessionAjaxView(ChatSessionBaseView):
    ## @brief replacements for special html chars (char "&" is in function included)
    htmlspecialchars         = {'"':'&quot;', '\'':'&#039;', '<':'&lt;', '>':'&gt;'} # {'"':'&quot;'} this comment is needed, because there is a bug in doxygen

    ## @brief list of chars, which aren't allowed in ajax parameters (star marks moderators)
    forbiddenchars           = [u"★", u"☆"]

    def __call__(self):
        self.request.response.setHeader("Content-type", "application/json")

        parameters = self.request.form

        if not parameters.get('method'):
            return json.dumps("ERROR: Parameter 'method' is required")

        if len(parameters.get('method')) <= 1:
            return json.dumps("ERROR: Parameter 'method' is invalid")

        method = "ajax{}{}".format(parameters.get('method')[0].upper(), parameters.get('method')[1:])
        del parameters['method']

        if hasattr(self, method):

            # decode string parameters to unicode parameters and remove forbidden chars
            for key in parameters.keys():
                if isinstance(parameters[key], str):
                    try:
                        parameters[key] = parameters[key].decode("utf-8")
                    except ValueError:
                        return json.dumps("ERROR: Parameter '{}' is no valid utf-8 string".format(key))

                    for forbiddenchar in self.forbiddenchars:
                        parameters[key] = parameters[key].replace(forbiddenchar, '')

            result = getattr(self, method)(**parameters)
            return json.dumps(result)
        else:
            return json.dumps("ERROR: Method not available")

    ## @brief get IP address from a request
    #  @return string IP address as a string or None if not available
    def getIp(self): # see: http://dev.menttes.com/collective.developermanual/serving/http_request_and_response.html#request-client-ip
        """  Extract the client IP address from the HTTP request in a proxy compatible way.

        @return: IP address as a string or None if not available
        """

        if "HTTP_X_FORWARDED_FOR" in self.request.environ:
            # Virtual host
            ip = self.request.environ["HTTP_X_FORWARDED_FOR"]
        elif "HTTP_HOST" in self.request.environ:
            # Non virtual host
            ip = self.request.environ["REMOTE_ADDR"]
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

    ## @brief this function tells the system, that the user is active
    def userHeartbeat(self):
        """ Updates the activity timestamp of the user.
            The user information will be retrieved from the request """
        session = self.request.SESSION
        user_properties = session.get('user_properties')
        name = user_properties.get('name')
        chat_users = self.cache['chat_users']
        chat_users[name]['date'] = DateTime().timeTime()
        self.cache['chat_users'] = chat_users

    ## @brief this function removes users who doesn't call the heart beat method for a defined timeout time
    def checkForInactiveUsers(self):
        """ Check for inactive users and kick them. """
        chat = self.context.getParentNode()
        timeout = chat.getField('timeout').get(chat)

        now = DateTime().timeTime()
        if now - self.cache['check_timestamp'] > 5: # Perform this check every 5 seconds
            for user in self.cache['chat_users'].keys():
                if now - self.cache['chat_users'][user].get('date') > timeout: # timeout
                    self.removeUser(user)
            self.cache['check_timestamp'] = now

    ## @brief check, if a user is banned from this chat
    #  @return bool True, if user is banned, otherwise False
    def isBanned(self):
        """ Check, if a user is banned.  """
        #ip_address = self.getIp(self.request)
        chat = self.context.getParentNode()
        ban_strategy = chat.getField('banStrategy').get(chat)

        session = self.request.SESSION
        user_properties=session.get('user_properties')

        banned_chat_users = self.cache['banned_chat_users']

        # Existing cookie
        if BanStrategy.COOKIE in ban_strategy and self.request.get('tudchat_is_banned') == 'true':
            return True

        """
        # Check by IP address
        if BanStrategy.IP in ban_strategy:
            banEntry = dict((user,baninfo) for user,baninfo in banned_chat_users.iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return True
        """

        if not user_properties:
            return False

        # Is in ban list? Add cookie
        if BanStrategy.COOKIE in ban_strategy and user_properties.get('name') in banned_chat_users.keys():
            self.request.RESPONSE.setCookie('tudchat_is_banned', 'true', expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            self.request.RESPONSE.setCookie('tudchat_ban_reason', banned_chat_users[user_properties.get('name')].get('reason'), expires=DateTime(int(DateTime()) + 365 * 24 * 60 * 60, 'US/Pacific').toZone('GMT').strftime('%A, %d-%b-%y %H:%M:%S ') + 'GMT' )
            # Free that username to be used by others
            if not BanStrategy.IP in ban_strategy:
                del banned_chat_users[user_properties.get('name')]
                self.cache['banned_chat_users'] = banned_chat_users
            return True

        return False

    ## @brief tell the client the reason for the ban, if the client was banned
    #  @return str ban reason
    def getBanReason(self):
        """ Helper method to get ban reason """
        #ip_address = self.getIp(self.request)
        chat = self.context.getParentNode()
        ban_strategy = chat.getField('banStrategy').get(chat)

        if BanStrategy.COOKIE in ban_strategy:
            # Retrieve information from given cookies or just recently set cookies
            tudchat_is_banned = self.request.get('tudchat_is_banned') or (self.request.RESPONSE.cookies.get('tudchat_is_banned') and self.request.RESPONSE.cookies.get('tudchat_is_banned')['value'])
            tudchat_ban_reason = self.request.get('tudchat_ban_reason') or (self.request.RESPONSE.cookies.get('tudchat_ban_reason') and self.request.RESPONSE.cookies.get('tudchat_ban_reason')['value'])

            if tudchat_is_banned == 'true':
                return tudchat_ban_reason

        """
        if BanStrategy.IP in ban_strategy:
            # Check by IP-Address
            banEntry = dict((user,baninfo) for user,baninfo in self.cache['banned_chat_users'].iteritems() if baninfo.get('ip_address') == ip_address)
                if len(banEntry) > 0:
                    return banEntry[banEntry.keys()[0]].get('reason')
            return 'Not banned'
        """
        return

    ## @brief this function adds an user to an existing chat session
    #  @param user str user name to add
    #  @param is_admin bool true if the user has admin privileges
    #  @return bool true on success or false if the user is already in the room
    def addUser(self, user, is_admin):
        """ Add yourself to the user list. """
        chat_users = self.cache['chat_users']
        if not chat_users.has_key(user):
            chat_users[user] = {'date': DateTime().timeTime(), 'last_message_sent' : 0, 'is_admin' : is_admin }
            self.cache['chat_users'] = chat_users
            return True
        return False

    ## @brief this function removes an user from a specific room
    #  @param user str user name to remove
    def removeUser(self, user):
        """ Remove a single user by its name. """
        chat_users = self.cache['chat_users']
        if chat_users.has_key(user):
            del chat_users[user]
            self.cache['chat_users'] = chat_users

    ## @brief this function returns all users of a specific room
    #  @return list users of the chat room
    def getUsers(self):
        """ Return the list of all user names in a chat room. """
        return self.cache['chat_users'].keys()

    ## @brief this function returns all users of a specific room
    #  @param user str user name to be banned
    #  @param reason str reason for banning the user
    #  @return bool true if the user was banned succesfully, otherwise false
    def addBannedUser(self, user, reason):
        """ Ban a user with a given reason. """
        banned_chat_users = self.cache['banned_chat_users']
        if not user in banned_chat_users.keys() and user in self.cache['chat_users'].keys():
            banned_chat_users[user] = {'reason': reason}
            self.cache['banned_chat_users'] = banned_chat_users
            self.removeUser(user)
            return True
        return False

    ## @brief this function removes a user from the list of banned users
    #  @param user str user name to remove from the banned user list
    #  @return bool true if the user was removed from the banned user list, otherwise false (the user wasn't in the list of banned users of the given room)
    def removeBannedUser(self, user):
        """ Unban a user. """
        banned_chat_users = self.cache['banned_chat_users']
        if user in banned_chat_users.keys():
            del banned_chat_users[user]
            self.cache['banned_chat_users'] = banned_chat_users
            return True
        return False

    ## @brief this function stores a warning message for a given user in a given chat room
    #  @param user str user name to be warned
    #  @param warning str message which would send to the user
    #  @return bool true if the user was found in the given room and if there is no other warning message for the user, otherwise false
    def addWarnedUser(self, user, warning):
        """ Warn a user with a given text.
            The user gets the message after calling the getActions method. """
        warned_chat_users = self.cache['warned_chat_users']
        if not user in warned_chat_users.keys() and user in self.cache['chat_users'].keys():
            warned_chat_users[user] = { 'warning': warning }
            self.cache['warned_chat_users'] = warned_chat_users
            return True
        return False

    ## @brief this function removes a warning message for a given user in a given chat room
    #  @param user str user name of the warned user
    #  @return bool true if the warning message was found in the given room, otherwise false
    def removeWarnedUser(self, user):
        """ Remove the warning message for a given user.
            This is usually done in the message sending process. """
        warned_chat_users = self.cache['warned_chat_users']
        if user in warned_chat_users.keys():
            del warned_chat_users[user]
            self.cache['warned_chat_users'] = warned_chat_users
            return True
        return False

    ## @brief this function stores the given user in the kicked users dict
    #  @param user str name of user to be kicked
    #  @param reason str reason for kicking the user
    #  @return bool true if the user was added successfully, otherwise false
    def addKickedUser(self, user, reason):
        """ Kicks a user with given message.
            The user gets the message after calling the getActions method. """
        kicked_chat_users = self.cache['kicked_chat_users']
        if not user in kicked_chat_users.keys() and user in self.cache['chat_users'].keys():
            kicked_chat_users[user] = {'reason': reason}
            self.cache['kicked_chat_users'] = kicked_chat_users
            return True
        return False

    ## @brief this function removes the given user from the kicked users dict
    #  @param user str user name to remove from the kicked users dict
    #  @return bool true if the user was removed successfully, otherwise false (the user wasn't in the kicked users dict)
    def removeKickedUser(self, user):
        """ Removes user from kicked users dict. """
        kicked_chat_users = self.cache['kicked_chat_users']
        if user in kicked_chat_users.keys():
            del kicked_chat_users[user]
            self.cache['kicked_chat_users'] = kicked_chat_users
            return True
        return False

    ## @brief this function removes an user from a chat room
    #  @return bool true if the user was successfully removed from the room, otherwise false
    def logout(self):
        """ Logout yourself.
            The associated room will be retrieved from the user session. """
        session=self.request.SESSION
        if session.get('user_properties'):
            user = session.get('user_properties').get('name')
            session.set('user_properties', None)

            self.removeUser(user)
        return True

    ## @brief this function registers an user to a chat room
    #  @param user str proposed name of the user
    #  @param chatroom int id of the room where the user want to enter
    #  @param password str optional password of the room
    #  @return bool true if the user was successfully added to the room, otherwise false
    def ajaxRegisterMe(self, user, agreement="false", password=None):
        """ Register a user to a chat room.
            Before the user was added, this function will check the pre-conditions to enter the room (password, user limit, user name restrictions, banned users, room state)
            If the room does not exist in the room list, it will be created here. """
        self.request.SESSION.set('user_properties', None)

        context = self.context
        chat = context.getParentNode()

        chat_id = context.getField('chat_id').get(context)
        user = user.strip()

        if agreement == "false":
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_privacy', default = u'You will not be able to enter the chat without agreeing the privacy notice.'))}}

        chat_password = context.getField('password').get(context)
        if chat_password and chat_password != password:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_password', default = u'The entered password is not correct.'))}}

        chat_max_users = context.getField('max_users').get(context)
        if chat_max_users and chat_max_users <= len(self.cache['chat_users']):
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_max_users', default = u'The user limit for this chat session has been reached.'))}}

        if len(re.findall(u"[a-zA-ZäöüÄÖÜ]",user))<3:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_short_name', default = u'Your username is too short and must be at least 3 characters long.'))}}

        if len(user) < 3:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_short_name', default = u'Your username is too short and must be at least 3 characters long.'))}}

        if len(user) > 20:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_long_name', default = u'Your username is too long and may not be longer than 20 characters.'))}}

        if not self.isActive():
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_session_inactive', default = u'The chosen chat session is currently inactive.'))}}

        if user.lower() in [chat_user.lower() for chat_user in self.cache['chat_users'].keys()]:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_name_in_use', default = u'The username is already in use.'))}}

        if self.isBanned():
            message = self.context.translate(_(u'login_err_banned', default = u'You were banned permanently.'))
            if self.getBanReason():
                message += '<br /><br />' + self.context.translate(_(u'login_err_banned_reason', default = u'Reason: ${reason}', mapping={u'reason': self.getBanReason()}))
            return {'status': {'code': UserStatus.LOGIN_ERROR, 'message': message}}

        session = self.request.SESSION
        old_messages_count = chat.getField('oldMessagesCount').get(chat)
        old_messages_minutes = chat.getField('oldMessagesMinutes').get(chat)
        start_action_id = self._dbo.getStartAction(chat_id, old_messages_count, old_messages_minutes)
        start_action_whisper_id = self._dbo.getLastAction(chat_id)
        self.checkForInactiveUsers()

        # Clean username
        user = self.html_escape(user)

        if not self.isBanned() and user and self.addUser(user, self.isAdmin()):
            session.set('user_properties', {'name': user,
                                            'start_action' : start_action_id,
                                            'start_action_whisper' : start_action_whisper_id,
                                            'last_action': start_action_id,
                                            'user_list': [],
                                            'chat_room_check': 0
                                            })
            return True
        return False

    ## @brief this function resets the last action to the start action of the user's chat room
    def ajaxResetLastAction(self):
        """ Reset last_action to get all messages from the beginning. """
        session = self.request.SESSION
        if session.get('user_properties'):
            user_properties = session.get('user_properties')
            user_properties['last_action'] = user_properties.get('start_action')
            user_properties['user_list'] = []
            session.set('user_properties', user_properties)

    def ajaxLogout(self):
        return self.logout()

    ## @brief this function returns all updates specific to the calling user since the last time this method was called
    #  @return dict special JSON dictonary that contains either a special state or message and user updates
    def ajaxGetActions(self):
        """ This function returns all actions specific to the calling user since the last function call.
            Also performs several checks. """
        session=self.request.SESSION
        context = self.context
        chat = context.getParentNode()

        if self.isBanned():
            session['chat_ban_message'] = self.getBanReason()
            self.logout()
            return {'status': {'code': UserStatus.BANNED, 'message': ''}}

        if not self.isRegistered():
            session['chat_not_authorized_message'] = _(u'session_not_authorized', default = u'Please log in to participate in a chat session.')
            return {'status': {'code': UserStatus.NOT_AUTHORIZED, 'message': 'NOT AUTHORIZED'}}


        user_properties = session.get('user_properties')
        old_user_properties = user_properties.copy()
        user = user_properties.get('name')
        chat_id = context.getField('chat_id').get(context)

        if user in self.cache['warned_chat_users']:
            warning = self.cache['warned_chat_users'][user]['warning']
            self.removeWarnedUser(user)
            return {'status': {'code': UserStatus.WARNED, 'message': warning}}

        if user in self.cache['kicked_chat_users']:
            session['chat_kick_message'] = self.cache['kicked_chat_users'][user]['reason']
            self.removeKickedUser(user)
            self.logout()
            return {'status': {'code': UserStatus.KICKED, 'message': ''}}

        self.userHeartbeat()
        self.checkForInactiveUsers()

        #check if the chat is still active
        now = DateTime().timeTime()
        if now - user_properties.get('chat_room_check') > 60: # Perform this check every 60 seconds
            user_properties['chat_room_check'] = now
            if not self.isActive():
                self.removeUser(user)
                session.set('user_properties', user_properties)
                return {'status': {'code': UserStatus.KICKED, 'message': _(u'session_expired', default = u'The chat session has expired.')}}

        # Lookup last action
        start_action = user_properties.get('start_action')
        start_action_whisper = user_properties.get('start_action_whisper')
        last_action = user_properties.get('last_action')
        #limit message count for users who get normally all messages since start action
        if start_action==last_action:
            limit = 30
        else:
            limit = 0
        list_actions = self._dbo.getActions(chat_id = chat_id, last_action = last_action, start_action = start_action, start_action_whisper = start_action_whisper, user = user, limit = limit)
        # build a list of extra attributes
        for i in range(len(list_actions)):
            list_actions[i]['attr'] = []
            if list_actions[i]['a_action'] != '':
                list_actions[i]['attr'].append({'a_action':list_actions[i]['a_action'], 'a_name':list_actions[i]['a_name']})
            if list_actions[i]['action'] == 'mod_add_message' or list_actions[i]['u_action'] == 'mod_add_message':
                list_actions[i]['attr'].append({'admin_message':True})
            if list_actions[i]['whisper_target'] is not None:
                list_actions[i]['attr'].append({'whisper_target':list_actions[i]['whisper_target']})

        return_dict = {
                        'messages':
                            {
                                'new': [ {  'id': action['id'],
                                            'date': int(action['date'].timeTime()),
                                            'name': action['user'],
                                            'message': action['message'],
                                            'attributes': action['attr'] } for action in list_actions if (action['action'] == "user_add_message" or action['action'] == "mod_add_message")],
                                'to_delete': [ { 'id': action['target'],
                                                  'date': int(action['date'].timeTime()),
                                                  'name': action['user'],
                                                  'attributes': action['attr'] } for action in list_actions if action['action'] == "mod_delete_message" ],
                                'to_edit': [ {  'id': action['target'],
                                                'date': int(action['date'].timeTime()),
                                                'name': action['user'],
                                                'message': action['message'],
                                                'attributes': action['attr'] } for action in list_actions if action['action'] == "mod_edit_message" ],
                            },
                        'users':
                            {
                                'new':       [ { 'name' : person,
                                                 'is_admin' :  self.cache['chat_users'][person]['is_admin']} for person in self.getUsers() if person not in session.get('user_properties').get('user_list')],
                                'to_delete': [ person for person in session.get('user_properties').get('user_list') if person not in self.getUsers() ]
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
        user_properties['user_list'] = self.getUsers()

        # Update session only if necessary
        if old_user_properties['last_action'] != user_properties['last_action'] or old_user_properties['user_list'] != user_properties['user_list'] or old_user_properties['chat_room_check'] != user_properties['chat_room_check']:
            session.set('user_properties', user_properties)

        return return_dict

    ## @brief this function adds a message to the chat room of the user
    #  @param message str message to send
    #  @param target_user str user name of whisper target (optional)
    def ajaxSendMessage(self, message, target_user = None):
        """ Send a message to the chat room of the user.
            If the user sends to many messages in a pre-defined interval, the message will be ignored.
            The maximum message length will be also checked (if the message length is to high, it will be truncated). """

        if not self.isRegistered():
            return

        session=self.request.SESSION
        chat = self.context.getParentNode()

        now = DateTime().timeTime()
        chat_id = self.context.getField('chat_id').get(self.context)
        user = session.get('user_properties').get('name')

        chat_users = self.cache['chat_users']

        block_time = chat.getField('blockTime').get(chat)
        max_message_length = chat.getField('maxMessageLength').get(chat)

        self.userHeartbeat()

        if target_user is not None:
            whisper = chat.getField('whisper').get(chat)

            if whisper == 'off':
                return
            if not chat_users.get(target_user):
                return
            if whisper == 'restricted' and not chat_users[user]['is_admin'] and not chat_users[target_user]['is_admin']:
                return
            if user == target_user:
                # can't whisper with yourself
                return

        if not message:
            return
        if (now - chat_users[user].get('last_message_sent')) < block_time: # Block spamming messages
            return
        else:
            chat_users[user]['last_message_sent'] = now

        if max_message_length:
            message = message[:max_message_length]
        msgid = self._dbo.sendAction(chat_id = chat_id,
                            user = user,
                            action = self.isAdmin() and 'mod_add_message' or 'user_add_message',
                            content = self.html_escape(message),
                            whisper_target = target_user)

        self.cache['chat_users'] = chat_users

    ## @brief this function edits an already sent message
    #  @param message int id of the message to edit
    #  @param message str text of the new message
    def ajaxEditMessage(self, message_id, message):
        """ Edit a message.
            This action can only performed by admins. """
        session = self.request.SESSION

        if not self.isAdmin():
            return
        self.userHeartbeat()
        if not message:
            return
        self._dbo.sendAction(chat_id = self.context.getField('chat_id').get(self.context),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_edit_message',
                                    content = self.html_escape(message),
                                    target = message_id)

    ## @brief this function deletes an already sent message
    #  @param message int id of the message to delete
    def ajaxDeleteMessage(self, message_id):
        """ Delete a message by its id.
            This action can only performed by admins. """
        session = self.request.SESSION

        if not self.isAdmin():
            return
        self.userHeartbeat()

        self._dbo.sendAction(chat_id = self.context.getField('chat_id').get(self.context),
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_delete_message',
                                    target = message_id)

    ## @brief this function removes an user from the chat room where the admin is inside
    #  @param target_user str name of the user to kick
    #  @param message str message text which will be send to the user
    def ajaxKickUser(self, target_user, message = ""):
        """ Kick a user. """
        target_user = self.html_escape(target_user)
        session=self.request.SESSION

        if not self.isAdmin():
            return

        # You can not kick yourself
        if session.get('user_properties').get('name') == target_user:
            return

        self.userHeartbeat()

        self.addKickedUser(target_user, message)

    ## @brief this function warns an user in the chat room where the admin is inside
    #  @param target_user str name of the user to warn
    #  @param message str message text which will be send to the user
    #  @return bool true if the warning message is stored otherwise false
    def ajaxWarnUser(self, target_user, message = ""):
        """ Warn a user. """
        target_user = self.html_escape(target_user)
        session=self.request.SESSION

        if not self.isAdmin():
            return
        # You can not warn yourself
        if session.get('user_properties').get('name') == target_user:
            return

        self.userHeartbeat()

        return self.addWarnedUser(target_user, message)

    ## @brief this function bans an user from the chat room where the admin is inside
    #  @param target_user str name of the user to ban
    #  @param message str reason text which will be displayed additionally to the ban
    #  @return bool true if the ban is stored otherwise false
    def ajaxBanUser(self, target_user, message = ""):
        """ Ban a user. """
        target_user = self.html_escape(target_user)
        session=self.request.SESSION

        if not self.isAdmin():
            return
        # You can not ban yourself
        if session.get('user_properties').get('name') == target_user:
            return

        self.userHeartbeat()

        return self.addBannedUser(target_user, message)

class ChatSessionView(ChatSessionBaseView):
    """Default chat session view
    """

    def __call__(self):
        if self.isRegistered():
            return super(ChatSessionView, self).__call__()
        else:
            if self.isActive():
                session=self.request.SESSION
                session['chat_not_authorized_message'] = _(u'session_not_authorized', default = u'Please log in to participate in a chat session.')
                target_url = "{}?room={}".format(self.context.getParentNode().absolute_url(), urllib.quote(self.context.id))
            else:
                target_url = self.context.getParentNode().absolute_url()

            self.request.response.redirect(target_url)

            return

    def getChatInformation(self):
        chat = self.context.getParentNode()

        result = {}
        for field in ('refreshRate', 'blockTime', 'maxMessageLength',):
            result[field] = chat.getField(field).get(chat)
        result['url'] = chat.absolute_url()

        return result

    def getWelcomeMessage(self):
        return self.context.getField('welcome_message').get(self.context) or None

    def getWhisperOption(self):
        chat = self.context.getParentNode()
        return chat.getField('whisper').get(chat)

    def getDateFrequencyOption(self):
        chat = self.context.getParentNode()
        return chat.getField('date_frequency').get(chat)

class ChatSessionLogView(ChatSessionBaseView):
    """Chat session log view
    """

    ## @brief this function returns all chat messages about a specific chat session
    #  @return list of dictionaries, the following information are in every dict: id, action, date, user, message, target, a_action, a_name
    def getLogs(self, REQUEST = None):
        """ Retrieve the whole and fully parsed chat log """
        chat_id = self.context.getField('chat_id').get(self.context)
        return self._dbo.getActions(chat_id, 0, 0, 0, '')[:-1]
