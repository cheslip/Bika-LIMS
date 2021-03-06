from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from bika.lims import PMF, logger
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.analysisrequest import AnalysisRequestsView
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.browser.bika_listing import WorkflowAction
from bika.lims.browser.publish import Publish
from bika.lims.browser.sample import SamplesView
from bika.lims.config import ManageResults
from bika.lims.utils import TimeOrDate
from operator import itemgetter
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from zope.interface import implements
import plone

class ClientWorkflowAction(WorkflowAction):
    """ Workflow actions taken in AnalysisRequest context
        This function is called to do the worflow actions
        that apply to objects transitioned directly
        from Client views
    """

    def __call__(self):
        form = self.request.form
        plone.protect.CheckAuthenticator(form)
        workflow = getToolByName(self.context, 'portal_workflow')
        pc = getToolByName(self.context, 'portal_catalog')
        rc = getToolByName(self.context, REFERENCE_CATALOG)

        # use came_from to decide which UI action was clicked.
        # "workflow_action" is the action name specified in the
        # portal_workflow transition url.
        came_from = "workflow_action"
        action = form.get(came_from, '')
        if not action:
            # workflow_action_button is the action name specified in
            # the bika_listing_view table buttons.
            came_from = "workflow_action_button"
            action = form.get(came_from, '')
            # XXX some browsers agree better than others about our JS ideas.
            if type(action) == type([]): action = action[0]
            if not action:
                if self.destination_url == "":
                    self.destination_url = self.request.get_header("referer",
                                           self.context.absolute_url())
                self.request.response.redirect(self.destination_url)
                return

        if action in ('prepublish', 'publish', 'prepublish'):
            # We pass a list of AR objects to Publish.
            # it returns a list of AR IDs which were actually published.
            ARs_to_publish = []
            transitioned = []
            if 'paths' in form:
                for path in form['paths']:
                    item_id = path.split("/")[-1]
                    item_path = path.replace("/" + item_id, '')
                    ar = pc(id = item_id,
                              path = {'query':item_path,
                                      'depth':1})[0].getObject()
                    # can't publish inactive items
                    if not(
                        'bika_inactive_workflow' in workflow.getChainFor(ar) and \
                        workflow.getInfoFor(ar, 'inactive_state', '') == 'inactive'):
                        ar.setDatePublished(DateTime())
                        ARs_to_publish.append(ar)

                transitioned = Publish(self.context,
                                       self.request,
                                       action,
                                       ARs_to_publish)()

            if len(transitioned) > 1:
                message = _('message_items_published',
                    default = '${items} were published.',
                    mapping = {'items': ', '.join(transitioned)})
            elif len(transitioned) == 1:
                message = _('message_item_published',
                    default = '${items} published.',
                    mapping = {'items': ', '.join(transitioned)})
            else:
                message = _('No items were published')
            message = self.context.translate(message)
            self.context.plone_utils.addPortalMessage(message, 'info')
            self.destination_url = self.request.get_header("referer",
                                   self.context.absolute_url())
            self.request.response.redirect(self.destination_url)

        else:
            # default bika_listing.py/WorkflowAction for other transitions
            WorkflowAction.__call__(self)

class ClientAnalysisRequestsView(AnalysisRequestsView):
    def __init__(self, context, request):
        super(ClientAnalysisRequestsView, self).__init__(context, request)
        self.view_url = self.view_url + "/analysisrequests"

        self.contentFilter['path'] = {"query": "/".join(context.getPhysicalPath()),
                                      "level" : 0 }

        self.context_actions = {}
        wf = getToolByName(self.context, 'portal_workflow')
        # client contact required
        active_contacts = [c for c in context.objectValues('Contact') if \
                           wf.getInfoFor(c, 'inactive_state', '') == 'active']
        if context.portal_type == "Client" and not active_contacts:
            msg = _("Client contact required before request may be submitted")
            self.context.plone_utils.addPortalMessage(self.context.translate(msg))
        else:
            # add actions enabled only for active clients
            # XXX subtractive workflow for these kinds of perms.
            self.context_actions = {}
            if wf.getInfoFor(self.context, 'inactive_state', '') == 'active':
                self.context_actions[_('Add')] = {
                    'url':'analysisrequest_add',
                    'icon': '++resource++bika.lims.images/add.png'}

        review_states = []
        for review_state in self.review_states:
            review_state['columns'].remove('Client')
            review_states.append(review_state)
        self.review_states = review_states

