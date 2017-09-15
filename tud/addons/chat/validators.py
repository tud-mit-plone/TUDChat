# -*- coding: utf-8 -*-

import re

from zope.interface import implementer

from Products.validation.interfaces.IValidator import IValidator

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
        try:
            value = int(value)
        except:
            return "Es muss eine Zahl eingegeben werden."


        if self.minimum is not None and value < self.minimum:
            return "Die Anzahl muss {0} oder größer {0} sein.".format(self.minimum)
        if self.maximum is not None and value > self.maximum:
            return "Die Anzahl muss {0} oder kleiner {0} sein.".format(self.maximum)

        return True

class LengthValidator(MinMaxValidator):
    """Checks that a string is within the defined length range.
    """

    def __call__(self, value, *args, **kwargs):
        value = unicode(value, "utf8")

        if self.minimum is not None and len(value) < self.minimum:
            return "Eine Länge von {0} Zeichen darf nicht unterschritten werden.".format(self.minimum)
        if self.maximum is not None and len(value) > self.maximum:
            return "Eine Länge von {0} Zeichen darf nicht überschritten werden.".format(self.maximum)

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
        value = unicode(value, "utf8")

        if not self.regexp.match(value):
            return "Es muss ein gültiger HTML-Farbcode im Hexadezimal-Format angegeben werden."

        return True
