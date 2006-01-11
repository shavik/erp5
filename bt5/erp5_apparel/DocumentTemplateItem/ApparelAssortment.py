##############################################################################
#
# Copyright (c) 2002, 2004 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from AccessControl import ClassSecurityInfo

from Products.ERP5.Document.Resource import Resource
from Products.ERP5Type import Permissions, PropertySheet, Constraint, Interface
from Products.ERP5Type.Base import Base
from Products.ERP5Type.XMLMatrix import XMLMatrix


from zLOG import LOG

class ApparelAssortment(Resource, XMLMatrix):
    """
      a assortment..
    """

    meta_type = 'ERP5 Apparel Assortment'
    portal_type = 'Apparel Assortment'

    # Declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(Permissions.AccessContentsInformation)

    # Declarative properties
    property_sheets = ( PropertySheet.Base
                      # this property sheet must be placed before resource to redefine some properties
                      , PropertySheet.ApparelAssortment
                      , PropertySheet.XMLObject
                      , PropertySheet.CategoryCore
                      , PropertySheet.DublinCore
                      , PropertySheet.Price
                      , PropertySheet.Resource
                      , PropertySheet.Reference
                      , PropertySheet.Arrow
                      , PropertySheet.Comment
                      , PropertySheet.ApparelCollection
                      , PropertySheet.ApparelSize
                      )

    # Hard Wired Variation List
    # XXX - may be incompatible with future versions of ERP5
    #variation_base_category_list = ('coloris', 'taille')


#    security.declareProtected(Permissions.View, 'getDefaultQuantityUnit')
#    def getDefaultQuantityUnit(self):
#      # Requires for Assorted Resource XXX temp patch until getAggregated methods use real classes instead of dicts
#      # and access props/cats through accessors
#      return "Unite"
#
#    security.declareProtected(Permissions.View, 'getQuantityUnit')
#    def getQuantityUnit(self):
#      # Requires for Assorted Resource XXX temp patch until getAggregated methods use real classes instead of dicts
#      # and access props/cats through accessors
#      return "Unite"
#
#    security.declareProtected(Permissions.View, 'getQuantityUnitList')
#    def getQuantityUnitList(self):
#      # Requires for Assorted Resource XXX temp patch until getAggregated methods use real classes instead of dicts
#      # and access props/cats through accessors
#      return ["Unite"]