class ClientSamplesView(SamplesView):
    def __init__(self, context, request):
        super(ClientSamplesView, self).__init__(context, request)

        self.contentFilter['path'] = {"query": "/".join(context.getPhysicalPath()),
                                      "level" : 0 }

        review_states = []
        for review_state in self.review_states:
            review_state['columns'].remove('Client')
            review_states.append(review_state)
        self.review_states = review_states

class ClientARImportsView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientARImportsView, self).__init__(context, request)
        self.contentFilter = {'portal_type': 'ARImport'}
        self.context_actions = {_('AR Import'):
                                {'url': 'createObject?type_name=ARImport',
                                 'icon': '++resource++bika.lims.images/add.png'}}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50

        self.icon = "++resource++bika.lims.images/arimport_big.png"
        self.title = _("Analysis Request Imports")
        self.description = _("Analysis Request Imports description", default="")

        self.columns = {
            'title': {'title': _('Import')},
            'getDateImported': {'title': _('Date Imported')},
            'getStatus': {'title': _('Validity')},
            'getDateApplied': {'title': _('Date Submitted')},
            'state_title': {'title': _('State')},
        }
        self.review_states = [
            {'title': _('All'), 'id':'all',
             'columns': ['title',
                         'getDateImported',
                         'getStatus',
                         'getDateApplied',
                         'state_title']},
            {'title': _('Imported'), 'id':'imported',
             'columns': ['title',
                         'getDateImported',
                         'getStatus']},
            {'title': _('Applied'), 'id':'submitted',
             'columns': ['title',
                         'getDateImported',
                         'getStatus',
                         'getDateApplied']},
        ]

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue

            items[x]['replace']['title'] = "<a href='%s'>%s</a>" % \
                 (items[x]['url'], items[x]['title'])

        return items

class ClientARProfilesView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientARProfilesView, self).__init__(context, request)
        self.contentFilter = {'portal_type': 'ARProfile',
                              'getClientUID': context.UID(),
                              'path': {"query": "/".join(context.getPhysicalPath()),
                                       "level" : 0 }
                              }
        bsc = getToolByName(context, 'bika_setup_catalog')
        self.contentsMethod = bsc
        self.context_actions = {_('Add'):
                                {'url': 'createObject?type_name=ARProfile',
                                 'icon': '++resource++bika.lims.images/add.png'}}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50
        self.icon = "++resource++bika.lims.images/arprofile_big.png"
        self.title = _("Analysis Request Profiles")
        self.description = _("Analysis Request Profiles description", "")

        self.columns = {
            'title': {'title': _('Title'),
                      'index': 'sortable_title'},
            'getProfileKey': {'title': _('Profile Key'),
                              'index':'getProfileKey'},
        }
        self.review_states = [
            {'id':'all',
             'title': _('All'),
             'columns': ['title', 'getProfileKey']},
        ]

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            items[x]['replace']['title'] = "<a href='%s'>%s</a>" % \
                 (items[x]['url'], items[x]['title'])

        return items

class ClientAnalysisSpecsView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientAnalysisSpecsView, self).__init__(context, request)
        bsc = getToolByName(context, 'bika_setup_catalog')
        self.contentFilter = {'portal_type': 'AnalysisSpec',
                              'getClientUID': context.UID(),
                              'path': {"query": "/".join(context.getPhysicalPath()),
                                       "level" : 0 }
                              }
        self.contentsMethod = bsc
        self.context_actions = {_('Add'):
                                {'url': 'createObject?type_name=AnalysisSpec',
                                 'icon': '++resource++bika.lims.images/add.png'},
                                _('Set to lab defaults'):
                                {'url': 'set_to_lab_defaults',
                                 'icon': '++resource++bika.lims.images/analysisspec.png'}}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50

        self.icon = "++resource++bika.lims.images/analysisspec_big.png"
        self.title = _("Analysis Specifications")
        self.description = _("Analysis Specifications description")

        self.columns = {
            'SampleType': {'title': _('Sample Type'),
                           'index': 'getSampleTypeTitle'},
        }
        self.review_states = [
            {'id':'all',
             'title': _('All'),
             'columns': ['SampleType'],
             },
        ]

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue

            obj = items[x]['obj']

            items[x]['SampleType'] = obj.getSampleType() and \
                 obj.getSampleType().Title()

            items[x]['replace']['SampleType'] = "<a href='%s'>%s</a>" % \
                 (items[x]['url'], items[x]['SampleType'])

        return items

