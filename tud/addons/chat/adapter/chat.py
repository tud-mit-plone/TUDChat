from zope.container.interfaces import IContainerModifiedEvent
from zope.component import getAdapter

from tud.addons.chat.interfaces import IDatabaseObject

def edited_handler(obj, event):
    """
    Invokes creation of non-existing tables after saving chat object.

    :param obj: chat, which was modified
    :type obj: tud.addons.chat.content.chat.Chat
    :param event: triggered event (used to ignore events which have been triggered by sub-objects)
    :type event: Products.Archetypes.event.ObjectEditedEvent or zope.container.contained.ContainerModifiedEvent
    """
    # ignore addition, removal and reordering of sub-objects
    if IContainerModifiedEvent.providedBy(event):
        return

    adapter_name = obj.getField('database_adapter').get(obj)

    db_adapter = getAdapter(obj, interface=IDatabaseObject, name=adapter_name)
    obj._v_db_adapter = db_adapter
    obj._v_db_adapter.createTables()
