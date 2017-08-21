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
from Products.validation.validators import ExpressionValidator
from Products.ZMySQLDA.DA import Connection

from raptus.multilanguagefields import fields as MultiLanguageFields
from raptus.multilanguagefields import widgets as MultiLanguageWidgets

from tud.addons.chat.core.TUDChatSqlStorage import TUDChatSqlStorage

from tud.addons.chat.interfaces import IChat

logger = logging.getLogger('tud.addons.chat')

DATE_FREQUENCIES = DisplayList((
    ('off', 'Deaktiviert'),
    ('minute', 'Aktiviert (maximal jede Minute)'),
    ('message', 'Aktiviert (bei jeder Nachricht)'),
    ))

BAN_STRATEGIES = DisplayList((
    ('COOKIE', 'Nur Cookie (empfohlen)'),
    ('IP', 'Nur IP-Adresse'),
    ('COOKIE_AND_IP', 'Cookie und IP-Adresse (restriktiv)'),
    ))

WHISPER_OPTIONS = DisplayList((
    ('off', 'Deaktiviert'),
    ('restricted', 'Eingeschraenkt aktiviert'),
    ('on', 'Aktiviert'),
    ))

ChatSchema = schemata.ATContentTypeSchema.copy() + Schema((
    MultiLanguageFields.TextField('introduction',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = MultiLanguageWidgets.TextAreaWidget(
            label        = u"Begrueßungstext",
            description  = u"Bitte geben Sie den Text an, der bei der Raumauswahl angezeigt werden soll."
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
            label        = u"Datenbank",
            description  = u"Bitte geben Sie die ID des ZMySQL-Objektes an. Das Objekt muss sich auf einem Teilpfad des Chat-Objektes befinden."
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
            label        = u"Datenbank-Praefix",
            description  = u"Bitte geben Sie einen Praefix fuer Tabellen in der Datebank an; z.B.: 'institutionsname'"
        )
    ),
    StringField('date_frequency',
        required           = True,
        default            = 'minute',
        vocabulary         = DATE_FREQUENCIES,
        widget             = SelectionWidget(
            label        = u"Haeufigkeit der Zeitangabe im Chat",
            description  = u"Bitte geben Sie an, wie haeufig die Zeit bei den Nachrichten im Chat angegeben werden soll. Wenn keine Zeitangabe erfolgen soll, waehlen Sie 'Deaktiviert'. Wenn maximal jede Minute eine Zeitangabe erfolgen soll, waehlen Sie 'Aktiviert (maximal jede Minute)'. Wenn bei jeder Nachricht eine Zeitangabe erfolgen soll, waehlen Sie 'Aktiviert (bei jeder Nachricht)'.",
            format       = "select",
        )
    ),
    StringField('adminColor',
        required           = True,
        default            = '#ff0000',
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = u"Textfarbe fuer Chatmoderator",
            description  = u"Bitte geben Sie die Textfarbe als HTML-Farbcode fuer die Chatmoderatoren an."
        )
    ),
    IntegerField('timeout',
        required           = True,
        default            = 15,
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = u"Socket-Timeout (in Sekunden)",
            description  = u"Bitte geben Sie den Socket-Timeout fuer den Chatuser an. Nach dieser Zeit wird dieser automatisch aus dem Chat entfernt."
        )
    ),
    IntegerField('refreshRate',
        required           = True,
        default            = 2,
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = u"Aktualisierungs-Rate (in Sekunden)",
            description  = u"Bitte geben Sie Frequenz an, in welcher der Chat aktualisiert werden soll."
        )
    ),
    IntegerField('maxMessageLength',
        required           = True,
        default            = 0,
        widget             = IntegerWidget(
            label        = u"maximale Nachrichtenlaenge",
            description  = u"Bitte geben Sie die maximale Anzahl von Zeichen an, aus der eine einzelne Chat-Nachricht bestehen darf. (0 bedeutet, dass keine Begrenzung aktiv ist)"
        )
    ),
    IntegerField('blockTime',
        required           = True,
        default            = 1,
        widget             = IntegerWidget(
            label        = u"Wartezeit zwischen Nachrichten (in Sekunden)",
            description  = u"Bitte geben Sie die Wartezeit an, bis der Benutzer wieder erneut eine Nachricht schicken kann."
        )
    ),
    StringField('banStrategy',
        required           = True,
        default            = 'COOKIE',
        vocabulary         = BAN_STRATEGIES,
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = SelectionWidget(
            visible      = -1,
            label        = u"Ban-Strategie",
            description  = u"Bitte waehlen Sie mit welchen Mitteln gebannte Benutzer markiert werden. ",
            format       = "select"
        )
    ),
    IntegerField('oldMessagesCount',
        required           = True,
        default            = 20,
        validators         = (ExpressionValidator('python: int(value) >= 0', u'Die Anzahl muss 0 oder groesser 0 sein.'), ),
        widget             = IntegerWidget(
            label        = u"Maximale Anzahl anzuzeigender vorangegangener Nachrichten beim Betreten eines Chat-Raums",
            description  = u"Bitte geben Sie die maximale Anzahl der vorangegangenen Nachrichten, die dem Benutzer beim Betreten eines Chat-Raums angezeigt werden sollen, an. (0 bedeutet, dass keine vorangegangenen Nachrichten angezeigt werden)"
        )
    ),
    IntegerField('oldMessagesMinutes',
        required           = True,
        default            = 0,
        validators         = (ExpressionValidator('python: int(value) >= 0', u'Die Minutenanzahl muss 0 oder groesser 0 sein.'), ),
        widget             = IntegerWidget(
            label        = u"Maximales Alter der vorangegangenen Nachrichten beim Betreten eines Chat-Raums (in Minuten)",
            description  = u"Diese Einstellung findet nur Anwendung, wenn die maximale Anzahl anzuzeigender vorangegangener Nachrichten groesser als 0 ist. Bitte geben Sie das maximale Alter der vorangegangenen Nachrichten, die dem Benutzer beim Betreten eines Chat-Raums angezeigt werden sollen, in Minuten an. (0 bedeutet, dass keine zeitliche Beschraenkung aktiv ist)"
        )
    ),
    StringField('whisper',
        required           = True,
        default            = 'on',
        vocabulary         = WHISPER_OPTIONS,
        widget             = SelectionWidget(
            label        = u"Fluestern",
            description  = u"Wenn Fluestern aktiviert ist, kann jeder Benutzer einem anderen Benutzer direkt eine Nachricht uebermitteln. Bei einer eingeschraenkten Aktivierung koennen zwei Benutzer, die beide keine Moderatoren sind, nicht miteinander fluestern.",
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
                    errors['connector_id'] = "Es wurde auf keinem Teilpfad ein Objekt mit dieser ID gefunden."
                    zmysql = None

                if zmysql:
                    dbc = zmysql()
                    tables = [table['table_name'] for table in dbc.tables() if table['table_type'] == 'table']
                    used_prefixes = [table[:-7].encode('utf-8') for table in tables if table.endswith(u'_action')]
                    if database_prefix in used_prefixes and not database_prefix in self.own_database_prefixes.get(connector_id, {}): # check if the prefix is free or is it an already used prefix
                        errors['database_prefix'] = "Dieser Prefix wird in dieser Datenbank bereits verwendet. Bitte wählen Sie einen anderen Prefix."
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
