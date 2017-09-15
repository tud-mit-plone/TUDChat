# -*- coding: utf-8 -*-

# Python imports
import logging

# Zope imports
from zope.interface import implementer

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, IntegerField, DateTimeField
from Products.Archetypes.public import StringWidget, IntegerWidget, CalendarWidget

from raptus.multilanguagefields import fields as MultiLanguageFields
from raptus.multilanguagefields import widgets as MultiLanguageWidgets

from tud.addons.chat.interfaces import IChatSession
from tud.addons.chat.validators import LengthValidator, MinMaxValidator

logger = logging.getLogger('tud.addons.chat')

ChatSessionSchema = schemata.ATContentTypeSchema.copy() + Schema((
    MultiLanguageFields.TextField('description',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = MultiLanguageWidgets.TextAreaWidget(
            label        = "Beschreibung",
            description  = "Wird über dem Chatfenster angezeigt."
        )
    ),
    DateTimeField('start_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = "Beginn",
            description  = "Datum und Zeit, zu der die Chatsitzung beginnt."
        )
    ),
    DateTimeField('end_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = "Ende",
            description  = "Datum und Zeit, zu der die Chatsitzung endet."
        )
    ),
    MultiLanguageFields.StringField('welcome_message',
        required           = False,
        default            = '',
        widget             = MultiLanguageWidgets.StringWidget(
            label        = "Willkommensnachricht",
            description  = "Diese Nachricht wird jedem Teilnehmer nach Betreten der Chatsitzung angezeigt."
        )
    ),
    StringField('password',
        required           = False,
        default            = '',
        validators         = (LengthValidator('max_30_check', maximum = 30), ),
        widget             = StringWidget(
            label        = "Passwort",
            description  = "Geben Sie ein Passwort für die Chatsitzung an, falls Sie den Zugang beschränken wollen."
        )
    ),
    IntegerField('max_users',
        required           = False,
        default            = 0,
        validators         = MinMaxValidator('min_0_check', minimum = 0),
        widget             = IntegerWidget(
            label        = "maximale Teilnehmerzahl",
            description  = "Geben Sie die maximale Anzahl an Teilnehmern der Chatsitzung ein, falls Sie diese limitieren möchten. Bei Eingabe von 0 gibt es keine Beschränkung."
        )
    ),
    IntegerField('chat_id',
        required           = True,
        default            = 0,
        validators         = MinMaxValidator('min_0_check', minimum = 0),
        read_permission    = 'tud.addons.chat: Manage Chat',
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = "Chat-ID",
            description  = "Eindeutige Datenbank-ID dieser Chatsitzung. Um die ID automatisch zu generieren, geben Sie an dieser Stelle 0 ein (funktioniert nur beim Anlegen)."
        )
    ),
),
)

fields_to_hide = [
    'creators',
    'effectiveDate',
    'expirationDate',
    'subject',
    'relatedItems',
    'location',
    'language',
    'allowDiscussion',
    'excludeFromNav',
    'contributors',
    'rights',
]

for field in fields_to_hide:
    ChatSessionSchema[field].widget.visible = {
        'edit': 'invisible',
        'view': 'invisible'
    }
    ChatSessionSchema[field].searchable = False

schemata.finalizeATCTSchema(ChatSessionSchema, folderish=False, moveDiscussion=False)

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

    def getChatStorage(self):
        chat = self.getParentNode()
        return chat.chat_storage

atapi.registerType(ChatSession, 'tud.addons.chat')
