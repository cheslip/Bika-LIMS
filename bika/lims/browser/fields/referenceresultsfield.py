from AccessControl import ClassSecurityInfo
from Products.ATExtensions.Extensions.utils import makeDisplayList
from Products.ATExtensions.ateapi import RecordField, RecordsField
from Products.Archetypes.Registry import registerField
from Products.Archetypes.public import *
from Products.CMFCore.utils import getToolByName
from bika.lims.config import COUNTRY_NAMES
from Products.validation import validation
from Products.validation.validators.RegexValidator import RegexValidator
import sys

class ReferenceResultsField(RecordsField):
    """a list of reference sample results """
    _properties = RecordsField._properties.copy()
    _properties.update({
        'type' : 'referenceresult',
        'subfields' : ('uid', 'result', 'min', 'max', 'error'),
        'required_subfields' : ('uid',),
        'subfield_labels':{'uid': 'Analysis Service',
                           'result': 'Result',
                           'min': 'Min',
                           'max': 'Max',
                           'error': 'Error %'},
        })
    security = ClassSecurityInfo()

registerField(ReferenceResultsField,
              title = "Reference Results",
              description = "Used for storing reference results",
              )

