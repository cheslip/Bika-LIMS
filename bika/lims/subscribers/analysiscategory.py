from DateTime import DateTime
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.utils import getToolByName
from bika.lims import bikaMessageFactory as _
import transaction

def AfterTransitionEventHandler(category, event):

    wf = getToolByName(category, 'portal_workflow')
    pc = getToolByName(category, 'portal_catalog')
    rc = getToolByName(category, REFERENCE_CATALOG)
    pu = getToolByName(category, 'plone_utils')

    # creation doesn't have a 'transition'
    if not event.transition:
        return

    if event.transition.id == "deactivate":
        # A category cannot be deactivated if it contains services
        bsc = getToolByName(category, 'bika_setup_catalog')
        ars = bsc(portal_type='AnalysisService', getCategoryUID = category.UID())
        if ars:
            message = _("Category cannot be deactivated because it contains Analysis Services")
            pu.addPortalMessage(message, 'error')
            transaction.get().abort()
            raise WorkflowException
