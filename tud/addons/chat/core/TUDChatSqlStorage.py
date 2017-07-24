# -*- coding: utf-8 -*-

# Zope imports
import Acquisition
import Globals
from AccessControl import ClassSecurityInfo
from DateTime import DateTime

# Products imports
from Products.ZSQLMethods.SQL import SQL as ZSQL
from tud.addons.chat.core.PersistenceInterface import ITUDChatStorage

import logging
logger = logging.getLogger('tud.addons.chat-sql')


class SQL(ZSQL):

    def __init__(self, id, title, connection_id, arguments, template):
        self.id=str(id)
        self.manage_edit(title, connection_id, arguments, template)
        self.max_rows_ = 0

class TUDChatSqlMethods(Globals.Persistent, Acquisition.Implicit):
    """Class containing all sql methods"""

    def __init__(self, sql_connector_id, prefix):
        """ """
        #Create tables
        create_table_query = ()

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

class TUDChatSqlStorage(Globals.Persistent, Acquisition.Implicit):
    """
    TUDChat SQL storage
    """

    __implements__ = (ITUDChatStorage,)
    security = ClassSecurityInfo()
    _message_names = ('date', 'id', 'member', 'message')
    _database_datetimeformat = "%Y/%m/%d %H:%M:%S"

    def __init__(self, sql_connector_id, prefix):
        self.sql_methods = TUDChatSqlMethods(sql_connector_id, prefix)

    def createTables(self):
        if len(self.sql_methods.tableCheck().dictionaries())<1:
            self.sql_methods.createTableChatAction()
            return True
        else:
            return False

    def getMaxSessionId(self):
        result = self.sql_methods.getMaxSessionId().tuples()[0][0]
        if result:
            result = int(result)
        return result

    def getLastAction(self, chat_id):
        result = self.sql_methods.getLastChatAction(chat_id = chat_id)
        last_action = result.tuples()[0][0]
        if last_action is None:
            last_action = 0

        return last_action

    def getStartAction(self, chat_id, old_messages_count = 0, old_messages_minutes = 0):
        if old_messages_count != 0:
            if old_messages_minutes == 0:
                result = self.sql_methods.getStartAction(chat_id = chat_id, old_messages_count = old_messages_count)
            else:
                result = self.sql_methods.getStartActionTimeLimit(chat_id = chat_id, old_messages_count = old_messages_count, old_messages_minutes = old_messages_minutes)
            action = result.tuples()[0][0]
            if action is None:
                start_action = None
            else:
                result = self.sql_methods.getPreviousAction(action_id = action)
                if result.tuples()[0][0] is None:
                    start_action = 0
                else:
                    start_action = result.tuples()[0][0]
        else:
            start_action = None

        if start_action is None:
            start_action = self.getLastAction(chat_id)

        return start_action

    def getActions(self, chat_id, last_action, start_action, start_action_whisper, user, limit = 0):
        results = self.sql_methods.getActions(chat_id = chat_id,
                                                last_action = last_action,
                                                start_action = start_action,
                                                start_action_whisper = start_action_whisper,
                                                user = user)
        if results:
            results = self.dictFromSql(results, names=["id", "action", "date", "user", "message", "target", "a_action", "a_name", "u_action", "whisper_target"])
            if limit:
                results = results[-limit-1:]
            return results
        else:
            return []

    def getRawActionContents(self, chat_id):
        results = self.sql_methods.getRawActionContents(chat_id = chat_id)
        if results:
            return self.dictFromSql(results, names=["id", "content"])
        else:
            return []

    def sendAction(self, chat_id, user, action, content = "", target = None, whisper_target = None):
        newid = self.sql_methods.sendAction(chat_id = chat_id,
                                    user = user,
                                    action = action,
                                    content = content,
                                    target = target,
                                    whisper_target = whisper_target)
        return int(self.dictFromSql(newid, names=('newid',))[0]['newid'])

    def getUsersBySessionId(self, chat_id):
        results = self.sql_methods.getUsersBySessionId(chat_id = chat_id)
        if results:
            return self.dictFromSql(results, ('user',))
        else:
            return []

    def updateUserName(self, chat_id, old_name, new_name):
        result = self.sql_methods.updateUserName(chat_id = chat_id, old_name = old_name, new_name = new_name)
        return True

    def updateActionContent(self, action_id, new_content):
        result = self.sql_methods.updateActionContent(action_id = action_id, new_content = new_content)
        return True

    def deleteActions(self, chat_id):
        result = self.sql_methods.deleteActions(chat_id = chat_id)
        return True

    def dictFromSql(self, results=(), names=()):
        """
        Convert a list of SQL rows to a list of dictionnaries
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
