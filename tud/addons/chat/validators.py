# -*- coding: utf-8 -*-

import re

from zope.interface import implementer

from Products.validation.interfaces.IValidator import IValidator

from tud.addons.chat import chatMessageFactory as _

@implementer(IValidator)
class MinMaxValidator(object):
    """Checks that a number is within the defined value range.
    """

    def __init__(self, name='min_max_check', title='', description='', minimum = None, maximum = None):
        self.name = name
        self.title = title or name
        self.description = description
        self.minimum = minimum
        self.maximum = maximum

    def __call__(self, value, *args, **kwargs):
        instance = kwargs.get('instance', None)

        try:
            value = int(value)
        except:
            return instance.translate(_(u'validation_no_number', default = u'A number must be entered.'))

        if self.minimum is not None and value < self.minimum:
            return instance.translate(_(u'validation_number_too_small', default = u'The number must be ${number} or greater than ${number}.', mapping={u'number': self.minimum}))
        if self.maximum is not None and value > self.maximum:
            return instance.translate(_(u'validation_number_too_large', default = u'The number must be ${number} or less than ${number}.', mapping={u'number': self.maximum}))

        return True

class LengthValidator(MinMaxValidator):
    """Checks that a string is within the defined length range.
    """

    def __call__(self, value, *args, **kwargs):
        instance = kwargs.get('instance', None)

        value = unicode(value, "utf8")

        if self.minimum is not None and len(value) < self.minimum:
            return instance.translate(_(u'validation_string_too_short', default = u'The length of this text cannot be below ${number} characters.', mapping={u'number': self.minimum}))
        if self.maximum is not None and len(value) > self.maximum:
            return instance.translate(_(u'validation_string_too_long', default = u'The length of this text cannot be above ${number} characters.', mapping={u'number': self.maximum}))

        return True

@implementer(IValidator)
class HexColorCodeValidator(object):
    """Checks that a string is a valid hexadecimal color code.
    """

    def __init__(self, name='hex_color_code_check', title='', description=''):
        self.name = name
        self.title = title or name
        self.description = description
        self.regexp = re.compile(r'^#[0-9a-f]{6}$', re.IGNORECASE)

    def __call__(self, value, *args, **kwargs):
        instance = kwargs.get('instance', None)
        value = unicode(value, "utf8")

        if not self.regexp.match(value):
            return instance.translate(_(u'validation_invalid_hex_color_code', default = u'A valid HTML color code in hexadecimal format must be specified.'))

        return True
