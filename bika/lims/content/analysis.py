from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.ATContentTypes.content import schemata
from Products.ATExtensions.ateapi import DateTimeField, DateTimeWidget, RecordsField
from Products.Archetypes import atapi
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.Archetypes.public import *
from Products.Archetypes.references import HoldingReference
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.CMFEditions.ArchivistTool import ArchivistRetrieveError
from bika.lims import bikaMessageFactory as _
from bika.lims import logger
from bika.lims.browser.fields import DurationField
from bika.lims.browser.fields import HistoryAwareReferenceField
from bika.lims.browser.fields import InterimFieldsField
from bika.lims.browser.widgets import DurationWidget
from bika.lims.browser.widgets import RecordsWidget as BikaRecordsWidget
from bika.lims.config import PROJECTNAME
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.interfaces import IAnalysis
from decimal import Decimal
from zope.interface import implements
import datetime

schema = BikaSchema.copy() + Schema((
    HistoryAwareReferenceField('Service',
        required = 1,
        allowed_types = ('AnalysisService',),
        relationship = 'AnalysisAnalysisService',
        referenceClass = HoldingReference,
        widget = ReferenceWidget(
            label = _("Analysis Service"),
        )
    ),
    HistoryAwareReferenceField('Calculation',
        allowed_types = ('Calculation',),
        relationship = 'AnalysisCalculation',
        referenceClass = HoldingReference,
    ),
    ReferenceField('Attachment',
        multiValued = 1,
        allowed_types = ('Attachment',),
        referenceClass = HoldingReference,
        relationship = 'AnalysisAttachment',
    ),
    InterimFieldsField('InterimFields',
        widget = BikaRecordsWidget(
            label = _("Calculation Interim Fields"),
        )
    ),
    StringField('Result',
    ),
    StringField('ResultDM',
    ),
    BooleanField('Retested',
        default = False,
    ),
    DurationField('MaxTimeAllowed',
        widget = DurationWidget(
            label = _("Maximum turn-around time"),
            description = _("Maximum turn-around time description",
                            "Maximum time allowed for completion of the analysis. "
                            "A late analysis alert is raised when this period elapses"),
        ),
    ),
    DateTimeField('DateAnalysisPublished',
        widget = DateTimeWidget(
            label = _("Date Published"),
        ),
    ),
    DateTimeField('DueDate',
        widget = DateTimeWidget(
            label = _("Due Date"),
        ),
    ),
    IntegerField('Duration',
        widget = IntegerWidget(
            label = _("Duration"),
        )
    ),
    IntegerField('Earliness',
        widget = IntegerWidget(
            label = _("Earliness"),
        )
    ),
    BooleanField('ReportDryMatter',
        default = False,
    ),

    StringField('Analyst',
    ),
    ReferenceField('Instrument',
        required = 0,
        allowed_types = ('Instrument',),
        relationship = 'WorksheetInstrument',
        referenceClass = HoldingReference,
    ),
    ReferenceField('SamplePartition',
        required = 0,
        allowed_types = ('SamplePartition',),
        relationship = 'AnalysisSamplePartition',
        referenceClass = HoldingReference,
    ),
    ComputedField('ClientUID',
        expression = 'context.aq_parent.aq_parent.UID()',
    ),
    ComputedField('ClientTitle',
        expression = 'context.aq_parent.aq_parent.Title()',
    ),
    ComputedField('RequestID',
        expression = 'context.aq_parent.getRequestID()',
    ),
    ComputedField('ClientOrderNumber',
        expression = 'context.aq_parent.getClientOrderNumber()',
    ),
    ComputedField('Keyword',
        expression = 'context.getService() and context.getService().getKeyword() or ""',
    ),
    ComputedField('ServiceTitle',
        expression = 'context.getService() and context.getService().Title() or ""',
    ),
    ComputedField('ServiceUID',
        expression = 'context.getService() and context.getService().UID() or ""',
    ),
    ComputedField('CategoryUID',
        expression = 'context.getService() and context.getService().getCategoryUID() or ""',
    ),
    ComputedField('CategoryTitle',
        expression = 'context.getService() and context.getService().getCategoryTitle() or ""',
    ),
    ComputedField('PointOfCapture',
        expression = 'context.getService() and context.getService().getPointOfCapture()',
    ),
    ComputedField('DateReceived',
        expression = 'context.aq_parent.getDateReceived()',
    ),
),
)

class Analysis(BaseContent):
    implements(IAnalysis)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    def _getCatalogTool(self):
        from bika.lims.catalog import getCatalog
        return getCatalog(self)

    def Title(self):
        """ Return the service title as title """
        try:
            s = self.getService()
        except ArchivistRetrieveError:
            return ""
        if s: return s.Title()

    def getUncertainty(self, result = None):
        """ Calls self.Service.getUncertainty with either the provided
            result value or self.Result
        """
        return self.getService().getUncertainty(result and result or self.getResult())

    def getDependents(self):
        """ Return a list of analyses who depend on us
            to calculate their result
        """
        rc = getToolByName(self, REFERENCE_CATALOG)
        dependents = []
        service = self.getService()
        ar = self.aq_parent
        for sibling in ar.getAnalyses(full_objects = True):
            if sibling == self:
                continue
            service = rc.lookupObject(sibling.getServiceUID())
            calculation = service.getCalculation()
            if not calculation:
                continue
            depservices = calculation.getDependentServices()
            if self.getService() in depservices:
                dependents.append(sibling)
        return dependents

    def getDependencies(self):
        """ Return a list of analyses who we depend on
            to calculate our result.
        """
        siblings = self.aq_parent.getAnalyses(full_objects = True)
        calculation = self.getService().getCalculation()
        if not calculation:
            return []
        dep_services = [d.UID() for d in calculation.getDependentServices()]
        dep_analyses = [a for a in siblings if a.getServiceUID() in dep_services]
        return dep_analyses

    def result_in_range(self, result = None, specification = "lab"):
        """ Check if a result is "in range".
            if result is None, self.getResult() is called for the result value.
            Return False,failed_spec if out of range
            Return True,None if in range
            return '1',None if in shoulder
        """

        client_uid = specification == "client" and self.getClientUID() or \
            self.bika_setup.bika_analysisspecs.UID()

        result = result and result or self.getResult()

        # if analysis result is not a number, then we assume in range
        try:
            result = float(str(result))
        except ValueError:
            return True, None

        service = self.getService()
        keyword = service.getKeyword()
        sampletype = self.aq_parent.getSample().getSampleType()
        sampletype_uid = sampletype and sampletype.UID() or ''
        bsc = getToolByName(self, 'bika_setup_catalog')
        proxies = bsc(portal_type = 'AnalysisSpec',
                      getSampleTypeUID = sampletype_uid)
        a = [p for p in proxies if p.getClientUID == client_uid]
        if a:
            spec_obj = a[0].getObject()
            spec = spec_obj.getResultsRangeDict()
        else:
            # if no range is specified we assume it is in range
            return True, None

        if spec.has_key(keyword):
            spec_min = float(spec[keyword]['min'])
            spec_max = float(spec[keyword]['max'])

            if spec_min <= result <= spec_max:
                return True, None

            """ check if in 'shoulder' error range - out of range, but in acceptable error """
            error_amount = (result / 100) * float(spec[keyword]['error'])
            error_min = result - error_amount
            error_max = result + error_amount
            if ((result < spec_min) and (error_max >= spec_min)) or \
               ((result > spec_max) and (error_min <= spec_max)):
                return '1', spec[keyword]
        else:
            return True, None
        return False, spec[keyword]

atapi.registerType(Analysis, PROJECTNAME)
