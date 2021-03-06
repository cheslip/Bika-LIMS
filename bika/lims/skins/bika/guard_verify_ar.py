## Script (Python) "guard_verify_ar"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##

from bika.lims import Verify, VerifyOwnResults

wf_tool = context.portal_workflow

# Can't do anything to the object if it's cancelled
if wf_tool.getInfoFor(context, 'cancellation_state') == "cancelled":
    return False

checkPermission = context.portal_membership.checkPermission
if not checkPermission(Verify, context):
    # Allow automatic verification if all analyses are already verified.
    for analysis in context.getAnalyses(full_objects = True):
        review_state = wf_tool.getInfoFor(analysis, 'review_state')
        if review_state in ('sample_due', 'sample_received', 'attachment_due', 'to_be_verified', 'assigned',):
            return False
    return True

if checkPermission(VerifyOwnResults, context):
    return True

# Check for self-submitted analyses.
from AccessControl import getSecurityManager
user_id = getSecurityManager().getUser().getId()

self_submitted = False
for analysis in context.getAnalyses(full_objects = True):
    review_state = wf_tool.getInfoFor(analysis, 'review_state')
    if review_state == 'to_be_verified':
        review_history = wf_tool.getInfoFor(analysis, 'review_history')
        review_history = context.reverseList(review_history)
        for event in review_history:
            if event.get('action') == 'submit':
                if event.get('actor') == user_id:
                    self_submitted = True
                break
        if self_submitted:
            break
if self_submitted:
    return False
else:
    return True

