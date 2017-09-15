# -*- coding: utf-8 -*-

# Python imports
import logging

from OFS.CopySupport import CopyError

# Zope imports
from AccessControl import ClassSecurityInfo
from zope.interface import implementer
from zope.security import checkPermission

# CMF imports
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, IntegerField
from Products.Archetypes.public import StringWidget, SelectionWidget, IntegerWidget
from Products.Archetypes.public import DisplayList
from Products.ZMySQLDA.DA import Connection

from raptus.multilanguagefields import fields as MultiLanguageFields
from raptus.multilanguagefields import widgets as MultiLanguageWidgets

from tud.addons.chat.core.TUDChatSqlStorage import TUDChatSqlStorage

from tud.addons.chat.interfaces import IChat
from tud.addons.chat.validators import MinMaxValidator, HexColorCodeValidator

logger = logging.getLogger('tud.addons.chat')

DATE_FREQUENCIES = DisplayList((
    ('off', 'deaktiviert'),
    ('minute', 'maximal jede Minute'),
    ('message', 'bei jeder Nachricht'),
    ))

BAN_STRATEGIES = DisplayList((
    ('COOKIE', 'nur Cookie (empfohlen)'),
    ('IP', 'nur IP-Adresse'),
    ('COOKIE_AND_IP', 'Cookie und IP-Adresse (restriktiv)'),
    ))

WHISPER_OPTIONS = DisplayList((
    ('off', 'deaktiviert'),
    ('restricted', 'nur mit Moderatoren'),
    ('on', 'aktiviert'),
    ))

ChatSchema = schemata.ATContentTypeSchema.copy() + Schema((
    MultiLanguageFields.TextField('introduction',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = MultiLanguageWidgets.TextAreaWidget(
            label        = "Begrüßungstext",
            description  = "Wird den Nutzern bei der Auswahl der Chatsitzung angezeigt."
        )
    ),
    StringField("connector_id",
        required           = True,
        searchable         = False,
        primary            = False,
        schemata           = 'default',
        default            = '',
        read_permission    = 'tud.addons.chat: Manage Chat',
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = "Datenbank",
            description  = "Bitte geben Sie die ID des ZMySQL-Objektes an. Das Objekt muss sich in einem Teilpfad des Chatobjektes befinden."
        )
    ),
    StringField("database_prefix",
        required           = True,
        searchable         = False,
        primary            = False,
        schemata           = 'default',
        default            = '',
        read_permission    = 'tud.addons.chat: Manage Chat',
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = "Datenbank-Präfix",
            description  = "Bitte geben Sie ein Präfix für Tabellen in der Datenbank an, z.B. institutionsname."
        )
    ),
    StringField('date_frequency',
        required           = True,
        default            = 'minute',
        vocabulary         = DATE_FREQUENCIES,
        widget             = SelectionWidget(
            label        = "Zeitangabe im Chat",
            description  = "Wenn zu jeder Nachricht eine Zeitangabe erfolgen soll, wählen Sie 'bei jeder Nachricht'. Bei Auswahl von 'maximal jede Minute' erfolgt die Zeitangabe maximal einmal pro Minute. Soll keine Zeitangabe vor den Nachrichten angegeben werden, wählen Sie 'deaktiviert'.",
            format       = "select",
        )
    ),
    StringField('adminColor',
        required           = True,
        default            = '#ff0000',
        validators         = (HexColorCodeValidator(), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = "Markierungsfarbe für Chatmoderatoren",
            description  = "Benutzername und Nachrichten von Moderatoren werden mit dieser Farbe markiert. Die Eingabe muss als HTML-Farbcode erfolgen (z.B. #ff0000)."
        )
    ),
    IntegerField('timeout',
        required           = True,
        default            = 15,
        validators         = (MinMaxValidator('min_5_check', minimum = 5), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = "Socket-Timeout (in Sekunden)",
            description  = "Wenn ein Teilnehmer über diese Zeitspanne hinweg nicht mit dem Server kommuniziert hat, wird er automatisch aus der Chatsitzung entfernt."
        )
    ),
    IntegerField('refreshRate',
        required           = True,
        default            = 2,
        validators         = (MinMaxValidator('min_1_check', minimum = 1), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = "Aktualisierungsrate (in Sekunden)",
            description  = "Gibt an, wie häufig die Anzeige des Chats aktualisiert wird."
        )
    ),
    IntegerField('maxMessageLength',
        required           = True,
        default            = 0,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = "maximale Nachrichtenlänge",
            description  = "Maximale Anzahl von Zeichen, aus der eine einzelne Chatnachricht bestehen darf. Geben Sie 0 ein, wenn Sie die Zeichenlänge nicht begrenzen wollen."
        )
    ),
    IntegerField('blockTime',
        required           = True,
        default            = 1,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = "Wartezeit zwischen Nachrichten (in Sekunden)",
            description  = "Zeitdauer, die mindestens zwischen zwei Nachrichten eines Nutzers liegen muss."
        )
    ),
    StringField('banStrategy',
        required           = True,
        default            = 'COOKIE',
        vocabulary         = BAN_STRATEGIES,
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = SelectionWidget(
            visible      = -1,
            label        = "Ban-Strategie",
            description  = "Methode, mit der ein Nutzer markiert wird, um permanent aus dem Chat ausgeschlossen zu werden.",
            format       = "select"
        )
    ),
    IntegerField('oldMessagesCount',
        required           = True,
        default            = 20,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = "Anzahl vergangener Nachrichten beim Betreten einer Chatsitzung",
            description  = "Gibt an, wie viele vergangene Nachrichten einem neuen Teilnehmer beim Betreten der Chatsitzung maximal angezeigt werden. Geben Sie 0 ein, wenn keine vergangenen Nachrichten angezeigt werden sollen."
        )
    ),
    IntegerField('oldMessagesMinutes',
        required           = True,
        default            = 0,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = "Alter der vergangenen Nachrichten beim Betreten einer Chatsitzung (in Minuten)",
            description  = "Gibt an, wie alt die vergangenen Nachrichten maximal sein dürfen, damit sie noch angezeigt werden. Geben Sie 0 ein, wenn vergangene Nachrichten unabhängig von ihrem Alter angezeigt werden sollen. Diese Einstellung findet nur Anwendung, wenn die Anzahl anzuzeigender vergangener Nachrichten größer als 0 ist."
        )
    ),
    StringField('whisper',
        required           = True,
        default            = 'on',
        vocabulary         = WHISPER_OPTIONS,
        widget             = SelectionWidget(
            label        = "Flüstern",
            description  = "Beim Flüstern wird eine private Nachricht verschickt, die nur Absender und Adressat sehen können. Ist der Modus 'nur mit Moderatoren' ausgewählt, können Teilnehmer nur mit Moderatoren flüstern, aber nicht untereinander.",
            format       = "select",
        )
    ),
),
)

