# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2006 Nexedi SARL and Contributors. All Rights Reserved.
#                    Ivan Tyagov <ivan@nexedi.com>
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

import os
import tempfile
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, DTMLFile
from Products.CMFCore.utils import getToolByName
from Products.ERP5Type.Tool.BaseTool import BaseTool
from Products.ERP5Type import Permissions
from AccessControl.SecurityManagement import setSecurityManager
from Products.ERP5 import _dtmldir
from Products.ERP5.Tool.LogMixin import LogMixin
from Products.ERP5Type.Utils import _setSuperSecurityManager
from App.config import getConfiguration
from AccessControl import Unauthorized
from Products.ERP5Type.Cache import CachingMethod
import tarfile

_MARKER = []

class IntrospectionTool(LogMixin, BaseTool):
  """
    This tool provides both local and remote introspection.
  """

  id = 'portal_introspections'
  title = 'Introspection Tool'
  meta_type = 'ERP5 Introspection Tool'
  portal_type = 'Introspection Tool'

  security = ClassSecurityInfo()

  security.declareProtected(Permissions.ManagePortal, 'manage_overview')
  manage_overview = DTMLFile('explainIntrospectionTool', _dtmldir )

  #
  #   Remote menu management
  #
  security.declareProtected(Permissions.AccessContentsInformation,
                            'getFilteredActionDict')
  def getFilteredActionDict(self, user_name=_MARKER):
    """
      Returns menu items for a given user
    """
    portal = self.getPortalObject()
    is_portal_manager = getToolByName(portal, 
      'portal_membership').checkPermission(Permissions.ManagePortal, self)
    downgrade_authenticated_user = user_name is not _MARKER and is_portal_manager
    if downgrade_authenticated_user:
      # downgrade to desired user
      original_security_manager = _setSuperSecurityManager(self, user_name)

    # call the method implementing it
    erp5_menu_dict = getToolByName(portal, 'portal_actions').listFilteredActionsFor(portal)

    if downgrade_authenticated_user:
      # restore original Security Manager
      setSecurityManager(original_security_manager)

    # Unlazyfy URLs and other lazy values so that it can be marshalled
    result = {}
    for key, action_list in erp5_menu_dict.items():
      result[key] = map(lambda action:dict(action), action_list)

    return result

  security.declareProtected(Permissions.AccessContentsInformation,
                           'getModuleItemList')
  def getModuleItemList(self, user_name=_MARKER):
    """
      Returns module items for a given user
    """
    portal = self.getPortalObject()
    is_portal_manager = getToolByName(portal, 
      'portal_membership').checkPermission(Permissions.ManagePortal, self)
    downgrade_authenticated_user = user_name is not _MARKER and is_portal_manager
    if downgrade_authenticated_user:
      # downgrade to desired user
      original_security_manager = _setSuperSecurityManager(self, user_name)

    # call the method implementing it
    erp5_module_list = portal.ERP5Site_getModuleItemList()

    if downgrade_authenticated_user:
      # restore original Security Manager
      setSecurityManager(original_security_manager)

    return erp5_module_list

  #
  #   Local file access
  #
  def _getLocalFile(self, REQUEST, RESPONSE, file_path, 
                         tmp_file_path='/tmp/', compressed=1):
    """
      It should return the local file compacted as tar.gz.
    """
    if file_path.startswith('/'):
      raise IOError, 'The file path must be relative not absolute'
    instance_home = getConfiguration().instancehome
    file_path = os.path.join(instance_home, file_path)
    if not os.path.exists(file_path):
      raise IOError, 'The file: %s does not exist.' % file_path

    if compressed:
      tmp_file_path = tempfile.mktemp(dir=tmp_file_path)
      tmp_file = tarfile.open(tmp_file_path,"w:gz")
      tmp_file.add(file_path)
      tmp_file.close()
      RESPONSE.setHeader('Content-type', 'application/x-tar')
    else:
      tmp_file_path = file_path

    f = open(tmp_file_path)
    try:
      RESPONSE.setHeader('Content-Length', os.stat(tmp_file_path).st_size)
      RESPONSE.setHeader('Content-Disposition', \
                 'attachment;filename="%s.tar.gz"' % file_path.split('/')[-1])
      for data in f:
        RESPONSE.write(data)
    finally:
      f.close()

    if compressed:
      os.remove(tmp_file_path)

    return ''

  security.declareProtected(Permissions.ManagePortal, 'getAccessLog')
  def getAccessLog(self,  compressed=1, REQUEST=None):
    """
      Get the Access Log.
    """
    if REQUEST is not None:
      response = REQUEST.RESPONSE
    else:
      return "FAILED"

    return self._getLocalFile(REQUEST, response, 
                               file_path='log/Z2.log', 
                               compressed=1) 

  security.declareProtected(Permissions.ManagePortal, 'getAccessLog')
  def getEventLog(self,  compressed=1, REQUEST=None):
    """
      Get the Access Log.
    """
    if REQUEST is not None:
      response = REQUEST.RESPONSE
    else:
      return "FAILED"

    return self._getLocalFile(REQUEST, response,
                               file_path='log/event.log',
                               compressed=1)

  security.declareProtected(Permissions.ManagePortal, 'getAccessLog')
  def getDataFs(self,  compressed=1, REQUEST=None):
    """
      Get the Access Log.
    """
    if REQUEST is not None:
      response = REQUEST.RESPONSE
    else:
      return "FAILED"

    return self._getLocalFile(REQUEST, response,
                               file_path='var/Data.fs',
                               compressed=1)

  #
  #   Instance variable definition access
  #
  security.declareProtected(Permissions.ManagePortal, '_loadExternalConfig')
  def _loadExternalConfig(self):
    """
      Load configuration from one external file, this configuration 
      should be set for security reasons to prevent people access 
      forbidden areas in the system.
    """
    def cached_loadExternalConfig():
      import ConfigParser
      config = ConfigParser.ConfigParser()
      config.readfp(open('/etc/erp5.cfg'))
      return config     

    cached_loadExternalConfig = CachingMethod(cached_loadExternalConfig,
                                id='IntrospectionTool__loadExternalConfig',
                                cache_factory='erp5_content_long')
    return  cached_loadExternalConfig()

  security.declareProtected(Permissions.ManagePortal, '_getZopeConfigurationFile')
  def _getZopeConfigurationFile(self, relative_path="", mode="r"):
    """
     Get a configuration file from the instance using relative path
    """
    if ".." in relative_path or relative_path.startswith("/"):
      raise Unauthorized("In Relative Path, you cannot use .. or startwith / for security reason.")

    instance_home = getConfiguration().instancehome
    file_path = os.path.join(instance_home, relative_path)
    if not os.path.exists(file_path):
      raise IOError, 'The file: %s does not exist.' % file_path

    return open(file_path, mode)
    

  security.declareProtected(Permissions.ManagePortal, 'getSoftwareHome')
  def getSoftwareHome(self):
    """
      EXPERIMENTAL - DEVELOPMENT

      Get the value of SOFTWARE_HOME for zopectl startup script
      or from zope.conf (whichever is most relevant)
    """
    return getConfiguration().softwarehome

  security.declareProtected(Permissions.ManagePortal, 'setSoftwareHome')
  def setSoftwareHome(self, path):
    """
      EXPERIMENTAL - DEVELOPMENT

      Set the value of SOFTWARE_HOME for zopectl startup script
      or from zope.conf (whichever is most relevant)

      Rationale: multiple versions of ERP5 / Zope can be present
      at the same time on the same system

      WARNING: the list of possible path should be protected 
      if possible (ex. /etc/erp5/software_home)
    """
    config = self._loadExternalConfig()
    allowed_path_list = config.get("main", "zopehome").split("\n")
  
    if path not in allowed_path_list:
      raise Unauthorized("You are setting one Unauthorized path as Zope Home.")

    config_file = self._getZopeConfigurationFile("bin/zopectl")
    new_file_list = []
    for line in config_file:
      if line.startswith("SOFTWARE_HOME="):
        # Only comment the line, so it can easily reverted 
        new_file_list.append("#%s" % (line))
        new_file_list.append('SOFTWARE_HOME="%s"\n' % (path))
      else:
        new_file_list.append(line)

    config_file.close()

    # reopen file for write
    config_file = self._getZopeConfigurationFile("bin/zopectl", "w")
    config_file.write("".join(new_file_list))
    config_file.close()
    return 

  security.declareProtected(Permissions.ManagePortal, 'getPythonExecutable')
  def getPythonExecutable(self):
    """
      Get the value of PYTHON for zopectl startup script
      or from zope.conf (whichever is most relevant)
    """
    config_file = self._getZopeConfigurationFile("bin/zopectl")
    new_file_list = []
    for line in config_file:
      if line.startswith("PYTHON="):
        return line.replace("PYTHON=","")

    # Not possible get configuration from the zopecl
    return None
    
  security.declareProtected(Permissions.ManagePortal, 'setPythonExecutable')
  def setPythonExecutable(self, path):
    """
      Set the value of PYTHON for zopectl startup script
      or from zope.conf (whichever is most relevant)

      Rationale: some day Zope will no longer use python2.4

      WARNING: the list of possible path should be protected 
      if possible (ex. /etc/erp5/python)
    """
    config = self._loadExternalConfig()
    allowed_path_list = config.get("main", "python").split("\n")

    if path not in allowed_path_list:
      raise Unauthorized("You are setting one Unauthorized path as Python.")

    config_file = self._getZopeConfigurationFile("bin/zopectl")
    new_file_list = []
    for line in config_file:
      if line.startswith("PYTHON="):
        # Only comment the line, so it can easily reverted 
        new_file_list.append("#%s" % (line))
        new_file_list.append('PYTHON="%s"\n' % (path))
      else:
        new_file_list.append(line)

    config_file.close()    
    # reopen file for write
    config_file = self._getZopeConfigurationFile("bin/zopectl", "w")
    config_file.write("".join(new_file_list))
    config_file.close()
    return 

  security.declareProtected(Permissions.ManagePortal, 'getProductPathList')
  def getProductPathList(self):
    """
      Get the value of SOFTWARE_HOME for zopectl startup script
      or from zope.conf (whichever is most relevant)
    """
    return getConfiguration().products

  security.declareProtected(Permissions.ManagePortal, 'setProductPathList')
  def setProductPathList(self, path_list):
    """
      Set the value of SOFTWARE_HOME for zopectl startup script
      or from zope.conf (whichever is most relevant)

      Rationale: multiple versions of Products can be present
      on the same system

      WARNING: the list of possible path should be protected 
      if possible (ex. /etc/erp5/product)
    """
    config = self._loadExternalConfig()
    allowed_path_list = config.get("main", "products").split("\n")

    for path in path_list:
       if path not in allowed_path_list:
         raise Unauthorized("You are setting one Unauthorized path as Product Path.")

    config_file = self._getZopeConfigurationFile("etc/zope.conf")
    new_file_list = []
    for line in config_file:
      new_line = line
      if line.strip(" ").startswith("products"):
        # Only comment the line, so it can easily reverted 
        new_line = "#%s" % ( line)
      new_file_list.append(new_line)
    for path in path_list:
      new_file_list.append("products %s\n" % (path))
    config_file.close()    

    # reopen file for write
    config_file = self._getZopeConfigurationFile("etc/zope.conf", "w")
    config_file.write("".join(new_file_list))
    config_file.close()
    return 

  security.declareProtected(Permissions.ManagePortal, 'updateSVNProductList')
  def updateSVNProductList(self, path_list, revision=None):
    """
      Allow developers to create local products from the SVN
      in order to play with recent versions of the system

      Rationale: we can not do more than that or we take too
      much risks for security. Large projects should simply use
      buildout installer (server level) and build a complex custom
      software home or product home
    """
    # XXX (rafael) it better use (and extend if needed) the portal_subversions.
    if self.getSystemSignatureDict()["pysvn"] is None:
      raise 
    raise NotImplemented 

  #
  #   Library signature
  #
  # XXX this function can be cached to prevent disk access.
  security.declareProtected(Permissions.ManagePortal, 'getSystemSignatureDict')
  def getSystemSignatureDict(self):
    """
      Returns a dictionnary with all versions of installed libraries

      {
         'python': '2.4.3'
       , 'pysvn': '1.2.3'
       , 'ERP5' : "5.4.3"       
      }
      NOTE: consider using autoconf / automake tools ?
    """
    def tuple_to_format_str(t):
       return '.'.join([str(i) for i in t])
    from Products import ERP5 as erp5_product
    erp5_product_path =  erp5_product.__file__.split("/")[:-1]
    erp5_version = open("/".join((erp5_product_path) + ["VERSION.txt"])).read().strip()
    zope_version = open(getConfiguration().softwarehome + "/version.txt").read().strip()

    from sys import version_info
    # Get only x.x.x numbers.
    py_version = tuple_to_format_str(version_info)
    try:
      import pysvn
      # Convert tuple to x.x.x format
      pysvn_version =  tuple_to_format_str(pysvn.version)
    except:
      pysvn_version = None
    
    return {
            "python" : py_version , 
            "pysvn"  : pysvn_version ,
            "erp5"   : erp5_version.replace("ERP5 ", ""),
            "zope"   : zope_version.replace("Zope ", "")
           }

InitializeClass(IntrospectionTool)
