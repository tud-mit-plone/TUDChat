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
from Products.Archetypes.atapi import StringField, TextField, IntegerField
from Products.Archetypes.public import StringWidget, TextAreaWidget, SelectionWidget, IntegerWidget
from Products.Archetypes.public import DisplayList
from Products.ZMySQLDA.DA import Connection

from tud.addons.chat.core.TUDChatSqlStorage import TUDChatSqlStorage

from tud.addons.chat import chatMessageFactory as _
from tud.addons.chat.interfaces import IChat
from tud.addons.chat.validators import MinMaxValidator, HexColorCodeValidator

logger = logging.getLogger('tud.addons.chat')

DATE_FREQUENCIES = DisplayList((
    ('off', _(u'chat_date_frequency_disabled', default = u'disabled')),
    ('minute', _(u'chat_date_frequency_minute', default = u'maximum once per minute')),
    ('message', _(u'chat_date_frequency_message', default = u'at every message')),
    ))

BAN_STRATEGIES = DisplayList((
    ('COOKIE', _(u'chat_ban_strategy_cookie', default = u'only cookie (recommended)')),
    ('IP', _(u'chat_ban_strategy_ip', default = u'only ip address')),
    ('COOKIE_AND_IP', _(u'chat_ban_strategy_cookie_and_ip', default = u'cookie and ip address (restrictive)')),
    ))

WHISPER_OPTIONS = DisplayList((
    ('off', _(u'chat_whisper_disabled', default = u'disabled')),
    ('restricted', _(u'chat_whisper_moderators', default = u'only with moderators')),
    ('on', _(u'chat_whisper_enabled', default = u'enabled')),
    ))

ChatSchema = schemata.ATContentTypeSchema.copy() + Schema((
    TextField('introduction',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = TextAreaWidget(
            label        = _(u'chat_introduction_label', default = u'Welcoming text'),
            description  = _(u'chat_introduction_desc', default = u'This text will be displayed at chat session selection.')
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
            label        = _(u'chat_database_label', default = u'database'),
            description  = _(u'chat_database_desc', default = u'Please enter the ID of the ZMySQL object. The object must be located in a sub-path of the chat object.')
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
            label        = _(u'chat_database_prefix_label', default = u'database prefix'),
            description  = _(u'chat_database_prefix_desc', default = u'Please enter a prefix for tables in the database, e.g. institutionname')
        )
    ),
    StringField('date_frequency',
        required           = True,
        default            = 'minute',
        vocabulary         = DATE_FREQUENCIES,
        widget             = SelectionWidget(
            label        = _(u'chat_date_frequency_label', default = u'Time stamp in chat'),
            description  = _(u'chat_date_frequency_desc', default = u'If you want a time stamp for each message, choose \'at every message\'. If you choose \'maximum once per minute\', the time is given maximally once per minute. If no time is to be given before messages, choose \'disabled\'.'),
            format       = "select",
        )
    ),
    StringField('adminColor',
        required           = True,
        default            = '#ff0000',
        validators         = (HexColorCodeValidator(), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = _(u'chat_admin_color_label', default = u'Marking color for chat moderators'),
            description  = _(u'chat_admin_color_desc', default = u'Username and messages of moderators will be marked with this color. The input must be made as HTML color code (e.g. #ff0000)')
        )
    ),
    IntegerField('timeout',
        required           = True,
        default            = 15,
        validators         = (MinMaxValidator('min_5_check', minimum = 5), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = _(u'chat_timeout_label', default = u'Socket timeout (in seconds)'),
            description  = _(u'chat_timeout_desc', default = u'If a participant has not communicated with the server during this time period, he or she will be removed automatically.')
        )
    ),
    IntegerField('refreshRate',
        required           = True,
        default            = 2,
        validators         = (MinMaxValidator('min_1_check', minimum = 1), ),
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = IntegerWidget(
            label        = _(u'chat_refresh_rate_label', default = u'Refresh rate (in seconds)'),
            description  = _(u'chat_refresh_rate_desc', default = u'Specifies how often the chat display is updated.')
        )
    ),
    IntegerField('maxMessageLength',
        required           = True,
        default            = 0,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = _(u'chat_max_message_length_label', default = u'Maximum message length'),
            description  = _(u'chat_max_message_length_desc', default = u'Maximum number of characters that a single chat message can consist of. Enter 0, if you do not want to restrict the message length.')
        )
    ),
    IntegerField('blockTime',
        required           = True,
        default            = 1,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = _(u'chat_block_time_label', default = u'Waiting time between messages (in seconds)'),
            description  = _(u'chat_block_time_desc', default = u'Minimum time period between two messages from a user.')
        )
    ),
    StringField('banStrategy',
        required           = True,
        default            = 'COOKIE',
        vocabulary         = BAN_STRATEGIES,
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = SelectionWidget(
            visible      = -1,
            label        = _(u'chat_ban_strategy_label', default = u'Ban strategy'),
            description  = _(u'chat_ban_strategy_desc', default = u'Method to mark a user, which is permanently banned from the chat.'),
            format       = "select"
        )
    ),
    IntegerField('oldMessagesCount',
        required           = True,
        default            = 20,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = _(u'chat_old_messages_count_label', default = u'Number of recent messages when entering a chat session'),
            description  = _(u'chat_old_messages_count_desc', default = u'Specifies the maximum number of recent messages displayed to a new participant when entering the chat session. Enter 0, if no recent messages should be shown.')
        )
    ),
    IntegerField('oldMessagesMinutes',
        required           = True,
        default            = 0,
        validators         = (MinMaxValidator('min_0_check', minimum = 0), ),
        widget             = IntegerWidget(
            label        = _(u'chat_old_messages_minutes_label', default = u'Age of recent messages on entering a chat session (in minutes)'),
            description  = _(u'chat_old_messages_minutes_desc', default = u'Specifies the maximum age of recent messages so that they will still be shown. Enter 0, if you want recent messages to be displayed regardless of their age. This setting is only used if the number of recent messages to be displayed is greater than 0.')
        )
    ),
    StringField('whisper',
        required           = True,
        default            = 'on',
        vocabulary         = WHISPER_OPTIONS,
        widget             = SelectionWidget(
            label        = _(u'chat_whisper_label', default = u'Whisper'),
            description  = _(u'chat_whisper_desc', default = u'When whispering, a private message is sent that only the sender and the recipient can see. If the mode \'only with moderators\' is chosen, participants can only whisper with moderators, but not among themselves'),
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
                        errors['connector_id'] = _(u'validation_object_is_not_zmysql_object', default = u'The chosen object is not a ZMySQL object.')
                        zmysql = None
                except AttributeError:
                    errors['connector_id'] = _(u'validation_object_not_found', default = u'No object with this ID was found in any subpath.')
                    zmysql = None

                if zmysql:
                    dbc = zmysql()
                    tables = [table['table_name'] for table in dbc.tables() if table['table_type'] == 'table']
                    used_prefixes = [table[:-7].encode('utf-8') for table in tables if table.endswith(u'_action')]
                    if database_prefix in used_prefixes and not database_prefix in self.own_database_prefixes.get(connector_id, {}): # check if the prefix is free or is it an already used prefix
                        errors['database_prefix'] = _(u'validation_prefix_in_use', default= u'The chosen prefix is already in use in this database. Please choose another prefix.')
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
