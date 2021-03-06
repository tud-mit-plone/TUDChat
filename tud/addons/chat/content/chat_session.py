# Zope imports
from zope.interface import implementer

from Products.Archetypes import atapi
from Products.ATContentTypes.content import base, schemata
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField, TextField, IntegerField, DateTimeField
from Products.Archetypes.public import StringWidget, TextAreaWidget, IntegerWidget, CalendarWidget

from tud.addons.chat import chatMessageFactory as _
from tud.addons.chat.interfaces import IChatSession
from tud.addons.chat.validators import LengthValidator, MinMaxValidator

ChatSessionSchema = schemata.ATContentTypeSchema.copy() + Schema((
    TextField('_description',
        required           = False,
        searchable         = False,
        schemata           = 'default',
        default            = '',
        widget            = TextAreaWidget(
            label        = _(u'session_description_label', default = u'Description'),
            description  = _(u'session_description_desc', default = u'Displayed above chat window.')
        )
    ),
    DateTimeField('_start_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = _(u'session_start_date_label', default = u'Begin'),
            description  = _(u'session_start_date_desc', default = u'Date and time when the chat session begins.')
        )
    ),
    DateTimeField('_end_date',
        required=True,
        searchable=False,
        widget=CalendarWidget(
            label        = _(u'session_end_date_label', default = u'End'),
            description  = _(u'session_end_date_desc', default = u'Date and time when the chat session end.')
        )
    ),
    StringField('_welcome_message',
        required           = False,
        default            = '',
        widget             = StringWidget(
            label        = _(u'session_welcome_message_label', default = u'Welcome message'),
            description  = _(u'session_welcome_message_desc', default = u'This message is displayed to each participant after entering chat session.')
        )
    ),
    StringField('_password',
        required           = False,
        default            = '',
        validators         = (LengthValidator('max_30_check', maximum = 30), ),
        widget             = StringWidget(
            label        = _(u'session_password_label', default = u'Password'),
            description  = _(u'session_password_desc', default = u'Enter a password if you want to restrict access.')
        )
    ),
    IntegerField('_max_users',
        required           = False,
        default            = 0,
        validators         = MinMaxValidator('min_0_check', minimum = 0),
        widget             = IntegerWidget(
            label        = _(u'session_max_users_label', default = u'Maximum number of participants'),
            description  = _(u'session_max_users_desc', default = u'Enter the maximum number of participants for this chat session if you want to limit it. If you enter 0, there is no restriction.')
        )
    ),
    IntegerField('_chat_id',
        required           = True,
        default            = 0,
        validators         = MinMaxValidator('min_0_check', minimum = 0),
        read_permission    = 'tud.addons.chat: Manage Chat',
        write_permission   = 'tud.addons.chat: Manage Chat',
        widget             = StringWidget(
            label        = _(u'session_chat_id_label', default = u'Chat ID'),
            description  = _(u'session_chat_id_desc', default = u'Unique database ID for this chat session. If you want to generate the ID, enter 0 (this works only during creation).')
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
    ChatSessionSchema[field].widget.visible = {
        'edit': 'invisible',
        'view': 'invisible'
    }
    ChatSessionSchema[field].searchable = False

schemata.finalizeATCTSchema(ChatSessionSchema, folderish=False, moveDiscussion=False)

@implementer(IChatSession)
class ChatSession(base.ATCTContent):
    """
    Chat session content type
    """

    meta_type = 'ChatSession'
    portal_type = "ChatSession"
    archetype_name = 'ChatSession'
    isPrincipiaFolderish = False

    #: Archetype schema
    schema = ChatSessionSchema

    description = atapi.ATFieldProperty('_description')
    start_date = atapi.ATFieldProperty('_start_date')
    end_date = atapi.ATFieldProperty('_end_date')
    welcome_message = atapi.ATFieldProperty('_welcome_message')
    password = atapi.ATFieldProperty('_password')
    max_users = atapi.ATFieldProperty('_max_users')
    chat_id = atapi.ATFieldProperty('_chat_id')

atapi.registerType(ChatSession, 'tud.addons.chat')
