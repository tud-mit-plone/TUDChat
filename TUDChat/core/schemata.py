# -*- coding: utf-8 -*-
## 
## Copyright (C)2005 Ingeniweb

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; see the file COPYING. If not, write to the
## Free Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

"""
__docformat__ = 'restructuredtext'


# CMF imports
from Products.CMFCore import CMFCorePermissions
from Products.CMFCore.utils import getToolByName

# Archetypes imports
from Products.Archetypes.public import *

# Validators
from Products.validation.interfaces.IValidator import IValidator
from Products.validation.validators.ExpressionValidator import ExpressionValidator

TUDChatSchema = BaseSchema.copy() + Schema((
    StringField(
        'connector_id',
        required        = True,
        vocabulary      = "getAllowedDbList",
        widget          = SelectionWidget(
                label                   = "Datenbank",
                description             = "Mit welcher Datenbank soll der Chat betrieben werden?",
                i18n_domain             = "tudchat",
                label_msgid             = "label_database",
                description_msgid       = "help_database")
    ),
    StringField(
        'database_prefix',
        default         = '',
        required        = False,
        widget          = StringWidget(
                label                   = "Datenbank-Präfix",
                description             = "Bitte geben Sie einen Präfix für Tabellen in der Datebank an; z.B.: 'chat')",
                i18n_domain             = "tudchat",
                label_msgid             = "label_database_prefix",
                description_msgid       = "help_database_prefix")
    ),    
    BooleanField(
        'showDate',
        default        = False,
        required       = True,
        widget         = BooleanWidget(
                label                   = "Zeitstempel an Chatnachrichten?",
                description             = "Bitte geben Sie an, ob die Chatnachricht mit einem Zeitstempel begleitet werden soll.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_show_date",
                description_msgid       = "help_show_date")
    ),        
    StringField(
        'chatDateFormat',
        default         = '%Y/%m/%d %H:%M:%S',
        required        = False,
        widget          = StringWidget(
                label                   = "Datumsformat des Zeitstempels",
                description             = "Bitte geben Sie das Datumsformat des Zeitstempels an.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_chat_date_format",
                description_msgid       = "help_chat_date_format")
    ),
    IntegerField(
        'timeout',
        default         = 15,
        required        = True,
        widget          = IntegerWidget(
                label                   = "Timeout für den Chatuser (in Sekunden)",
                description             = "Bitte geben Sie die Zeit an, die der Benutzer ohne Rückmeldung im Chat verbleiben kann. Nach dieser Zeit wird dieser automatisch aus dem Chat entfernt.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_timeout",
                description_msgid       = "help_timeout"
        )
    ),
    IntegerField(
        'refreshRate',               
        default         = 5,
        required        = True,
        widget          = IntegerWidget(
                label                   = "Aktualisierungs-Rate (in Sekunden)",
                description             = "Bitte geben Sie Frequenz an, in welcher der Chat aktualisiert werden soll.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_refresh_rate",
                description_msgid       = "help_refresh_rate"
        )
    ),
    IntegerField(
        'blockTime',
        default         = 1,
        required        = True,
        widget          = IntegerWidget(
                label                   = "Abstand zwischen Nachrichten (in Sekunden)",
                description             = "Bitte geben Sie die Wartezeit an, bis der Benutzer wieder erneut eine Nachricht schicken kann. ",
                i18n_domain             = "tudchat",
                label_msgid             = "label_blockTime",
                description_msgid       = "help_blockTime"
        )
    ),    
))