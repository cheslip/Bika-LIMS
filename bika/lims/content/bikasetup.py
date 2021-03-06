from AccessControl import ClassSecurityInfo
from Products.ATExtensions.ateapi import RecordsField
from bika.lims.browser.widgets import RecordsWidget
from Products.Archetypes.public import *
from Products.Archetypes.references import HoldingReference
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from bika.lims import bikaMessageFactory as _
from bika.lims.config import *
from bika.lims.content.bikaschema import BikaFolderSchema
from bika.lims.interfaces import IBikaSetup
from bika.lims.interfaces import IHaveNoBreadCrumbs
from plone.app.folder import folder
from zope.interface import implements
import sys

class PrefixesField(RecordsField):
    """a list of prefixes per portal_type"""
    _properties = RecordsField._properties.copy()
    _properties.update({
        'type' : 'prefixes',
        'subfields' : ('portal_type', 'prefix', 'padding'),
        'subfield_labels':{'portal_type': 'Portal type',
                           'prefix': 'Prefix',
                           'padding': 'Padding',
                           },
        'subfield_readonly':{'portal_type': False,
                             'prefix': False,
                             'padding': False,
                            },
        'subfield_sizes':{'portal_type':32,
                          'prefix': 12,
                          'padding':12},
    })
    security = ClassSecurityInfo()

LABEL_AUTO_OPTIONS = DisplayList((
    ('None', _('None')),
    ('register', _('Register')),
    ('receive', _('Recieve')),
))

LABEL_AUTO_SIZES = DisplayList((
    ('small', _('Small')),
    ('normal', _('Normal')),
))

