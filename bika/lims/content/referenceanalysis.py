"""ReferenceAnalysis

$Id: ReferenceAnalysis.py 914 2007-10-16 19:49:15Z anneline $
"""
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.ATExtensions.ateapi import DateTimeField, DateTimeWidget, RecordsField
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.Archetypes.public import *
from Products.Archetypes.references import HoldingReference
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from bika.lims.browser.fields import InterimFieldsField
from bika.lims.browser.widgets import RecordsWidget as BikaRecordsWidget
from bika.lims.config import I18N_DOMAIN, STD_TYPES, PROJECTNAME
from bika.lims.content.bikaschema import BikaSchema

#try:
#    from BikaCalendar.config import TOOL_NAME as BIKA_CALENDAR_TOOL # XXX
#except:
#    pass

schema = BikaSchema.copy() + Schema((
    StringField('ReferenceAnalysisID',
        required = 1,
        index = 'FieldIndex',
        searchable = True,
        widget = StringWidget(
            label = 'ReferenceAnalysis ID',
            label_msgid = 'label_requestid',
            description = 'The ID assigned to the reference analysis',
            description_msgid = 'help_referenceanalysis_id',
            i18n_domain = I18N_DOMAIN,
            visible = {'edit':'hidden'},
        ),
    ),
    StringField('ReferenceType',
        vocabulary = STD_TYPES,
        index = 'FieldIndex',
        widget = SelectionWidget(
            label = 'Reference Type',
            label_msgid = 'label_referencetype',
            i18n_domain = I18N_DOMAIN,
        ),
    ),
    ReferenceField('Service',
        required = 1,
        allowed_types = ('AnalysisService',),
        relationship = 'ReferenceAnalysisAnalysisService',
        referenceClass = HoldingReference,
        widget = ReferenceWidget(
            label = 'Analysis service',
            label_msgid = 'label_analysis',
            i18n_domain = I18N_DOMAIN,
        )
    ),
    StringField('Unit',
        widget = StringWidget(
            label_msgid = 'label_unit',
        ),
    ),
    ReferenceField('Calculation',
        allowed_types = ('Calculation',),
        relationship = 'AnalysisCalculation',
        referenceClass = HoldingReference,
    ),
    InterimFieldsField('InterimFields',
        widget = BikaRecordsWidget(
            label = 'Calculation Interim Fields',
            label_msgid = 'label_interim_fields',
            i18n_domain = I18N_DOMAIN,
        )
    ),
    StringField('Result',
        widget = StringWidget(
            label = 'Result',
            label_msgid = 'label_result',
            i18n_domain = I18N_DOMAIN,
        )
    ),
    StringField('InterimCalcs',
        widget = StringWidget(
            label = 'Interim Calculations',
            label_msgid = 'label_interim',
            i18n_domain = I18N_DOMAIN,
        )
    ),
    BooleanField('Retested',
        default = False,
        widget = BooleanWidget(
            label = "Retested",
            label_msgid = "label_retested",
            i18n_domain = I18N_DOMAIN,
        ),
    ),
    DateTimeField('DateRequested',
        required = 1,
        default_method = 'current_date',
        index = 'DateIndex',
        widget = DateTimeWidget(
            label = 'Date Requested',
            label_msgid = 'label_daterequested',
            visible = {'edit':'hidden'},
        ),
    ),
    DateTimeField('DateVerified',
        index = 'DateIndex',
        widget = DateTimeWidget(
            label = 'Date Verified',
            label_msgid = 'label_dateverified',
            visible = {'edit':'hidden'},
        ),
    ),
    ComputedField('ReferenceSampleUID',
        index = 'FieldIndex',
        expression = 'context.aq_parent.UID()',
        widget = ComputedWidget(
            visible = False,
        ),
    ),
    ComputedField('ReferenceSupplierUID',
        index = 'FieldIndex',
        expression = 'context.aq_parent.aq_parent.UID()',
        widget = ComputedWidget(
            visible = False,
        ),
    ),
    ComputedField('ServiceUID',
        index = 'FieldIndex',
        expression = 'context.getService().UID()',
        widget = ComputedWidget(
            visible = False,
        ),
    ),
),
)

class ReferenceAnalysis(BaseContent):
    security = ClassSecurityInfo()
    archetype_name = 'ReferenceAnalysis'
    schema = schema
    allowed_content_types = ()
    immediate_view = 'base_view'
    global_allow = 0
    filter_content_types = 0
    use_folder_tabs = 0
    actions = ()

    def Title(self):
        """ Return the Service ID as title """
        s = self.getService()
        return s and s.Title() or ''

    def getUncertainty(self, result=None):
        """ Calls self.Service.getUncertainty with either the
            provided result value or self.Result
        """
        return self.getService().getUncertainty(result and result or self.getResult())

    def result_in_range(self, result=None):
        """ Check if the result is in range for the Analysis' service.
            if result is None, self.getResult() is called for the result value.
            Return False if out of range
            Return True if in range
            return '1' if in shoulder
        """

        result = result and result or self.getResult()

        try:
            result = float(str(result))
        except:
            # if it is not a number we assume it is in range
            return True

        service_uid = self.getService().UID()
        specs = self.aq_parent.getResultsRangeDict()
        if specs.has_key(service_uid):
            spec = specs[service_uid]
            spec_min = float(spec['min'])
            spec_max = float(spec['max'])

            if spec_min <= result <= spec_max:
                return True

            """ check if in 'shoulder' error range - out of range, but in acceptable error """
            error_amount =  (result/100)*float(spec['error'])
            error_min = result - error_amount
            error_max = result + error_amount
            if ((result < spec_min) and (error_max >= spec_min)) or \
               ((result > spec_max) and (error_min <= spec_max)):
                return '1'
        else:
            return True
        return False

    security.declarePublic('getWorksheet')
    def getWorksheet(self):
        tool = getToolByName(self, REFERENCE_CATALOG)
        worksheet = ''
        uids = [uid for uid in
                tool.getBackReferences(self, 'WorksheetReferenceAnalysis')]
        if len(uids) == 1:
            reference = uids[0]
            worksheet = tool.lookupObject(reference.sourceUID)
        return worksheet

    security.declarePublic('current_date')
    def current_date(self):
        """ return current date """
        return DateTime()

    def workflow_script_verify(self, state_info):
        """ reference analysis """
        self.setDateVerified(DateTime())

registerType(ReferenceAnalysis, PROJECTNAME)

def modify_fti(fti):
    for a in fti['actions']:
        if a['id'] in ('syndication', 'references', 'metadata',
                       'localroles'):
            a['visible'] = 0
    return fti