class SetSpecsToLabDefaults(BrowserView):
    """ Remove all client specs, and add copies of all lab specs
    """
    def __call__(self):
        form = self.request.form
        bsc = getToolByName(self.context, 'bika_setup_catalog')

        # find and remove existing specs
        cs = bsc(portal_type = 'AnalysisSpec',
                  getClientUID = self.context.UID())
        if cs:
            self.context.manage_delObjects([s.id for s in cs])

        # find and duplicate lab specs
        ls = bsc(portal_type = 'AnalysisSpec',
                 getClientUID = self.context.bika_setup.bika_analysisspecs.UID())
        ls = [s.getObject() for s in ls]
        for labspec in ls:
            _id = self.context.invokeFactory(type_name = 'AnalysisSpec', id = 'tmp')
            clientspec = self.context[_id]
            clientspec.processForm()
            clientspec.edit(
                SampleType = labspec.getSampleType(),
                ResultsRange = labspec.getResultsRange(),
            )
        message = self.context.translate(
            _("Analysis specs reset to lab defaults."))
        self.context.plone_utils.addPortalMessage(message, 'info')
        self.request.RESPONSE.redirect(self.context.absolute_url() + "/analysisspecs")
        return

class ClientAttachmentsView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientAttachmentsView, self).__init__(context, request)
        self.contentFilter = {'portal_type': 'Attachment',
                              'sort_order': 'reverse'}
        self.context_actions = {}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50

        self.icon = "++resource++bika.lims.images/attachment_big.png"
        self.title = _("Attachments")
        self.description = _("Attachments description", default="")

        self.columns = {
            'getTextTitle': {'title': _('Request ID')},
            'AttachmentFile': {'title': _('File')},
            'AttachmentType': {'title': _('Attachment Type')},
            'ContentType': {'title': _('Content Type')},
            'FileSize': {'title': _('Size')},
            'DateLoaded': {'title': _('Date Loaded')},
        }
        self.review_states = [
            {'title': 'All', 'id':'all',
             'columns': ['getTextTitle',
                         'AttachmentFile',
                         'AttachmentType',
                         'ContentType',
                         'FileSize',
                         'DateLoaded']},
        ]

    def lookupMime(self, name):
        mimetool = getToolByName(self, 'mimetypes_registry')
        mimetypes = mimetool.lookup(name)
        if len(mimetypes):
            return mimetypes[0].name()
        else:
            return name

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            obj = items[x]['obj']
            obj_url = obj.absolute_url()
            file = obj.getAttachmentFile()
            icon = file.getBestIcon()

            items[x]['AttachmentFile'] = file.filename()
            items[x]['AttachmentType'] = obj.getAttachmentType().Title()
            items[x]['AttachmentType'] = obj.getAttachmentType().Title()
            items[x]['ContentType'] = self.lookupMime(file.getContentType())
            items[x]['FileSize'] = '%sKb' % (file.get_size() / 1024)
            items[x]['DateLoaded'] = obj.getDateLoaded()

            items[x]['replace']['getTextTitle'] = "<a href='%s'>%s</a>" % \
                 (obj_url, items[x]['getTextTitle'])

            items[x]['replace']['AttachmentFile'] = \
                 "<a href='%s/at_download/AttachmentFile'>%s</a>" % \
                 (obj_url, items[x]['AttachmentFile'])
        return items

