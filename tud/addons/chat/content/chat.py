# -*- coding: utf-8 -*-

# Python imports
import logging

# Zope imports
from AccessControl import ClassSecurityInfo
from zope.interface import implementer

# CMF imports
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, BooleanField, IntegerField
from Products.Archetypes.public import StringWidget, SelectionWidget, BooleanWidget, IntegerWidget
from Products.Archetypes.public import DisplayList

try:
    from raptus.multilanguagefields import fields
    from raptus.multilanguagefields import widgets
except ImportError:
    from Products.Archetypes import Field as fields
    from Products.Archetypes import Widget as widgets

from tud.addons.chat.core.TUDChatSqlStorage import TUDChatSqlStorage

from tud.addons.chat.interfaces import IChat

logger = logging.getLogger('tud.addons.chat')

TIME_FORMATS = DisplayList((
    ('%H:%M:%S', 'Uhrzeit'),
    ('%H:%M', 'Uhrzeit (ohne Sekunden)'),
    ('%d.%m.%Y %H:%M:%S', 'Datum und Uhrzeit'),
    ('%d.%m.%Y %H:%M', 'Datum und Uhrzeit (ohne Sekunden)'),
    ))

BAN_STRATEGIES = DisplayList((
    ('COOKIE', 'Nur Cookie (empfohlen)'),
    ('IP', 'Nur IP-Adresse'),
    ('COOKIE_AND_IP', 'Cookie und IP-Adresse (restriktiv)'),
    ))

ChatSchema = schemata.ATContentTypeSchema.copy() + Schema((
    fields.TextField('introduction',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = widgets.TextAreaWidget(
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
        storage            = atapi.AnnotationStorage(),
        enforceVocabulary  = True,
        vocabulary         = "getAllowedDbList",
        widget             = SelectionWidget(
            label        = u"Datenbank",
            description  = u"Mit welcher Datenbank soll der Chat betrieben werden?"
        )
    ),
    StringField("database_prefix",
        required           = True,
        searchable         = False,
        primary            = False,
        schemata           = 'default',
        default            = '',
        storage            = atapi.AnnotationStorage(),
        widget             = StringWidget(
            label        = u"Datenbank-Praefix",
            description  = u"Bitte geben Sie einen Praefix fuer Tabellen in der Datebank an; z.B.: 'institutionsname'"
        )
    ),
    BooleanField('showDate',
        required           = True,
        default            = True,
        widget             = BooleanWidget(
            label        = u"Zeitstempel an Chatnachrichten?",
            description  = u"Bitte geben Sie an, ob die Chatnachricht mit einem Zeitstempel begleitet werden soll."
        )
    ),
    StringField('chatDateFormat',
        required           = False,
        default            = '%H:%M:%S',
        vocabulary         = TIME_FORMATS,
        widget             = SelectionWidget(
            label        = u"Format des Zeitstempels",
            description  = u"Bitte geben Sie das Format des Zeitstempels an.",
            format       = "select",
        )
    ),
    StringField('adminColor',
        required           = True,
        default            = '#ff0000',
        widget             = StringWidget(
            label        = u"Textfarbe fuer Chatmoderator",
            description  = u"Bitte geben Sie die Textfarbe als HTML-Farbcode fuer die Chatmoderatoren an."
        )
    ),
    IntegerField('timeout',
        required           = True,
        default            = 15,
        widget             = IntegerWidget(
            label        = u"Socket-Timeout (in Sekunden)",
            description  = u"Bitte geben Sie den Socket-Timeout fuer den Chatuser an. Nach dieser Zeit wird dieser automatisch aus dem Chat entfernt."
        )
    ),
    IntegerField('refreshRate',
        required           = True,
        default            = 2,
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
        widget             = SelectionWidget(
            visible      = -1,
            label        = u"Ban-Strategie",
            description  = u"Bitte waehlen Sie mit welchen Mitteln gebannte Benutzer markiert werden. ",
            format       = "select"
        )
    ),
),
)

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

    # Data
    ## @brief for each connector_id the own prefixes in this database
    own_database_prefixes    = {}

    ## @brief class constructor which prepares the database connection
    #  @param id the identifier of the chat object
    def __init__(self, id):
        super(Chat, self).__init__(id)
        self.own_database_prefixes = self.own_database_prefixes

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
            if not errors:
                self.chat_storage = TUDChatSqlStorage(connector_id, database_prefix) # Update chat_storage
                if self.chat_storage.createTables() or database_prefix in self.own_database_prefixes.get(connector_id, []): # check if the prefix is free or is it an already used prefix
                    if self.own_database_prefixes.get(connector_id):
                        self.own_database_prefixes[connector_id].add(database_prefix)
                    else:
                        self.own_database_prefixes[connector_id] = set([database_prefix])
                    logger.info("TUDChat: connector_id = %s" % (connector_id,))
                else:
                    errors['database_prefix'] = "Dieser Prefix wird in dieser Datenbank bereits verwendet. Bitte wählen Sie einen anderen Prefix."
            REQUEST.set('post_validated', True)

    security.declarePublic("getAllowedDbList")
    ## @brief get a list of for chat usage allowed database connections
    #  @return list list of allowed databases
    def getAllowedDbList(self):
        """
        Get a list of allowed Mysql_Connection_IDs
        """
        dl = DisplayList()
        portal_tud_chat_tool = getToolByName(self, 'portal_tud_chat')

        url=self.absolute_url()
        if url.count('/')<3:
            path = '/'
        else:
            path = '/'.join(url.split('/')[3:])

        for connection in portal_tud_chat_tool.getAllowedDbList(path):
            dl.add(connection, connection)
        return dl

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

    def getStateTitle(self, obj):
        """ Returns current workflow state title of given object """
        wftool = getToolByName(self, 'portal_workflow')
        state = wftool.getInfoFor(obj, 'review_state')
        workflows = wftool.getWorkflowsFor(obj)
        if workflows:
            for wf in workflows:
                if state in wf.states:
                    return wf.states[state].title or state

atapi.registerType(Chat, 'tud.addons.chat')
