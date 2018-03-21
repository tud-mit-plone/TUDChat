import re

from zope.component import getGlobalSiteManager, getAdapter
from zope.interface import Invalid, provider
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
import z3c.form.validator
import z3c.form.interfaces

from tud.addons.chat.content.chat import DATE_FREQUENCIES as DATE_FREQUENCIES_dl
from tud.addons.chat.content.chat import BAN_STRATEGIES as BAN_STRATEGIES_dl
from tud.addons.chat.content.chat import WHISPER_OPTIONS as WHISPER_OPTIONS_dl

from tud.addons.chat import chatMessageFactory as _
from tud.addons.chat.interfaces import IDatabaseObject, IChat

def setupSimpleVocabulary(display_list):
    """
    Generates vocabulary with values from given display list.

    :param display_list: archetypes display list
    :type display_list: Products.Archetypes.utils.DisplayList
    :return: vocabulary with values from given display list
    :rtype: zope.schema.vocabulary.SimpleVocabulary
    """
    terms = []
    for value, title in display_list.items():
        terms.append(SimpleTerm(value = value, title = title))
    return SimpleVocabulary(terms)

DATE_FREQUENCIES = setupSimpleVocabulary(DATE_FREQUENCIES_dl)
BAN_STRATEGIES = setupSimpleVocabulary(BAN_STRATEGIES_dl)
WHISPER_OPTIONS = setupSimpleVocabulary(WHISPER_OPTIONS_dl)

@provider(IContextSourceBinder)
def getDatabaseAdapters(context):
    """
    Returns vocabulary with available database adapters.

    :param context: container of new chat object on add or chat itself on edit
    :type context: OFS.SimpleItem.Item
    :return: available database adapters
    :rtype: zope.schema.vocabulary.SimpleVocabulary
    """
    sm = getGlobalSiteManager()
    adapters = [adapter for adapter in sm.registeredAdapters() if adapter.provided == IDatabaseObject]

    terms = [SimpleTerm(value = adapter.name, title = adapter.name) for adapter in adapters]

    return SimpleVocabulary(terms)

class HexColorCodeValidator(z3c.form.validator.SimpleFieldValidator):
    """
    Checks that a string is a valid hexadecimal color code.
    """

    def validate(self, value, force = False):
        """
        Validates given value.

        :param value: value to validate
        :type value: str
        :param force: not relevant for custom validation
        :type force: bool
        """
        super(HexColorCodeValidator, self).validate(value, force)

        if not re.match(r'^#[0-9a-f]{6}$', value, re.IGNORECASE):
            raise Invalid(_(u'validation_invalid_hex_color_code', default = u'A valid HTML color code in hexadecimal format must be specified.'))

class DatabaseConnectionValidator(z3c.form.validator.SimpleFieldValidator):
    """
    Checks database connection.
    """

    def validate(self, value, force = False):
        """
        Delegates validation for database connection to configured database adapter.
        Custom validation is disabled for inline validation.

        :param value: value to validate
        :type value: str
        :param force: not relevant for custom validation
        :type force: bool
        """
        super(DatabaseConnectionValidator, self).validate(value, force)

        if self.request.steps[-1] != '@@z3cform_validate_field':
            sm = getGlobalSiteManager()
            adapter_name = self.widget.form.widgets.get('database_adapter').value[0]
            adapters = [adapter for adapter in sm.registeredAdapters() if adapter.provided == IDatabaseObject and adapter.name == adapter_name]
            if adapters:
                adapter = adapters[0].factory # in object creation phase the adapter can't be instantiated, because the chat object isn't available
                try:
                    adapter.validate(self.context, {"connector_id" : value})
                except ValueError as e:
                    raise Invalid(e.message)

class StartEndDateValidator(z3c.form.validator.SimpleFieldValidator):
    """
    Checks that start date is before end date.
    """

    def validate(self, value, force = False):
        """
        Obtains start date and checks if possible that start date is before end date.
        Custom validation is disabled for inline validation.

        :param value: end date
        :type value: datetime
        :param force: not relevant for custom validation
        :type force: bool
        """
        super(StartEndDateValidator, self).validate(value, force)

        if self.request.steps[-1] != '@@z3cform_validate_field':
            start_date_widget = self.widget.form.widgets.get('start_date')
            start_date_raw = start_date_widget.extract()
            if start_date_raw is z3c.form.interfaces.NO_VALUE:
                return
            start_date = z3c.form.interfaces.IDataConverter(start_date_widget).toFieldValue(start_date_raw)

            if start_date and start_date > value:
                raise Invalid(_(u'validation_end_before_start', default = u'Start of the chat must be before its end.'))