class ClientOrdersView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientOrdersView, self).__init__(context, request)
        self.contentFilter = {'portal_type': 'SupplyOrder',
                              'sort_on':'id',
                              'sort_order': 'reverse'}
        self.context_actions = {_('Add'):
                                {'url': 'createObject?type_name=SupplyOrder',
                                 'icon': '++resource++bika.lims.images/add.png'}}
        self.show_table_only = False
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 25

        self.icon = "++resource++bika.lims.images/order_big.png"
        self.title = _("Orders")
        self.description = _("Orders description")

        self.columns = {
            'OrderNumber': {'title': _('Order Number')},
            'OrderDate': {'title': _('Order Date')},
            'DateDispatched': {'title': _('Date Dispatched')},
            'state_title': {'title': _('State')},
        }
        self.review_states = [
            {'title': _('All'), 'id':'all',
             'columns': ['OrderNumber',
                         'OrderDate',
                         'DateDispatched',
                         'state_title']},
            {'title': _('Pending'), 'id':'pending',
             'columns': ['OrderNumber',
                         'OrderDate']},
            {'title': _('Dispatched'), 'id':'dispatched',
             'columns': ['OrderNumber',
                         'OrderDate',
                         'DateDispatched']},
        ]

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            obj = items[x]['obj']
            items[x]['OrderNumber'] = obj.getOrderNumber()
            items[x]['OrderDate'] = TimeOrDate(self.context, obj.getOrderDate())
            items[x]['DateDispatched'] = TimeOrDate(self.context, obj.getDateDispatched())

            items[x]['replace']['OrderNumber'] = "<a href='%s'>%s</a>" % \
                 (items[x]['url'], items[x]['OrderNumber'])

        return items

class ClientContactsView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ClientContactsView, self).__init__(context, request)
        self.contentFilter = {'portal_type': 'Contact',
                              'sort_on':'sortable_title',
                              'path': {"query": "/".join(context.getPhysicalPath()),
                                       "level" : 0 }
                              }
        self.context_actions = {_('Add'):
                                {'url': 'createObject?type_name=Contact',
                                 'icon': '++resource++bika.lims.images/add.png'}}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50

        self.icon = "++resource++bika.lims.images/client_contact_big.png"
        self.title = _("Contacts")
        self.description = _("Contacts description", "")

        self.columns = {
            'getFullname': {'title': _('Full Name'),
                            'index': 'getFullname'},
            'getEmailAddress': {'title': _('Email Address')},
            'getBusinessPhone': {'title': _('Business Phone')},
            'getMobilePhone': {'title': _('Mobile Phone')},
            'getFax': {'title': _('Fax')},
        }
        self.review_states = [
            {'title': 'All', 'id':'all',
             'columns': ['getFullname',
                         'getEmailAddress',
                         'getBusinessPhone',
                         'getMobilePhone',
                         'getFax']},
            {'title': 'Active', 'id':'active',
             'contentFilter': {'inactive_state': 'active'},
             'transitions': ['deactivate', ],
             'columns': ['getFullname',
                         'getEmailAddress',
                         'getBusinessPhone',
                         'getMobilePhone',
                         'getFax']},
            {'title': 'Dormant', 'id':'inactive',
             'contentFilter': {'inactive_state': 'inactive'},
             'transitions': ['activate', ],
             'columns': ['getFullname',
                         'getEmailAddress',
                         'getBusinessPhone',
                         'getMobilePhone',
                         'getFax']},
        ]

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue

            obj = items[x]['obj']
            items[x]['getFullname'] = obj.getFullname()
            items[x]['getEmailAddress'] = obj.getEmailAddress()
            items[x]['getBusinessPhone'] = obj.getBusinessPhone()
            items[x]['getMobilePhone'] = obj.getMobilePhone()

            items[x]['replace']['getFullname'] = "<a href='%s'>%s</a>" % \
                 (items[x]['url'], items[x]['getFullname'])

            if items[x]['getEmailAddress']:
                items[x]['replace']['getEmailAddress'] = "<a href='mailto:%s'>%s</a>" % \
                     (items[x]['getEmailAddress'], items[x]['getEmailAddress'])

        return items
