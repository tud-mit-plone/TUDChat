# Architecture

## Overview
This product introduces two new content types: "Chat" and "ChatSession".

## Chat object
The chat object is a container object for chat sessions. All sessions use the database configured in the chat object. Multiple chat objects can use the same database. To prohibit conflicts you have to define a unique table prefix for each chat object.

### Default view
The default view provides the chat login form. If more than one chat session is active, the user can choose one to take part in. If sessions have been planned, these sessions are listed at the bottom. Furthermore, this view shows information about data protection depending on the configuration if at least one open chat session exists.

### Chat session management view
This view lists all chat sessions with session specific information. If the session is editable, an edit link is shown. For archived chat sessions, links to their chat logs are provided.

## Chat session object
This object realizes the web chat. You can configure session specific options like start and end time. It is also possible to define a limit for the number of participants and to set a password for the session.

### Default view
To access the default view, a visitor has to sign in with a nickname on the default chat view. Otherwise he will be redirected to the chat object. The template of the default view defines some data, which are needed by the JavaScript files.

### Ajax view
This view represents the JavaScript communication endpoint. To communicate with this endpoint you have to specify with the get parameter 'method' your requested method. The call method of this browser view searches for the requested method, which has to be prefixed with 'ajax' and calls it with the given parameters. The result of the method will be transmitted to the client in JSON format.

This view is also responsible for the user management. Therefore, a user specific and a shared storage is needed.
The following information are stored in the user session:

Name                   | Type   | Content
---------------------- | ------ | ---------------------------------------------------------------------------
name                   | str    | Chosen nickname
start_action           | int    | Id of the first action that was sent to this client on chat login (calculated on the basis of the chat settings)
start_action_whisper   | int    | Id of the last action that was sent before this client logged in
last_action            | int    | Id of the last action that was sent to this client, value changes over time
user_list              | list   | List of users known to the client
chat_room_check        | int    | Timestamp used for check if the chat session is still active

The following information are stored in the shared cache:

Name                 | Type   | Content
-------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
chat_users           | dict   | Dictionary with all users of the chat session
kicked_chat_users    | dict   | Dictionary with all users marked for kicking
warned_chat_users    | dict   | Dictionary with all users marked for warning
banned_chat_users    | dict   | Dictionary with all users marked for banning
check_timestamp      | int    | Timestamp used to check for inactive users

The shared "chat_users" dictionary contains the following information for each user:
*  date: Timestamp needed to check for inactive users (will be updated by many user actions)
*  last_message_sent: Timestamp of the last sent message (needed to enforce configured delay between two messages)
*  is_admin: True if the user is a moderator otherwise False

The dictionaries "kicked_chat_users", "warned_chat_users" and "banned_chat_users" store user names associated with the messages. In case of kicked and banned users the message is optional.

#### Ajax method 'getActions'
To stay informed about the current state and new messages, the ajax method 'getActions' is used. This method is called periodically by the client. The time interval can be configured via the chat object.
The function can be roughly divided into two phases. First some pre-checks have to be done:
*  Check if user is banned
*  Check if user is registered
*  Check if user is warned
*  Check if user is kicked
*  Check if session is still active (not checked on every call)

If no pre-check stops the method, execution phase two starts. In this phase all message related actions will be retrieved from the database. Furthermore all user changes will be determined. The JSON result has the following format:

    {
      'status':{
        'code': integer,                       // state code
        'message': string                      // human readable message
      },
      'messages':{
        'new': [ {                             // list of new messages (optional)
          'id': integer,                       // message id
          'date': string,                      // time of the message
          'name': string,                      // sender of the message
          'message': string,                   // message content
          'attributes':[ {                     // list of attributes (optional)
            'admin_message: true               // true if the sender is a moderator (optional)
          } ... ],                             // .. further attributes
        }, ... ],                              // .. further new messages
        'to_delete': [ {                       // list of deleted messages (optional)
          'id': integer,                       // id of the deleted message
          'date': string,                      // time of the message
          'name': string,                      // sender of the message
          'attributes':[ {                     // list of attributes
            'a_action': 'mod_delete_message',  // moderator action
            'a_name': string,                  // nickname of the moderator
          } ... ],                             // .. further attributes (optional)
        }, ... ],                              // .. further deleted messages
       'to_edit': [ {                          // list of edited messages (optional)
          'id': integer,                       // id of the message
          'date': string,                      // time of the message
          'name': string,                      // sender of the message
          'message': string,                   // edited message content
          'attributes':[ {                     // list of attributes
            'a_action': 'mod_edit_message',    // moderator action
            'a_name': string,                  // nickname of the moderator
          } ... ],                             // .. further attributes (optional)
        }, ... ],                              // .. further edited messages
      },
      'users':{
        'new': [ {                             // list of users to add
          'name': string,                      // nickname of the user
          'is_admin': boolean,                 // true if user is moderator
        } ... ],                               // further users to add
        'to_delete': [                         // list of users to delete
          string,                              // nickname of the user
          ...                                  // further nicknames
        ]
      }
    }

This method returns one of the following state codes:

State code         | Meaning                                                     | Operation
------------------ | ----------------------------------------------------------- | -----------------------------------------------------------------------------------------------
OK (0)             | Everything is all right.                                    | Received actions will be interpreted.
NOT_AUTHORIZED (1) | User is not authorized.                                     | User will be redirected to the login page.
KICKED (2)         | User will be removed from the chat session.                 | User will be redirected to the login page. An optional message will be shown.
BANNED (3)         | User will be permanently removed from the chat session.     | User will get two cookies and will be redirected to the login page. An optional message will be shown.
WARNED (5)         | User will be warned.                                        | User will get a popup with a defined message.

### Log view
This view is only available for archived chat sessions. On top this view basic information like start and end time of the chat session is shown. Below the basic information all messages of the chat session are listed. Once a session got archived, all nicknames will be replaced by anonymous names.
