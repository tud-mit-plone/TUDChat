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
                description             = "Bitte geben Sie einen Präfix für Tabellen in der Datebank an; z.B.: 'institutionsname')",
                i18n_domain             = "tudchat",
                label_msgid             = "label_database_prefix",
                description_msgid       = "help_database_prefix")
    ),
    BooleanField(
        'showDate',
        default        = True,
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
        default         = '%H:%M:%S',
        required        = False,
        vocabulary      = TIME_FORMATS,
        widget          = SelectionWidget(
                label                   = "Format des Zeitstempels",
                description             = "Bitte geben Sie das Format des Zeitstempels an.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_chat_date_format",
                description_msgid       = "help_chat_date_format",
                format                  = "select",
        )
    ),
    IntegerField(
        'timeout',
        default         = 15,
        required        = True,
        widget          = IntegerWidget(
                label                   = "Socket-Timeout (in Sekunden)",
                description             = "Bitte geben Sie den Socket-Timeout für den Chatuser an. Nach dieser Zeit wird dieser automatisch aus dem Chat entfernt.",
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
        'maxMessageLength',
        default         = 0,
        required        = True,
        widget          = IntegerWidget(
                label                   = "maximale Nachrichtenlänge",
                description             = "Bitte geben Sie die maximale Anzahl von Zeichen an, aus der eine einzelne Chat-Nachricht bestehen darf. (0 bedeutet, dass keine Begrenzung aktiv ist)",
                i18n_domain             = "tudchat",
                label_msgid             = "label_maxMessageLength",
                description_msgid       = "help_maxMessageLength"
        )
    ),
    IntegerField(
        'blockTime',
        default         = 1,
        required        = True,
        widget          = IntegerWidget(
                label                   = "Abstand zwischen Nachrichten (in Sekunden)",
                description             = "Bitte geben Sie die Wartezeit an, bis der Benutzer wieder erneut eine Nachricht schicken kann.",
                i18n_domain             = "tudchat",
                label_msgid             = "label_blockTime",
                description_msgid       = "help_blockTime"
        )
    ),
    StringField(
        'banStrategy',
        default         = 'COOKIE',
        required        = True,
        vocabulary      = BAN_STRATEGIES,
        widget          = SelectionWidget(
                label                   = "Ban-Strategie",
                description             = "Bitte wählen Sie mit welchen Mitteln gebannte Benutzer markiert werden. ",
                i18n_domain             = "tudchat",
                label_msgid             = "label_banStrategy",
                description_msgid       = "help_banStrategy",
                format                  = "select",
        )
    ),
))