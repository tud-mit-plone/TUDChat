# -*- coding: utf-8 -*-

import datetime

# Zope imports
import Acquisition
import Globals
from AccessControl import ClassSecurityInfo
from Interface import Interface

# Products imports
from Products.ZSQLMethods.SQL import SQL as ZSQL
from Products.TUDChat.core.PersistenceInterface import ITUDChatStorage

import logging
logger = logging.getLogger('TUDChat-SQL')


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
        
        self.tableCheck = SQL('tableCheck', 'Check for the existence of the action und session table with a given prefix',
            sql_connector_id, '',
            """
            SELECT table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE table_name='%s_action' OR table_name='%s_session'
            """ % (prefix, prefix))
        
        self.createTableChatSession = SQL('createTableChatSession', 'Create session table',
            sql_connector_id, '',
            """
            CREATE TABLE IF NOT EXISTS `%s_session` (
                `id`          INT UNSIGNED         NOT NULL AUTO_INCREMENT,
                `name`        VARCHAR( 255 )       NOT NULL,
                `description` VARCHAR( 255 )       DEFAULT NULL,
                `password`    VARCHAR( 30 )        DEFAULT NULL,
                `max_users`   INT UNSIGNED         DEFAULT NULL,
                `start`       DATETIME             DEFAULT NULL,
                `end`         DATETIME             DEFAULT NULL,
            PRIMARY KEY (`id` )
            );
            """ % (prefix))

        self.createTableChatAction = SQL('createTableChatAction', 'Create action table',
            sql_connector_id, '',
            """
            CREATE TABLE IF NOT EXISTS `%s_action` (
                `id`              INT UNSIGNED         NOT NULL AUTO_INCREMENT ,
                `chat_uid`        VARCHAR( 255 )       NOT NULL,
                `date`            DATETIME             NOT NULL,
                `user`            VARCHAR( 255 )       NOT NULL,
                `action` ENUM( 'add_message', 'edit_message', 'delete_message', 'open_chat', 'close_chat', 'ban_user', 'unban_user' ) NOT NULL, 
                `content`         TEXT                 NOT NULL,
                `target`          INT                      NULL DEFAULT NULL,
            PRIMARY KEY (`id` ),
            INDEX ( `chat_uid` )
            );
            """ % (prefix))
            
        self.createChatSession = SQL('createChatSession', 'Create chat session',
            sql_connector_id, 'name description starttime endtime password max_users',
            """
            INSERT INTO `%s_session` (
                `name`,
                `description`,
                `start`,
                `end`,
                `password`,
                `max_users` )
            VALUES (
                <dtml-sqlvar name type="string">,
                <dtml-sqlvar description type="string">,
                <dtml-sqlvar starttime type="string">,
                <dtml-sqlvar endtime type="string">,
                <dtml-sqlvar password type="string">,
                <dtml-sqlvar max_users type="string">
            );
            <dtml-var sql_delimiter>
            SELECT LAST_INSERT_ID() AS newid
            """ % (prefix))
        
        self.deleteChatSession = SQL('deleteChatSession', 'Delete chat session',
            sql_connector_id, 'chat_uid',
            """
            DELETE FROM `%s_session`
            WHERE id = <dtml-sqlvar chat_uid type="string">
            """ % (prefix)) 

        self.closeChatSession = SQL('closeChatSession', 'close chat session',
            sql_connector_id, 'chat_uid', 
            """
            UPDATE `%s_action`
            SET         is_open = 0,
                        closed = NOW()
            WHERE
                    id         = <dtml-sqlvar chat_uid type="int">
            """ % (prefix))
        
        self.getChatSessions = SQL('getChatSessions', 'get all planned and active chat sessions',
            sql_connector_id, '', 
            """
            SELECT      *
            FROM        `%s_session`
            WHERE       (end > NOW() OR end is NULL)
            ORDER BY    id
            """ % (prefix))
        
        self.getActiveChatSessions = SQL('getActiveChatSessions', 'get active chat sessions',
            sql_connector_id, '', 
            """
            SELECT      *
            FROM        `%s_session`
            WHERE       (end > NOW() OR end is NULL)
            AND         start < NOW()
            """ % (prefix))
        
        self.getNextChatSessions = SQL('getNextChatSessions', 'get next chat session',
            sql_connector_id, '', 
            """
            SELECT      *
            FROM        `%s_session`
            WHERE       start > NOW()
            ORDER BY    start, id
            """ % (prefix))
        self.getNextChatSessions.max_rows_ = 0
        
        self.getLastChatAction = SQL('getLastChatAction', 'get the last action from an active chat by chat_uid',
            sql_connector_id, 'chat_uid',
            """
            SELECT      MAX(id) AS action_id
            FROM        `%s_action`
            WHERE       chat_uid = <dtml-sqlvar chat_uid type="int">
            """ % (prefix))
  
        self.getChatSessionById = SQL('getChatSessionById', 'get chat session by its id',
            sql_connector_id, 'chat_uid',
            """
            SELECT        *, start<NOW() and NOW()<end as active
            FROM         `%s_session`
            WHERE         id = <dtml-sqlvar chat_uid type="int">
            """ % (prefix))

        self.getActions = SQL('getActions', 'get actions of a chat',
            sql_connector_id, 'chat_uid last_action start_action',
            """
            SELECT id, action, date, user, content AS message, NULL AS target, '' AS a_action, '' AS a_name
            FROM `%s_action`
            WHERE id NOT IN
              (SELECT target
               FROM `%s_action`
               WHERE target IS NOT NULL AND chat_uid = <dtml-sqlvar chat_uid type="int">)
              AND chat_uid = <dtml-sqlvar chat_uid type="int">
              AND id > <dtml-sqlvar last_action type="int">
              AND action='add_message'
            UNION ALL
            SELECT action.a_id AS 'id', a_action.action AS action, u_action.date AS date, u_action.user AS user, a_action.content AS content, action.u_id as target, a_action.action AS a_action, a_action.user AS a_name
            FROM (SELECT target AS 'u_id', MAX(id) AS 'a_id'
                  FROM `%s_action`
                  WHERE (action='delete_message' OR action='edit_message')
                    AND chat_uid = <dtml-sqlvar chat_uid type="int">
                    AND id > <dtml-sqlvar last_action type="int">
                    AND <dtml-sqlvar last_action type="int"> >= target
                    AND target >= <dtml-sqlvar start_action type="int">
                  GROUP BY target) AS action
            INNER JOIN `%s_action` AS a_action ON action.a_id = a_action.id
            INNER JOIN `%s_action` AS u_action ON action.u_id = u_action.id
            UNION ALL
            SELECT action.u_id AS 'id', 'add_message' AS action, u_action.date AS date, u_action.user AS user, a_action.content AS content, NULL as target, a_action.action AS a_action, a_action.user AS a_name
            FROM (SELECT target AS 'u_id', MAX(id) AS 'a_id'
                  FROM `%s_action`
                  WHERE (action='delete_message' OR action='edit_message')
                    AND chat_uid = <dtml-sqlvar chat_uid type="int">
                    AND id > <dtml-sqlvar last_action type="int">
                    AND <dtml-sqlvar last_action type="int"> < target
                    AND target >= <dtml-sqlvar start_action type="int">
                  GROUP BY target) AS action
            INNER JOIN `%s_action` AS a_action ON action.a_id = a_action.id
            INNER JOIN `%s_action` AS u_action ON action.u_id = u_action.id
            UNION ALL
            SELECT MAX(id) AS 'ID', '' AS 'action', NOW() AS 'date', '' AS 'user', '' AS 'message', '' AS 'target', '' AS 'a_action', '' AS 'a_name'
            FROM `%s_action`
            WHERE chat_uid=<dtml-sqlvar chat_uid type="int">
            ORDER BY `ID` ASC
            """ % (prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix))
        self.getActions.max_rows_ = 0
        
        self.getActionById = SQL('getActionById', 'get action by its id',
            sql_connector_id, 'action_id',
            """
            SELECT        *
            FROM         `%s_action`
            WHERE         id = <dtml-sqlvar action_id type="string">
            """ % (prefix))
            
        self.sendAction = SQL('sendAction', 'send an action',
            sql_connector_id, 'chat_uid user action content target',
            """
            INSERT INTO `%s_action` (
                `chat_uid`, `date`, `user`, `action`, `content`, `target`  )
            VALUES (
                <dtml-sqlvar chat_uid type="int">,
                NOW(),
                <dtml-sqlvar user type="string">,
                <dtml-sqlvar action type="string">,
                <dtml-sqlvar content type="string">,
                <dtml-sqlvar target type="int">
            );
            <dtml-var sql_delimiter>
            SELECT LAST_INSERT_ID() AS newid            
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
        if len(self.sql_methods.tableCheck().dictionaries())<2:
            self.sql_methods.createTableChatSession()
            self.sql_methods.createTableChatAction()
            return True
        else:
            return False
    
    def createChatSession(self, name, description = "NULL", start = "NOW()", end = "NULL", password = None, max_users = "NULL"):
        result = self.sql_methods.createChatSession(name =name, description=description, starttime = start, endtime = end, password = password, max_users = max_users)
        chat_uid = int(self.dictFromSql(result, names=('newid',))[0]['newid'])
        return chat_uid
    
    def deleteChatSession(self, id):
        result = self.sql_methods.deleteChatSession(chat_uid = id)
        return True
        
    def getChatSession(self, chat_uid):
        result = self.sql_methods.getChatSessionById(chat_uid = chat_uid)
        session_dict = self.dictFromSql(result, names=('id','name','description','password','max_users','start','end','active',))[0]
        return session_dict
        
    def closeChatSession(self, chat_uid):
        self.sql_methods.closeChatSession(chat_uid = chat_uid)
        return True
    
    def getChatSessions(self):
        result = self.sql_methods.getChatSessions()
        return self.dictFromSql(result, ('id','name','description','password','max_users','start','end',))
    
    def getActiveChatSessions(self):
        result = self.sql_methods.getActiveChatSessions()
        return self.dictFromSql(result, ('id','name','description','password','max_users','start','end',))
    
    def getNextChatSessions(self):
        result = self.sql_methods.getNextChatSessions()
        return self.dictFromSql(result, ('id','name','start','end',))
    
    def getLastChatAction(self, chat_uid):
        result = self.sql_methods.getLastChatAction(chat_uid = chat_uid)
        result_dict = self.dictFromSql(result, ('action_id',))
        return result_dict[0]['action_id'] or 0
    
    def getActions(self, chat_uid, last_action, start_action):
        results = self.sql_methods.getActions(chat_uid = chat_uid,
                                                last_action = last_action,
                                                start_action = start_action)
        if results:
            #logger.info(results)
            #logger.info(results.dictionaries())
            results = self.dictFromSql(results, names=["id", "action", "date", "user", "message", "target", "a_action", "a_name"])
            #logger.info(results)
            return results
        else:
            return []
            
    def sendAction(self, chat_uid, user, action, content = "", target = None):
        newid = self.sql_methods.sendAction(chat_uid = chat_uid,
                                    user = user,
                                    action = action,
                                    content = content,
                                    target = target)
        return int(self.dictFromSql(newid, names=('newid',))[0]['newid'])

    def dictFromSql(self, results=(), names=()):
        """ 
        Convert a list of SQL rows to a list of dictionnaries
        """
        rows = []
        for sql_row in results.dictionaries():
            mapping = {}
            for col_name in names:
                mapping[col_name] = sql_row.get(col_name)
            rows.append(mapping)
        return rows
