## Script (Python) "guard_attach_analysis"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##

wf_tool = context.portal_workflow

# Can't do anything to the object if it's cancelled
# reference and duplicate analyses don't have cancellation_state
if context.portal_type == "Analysis":
    if wf_tool.getInfoFor(context, 'cancellation_state') == "cancelled":
        return False

# For now, more thorough than strictly needed.
if not context.getAttachment():
    service = context.getService()
    if service.getAttachmentOption() == 'r':
        return False

# reference and duplicate analyses don't happen on services with dependencies
if context.portal_type != "Analysis":
    return True

dependencies = context.getDependencies()
if dependencies:
    interim_fields = False
    service = context.getService()
    calculation = service.getCalculation()
    if calculation:
        interim_fields = calculation.getInterimFields()
    for dep in dependencies:
        review_state = wf_tool.getInfoFor(dep, 'review_state')
        if interim_fields:
            if review_state in ('sample_due', 'sample_received', 'attachment_due', 'to_be_verified',):
                return False
        else:
            if review_state in ('sample_due', 'sample_received', 'attachment_due',):
                return False
return True

