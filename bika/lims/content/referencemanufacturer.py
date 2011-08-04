from AccessControl import ClassSecurityInfo
from Products.Archetypes.public import *
from Products.CMFCore.permissions import View, ModifyPortalContent
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.config import I18N_DOMAIN, PROJECTNAME

schema = BikaSchema.copy()

class ReferenceManufacturer(BaseContent):
    security = ClassSecurityInfo()
    schema = schema

registerType(ReferenceManufacturer, PROJECTNAME)