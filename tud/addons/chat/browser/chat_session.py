# -*- coding: utf-8 -*-
import re
import json
import urllib
import inspect

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
    """
    Inside this class are different user states defined. These states will be used for ajax responses.
    """
    OK, NOT_AUTHORIZED, KICKED, BANNED, LOGIN_ERROR, WARNED = range(6)

class BanStrategy:
    """
    Inside this class are different ban strategies defined. Currently only the cookie strategy is used.
    """
    COOKIE, IP, COOKIE_AND_IP = ('COOKIE', 'IP', 'COOKIE_AND_IP')

class ChatSessionBaseView(BrowserView):
    """
    This base class for session views prepares cache and database access and introduces some helper methods.

    :ivar cache: storage for cached data (shared between all chat session users)
    :ivar _dbo: database object to communicate with the database
    """

    def __init__(self, context, request):
        """
        Prepares cache and database access.

        :param context: chat session
        :type context: tud.addons.chat.content.chat_session.ChatSession
        :param request: request
        :type request: ZPublisher.HTTPRequest.HTTPRequest
        """
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
        """
        Returns database object which provides database access.
        Primary the database object will be obtained from the chat object. The success is not guaranteed, because the database object is stored as volatile attribute in the chat object.
        If the database object could not be obtained from the chat object, a new database object will be instantiated.

        :return: database object
        :rtype: tud.addons.chat.interfaces.IDatabaseObject
        """
        chat = self.context.getParentNode()
        dbo = getattr(chat, '_v_db_adapter', marker)
        if dbo != marker:
            return dbo
        else:
            dbo = getAdapter(chat, IDatabaseObject, chat.database_adapter)
            chat._v_db_adapter = dbo
            return dbo

    def isAdmin(self):
        """
        Checks, if current user is a moderator.

        :return: True, if user is a moderator, otherwise False
        :rtype: bool
        """
        return checkPermission('tud.addons.chat.ModerateChat', self.context)

    def hasUser(self, user):
        """
        Checks, if given user exists in respective chat session.

        :param user: user name to check
        :type user: str
        :return: True if the user exists, otherwise False
        :rtype: bool
        """
        return user in self.cache['chat_users'].keys()

    def isRegistered(self):
        """
        Checks, if current user is registered to a chat session.

        :return: True, if user is registered, otherwise False
        :rtype: bool
        """
        session = self.request.SESSION

        if session.get('user_properties'):
            if self.hasUser(session.get('user_properties').get('name')):
                return True
            else:
                session.clear()
        return False

    def isActive(self):
        """
        Checks, if chat session is currently active.

        :return: True, if session is active, otherwise False
        :rtype: bool
        """
        chat_start = self.context.start_date
        chat_end = self.context.end_date
        now = DateTime()
        return now > chat_start and now < chat_end