schema = BikaFolderSchema.copy() + Schema((
    IntegerField('PasswordLifetime',
        schemata = _("Security"),
        required = 1,
        default = 0,
        widget = IntegerWidget(
            label = _("Password lifetime"),
            description = _("Password lifetime description",
                            "The number of days before a password expires. 0 disables password expiry"),
        )
    ),
    IntegerField('AutoLogOff',
        schemata = _("Security"),
        required = 1,
        default = 0,
        widget = IntegerWidget(
            label = _("Automatic log-off"),
            description = _("Automatic log-off description",
                            "The number of minutes before a user is automatically logged off. "
                            "0 disables automatic log-off"),
        )
    ),
    FixedPointField('MemberDiscount',
        schemata = _("Accounting"),
        default = '33.33',
        widget = DecimalWidget(
            label = _("Member discount %"),
            description = _("Bika Setup Member discount % description",
                            "The discount percentage entered here, is applied to the prices for clients "
                            "flagged as 'members', normally co-operative members or associates deserving "
                            "of this discount"),
        )
    ),
    FixedPointField('VAT',
        schemata = _("Accounting"),
        default = '14.00',
        widget = DecimalWidget(
            label = _("VAT %"),
            description = _("Bika Setup VAT % description",
                            "Enter percentage value eg. 14.0. This percentage is applied system wide "
                            "but can be overwrittem on individual items"),
        )
    ),
    IntegerField('MinimumResults',
        schemata = _("Results reports"),
        required = 1,
        default = 5,
        widget = IntegerWidget(
            label = _("QC Minimum results",
                      "Minimum number of results for QC stats calculations"),
            description = _("QC Minimum results description",
                            "Using too few data points does not make statistical sense. "
                            "Set an acceptable minimum number of results before QC statistics "
                            "will be calculated and plotted"),
        )
    ),
    IntegerField('BatchEmail',
        schemata = _("Results reports"),
        required = 1,
        default = 5,
        widget = IntegerWidget(
            label = _("Maximum cols per email",
                      "Maximum columns per results email"),
            description = _("Maximum cols per email description",
                            "Set the maximum number of analysis requests per results email. "
                            "Too many columns per email are difficult to read for some clients "
                            "who prefer fewer results per email"),
        )
    ),
    IntegerField('BatchFax',
        schemata = _("Results reports"),
        required = 1,
        default = 4,
        widget = IntegerWidget(
            label = _("Maximum cols per fax",
                      "Maximum columns per results fax"),
            description = _("Maximum cols per fax description",
                            "Too many AR columns per fax will see the font size minimised and could "
                            "render faxes illegible. 4 ARs maximum per page is recommended"),
        )
    ),
    # XXX stringfield, chars to strip from cell number
    StringField('SMSGatewayAddress',
        schemata = _("Results reports"),
        required = 0,
        widget = StringWidget(
            label = _("SMS Gateway Email Address"),
            description = _("SMS Gateway Email Address description",
                            "The email to SMS gateway address. Either a complete email address, "
                             "or just the domain, e.g. '@2way.co.za', the contact's mobile phone "
                             "number will be prepended to"),
        )
    ),
    ReferenceField('DryMatterService',
        schemata = _("Analyses"),
        required = 0,
        vocabulary_display_path_bound = sys.maxint,
        allowed_types = ('AnalysisService',),
        relationship = 'SetupDryAnalysisService',
        vocabulary = 'getAnalysisServices',
        referenceClass = HoldingReference,
        widget = ReferenceWidget(
            label = _("Dry matter analysis"),
            description = _("Dry matter analysis description",
                            "The analysis to be used for determining dry matter."),
        )
    ),
    LinesField('ARImportOption',
        schemata = _("Analyses"),
        vocabulary = ARIMPORT_OPTIONS,
        widget = MultiSelectionWidget(
            label = _("AR Import options"),
            description = _("AR Import options description",
                            "'Classic' indicates importing analysis requests per sample and "
                            "analysis service selection. With 'Profiles', analysis profile keywords "
                            "are used to select multiple analysis services together"),
        )
    ),
    StringField('ARAttachmentOption',
        schemata = _("Analyses"),
        default = 'p',
        vocabulary = ATTACHMENT_OPTIONS,
        widget = SelectionWidget(
            label = _("AR Attachment Option"),
            description = _("AR Attachment Option description",
                            "The system wide default configuration to indicate "
                            "whether file attachments are required, permitted or not "
                            "per analysis request"),
        )
    ),
    StringField('AnalysisAttachmentOption',
        schemata = _("Analyses"),
        default = 'p',
        vocabulary = ATTACHMENT_OPTIONS,
        widget = SelectionWidget(
            label = _("Analysis Attachment Option"),
            description = _("Analysis Attachment Option description",
                            "Same as the above, but sets the default on analysis services. "
                            "This setting can be set per individual analysis on its "
                            "own configuration"),
        )
    ),
    IntegerField('DefaultSampleLifetime',
        schemata = _("Analyses"),
        required = 1,
        default = 30,
        widget = IntegerWidget(
            label = _("Default sample retention period"),
            description = _("Default sample retention period description",
                            "The number of days before a sample expires and cannot be analysed "
                            "any more. This setting can be overwritten per individual sample type "
                            "in the sample types setup"),
        )
    ),
    LinesField('AutoPrintLabels',
        schemata = _("Labels"),
        vocabulary = LABEL_AUTO_OPTIONS,
        widget = SelectionWidget(
            format = 'select',
            label = _("Automatic AR label printing"),
            description = _("Automatic AR label printing description",
                            "Select 'Register' if you want labels to be automatically printed when "
                            "new ARs are created.  Select 'Receive' to print labels when the 'Receive' "
                            "transition is invoked on ARs or Samples.  Select None to disable automatic "
                            "printing"),
        )
    ),
    LinesField('AutoLabelSize',
        schemata = _("Labels"),
        vocabulary = LABEL_AUTO_SIZES,
        widget = SelectionWidget(
            format = 'select',
            label = _("Automatic AR label sizes"),
            description = _("Automatic AR label sizes description",
                            "Select the size label to print if Automatic label printing is enabled."),
        )
    ),
    PrefixesField('Prefixes',
        schemata = _("ID Server"),
        default = [{'portal_type': 'ARImport', 'prefix': 'B', 'padding': '3'},
                   {'portal_type': 'Client', 'prefix': 'client', 'padding': '0'},
                   {'portal_type': 'DuplicateAnalysis', 'prefix': 'DA', 'padding': '0'},
                   {'portal_type': 'Invoice', 'prefix': 'I', 'padding': '4'},
                   {'portal_type': 'ReferenceAnalysis', 'prefix': 'RA', 'padding': '4'},
                   {'portal_type': 'ReferenceSample', 'prefix': 'RS', 'padding': '4'},
                   {'portal_type': 'SupplyOrder', 'prefix': 'O', 'padding': '3'},
                   {'portal_type': 'Worksheet', 'prefix': 'WS', 'padding': '4'},
                   {'portal_type': 'SamplePartition', 'prefix': 'part', 'padding': '0'},
                   ],
#        fixedSize=8,
        widget=RecordsWidget(
            label = _("Prefixes"),
            description = _("Prefixes description",
                            "Define the prefixes for the unique sequential IDs the system issues "
                            "for objects such as samples and analysis requests. In the 'Padding' "
                            "field, indicate with how many leading zeros the numbers must be padded. "
                            "E.g. a prefix of AR with padding of 4 for analysis requests, will see "
                            "them numbered from AR0001 to AR9999."),
            allowDelete=False,
        )
    ),
    BooleanField('YearInPrefix',
        schemata = _("ID Server"),
        default = False,
        widget = BooleanWidget(
            label = _("Include year in ID prefix"),
            description = _("Include year in ID prefix description",
                            "Adds a two-digit year after the ID prefix.")
        ),
    ),
    IntegerField('SampleIDPadding',
        schemata = _("ID Server"),
        required = 1,
        default = 4,
        widget = IntegerWidget(
            label = _("Sample ID Padding"),
            description = _("Sample ID Padding description",
                            "The length of the zero-padding for Sample IDs"),
        )
    ),
    IntegerField('ARIDPadding',
        schemata = _("ID Server"),
        required = 1,
        default = 2,
        widget = IntegerWidget(
            label = _("AR ID Padding"),
            description = _("AR ID Padding description",
                            "The length of the zero-padding for the AR number in AR IDs"),
        )
    ),
    BooleanField('ExternalIDServer',
        schemata = _("ID Server"),
        default = False,
        widget = BooleanWidget(
            label = _("Use external ID server"),
            description = _("Use external ID server description",
                            "Check this if you want to use a seperate ID server. "
                            "Prefixes are configurable seperately in each Bika site.")
        ),
    ),
    StringField('IDServerURL',
        schemata = _("ID Server"),
        widget = StringWidget(
            label = _("ID Server URL"),
            description = _("ID Server URL description",
                            "The full URL: protocol://URL/path:port")

        ),
    ),
))

