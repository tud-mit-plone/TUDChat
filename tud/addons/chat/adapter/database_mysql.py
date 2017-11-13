from DateTime import DateTime
from zope.interface import implementer

from Products.ZMySQLDA.DA import Connection
from Products.ZSQLMethods.SQL import SQL as ZSQL

from tud.addons.chat import chatMessageFactory as _
from tud.addons.chat.interfaces import IDatabaseObject

class SQL(ZSQL):
    """
    This class provides database access in form of a stored sql statement.
    """

    def __init__(self, id, title, connection_id, arguments, template):
        """
        Saves sql statement and removes result row limitation.

        :param id: id of sql object
        :type id: str
        :param title: title of sql object
        :type title: str
        :param connection_id: id of object, which provides database access
        :type connection_id: str
        :param arguments: parameters of sql statement (multiple parameters have to be separated by spaces)
        :type arguments: str
        :param template: sql statement
        :type template: str
        """
        self.id = str(id)
        self.manage_edit(title, connection_id, arguments, template)
        self.max_rows_ = 0

class TUDChatSqlMethods():
    """
    This class contains all sql methods.
    """

    def __init__(self, sql_connector_id, prefix):
        """
        Creates needed sql objects.

        :param sql_connector_id: id of object, which provides database access
        :type sql_connector_id: str
        :param prefix: prefix, which is used in database (for action table)
        :type prefix: str
        """
        self.tableCheck = SQL('tableCheck', 'Check for the existence of the action table with a given prefix',
            sql_connector_id, '',
            """
            SELECT table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE table_name='%s_action'
            """ % (prefix))

        self.createTableChatAction = SQL('createTableChatAction', 'Create action table',
            sql_connector_id, '',
            """
            CREATE TABLE IF NOT EXISTS `%s_action` (
                `id`              INT UNSIGNED         NOT NULL AUTO_INCREMENT ,
                `chat_id`        VARCHAR( 255 )       NOT NULL,
                `date`            DATETIME             NOT NULL,
                `user`            VARCHAR( 255 )       NOT NULL,
                `action` ENUM('user_add_message', 'mod_add_message', 'mod_edit_message', 'mod_delete_message') NOT NULL,
                `content`         TEXT                 NOT NULL,
                `target`          INT                      NULL DEFAULT NULL,
                `whisper_target`  VARCHAR( 255 )           NULL DEFAULT NULL,
            PRIMARY KEY (`id` ),
            INDEX ( `chat_id` )
            ) CHARSET=utf8mb4 COLLATE utf8mb4_general_ci;
            """ % (prefix))

        self.getPreviousAction = SQL('getPreviousAction', 'get id of previous action',
            sql_connector_id, 'action_id',
            """
            SELECT MAX(`id`)
            FROM `%s_action`
            WHERE `id` < <dtml-sqlvar action_id type="int"> AND `chat_id` = (SELECT `chat_id`
                                                                             FROM `%s_action`
                                                                             WHERE `id` = <dtml-sqlvar action_id type="int">)
            """ % (prefix, prefix))

        self.getMaxSessionId = SQL('getMaxSessionId', 'get max session id',
            sql_connector_id, '',
            """
            SELECT MAX(`chat_id`) FROM `%s_action`
            """ % (prefix))

        self.getLastChatAction = SQL('getLastChatAction', 'get the last action from an active chat by chat_id',
            sql_connector_id, 'chat_id',
            """
            SELECT      MAX(id) AS action_id
            FROM `%s_action`
            WHERE       chat_id = <dtml-sqlvar chat_id type="int">
            """ % (prefix))

        self.getStartAction = SQL('getStartAction', 'get the start action so that a given number of old messages will be shown',
            sql_connector_id, 'chat_id old_messages_count',
            """
            SELECT MIN(id)
            FROM (SELECT id
                  FROM `%s_action`
                  WHERE chat_id = <dtml-sqlvar chat_id type="int"> AND action LIKE '%%_add_message'
                  ORDER BY id DESC
                  LIMIT <dtml-sqlvar old_messages_count type="int">) AS action
            """ % (prefix))

        self.getStartActionTimeLimit = SQL('getStartActionTimeLimit', 'get the start action so that a given number of old messages with a given maximum age will be shown',
            sql_connector_id, 'chat_id old_messages_count old_messages_minutes',
            """
            SELECT MIN(id)
            FROM (SELECT id
                  FROM `%s_action`
                  WHERE chat_id = <dtml-sqlvar chat_id type="int"> AND `date` > DATE_SUB(NOW(), INTERVAL <dtml-sqlvar old_messages_minutes type="int"> MINUTE) AND action LIKE '%%_add_message'
                  ORDER BY id DESC
                  LIMIT <dtml-sqlvar old_messages_count type="int">) AS action
            """ % (prefix))

        self.getActions = SQL('getActions', 'get actions of a chat',
            sql_connector_id, 'chat_id last_action start_action start_action_whisper user',
            """
            SELECT id, action, date, user, content AS message, NULL AS target, '' AS a_action, '' AS a_name, '' AS u_action, NULL AS whisper_target
            FROM `%s_action`
            WHERE id NOT IN
              (SELECT target
               FROM `%s_action`
               WHERE target IS NOT NULL AND chat_id = <dtml-sqlvar chat_id type="int">)
              AND chat_id = <dtml-sqlvar chat_id type="int">
              AND id > <dtml-sqlvar last_action type="int">
              AND action LIKE '%%add_message'
              AND whisper_target IS NULL
            UNION ALL
            SELECT id, action, date, user, content AS message, NULL AS target, '' AS a_action, '' AS a_name, '' AS u_action, whisper_target
            FROM `%s_action`
            WHERE chat_id = <dtml-sqlvar chat_id type="int">
              AND id > <dtml-sqlvar last_action type="int">
              AND id > <dtml-sqlvar start_action_whisper type="int">
              AND action LIKE '%%add_message'
              AND whisper_target IS NOT NULL
              AND (whisper_target = <dtml-sqlvar user type="string"> OR user = <dtml-sqlvar user type="string">)
            UNION ALL
            SELECT action.a_id AS 'id', a_action.action AS action, u_action.date AS date, u_action.user AS user, a_action.content AS content, action.u_id as target, a_action.action AS a_action, a_action.user AS a_name, u_action.action AS u_action, NULL AS whisper_target
            FROM (SELECT target AS 'u_id', MAX(id) AS 'a_id'
                  FROM `%s_action`
                  WHERE (action='mod_delete_message' OR action='mod_edit_message')
                    AND chat_id = <dtml-sqlvar chat_id type="int">
                    AND id > <dtml-sqlvar last_action type="int">
                    AND <dtml-sqlvar last_action type="int"> >= target
                    AND target >= <dtml-sqlvar start_action type="int">
                  GROUP BY target) AS action
            INNER JOIN `%s_action` AS a_action ON action.a_id = a_action.id
            INNER JOIN `%s_action` AS u_action ON action.u_id = u_action.id
            UNION ALL
            SELECT action.u_id AS 'id', u_action.action AS action, u_action.date AS date, u_action.user AS user, a_action.content AS content, NULL as target, a_action.action AS a_action, a_action.user AS a_name, '' AS u_action, NULL AS whisper_target
            FROM (SELECT target AS 'u_id', MAX(id) AS 'a_id'
                  FROM `%s_action`
                  WHERE (action='mod_delete_message' OR action='mod_edit_message')
                    AND chat_id = <dtml-sqlvar chat_id type="int">
                    AND id > <dtml-sqlvar last_action type="int">
                    AND <dtml-sqlvar last_action type="int"> < target
                    AND target >= <dtml-sqlvar start_action type="int">
                  GROUP BY target) AS action
            INNER JOIN `%s_action` AS a_action ON action.a_id = a_action.id
            INNER JOIN `%s_action` AS u_action ON action.u_id = u_action.id
            UNION ALL
            SELECT MAX(id) AS 'ID', '' AS 'action', NOW() AS 'date', '' AS 'user', '' AS 'message', '' AS 'target', '' AS 'a_action', '' AS 'a_name', '' AS u_action, '' AS whisper
            FROM `%s_action`
            WHERE chat_id=<dtml-sqlvar chat_id type="int">
            ORDER BY `ID` ASC
            """ % (prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix))
        self.getActions.max_rows_ = 0

        self.getRawActionContents = SQL('getRawActionContents', 'get raw actions of a chat session',
            sql_connector_id, 'chat_id',
            """
            SELECT id, content
            FROM `%s_action`
            WHERE chat_id = <dtml-sqlvar chat_id type="int">
            """ % (prefix))
        self.getRawActionContents.max_rows_ = 0

        self.sendAction = SQL('sendAction', 'send an action',
            sql_connector_id, 'chat_id user action content target whisper_target',
            """
            INSERT INTO `%s_action` (
                `chat_id`, `date`, `user`, `action`, `content`, `target`, `whisper_target`)
            VALUES (
                <dtml-sqlvar chat_id type="int">,
                NOW(),
                <dtml-sqlvar user type="string">,
                <dtml-sqlvar action type="string">,
                <dtml-sqlvar content type="string">,
                <dtml-sqlvar target type="int">,
                <dtml-sqlvar whisper_target type="string">
            );
            <dtml-var sql_delimiter>
            SELECT LAST_INSERT_ID() AS newid
            """ % (prefix))

        self.getUsersBySessionId = SQL('getUsersBySessionId', 'get users of a chat session',
            sql_connector_id, 'chat_id',
            """
            SELECT DISTINCT user
            FROM            `%s_action`
            WHERE           chat_id = <dtml-sqlvar chat_id type="int">
            """ % (prefix))

        self.updateUserName = SQL('updateUserName', 'change name of user of a chat session',
            sql_connector_id, 'chat_id old_name new_name',
            """
            UPDATE `%s_action`
            SET user = <dtml-sqlvar new_name type="string">
            WHERE chat_id = <dtml-sqlvar chat_id type="int"> AND user = <dtml-sqlvar old_name type="string">
            """ % (prefix))

        self.updateActionContent = SQL('updateActionContent', 'change content of an action',
            sql_connector_id, 'action_id new_content',
            """
            UPDATE `%s_action`
            SET content = <dtml-sqlvar new_content type="string">
            WHERE id = <dtml-sqlvar action_id type="int">
            """ % (prefix))

        self.deleteActions = SQL('deleteActions', 'delete actions of a chat session',
            sql_connector_id, 'chat_id',
            """
            DELETE FROM `%s_action`
            WHERE chat_id = <dtml-sqlvar chat_id type="string">
            """ % (prefix))

