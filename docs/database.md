# Database

## Default database adapter (mysql)
This document describes the database interaction using the delivered "mysql" database adapter.

On chat object creation a table with the configured prefix will be added, if it does not exist. In this table all message-related actions are stored.
The following columns will be used:

Column           | Description
---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
id               | Unique action id
chat_id          | Association to the corresponding chat session
date             | Time of action
user             | Name of action invoker
action           | Action type (new message, new message sent by a moderator, message edited by a moderator, message deleted by a moderator)
content          | Message content (edited message content for edit action; empty for delete action)
target           | Id of referenced message (only for editing and deleting)
whisper_target   | Name of private message recipient


In addition to creating tables, the adapter performs a number of other tasks, such as retrieving actions. Because of the task complexity for getting actions a detailed explanation of this process follows.
The action retrieval is realized by a complex sql query. To get a user specific result the sql query needs five parameters:
*  chat_id: Id of chat session (show only actions of this session)
*  last_action: Maximum action id for this chat session in last request (only newer actions will be received)
*  start_action: Smallest relevant action id (is defined in registration process; if an action references another action with a smaller id then referencing action is ignored)
*  start_action_whisper: Maximum action id when entering chat session (don't show whispered messages with smaller ids)
*  user: Name of requesting user (needed to get whispered messages)

The query itself is a union of 5 subqueries:
1. At first all public messages, which were not retrieved in the last request, will be requested. Only messages that are not referenced by another action (edit or delete) will be retrieved.
2. In the second query all new private messages (given user has to be sender or recipient) will be retrieved.
3. The third query determines actions for edited and deleted messages. If the same message is referenced by multiple actions only the newest action is in the result. Because of two joins information about the referencing and the referenced action will be available. Only actions, which reference already transmitted messages, will be in the result.
4. The fourth query acts similar to the third query. The difference is that modify and delete actions for messages, which the client not know, will be retrieved. This split is caused by different handling on client side. Actions of this block have to be handled as new messages, because they don't reference an existing message. This block is relevant on page reloads for example.
5. The last part determines the maximum action id of this session. This id is later used as 'last_action' parameter.

At the end the result of the union is ordered by id. The result has the following columns:

Column   | Description
-------- | ---------------------------------------------------------------------------------------------------------------------------
id       | Unique action id (ordered ascending; ids of newer actions are greater than ids of older actions)
action   | Action type (new message, new message sent by a moderator, message edited by a moderator, message deleted by a moderator)
date     | Time of (original) message
user     | Sender of (original) message
message  | New or edited message (empty if message was deleted)
target   | Id of referenced message (only for moderator actions)
a_action | Action type of moderator action (message edited or deleted)
a_name   | Invoker of the moderator action
u_action | Action type of referenced action
whisper  | Recipient of private message

## Other database adapters
If you want to implement your own adapter you have to satisfy the interface `IDatabaseObject` (defined in [interfaces.py](../tud/addons/chat/interfaces.py)). After registration of your adapter you can choose your adapter in the chat configuration.
