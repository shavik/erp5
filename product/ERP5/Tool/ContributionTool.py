# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets <jp@nexedi.com>
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

import cStringIO
import re
import socket
import urllib2, urllib
import urlparse
from cgi import parse_header
import os

from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.ERP5Type.Globals import InitializeClass, DTMLFile
from Products.CMFCore.utils import _checkPermission
from Products.ERP5Type.Tool.BaseTool import BaseTool
from Products.ERP5Type import Permissions
from Products.ERP5 import _dtmldir
from Products.ERP5.Document.Url import no_crawl_protocol_list
from AccessControl import Unauthorized

from DateTime import DateTime
import warnings

# Install openers
import ContributionOpener
opener = urllib2.build_opener(ContributionOpener.DirectoryFileHandler)
urllib2.install_opener(opener)

# A temporary hack until urllib2 supports timeout setting - XXX
import socket
socket.setdefaulttimeout(600) # 1 minute timeout

# Global parameters
TEMP_NEW_OBJECT_KEY = '_v_new_object'
MAX_REPEAT = 10

_marker = []  # Create a new marker object.

class ContributionTool(BaseTool):
  """
    ContributionTool provides an abstraction layer to unify the contribution
    of documents into an ERP5 Site.

    ContributionTool needs to be configured in portal_types (allowed contents) so
    that it can store Text, Spreadsheet, PDF, etc. 

    The main method of ContributionTool is newContent. This method can
    be provided various parameters from which the portal type and document
    metadata can be derived. 

    Configuration Scripts:

      - ContributionTool_getPropertyDictFromFilename: receives file name and a 
        dict derived from filename by regular expression, and does any necesary
        operations (e.g. mapping document type id onto a real portal_type).

    Problems which are not solved

      - handling of relative links in HTML contents (or others...)
        some text rewriting is necessary.

  """
  title = 'Contribution Tool'
  id = 'portal_contributions'
  meta_type = 'ERP5 Contribution Tool'
  portal_type = 'Contribution Tool'

  

  # Declarative Security
  security = ClassSecurityInfo()

  security.declareProtected(Permissions.ManagePortal, 'manage_overview' )
  manage_overview = DTMLFile( 'explainContributionTool', _dtmldir )

  security.declareProtected(Permissions.AddPortalContent, 'newContent')
  def newContent(self, **kw):
    """
      The newContent method is overriden to implement smart content
      creation by detecting the portal type based on whatever information
      was provided and finding out the most appropriate module to store
      the content.

      explicit named parameters was:
        id - ignored argument
        portal_type - explicit portal_type parameter, must be honoured
        url - Identifier of external resource. Content will be downloaded
              from it
        container - if specified, it is possible to define
                    where to contribute the content. Else, ContributionTool
                    tries to guess.
        container_path - if specified, defines the container path
                         and has precedence over container
        discover_metadata - Enable metadata extraction and discovery
                            (default True)
        temp_object - build tempObject or not (default False)
        user_login - is the name under which the content will be created
                     XXX - this is a security hole which needs to be fixed by
                     making sure only Manager can use this parameter
        data - Binary representation of content
        filename - explicit filename of content
    """
    kw.pop('id', None) # Never use hardcoded ids anymore longer

    # Useful for metadata discovery, keep it as it as been provided
    input_parameter_dict = kw.copy()
    # But file and data are exceptions.
    # They are potentialy too big to be keept into memory.
    # We want to keep only one reference of thoses values
    # on futur created document only !
    if 'file' in input_parameter_dict:
      del input_parameter_dict['file']
    if 'data' in input_parameter_dict:
      del input_parameter_dict['data']
    # pop: remove keys which are not document properties
    url = kw.pop('url', None)
    container = kw.pop('container', None)
    container_path = kw.pop('container_path', None)
    discover_metadata = kw.pop('discover_metadata', True)
    user_login = kw.pop('user_login', None)
    # check file_name argument for backward compatibility.
    if 'file_name' in kw:
      if 'filename' not in kw:
        kw['filename'] = kw['file_name']
      del(kw['file_name'])
    filename = kw.get('filename', None)
    portal_type = kw.get('portal_type')
    temp_object = kw.get('temp_object', False)

    document = None
    portal = self.getPortalObject()
    # Try to find the filename
    content_type = None
    if not url:
      # check if file was provided
      file_object = kw.get('file')
      if file_object is not None:
        if not filename:
          filename = file_object.filename
      else:
        # some channels supply data and file-name separately
        # this is the case for example for email ingestion
        # in this case, we build a file wrapper for it
        data = kw.get('data')
        if data is not None and filename:
          file_object = cStringIO.StringIO()
          file_object.write(data)
          file_object.seek(0)
          kw['file'] = file_object
          del kw['data']
        else:
          raise TypeError, 'data and filename must be provided'
    else:
      file_object, filename, content_type = self._openURL(url)
      if content_type:
        kw['content_type'] = content_type
      kw['file'] = file_object

    if not content_type:
      # fallback to a default content_type according provided
      # filename
      content_type = self.guessMimeTypeFromFilename(filename)

    # If the portal_type was provided, we can go faster
    if portal_type and container is None:
      # We know the portal_type, let us find the default module
      # and use it as container
      try:
        container = portal.getDefaultModule(portal_type)
      except ValueError:
        container = None

    # From here, there is no hope unless a file was provided
    if file_object is None:
      raise ValueError, "No data provided"


    if portal_type is None:
      # Guess it with help of portal_contribution_registry
      registry = portal.portal_contribution_registry
      portal_type = registry.findPortalTypeName(filename=filename,
                                                content_type=content_type)
    #
    # Check if same file is already exists. if it exists, then update it.
    #
    property_dict = self.getMatchedFilenamePatternDict(filename)
    reference = property_dict.get('reference', None)
    version  = property_dict.get('version', None)
    language  = property_dict.get('language', None)
    if portal_type and reference and version and language:
      portal_catalog = portal.portal_catalog
      document = portal_catalog.getResultValue(portal_type=portal_type,
                                                reference=reference,
                                                version=version,
                                                language=language)

      if document is not None:
        # document is already uploaded. So overrides file.
        if not _checkPermission(Permissions.ModifyPortalContent, document):
          raise Unauthorized, "[DMS] You are not allowed to update the existing document which has the same coordinates (id %s)" % document.getId()
        document.edit(file=kw['file'])
        return document
    # Temp objects use the standard newContent from Folder
    if temp_object:
      # For temp_object creation, use the standard method
      kw['portal_type'] = portal_type
      return BaseTool.newContent(self, **kw)

    # Then put the file inside ourselves for a short while
    if container_path is not None:
      container = self.getPortalObject().restrictedTraverse(container_path)
    document = self._setObject(filename, None, portal_type=portal_type,
                               user_login=user_login, container=container,
                               discover_metadata=discover_metadata,
                               filename=filename,
                               input_parameter_dict=input_parameter_dict
                               )
    object_id = document.getId()
    document = self._getOb(object_id) # Call _getOb to purge cache
    rewrite_method = document._getTypeBasedMethod('rewriteIngestionData')
    if rewrite_method is not None:
      modified_kw = rewrite_method(**kw.copy())
      if modified_kw is not None:
        kw.update(modified_kw)

    kw['filename'] = filename # Override filename property
    # Then edit the document contents (so that upload can happen)
    document._edit(**kw)
    if url:
      document.fromURL(url)

    # Allow reindexing, reindex it and return the document
    try:
      delattr(document, 'isIndexable')
    except AttributeError:
      # Document does not have such attribute
      pass
    document.reindexObject()
    return document

  security.declareProtected( Permissions.AddPortalContent, 'newXML' )
  def newXML(self, xml):
    """
      Create a new content based on XML data. This is intended for contributing
      to ERP5 from another application.
    """
    pass

  security.declareProtected(Permissions.ModifyPortalContent,
                            'getMatchedFilenamePatternDict')
  def getMatchedFilenamePatternDict(self, filename):
    """
      Get matched group dict of file name parsing regular expression.
    """
    property_dict = {}

    if filename is None:
      return property_dict

    regex_text = self.portal_preferences.\
                                getPreferredDocumentFilenameRegularExpression()
    if regex_text in ('', None):
      return property_dict

    if regex_text:
      pattern = re.compile(regex_text)
      if pattern is not None:
        try:
          property_dict = pattern.match(filename).groupdict()
        except AttributeError: # no match
          pass
    return property_dict

  # backward compatibility
  security.declareProtected(Permissions.ModifyPortalContent,
                            'getMatchedFileNamePatternDict')
  def getMatchedFileNamePatternDict(self, filename):
    """
    (deprecated) use getMatchedFilenamePatternDict() instead.
    """
    warnings.warn('getMatchedFileNamePatternDict() is deprecated. '
                  'use getMatchedFilenamePatternDict() instead.')
    return self.getMatchedFilenamePatternDict(filename)

  security.declareProtected(Permissions.ModifyPortalContent,
                            'getPropertyDictFromFilename')
  def getPropertyDictFromFilename(self, filename):
    """
      Gets properties from filename. File name is parsed with a regular expression
      set in preferences. The regexp should contain named groups.
    """
    if filename is None:
      return {}
    property_dict = self.getMatchedFilenamePatternDict(filename)
    method = self._getTypeBasedMethod('getPropertyDictFromFilename',
             fallback_script_id='ContributionTool_getPropertyDictFromFilename')
    property_dict = method(filename, property_dict)
    return property_dict

  # backward compatibility
  security.declareProtected(Permissions.ModifyPortalContent,
                            'getPropertyDictFromFileName')
  def getPropertyDictFromFileName(self, filename):
    """
    (deprecated) use getPropertyDictFromFilename() instead.
    """
    warnings.warn('getPropertyDictFromFileName() is deprecated. '
                  'use getPropertyDictFromFilename() instead.')
    return self.getPropertyDictFromFilename(filename)

  # WebDAV virtual folder support
  def _setObject(self, id, ob, portal_type=None, user_login=None,
                 container=None, discover_metadata=True, filename=None,
                 input_parameter_dict=None):
    """
      portal_contribution_registry will find appropriate portal type
      name by filename and content itself.

      The ContributionTool instance must be configured in such
      way that _verifyObjectPaste will return TRUE.

    """
    # _setObject is called by constructInstance at a time
    # when the object has no portal_type defined yet. It
    # will be removed later on. We can safely store the
    # document inside us at this stage. Else we
    # must find out where to store it.
    if ob is not None:
      # Call from webdav API
      # redefine parameters
      portal_type = ob.getPortalType()
      container = ob.getParentValue()
    if not portal_type:
      document = BaseTool.newContent(self, id=id,
                                     portal_type=portal_type,
                                     is_indexable=0)
    else:
      # We give the system a last chance to analyse the
      # portal_type based on the document content
      # (ex. a Memo is a kind of Text which can be identified
      # by the fact it includes some specific content)

      # Now we know the portal_type, let us find the module
      # to which we should move the document to
      if container is None:
        module = self.getDefaultModule(portal_type)
      else:
        module = container
      # There is no preexisting document - we can therefore
      # set the new object
      document = module.newContent(portal_type=portal_type, is_indexable=0)
      # We can now discover metadata
      if discover_metadata:
        # Metadata disovery is done as an activity by default
        # If we need to discoverMetadata synchronously, it must
        # be for user interface and should thus be handled by
        # ZODB scripts
        document.activate(after_path_and_method_id=(document.getPath(),
          ('convertToBaseFormat', 'Document_tryToConvertToBaseFormat'))) \
        .discoverMetadata(filename=filename,
                          user_login=user_login,
                          input_parameter_dict=input_parameter_dict)
      # Keep the document close to us - this is only useful for
      # file upload from webdav
      volatile_cache = getattr(self, '_v_document_cache', None)
      if volatile_cache is None:
        self._v_document_cache = {}
        volatile_cache = self._v_document_cache
      volatile_cache[document.getId()] = document.getRelativeUrl()

    # Return document to newContent method
    return document

  def _getOb(self, id, default=_marker):
    """
    Check for volatile temp object info first
    and try to find it
    """
    # Use the document cache if possible and return result immediately
    # this is only useful for webdav
    volatile_cache = getattr(self, '_v_document_cache', None)
    if volatile_cache is not None:
      document_url = volatile_cache.get(id)
      if document_url is not None:
        del volatile_cache[id]
        return self.getPortalObject().unrestrictedTraverse(document_url)

    # Try first to return the real object inside
    # This is much safer than trying to access objects displayed by listDAVObjects
    # because the behaviour of catalog is unpredicatble if a string is passed
    # for a UID. For example 
    #   select path from catalog where uid = "001193.html";
    # will return the same as
    #   select path from catalog where uid = 1193;
    # This was the source of an error in which the contribution tool
    # was creating a web page and was returning a Base Category
    # when
    #   o = folder._getOb(id)
    # was called in DocumentConstructor
    if default is _marker:
      result = BaseTool._getOb(self, id)
    else:
      result = BaseTool._getOb(self, id, default=default)
    if result is not None:
      # if result is None, ignore it at this stage
      # we can be more lucky with portal_catalog
      return result

    # Return an object listed by listDAVObjects
    # ids are concatenation of uid + '-' + standard file name of documents
    # get the uid
    uid = str(id).split('-', 1)[0]
    object = self.getPortalObject().portal_catalog.unrestrictedGetResultValue(uid=uid)
    if object is not None:
      return object.getObject() # Make sure this does not break security. XXX
    if default is not _marker:
      return default
    # Raise an AttributeError the same way as in OFS.ObjectManager._getOb
    raise AttributeError, id


  def listDAVObjects(self):
    """
      Get all contents contributed by the current user. This is
      delegated to a script in order to help customisation.
    XXX Killer feature, it is not scalable
    """
    method = getattr(self, 'ContributionTool_getMyContentList', None)
    if method is not None:
      object_list = method()
    else:
      sm = getSecurityManager()
      user = sm.getUser()
      object_list = self.portal_catalog(portal_type=self.getPortalMyDocumentTypeList(),
                                        owner=str(user))

    def wrapper(o_list):
      for o in o_list:
        o = o.getObject()
        id = '%s-%s' % (o.getUid(), o.getStandardFilename(),)
        yield o.asContext(id=id)

    return wrapper(object_list)

  security.declareProtected(Permissions.AddPortalContent, 'crawlContent')
  def crawlContent(self, content, container=None):
    """
      Analyses content and download linked pages

      XXX: missing is the conversion of content local href to something
      valid.
    """
    portal = self.getPortalObject()
    url_registry_tool = portal.portal_url_registry
    depth = content.getCrawlingDepth()
    if depth < 0:
      # Do nothing if crawling depth is reached
      # (this is not a duplicate code but a way to prevent
      # calling isIndexContent unnecessarily)
      return
    if not content.isIndexContent(): # Decrement depth only if it is a content document
      depth = depth - 1
    if depth < 0:
      # Do nothing if crawling depth is reached
      return
    url_list = content.getContentNormalisedURLList()
    for url in set(url_list):
      # LOG('trying to crawl', 0, url)
      # Some url protocols should not be crawled
      if urlparse.urlsplit(url)[0] in no_crawl_protocol_list:
        continue
      if container is None:
        #if content.getParentValue()
        # in place of not ?
        container = content.getParentValue()
      try:
        url_registry_tool.getReferenceFromURL(url, context=container)
      except KeyError:
        pass
      else:
        # url already crawled
        continue
      # XXX - This call is not working due to missing group_method_id
      # therefore, multiple call happen in parallel and eventually fail
      # (the same URL is created multiple times)
      # LOG('activate newContentFromURL', 0, url)
      self.activate(activity="SQLQueue").newContentFromURL(
                                  container_path=container.getRelativeUrl(),
                                  url=url, crawling_depth=depth)
      # Url is not known yet but register right now to avoid
      # creation of duplicated crawled content
      # An activity will later setup the good reference for it.
      url_registry_tool.registerURL(url, None, context=container)

  security.declareProtected(Permissions.AddPortalContent, 'updateContentFromURL')
  def updateContentFromURL(self, content, repeat=MAX_REPEAT, crawling_depth=0):
    """
      Updates an existing content.
    """
    # First, test if the document is updatable according to
    # its workflow states (if it has a workflow associated with)
    if content.isUpdatable():
      # Step 0: update crawling_depth if required
      if crawling_depth > content.getCrawlingDepth():
        content._setCrawlingDepth(crawling_depth)
      # Step 1: download new content
      try:
        url = content.asURL()
        file_object, filename, content_type = self._openURL(url)
      except urllib2.HTTPError, error:
        if repeat == 0:
          # XXX - Call the extendBadURLList method,--NOT Implemented--
          # IDEA : ajouter l'url en question dans une list "bad_url_list" puis lors du crawling au lieu que de boucler sur 
          #        la liste des url extraites de la page web on fait un test supplementaire qui verifie que l'url n'est pas 
          #        dans la liste bad_url_lis
          raise
        content.activate(at_date=DateTime() + 1).updateContentFromURL(repeat=repeat - 1)
        return
      except urllib2.URLError, error:
        if repeat == 0:
          # XXX - Call the extendBadURLList method,--NOT Implemented--
          raise
        content.activate(at_date=DateTime() + 1).updateContentFromURL(repeat=repeat - 1)
        return

      content._edit(file=file_object, content_type=content_type)
                              # Please make sure that if content is the same
                              # we do not update it
                              # This feature must be implemented by Base or File
                              # not here (look at _edit in Base)
      # Step 2: convert to base format
      if content.isSupportBaseDataConversion():
        content.activate().Document_tryToConvertToBaseFormat()
      # Step 3: run discoverMetadata
      content.activate(after_path_and_method_id=(content.getPath(),
            ('convertToBaseFormat', 'Document_tryToConvertToBaseFormat'))) \
          .discoverMetadata(filename=filename)
      # Step 4: activate populate (unless interaction workflow does it)
      content.activate().populateContent()
      # Step 5: activate crawlContent
      depth = content.getCrawlingDepth()
      if depth > 0:
        content.activate().crawlContent()

  security.declareProtected(Permissions.AddPortalContent, 'newContentFromURL')
  def newContentFromURL(self, container_path=None, id=None, repeat=MAX_REPEAT,
                        repeat_interval=1, batch_mode=True, url=None, **kw):
    """
      A wrapper method for newContent which provides extra safety
      in case or errors (ie. download, access, conflict, etc.).
      The method is able to handle a certain number of exceptions
      and can postpone itself through an activity based on
      the type of exception (ex. for a 404, postpone 1 day), using
      the at_date parameter and some standard values.

      NOTE: implementation needs to be done.
      id parameter is ignored
    """
    document = None
    if not url:
      raise TypeError, 'url parameter is mandatory'
    try:
      document = self.newContent(container_path=container_path, url=url, **kw)
      if document.isIndexContent() and document.getCrawlingDepth() >= 0:
        # If this is an index document, keep on crawling even if crawling_depth is 0
        document.activate().crawlContent()
      elif document.getCrawlingDepth() > 0:
        # If this is an index document, stop crawling if crawling_depth is 0
        document.activate().crawlContent()
    except urllib2.HTTPError, error:
      if repeat == 0 and batch_mode:
        # here we must call the extendBadURLList method,--NOT Implemented--
        # which had to add this url to bad URL list, so next time we avoid
        # crawling bad URL
        raise
      if repeat > 0:
        # Catch any HTTP error
        self.activate(at_date=DateTime() + repeat_interval).newContentFromURL(
                          container_path=container_path, url=url,
                          repeat=repeat - 1,
                          repeat_interval=repeat_interval, **kw)
    except urllib2.URLError, error:
      if repeat == 0 and batch_mode:
        # XXX - Call the extendBadURLList method, --NOT Implemented--
        raise
      #if getattr(error.reason,'args',None):
        #if error.reason.args[0] == socket.EAI_AGAIN:
          ## Temporary failure in name resolution - try again in 1 day
      if repeat > 0:
        self.activate(at_date=DateTime() + repeat_interval,
                      activity="SQLQueue").newContentFromURL(
                        container_path=container_path, url=url,
                        repeat=repeat - 1,
                        repeat_interval=repeat_interval, **kw)
    return document

  security.declareProtected(Permissions.AccessContentsInformation,
                            'guessMimeTypeFromFilename')
  def guessMimeTypeFromFilename(self, filename):
    """
      get mime type from file name
    """
    if not filename:
      return
    portal = self.getPortalObject()
    content_type = portal.mimetypes_registry.lookupExtension(filename)
    if content_type:
      return str(content_type)
    return content_type

  def _openURL(self, url):
    """Download content from url,
    read filename and content_type
    return file_object, filename, content_type tuple
    """
    # Quote path part of url
    url_tuple = urlparse.urlsplit(url)
    quoted_path = urllib.quote(url_tuple[2])
    url = urlparse.urlunsplit((url_tuple[0], url_tuple[1], quoted_path,
                               url_tuple[3], url_tuple[4]))
    # build a new file from the url
    url_file = urllib2.urlopen(urllib2.Request(url,
                                               headers={'Accept':'*/*'}))
    data = url_file.read() # time out must be set or ... too long XXX
    file_object = cStringIO.StringIO()
    file_object.write(data)
    file_object.seek(0)
    # if a content-disposition header is present,
    # try first to read the suggested filename from it.
    header_info = url_file.info()
    content_disposition = header_info.getheader('content-disposition', '')
    filename = parse_header(content_disposition)[1].get('filename')
    if not filename:
      # Now read the filename from url.
      # In case of http redirection, the real url must be read
      # from file object returned by urllib2.urlopen.
      # It can happens when the header 'Location' is present in request.
      # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.30
      url = url_file.geturl()
      # Create a file name based on the URL and quote it
      filename = urlparse.urlsplit(url)[-3]
      filename = os.path.basename(filename)
      filename = urllib.quote(filename, safe='')
      filename = filename.replace('%', '')
    content_type = header_info.gettype()
    return file_object, filename, content_type

InitializeClass(ContributionTool)