@implementer(IDatabaseObject)
class DatabaseMySQL():
    """
    Implementation for MySQL databases
    """

    def __init__(self, chat):
        """
        Prepares database access. Needed information is obtained from chat object.

        :param chat: chat object
        :type chat: tud.addons.chat.content.chat.Chat
        """
        self.chat = chat

        sql_connector_id = chat.connector_id
        prefix = chat.database_prefix
        self.sql_methods = TUDChatSqlMethods(sql_connector_id, prefix)

        # set acquisition context for sql methods
        for query_name, query in self.sql_methods.__dict__.items():
            setattr(self.sql_methods, query_name, query.__of__(self.chat))

    def validate(self, REQUEST):
        """
        Validates connector id, which is given via request.
        An error is raised if no object with given id could be found or if object found has wrong type.

        :param REQUEST: request with form data
        :type REQUEST: ZPublisher.HTTPRequest.HTTPRequest
        """
        sql_connector_id = REQUEST.get('connector_id', '')
        try:
            zmysql = getattr(self.chat, sql_connector_id)
            if not isinstance(zmysql, Connection):
                raise ValueError(_(u'validation_object_is_not_zmysql_object', default=u'The chosen object is not a ZMySQL object.'))
        except AttributeError:
            raise ValueError(_(u'validation_object_not_found', default=u'No object with this ID was found in any subpath.'))

    def prefixInUse(self, REQUEST):
        """
        Checks if prefix (received from request) is in use in the database.

        :param REQUEST: request with form data
        :type REQUEST: ZPublisher.HTTPRequest.HTTPRequest
        :return: True, if prefix is in use, otherwise False
        :rtype: bool
        """
        sql_connector_id = REQUEST.get('connector_id', '')
        prefix = REQUEST.get('database_prefix', '')

        zmysql = getattr(self.chat, sql_connector_id)
        dbc = zmysql()
        tables = [table['table_name'] for table in dbc.tables() if table['table_type'] == 'table']
        used_prefixes = [table[:-7].encode('utf-8') for table in tables if table.endswith(u'_action')]
        return prefix in used_prefixes

    def createTables(self):
        """
        Creates action table, if it not exists, with configured prefix.

        :return: True, if action table was created, otherwise False
        :rtype: bool
        """
        if len(self.sql_methods.tableCheck().dictionaries()) < 1:
            self.sql_methods.createTableChatAction()
            return True
        else:
            return False

    def getMaxSessionId(self):
        """
        Determines maximum session id.

        :return: maximum session id, if at least one entry exists in action table, otherwise None
        :rtype: int or None
        """
        result = self.sql_methods.getMaxSessionId().tuples()[0][0]
        if result:
            result = int(result)
        return result

    def getLastAction(self, chat_id):
        """
        Determines largest action id for a given chat session id.

        :param chat_id: id of chat session
        :type chat_id: int
        :return: largest action id
        :rtype: int
        """
        result = self.sql_methods.getLastChatAction(chat_id=chat_id)
        last_action = result.tuples()[0][0]
        if last_action is None:
            last_action = 0

        return last_action

    def getStartAction(self, chat_id, old_messages_count=0, old_messages_minutes=0):
        """
        Determines id of first relevant action. This id is important, for example, when entering chat session.
        If count of old messages is 0 then last action represents the start action id. The parameter for the message age is ignored in this case.
        If count of old messages is larger than 0, then the id of the start action is determined in such a way that the configured maximum number of messages is displayed.
        If count of old messages is larger than 0 and the parameter for message age is larger than 0, only messages that are not older than the configured number of minutes are displayed.

        :param chat_id: id of chat session
        :type chat_id: int
        :param old_messages_count: number of recent messages to show
        :type old_messages_count: int
        :param old_messages_minutes: maximum age of recent messages in minutes
        :type old_messages_minutes: int
        :return: start action id
        :rtype: int
        """
        if old_messages_count != 0:
            if old_messages_minutes == 0:
                result = self.sql_methods.getStartAction(chat_id=chat_id, old_messages_count=old_messages_count)
            else:
                result = self.sql_methods.getStartActionTimeLimit(chat_id=chat_id, old_messages_count=old_messages_count, old_messages_minutes=old_messages_minutes)
            action = result.tuples()[0][0]
            if action is None:
                start_action = None
            else:
                result = self.sql_methods.getPreviousAction(action_id=action)
                if result.tuples()[0][0] is None:
                    start_action = 0
                else:
                    start_action = result.tuples()[0][0]
        else:
            start_action = None

        if start_action is None:
            start_action = self.getLastAction(chat_id)

        return start_action

    def getActions(self, chat_id, last_action, start_action, start_action_whisper, user, limit=0):
        """
        Returns list of new actions since last request.
        A detailed description can be found in database documentation.

        :param chat_id: id of chat session
        :type chat_id: int
        :param last_action: largest action id for this chat session in last request
        :type last_action: int
        :param start_action: smallest relevant action id (actions, which reference actions with a smaller id than this, will be ignored)
        :type start_action: int
        :param start_action_whisper: smallest action id for private messages (no private message with a smaller id will be shown)
        :type start_action_whisper: int
        :param user: name of the user (needed to get private messages)
        :type user: str
        :param limit: maximum amount of actions to retrieve
        :type limit: int
        :return: actions
        :rtype: list[dict]
        """
        results = self.sql_methods.getActions(chat_id=chat_id,
                                                last_action=last_action,
                                                start_action=start_action,
                                                start_action_whisper=start_action_whisper,
                                                user=user)
        if results:
            results = self.dictFromSql(results, names=["id", "action", "date", "user", "message", "target", "a_action", "a_name", "u_action", "whisper_target"])
            if limit:
                results = results[-limit-1:]
            return results
        else:
            return []

    def getRawActionContents(self, chat_id):
        """
        Returns all actions of specified chat session.
        No actions like editing or deleting of messages will be interpreted.
        This method is used for anonymization.

        :param chat_id: id of chat session
        :type chat_id: int
        :return: raw actions
        :rtype: list[dict]
        """
        results = self.sql_methods.getRawActionContents(chat_id=chat_id)
        if results:
            return self.dictFromSql(results, names=["id", "content"])
        else:
            return []

    def sendAction(self, chat_id, user, action, content="", target=None, whisper_target=None):
        """
        Adds specified action to the database.

        :param chat_id: id of chat session
        :type chat_id: int
        :param user: name of invoking user
        :type user: str
        :param action: action type (have to be one of: 'user_add_message', 'mod_add_message', 'mod_edit_message', 'mod_delete_message')
        :type action: str
        :param content: content of new or edited message (empty on delete action)
        :type content: str
        :param target: id of referenced action (only for action types 'mod_edit_message' and 'mod_delete_message')
        :type target: int or None
        :param whisper_target: recipient name for private messages
        :type whisper_target: str or None
        :return: id of added action
        :rtype: int
        """
        newid = self.sql_methods.sendAction(chat_id=chat_id,
                                    user=user,
                                    action=action,
                                    content=content,
                                    target=target,
                                    whisper_target=whisper_target)
        return int(self.dictFromSql(newid, names=('newid',))[0]['newid'])

    def getUsersBySessionId(self, chat_id):
        """
        Returns all names of users, which have at least one action transmitted in the specified session.
        This method is used for anonymization.

        :param chat_id: id of chat session
        :type chat_id: int
        :return: user names (every dictionary contains only the key 'user')
        :rtype: list[dict]
        """
        results = self.sql_methods.getUsersBySessionId(chat_id = chat_id)
        if results:
            return self.dictFromSql(results, ('user',))
        else:
            return []

    def updateUserName(self, chat_id, old_name, new_name):
        """
        Changes user names in column 'user' of action table for specified session.
        This method is used for anonymization.

        :param chat_id: id of chat session
        :type chat_id: int
        :param old_name: user name to be replaced
        :type old_name: str
        :param new_name: user name to replaced with
        :type new_name: str
        :return: always True
        :rtype: bool
        """
        self.sql_methods.updateUserName(chat_id=chat_id, old_name=old_name, new_name=new_name)
        return True

    def updateActionContent(self, action_id, new_content):
        """
        Updates value of 'content' column of action table for specified session and action.
        This method is used for anonymization.

        :param chat_id: id of chat session
        :type chat_id: int
        :param action_id: id of concerned action
        :type action_id: int
        :param new_content: new value for 'content' column
        :type new_content: str
        :return: always True
        :rtype: bool
        """
        self.sql_methods.updateActionContent(action_id=action_id, new_content=new_content)
        return True

    def deleteActions(self, chat_id):
        """
        Deletes all actions of specified chat session.
        This method is called on session deletion.

        :param chat_id: id of chat session
        :type chat_id: int
        :return: always True
        :rtype: bool
        """
        self.sql_methods.deleteActions(chat_id=chat_id)
        return True

    def dictFromSql(self, results=(), names=()):
        """
        Converts a list of SQL rows to a list of dictionaries.
        During this process the time zone of DateTime objects will be fixed.

        :param results: sql result object
        :type results: tuple or Shared.DC.ZRDB.Results.Results
        :param names: wanted keys of result dictionaries
        :type names: tuple or list
        :return: dictionaries with keys defined in parameter 'names'
        :rtype: list[dict]
        """
        rows = []
        for sql_row in results.dictionaries():
            mapping = {}
            for col_name in names:
                if isinstance(sql_row.get(col_name), DateTime):
                    #fix to get DateTime objects in corret timezone
                    dobj = sql_row.get(col_name).toZone('UTC')
                    mapping[col_name] = DateTime(dobj.Date()+' '+dobj.Time())
                else:
                    mapping[col_name] = sql_row.get(col_name)
            rows.append(mapping)
        return rows