schema['title'].validators = ()
schema['title'].widget.visible = False
# Update the validation layer after change the validator in runtime
schema['title']._validationLayer()

class BikaSetup(folder.ATFolder):
    security = ClassSecurityInfo()
    schema = schema
    implements(IBikaSetup, IHaveNoBreadCrumbs)

    def getAttachmentsPermitted(self):
        """ are any attachments permitted """
        if self.getARAttachmentOption() in ['r', 'p'] \
        or self.getAnalysisAttachmentOption() in ['r', 'p']:
            return True
        else:
            return False

    def getARAttachmentsPermitted(self):
        """ are AR attachments permitted """
        if self.getARAttachmentOption() == 'n':
            return False
        else:
            return True

    def getAnalysisAttachmentsPermitted(self):
        """ are analysis attachments permitted """
        if self.getAnalysisAttachmentOption() == 'n':
            return False
        else:
            return True

    def getAnalysisServices(self):
        """
        """
        bsc = getToolByName(self, 'bika_setup_catalog')
        items = [('','')] + [(o.UID, o.Title) for o in \
                               bsc(portal_type='AnalysisService',
                                   inactive_state = 'active')]
        items.sort(lambda x,y: cmp(x[1], y[1]))
        return DisplayList(list(items))

registerType(BikaSetup, PROJECTNAME)