fields_to_hide = [
    'creators',
    'description',
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
    ChatSchema[field].widget.visible = {
        'edit': 'invisible',
        'view': 'invisible'
    }
    ChatSchema[field].searchable = False

schemata.finalizeATCTSchema(ChatSchema, folderish=False, moveDiscussion=False)

@implementer(IChat)
class Chat(base.ATCTFolder):
    """Chat content type

    """

    meta_type = 'Chat'
    portal_type = "Chat"
    archetype_name = 'Chat'
    isPrincipiaFolderish = True

    #: Archetype schema
    schema = ChatSchema

    security = ClassSecurityInfo()

    chat_storage = None

    ## @brief class constructor which prepares the database connection
    #  @param oid the identifier of the chat object
    def __init__(self, oid, **kwargs):
        super(Chat, self).__init__(oid, **kwargs)
        self.own_database_prefixes = {}

    def manage_cutObjects(self, *args, **kwargs):
        """Forbid moving chat sessions
        """
        raise CopyError()

    def canSetDefaultPage(self):
        """Forbid default page selection

        :return: False
        :rtype: bool
        """
        return False

    ##########################################################################
    # General Utility methods
    ##########################################################################

    # override the default actions

    ## @brief check and apply admin settings
    #  @param error list of errors
    def post_validate(self, REQUEST, errors):
        """
        This function checks the edit form values in context.
        It's called after the field validation passes.
        """
        if not REQUEST.get('post_validated'):
            connector_id = REQUEST.get('connector_id')
            database_prefix = REQUEST.get('database_prefix')
            if checkPermission('tud.addons.chat.ManageChat', self) and connector_id and not errors:
                try:
                    zmysql = getattr(self, connector_id)
                    if not isinstance(zmysql, Connection):
                        errors['connector_id'] = "Beim angegebenen Objekt handelt es sich nicht um ein ZMySQL-Objekt."
                        zmysql = None
                except AttributeError:
                    errors['connector_id'] = "Es wurde in keinem Teilpfad ein Objekt mit dieser ID gefunden."
                    zmysql = None

                if zmysql:
                    dbc = zmysql()
                    tables = [table['table_name'] for table in dbc.tables() if table['table_type'] == 'table']
                    used_prefixes = [table[:-7].encode('utf-8') for table in tables if table.endswith(u'_action')]
                    if database_prefix in used_prefixes and not database_prefix in self.own_database_prefixes.get(connector_id, {}): # check if the prefix is free or is it an already used prefix
                        errors['database_prefix'] = "Das Präfix wird in dieser Datenbank bereits verwendet. Bitte wählen Sie ein anderes Präfix."
            REQUEST.set('post_validated', True)

    security.declarePublic("show_id")


    def show_id(self,):
        """
        Determine whether to show an id in an edit form

        show_id() used to be in a Python Script, but was removed from Plone 2.5,
        so we had to add the method here for compatability
        """

        if getToolByName(self, 'plone_utils').isIDAutoGenerated(self.REQUEST.get('id', None) or self.getId()):
            return not (self.portal_factory.isTemporary(self) or self.CreationDate() == self.ModificationDate())
        return

    security.declareProtected(permissions.View, "addPrefix")
    ## @brief this function adds a prefix to a given database
    #  @param db str database connector id
    #  @param prefix str prefix of the database
    def addPrefix(self, db, prefix, REQUEST = None):
        """ Add the prefix to the list of own db prefixes. """
        if not self.isAdmin(REQUEST):
            return

        already_exist = False
        if self.own_database_prefixes.get(db):
            already_exist = prefix in self.own_database_prefixes[db]
            self.own_database_prefixes[db].add(prefix)
        else:
            self.own_database_prefixes[db] = set([prefix])

        self._p_changed = 1

        return str(not already_exist)

atapi.registerType(Chat, 'tud.addons.chat')