class ChatSessionAjaxView(ChatSessionBaseView):
    """
    This view class represents the endpoint for javascript requests. All methods prefixed with "ajax" can be accessed from outside.

    :cvar htmlspecialchars: replacements for special html chars (char "&" is in function included)
    :cvar forbiddenchars: list of chars, which aren't allowed in ajax parameters (star marks moderators)
    """

    htmlspecialchars         = {'"':'&quot;', '\'':'&#039;', '<':'&lt;', '>':'&gt;'}
    forbiddenchars           = [u"★", u"☆"]

    def __call__(self):
        """
        Determines and calls the requested method.
        If the method could not be found or if required parameters are missing, an error is returned.
        String parameters get a special handling. First they will be decoded to unicode objects. Second forbidden characters (see class variable 'forbiddenchars') will be removed.

        :return: error message or return value of desired method (result is in every case json formatted)
        :rtype: str
        """
        self.request.response.setHeader("Content-type", "application/json")

        parameters = self.request.form

        if not parameters.get('method'):
            return json.dumps("ERROR: Parameter 'method' is required")

        if len(parameters.get('method')) <= 1:
            return json.dumps("ERROR: Parameter 'method' is invalid")

        method = "ajax{}{}".format(parameters.get('method')[0].upper(), parameters.get('method')[1:])
        del parameters['method']

        if hasattr(self, method):
            method = getattr(self, method)
            method_args = {}

            argspec = inspect.getargspec(method)
            arg_len = len(argspec[0])
            if argspec[3]:
                arg_defaults_len = len(argspec[3])
            else:
                arg_defaults_len = 0

            for arg_num in range(1, arg_len):
                arg_name = argspec[0][arg_num]

                if arg_name in parameters:
                    # decode string parameters to unicode parameters and remove forbidden chars
                    if isinstance(parameters[arg_name], str):
                        try:
                            parameters[arg_name] = parameters[arg_name].decode("utf-8")
                        except ValueError:
                            return json.dumps("ERROR: Parameter '{}' is no valid utf-8 string".format(arg_name))

                        for forbiddenchar in self.forbiddenchars:
                            parameters[arg_name] = parameters[arg_name].replace(forbiddenchar, '')

                    method_args[arg_name] = parameters[arg_name]

                # stop execution if parameter is required
                elif arg_num < arg_len - arg_defaults_len:
                    return json.dumps("ERROR: Not all required parameters have been given")

            result = method(**method_args)
            return json.dumps(result)
        else:
            return json.dumps("ERROR: Method not available")

    def getIp(self):
        """Extract the client IP address from the HTTP request in a proxy compatible way.
           see: http://dev.menttes.com/collective.developermanual/serving/http_request_and_response.html#request-client-ip

        :return: IP address as a string or None if not available
        :rtype: str or None
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
        """
        Escapes html characters.

        :param text: text with possibly not escaped html characters
        :type text: str
        :return: text with escaped html characters
        :rtype: str
        """
        tmptext = text.replace('&','&amp;')
        for key in self.htmlspecialchars:
            tmptext = tmptext.replace(key, self.htmlspecialchars[key])
        return tmptext

    def userHeartbeat(self):
        """
        Updates the activity timestamp of the current user to tell the system, that the user is active.
        """
        session = self.request.SESSION
        user_properties = session.get('user_properties')
        name = user_properties.get('name')
        chat_users = self.cache['chat_users']
        chat_users[name]['date'] = DateTime().timeTime()
        self.cache['chat_users'] = chat_users

    def checkForInactiveUsers(self):
        """
        Removes users who don't call the heart beat method for a defined timeout.
        The check will only be performed, if the last check was more than 5 seconds ago.
        """
        chat = self.context.getParentNode()
        timeout = chat.timeout

        now = DateTime().timeTime()
        if now - self.cache['check_timestamp'] > 5: # Perform this check every 5 seconds
            for user in self.cache['chat_users'].keys():
                if now - self.cache['chat_users'][user].get('date') > timeout: # timeout
                    self.removeUser(user)
            self.cache['check_timestamp'] = now

    def isBanned(self):
        """
        Checks, if current user is banned.

        :return: True, if user is banned, otherwise False
        :rtype: bool
        """
        #ip_address = self.getIp(self.request)
        chat = self.context.getParentNode()
        ban_strategy = chat.banStrategy

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

    def getBanReason(self):
        """
        Tells the client the reason for the ban, if the client was banned.

        :return: ban reason, if the client was banned, otherwise None
        :rtype: str or None
        """
        #ip_address = self.getIp(self.request)
        chat = self.context.getParentNode()
        ban_strategy = chat.banStrategy

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

    def addUser(self, user, is_admin):
        """
        Adds a user to the respective chat session.

        :param user: user name to add
        :type user: str
        :param is_admin: True, if user is moderator
        :type is_admin: bool
        :return: True on success or False, if the user is already in the session
        :rtype: bool
        """
        chat_users = self.cache['chat_users']
        if not chat_users.has_key(user):
            chat_users[user] = {'date': DateTime().timeTime(), 'last_message_sent' : 0, 'is_admin' : is_admin }
            self.cache['chat_users'] = chat_users
            return True
        return False

    def removeUser(self, user):
        """
        Removes a user from respective chat session.

        :param user: user name to remove
        :type user: str
        """
        chat_users = self.cache['chat_users']
        if chat_users.has_key(user):
            del chat_users[user]
            self.cache['chat_users'] = chat_users

    def getUsers(self):
        """
        Returns all user names of respective chat session.

        :return: user names of the chat session
        :rtype: list[str]
        """
        return self.cache['chat_users'].keys()

    def addBannedUser(self, user, reason):
        """
        Flags ban for user with given reason.

        :param user: user name to ban
        :type user: str
        :param reason: reason for banning the user
        :type reason: str
        :return: True, if the flag was added, otherwise False
        :rtype: bool
        """
        banned_chat_users = self.cache['banned_chat_users']
        if not user in banned_chat_users.keys() and user in self.cache['chat_users'].keys():
            banned_chat_users[user] = {'reason': reason}
            self.cache['banned_chat_users'] = banned_chat_users
            self.removeUser(user)
            return True
        return False

    def removeBannedUser(self, user):
        """
        Removes a user from the dict of banned users.

        :param user: user name to remove from the banned users dict
        :type user: str
        :return: True, if the user was removed from the banned users dict, otherwise False (the user wasn't in the dict of banned users)
        :rtype: bool
        """
        banned_chat_users = self.cache['banned_chat_users']
        if user in banned_chat_users.keys():
            del banned_chat_users[user]
            self.cache['banned_chat_users'] = banned_chat_users
            return True
        return False

    def addWarnedUser(self, user, warning):
        """
        Flags warning for user with given text.
        The user gets the message after calling the 'getActions' method.

        :param user: user name to warn
        :type user: str
        :param warning: message which would be send to the user
        :type warning: str
        :return: True, if no warning flag exists for the user and if the user was found in respective chat session, otherwise False
        :rtype: bool
        """
        warned_chat_users = self.cache['warned_chat_users']
        if not user in warned_chat_users.keys() and user in self.cache['chat_users'].keys():
            warned_chat_users[user] = { 'warning': warning }
            self.cache['warned_chat_users'] = warned_chat_users
            return True
        return False

    def removeWarnedUser(self, user):
        """
        Removes warning flag for the given user.

        :param user: user name to remove from the warned users dict
        :type user: str
        :return: True, if a warning flag exists for the user, otherwise False
        :rtype: bool
        """
        warned_chat_users = self.cache['warned_chat_users']
        if user in warned_chat_users.keys():
            del warned_chat_users[user]
            self.cache['warned_chat_users'] = warned_chat_users
            return True
        return False

    def addKickedUser(self, user, reason):
        """
        Flags kick for user with given reason.
        The user will be kicked after calling the 'getActions' method.

        :param user: name of user to kick
        :type user: str
        :param reason: reason for kicking the user
        :type reason: str
        :return: True, if the flag was added, otherwise False
        :rtype: bool
        """
        kicked_chat_users = self.cache['kicked_chat_users']
        if not user in kicked_chat_users.keys() and user in self.cache['chat_users'].keys():
            kicked_chat_users[user] = {'reason': reason}
            self.cache['kicked_chat_users'] = kicked_chat_users
            return True
        return False

    def removeKickedUser(self, user):
        """
        Removes kick flag for the given user.

        :param user: user name to remove from the kicked users dict
        :type user: str
        :return: True, if the user was removed from the kicked users dict, otherwise False (the user wasn't in the kicked users dict)
        :rtype: bool
        """
        kicked_chat_users = self.cache['kicked_chat_users']
        if user in kicked_chat_users.keys():
            del kicked_chat_users[user]
            self.cache['kicked_chat_users'] = kicked_chat_users
            return True
        return False

    def logout(self):
        """
        Removes current user from respective chat session.

        :return: always True
        :rtype: bool
        """
        session=self.request.SESSION
        if session.get('user_properties'):
            user = session.get('user_properties').get('name')
            session.set('user_properties', None)

            self.removeUser(user)
        return True

    def ajaxRegisterMe(self, user, agreement="false", password=None):
        """
        Registers user to respective chat session.
        Before the user was added, this function checks the pre-conditions for entering the session (data protection information agreement, password, user limit, user name restrictions, session state, user ban state).

        :param user: proposed name of the user
        :type user: str
        :param agreement: agreement to data protection information
        :type agreement: str
        :param password: optional password of the session
        :type password: str
        :return: True, if the user was successfully added to the session, otherwise False
        :rtype: bool
        """
        self.request.SESSION.set('user_properties', None)

        context = self.context
        chat = context.getParentNode()

        chat_id = context.chat_id
        user = user.strip()

        if agreement == "false":
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_privacy', default = u'You will not be able to enter the chat without agreeing the privacy notice.'))}}

        chat_password = context.password
        if chat_password and chat_password != password:
            return {'status': {'code':UserStatus.LOGIN_ERROR, 'message':self.context.translate(_(u'login_err_password', default = u'The entered password is not correct.'))}}

        chat_max_users = context.max_users
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
        old_messages_count = chat.oldMessagesCount
        old_messages_minutes = chat.oldMessagesMinutes
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

    def ajaxResetLastAction(self):
        """
        Resets last action to start action to get all messages from the beginning.
        """
        session = self.request.SESSION
        if session.get('user_properties'):
            user_properties = session.get('user_properties')
            user_properties['last_action'] = user_properties.get('start_action')
            user_properties['user_list'] = []
            session.set('user_properties', user_properties)

    def ajaxLogout(self):
        """
        Logs user from respective chat session out.

        :return: always True
        :rtype: bool
        """
        return self.logout()

    def ajaxGetActions(self):
        """
        Returns all actions specific to the calling user since last function call.
        This function also performs several checks.

        :return: dictionary that contains either state information or message and user updates
        :rtype: dict
        """
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
        chat_id = context.chat_id

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

    def ajaxSendMessage(self, message, target_user = None):
        """
        Sends a message to all users, if not target user is given. Otherwise the message is only send to the specified user.
        If the pre-defined minimum delay between two messages wasn't respected, the message will be ignored.
        The maximum message length will be also checked (if the message is too long, it will be truncated).

        :param message: message to send
        :type message: str
        :param target_user: optional user name of whisper target
        :type target_user: str or None
        """
        if not self.isRegistered():
            return

        session=self.request.SESSION
        chat = self.context.getParentNode()

        now = DateTime().timeTime()
        chat_id = self.context.chat_id
        user = session.get('user_properties').get('name')

        chat_users = self.cache['chat_users']

        block_time = chat.blockTime
        max_message_length = chat.maxMessageLength

        self.userHeartbeat()

        if target_user is not None:
            whisper = chat.whisper

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

    def ajaxEditMessage(self, message_id, message):
        """
        Edits an already sent message.
        This action can only performed by moderators.

        :param message_id: id of message to edit
        :type message_id: str
        :param message: text of new message
        :type message: str
        """
        session = self.request.SESSION

        if not self.isAdmin():
            return
        self.userHeartbeat()
        if not message:
            return
        self._dbo.sendAction(chat_id = self.context.chat_id,
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_edit_message',
                                    content = self.html_escape(message),
                                    target = message_id)

    def ajaxDeleteMessage(self, message_id):
        """
        Deletes an already sent message.
        This action can only performed by moderators.

        :param message_id: id of message to delete
        :type message_id: str
        """
        session = self.request.SESSION

        if not self.isAdmin():
            return
        self.userHeartbeat()

        self._dbo.sendAction(chat_id = self.context.chat_id,
                                    user = session.get('user_properties').get('name'),
                                    action = 'mod_delete_message',
                                    target = message_id)

    def ajaxKickUser(self, target_user, message = ""):
        """
        Removes a user from respective chat session.
        This action can only performed by moderators.

        :param target_user: name of user to kick
        :type target_user: str
        :param message: message text which will be send to the user
        :type message: str
        """
        target_user = self.html_escape(target_user)
        session=self.request.SESSION

        if not self.isAdmin():
            return

        # You can not kick yourself
        if session.get('user_properties').get('name') == target_user:
            return

        self.userHeartbeat()

        self.addKickedUser(target_user, message)

    def ajaxWarnUser(self, target_user, message = ""):
        """
        Warns a user in respective chat session.
        This action can only performed by moderators.

        :param target_user: name of user to warn
        :type target_user: str
        :param message: message text which will be send to the user
        :type message: str
        :return: True, if warning flag is set, otherwise False
        :rtype: bool
        """
        target_user = self.html_escape(target_user)
        session=self.request.SESSION

        if not self.isAdmin():
            return
        # You can not warn yourself
        if session.get('user_properties').get('name') == target_user:
            return

        self.userHeartbeat()

        return self.addWarnedUser(target_user, message)

    def ajaxBanUser(self, target_user, message = ""):
        """
        Bans a user from respective chat session.
        This action can only performed by moderators.

        :param target_user: name of user to ban
        :type target_user: str
        :param message: reason text which will be additionally displayed
        :type message: str
        :return: True, if ban flag is set, otherwise False
        :rtype: bool
        """
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
    """
    Default chat session view
    """

    def __call__(self):
        """
        Returns rendered chat session template if requesting user is registered for respective chat session.
        If no registration can be found in the user session, the user will be redirected to the chat overview page.

        :return: rendered template, if user is registered, otherwise None
        :rtype: str or None
        """
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

class ChatSessionLogView(ChatSessionBaseView):
    """
    Chat session log view
    """

    def getLogs(self, REQUEST = None):
        """
        Returns all public chat messages of respective chat session.
        Edited messages will be shown in version of last edit.
        Deleted messages will be shown as empty messages.

        :param REQUEST: request
        :type REQUEST: ZPublisher.HTTPRequest.HTTPRequest
        :return: message list with following information for every message: id, action, date, user, message, target, a_action, a_name
        :rtype: list[dict]
        """
        chat_id = self.context.chat_id
        return self._dbo.getActions(chat_id, 0, 0, 0, '')[:-1]

    def canArchive(self):
        """
        Checks if chat session is closed for more than five minutes.
        This check is used as precondition for the workflow transition 'archive'.

        :return: True, if session is closed for more than five minutes, otherwise False
        :rtype: bool
        """
        now = DateTime().timeTime()
        end_date = self.context.end_date

        if end_date < now - 300:
            return True
        else:
            return False
