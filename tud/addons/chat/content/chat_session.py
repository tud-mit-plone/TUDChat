# -*- coding: utf-8 -*-

# Python imports
import logging

# Zope imports
from zope.interface import implementer

# CMF imports
from Products.CMFCore import permissions

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, IntegerField, DateTimeField
from Products.Archetypes.public import StringWidget, IntegerWidget, CalendarWidget
from Products.validation.validators import ExpressionValidator, RegexValidator

try:
    from raptus.multilanguagefields import fields
    from raptus.multilanguagefields import widgets
except ImportError:
    from Products.Archetypes import Field as fields
    from Products.Archetypes import Widget as widgets

from tud.addons.chat.interfaces import IChatSession

logger = logging.getLogger('tud.addons.chat')

ChatSessionSchema = schemata.ATContentTypeSchema.copy() + Schema((
    fields.TextField('description',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = widgets.TextAreaWidget(
            label        = u"Beschreibung",
            description  = u"Bitte geben Sie eine Beschreibung fuer die Chat-Sitzung an."
        )
    ),
    DateTimeField('start_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = u"Beginn",
            description  = u"Bitte geben Sie den Beginn der Chat-Sitzung an."
        )
    ),
    DateTimeField('end_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = u"Ende",
            description  = u"Bitte geben Sie das Ende der Chat-Sitzung an."
        )
    ),
    StringField('password',
        required           = False,
        default            = '',
        validators         = (ExpressionValidator('python: len(value) <= 30', 'Das Passwort darf maximal 30 Zeichen lang sein.'), ),
        widget             = StringWidget(
            label        = u"Passwort",
            description  = u"Bitte geben Sie ein Passwort fuer die Chat-Sitzung an, falls Sie den Zugang beschraenken wollen."
        )
    ),
    IntegerField('max_users',
        required           = False,
        default            = 0,
        validators         = RegexValidator('checkNum', '^[0-9]+$', errmsg = 'Die maximale Benutzeranzahl muss eine Zahle groesser oder gleich 0 sein.'),
        widget             = IntegerWidget(
            label        = u"maximale Benutzer",
            description  = u"Bitte geben Sie die maximale Benutzerzahl ein, falls Sie die Anzahl der Chat-Benutzer limitieren moechten. (0 bedeutet keine Beschraenkung)"
        )
    ),
    IntegerField('chat_id',
        required           = True,
        default            = 0,
        validators         = RegexValidator('checkNum', '^[0-9]+$', errmsg = 'Die Chat-ID muss eine Zahl groesser oder gleich 0 sein.'),
        read_permission    = permissions.ManagePortal,
        write_permission   = permissions.ManagePortal,
        widget             = StringWidget(
            label        = u"Chat-ID",
            description  = u"Eindeutige Datenbank-ID dieser Chat-Sitzung (bei 0 wird die ID generiert, wenn die Sitzung angelegt wird)"
        )
    ),
),
)

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

    # Data
    ## @brief collection of timestamps to call methods in certain intervals
    timestamps               = {}
    ## @brief chat room container with userlist, kicked_users, banned_users and timestamps
    chat_rooms               = {}

    def getChatStorage(self):
        chat = self.getParentNode()
        return chat.chat_storage

atapi.registerType(ChatSession, 'tud.addons.chat')
