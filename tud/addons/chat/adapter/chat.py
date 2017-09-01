import logging

from zope.container.interfaces import IContainerModifiedEvent

from tud.addons.chat.core.TUDChatSqlStorage import TUDChatSqlStorage

logger = logging.getLogger('tud.addons.chat')

def edited_handler(obj, event):
    # ignore addition, removal and reordering of sub-objects
    if IContainerModifiedEvent.providedBy(event):
        return

    connector_id = obj.getField('connector_id').get(obj)
    database_prefix = obj.getField('database_prefix').get(obj)

    obj.chat_storage = TUDChatSqlStorage(connector_id, database_prefix)
    obj.chat_storage.createTables()

    if obj.own_database_prefixes.get(connector_id):
        obj.own_database_prefixes[connector_id].add(database_prefix)
    else:
        obj.own_database_prefixes[connector_id] = set([database_prefix])

    logger.info("TUDChat: connector_id = %s" % (connector_id,))
