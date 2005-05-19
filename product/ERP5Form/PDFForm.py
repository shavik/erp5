##############################################################################
#
# Copyright (c) 2005 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jerome PERRIN <jerome@nexedi.com>
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

from OFS.Image import File
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ERP5Type import PropertySheet
from Products.PageTemplates.Expressions import getEngine
from Products.PageTemplates.TALES import SafeMapping

from urllib import quote
from Globals import InitializeClass, PersistentMapping, DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl.SecurityInfo import allow_class

from zLOG import LOG

import types, popen2, os
from tempfile import mktemp

try:
    from webdav.Lockable import ResourceLockedError
    from webdav.WriteLockInterface import WriteLockInterface
    SUPPORTS_WEBDAV_LOCKS = 1
except ImportError:
    SUPPORTS_WEBDAV_LOCKS = 0
    
# FIXME: Programs linked against mandriva libgcj v 3.4.0 ave a strange 
# issue that make them impossible to popen within zope. 
# if you encounter problems (zope freezes), use the adhoc java library 
# and the wrapper script available at :
# http://www.nexedi.org/workspaces/members/jerome/pub/pdftk
PDFTK_PREFIX = "/home/jerome/java/my"
PDFTK_PREFIX = ""

class PDFTk :
    """ 
    A class to wrapp calls to pdftk executable, found at 
      http://www.accesspdf.com/pdftk/
    """
    def catPages(self, pdfFile, cat_option) : 
        """ limit to a specific range of pages, like pdftk's cat option"""
        return self._getOutput(
            PDFTK_PREFIX+
            "pdftk - cat %s output - "%cat_option, pdfFile)

    def dumpDataFields(self, pdfFile) :
        """ returns the output of pdftk dump_data_fields as dict """
        return self._parseDumpDataFields(self.dumpDataFieldsTxt(pdfFile))
    
    def fillFormWithDict(self, pdfFile, values) :
        """ fill the form with values in """
        return self.fillFormWithFDF(pdfFile, self._createFdf(values))
    
    def fillFormWithFDF(self, pdfFile, fdfFile) :
        """ fill the form of pdfFile with the FDF data fdfFile """
        pdfFormFileName = mktemp(suffix=".pdf")
        fdfFormFileName = mktemp(suffix=".fdf")
        
        if hasattr(pdfFile, "read") :
            pdfFile = pdfFile.read()
        tmpPdfFile=open(pdfFormFileName, "w")
        tmpPdfFile.write(pdfFile)
        tmpPdfFile.close()
        
        if hasattr(fdfFile, "read") :
            fdfFile = fdfFile.read()
        tmpFdfFile=open(fdfFormFileName, "w")
        tmpFdfFile.write(fdfFile)
        tmpFdfFile.close()
        
        out = self._getOutput(
            PDFTK_PREFIX+
            "pdftk %s fill_form %s output - "%(
            pdfFormFileName, fdfFormFileName))
        os.remove(fdfFormFileName)
        os.remove(pdfFormFileName)
        return out
    
    def dumpDataFieldsTxt(self, pdfFile) :
        """ returns the output of pdftk dump_data_fields as text, 
          pdf file is either the file object or its content"""
        return self._getOutput(
                PDFTK_PREFIX+"pdftk - dump_data_fields", pdfFile)
              
    def _parseDumpDataFields(self, data_fields_dump) :
        """ parses the output of pdftk X.pdf dump_data_fields and
            returns a sequence of dicts [{key = value}] """
        fields = []
        for txtfield in data_fields_dump.split("---") :
            field = {}
            for line in txtfield.splitlines() :
                if line.strip() == "" :
                    continue
                splits = line.split(":", 1)
                if len(splits) == 2 :
                    field[splits[0]] = splits[1].strip()
            if field != {} :
                fields+=[field]
        return fields
    
    def _getOutput(self, command, input=None) :
        """ returns the output of command with sending input through command's
        input stream (if input parameter is given) """
        stdout, stdin = popen2.popen2(command)
        if input:
            if hasattr(input, "read") :
                input = input.read()
            stdin.write(input)
        stdin.close()
        ret = stdout.read()
        stdout.close()
        return ret
        
    def _escapeString(self, value) : 
        if value is None :
            return ""
        string = str(value)
        escaped  = ''
        for c in string : 
          if (ord(c) == 0x28 or # open paren
              ord(c) == 0x29 or # close paren
              ord(c) == 0x5c):  # backslash
            escaped += '\\' + c
          elif ord(c) < 32 or 126 < ord(c):
            escaped += "\\%03o" % ord(c)
          else:
            escaped += c
        return escaped
    
    def _createFdf(self, values, pdfFormUrl=None) : 
        """ create an fdf document with the dict values """
        fdf = "%FDF-1.2\x0d%\xe2\xe3\xcf\xd3\x0d\x0a"
        fdf+= "1 0 obj\x0d<< \x0d/FDF << /Fields [ "
        for key, value in values.items(): 
            fdf+= "<< /T (%s) /V (%s)>> \x0d"%( 
                     self._escapeString(key),
                     self._escapeString(value))
      
        fdf+= "] \x0d"
    
        # the PDF form filename or URL, if any
        if pdfFormUrl not in ("", None) : 
            fdf+= "/F ("+self._escapeString(pdfFormUrl)+") \x0d"
      
        fdf+= ">> \x0d>> \x0dendobj\x0d"; 
        fdf+= "trailer\x0d<<\x0d/Root 1 0 R \x0d\x0d>>\x0d%%EOF\x0d\x0a"
        return fdf

# Constructors
manage_addPDFForm = DTMLFile("dtml/PDFForm_add", globals())
def addPDFForm(self, id, title="", pdf_file=None,  REQUEST=None):
    """ Add a pdf form to folder. """
    # add actual object
    id = self._setObject(id, PDFForm(id, title, pdf_file))  
    
    # upload content
    if pdf_file:
        self._getOb(id).manage_upload(pdf_file)
        self._getOb(id).content_type="application/pdf"

    if REQUEST :
        u = REQUEST['URL1']
        if REQUEST['submit'] == " Add and Edit ":
            u = "%s/%s" % (u, quote(id))
        REQUEST.RESPONSE.redirect(u+'/manage_main')

class CalculatedValues : 
    """
    This class holds a reference to calculated values, for use in TALES, 
    because in PDF Form filling, there is lots of references to others cell
    values (sums ...). This class will be in TALES context under the key 'cell'
    
    It will make possible the use of TALES expressions like : 
      cell/a95
      python: cell['a1'] + cell['a2'] 
      
    """
    security = ClassSecurityInfo()
    def __init__(self, values, key, not_founds) :
        """ 'values' are a dict of already calculated values
        'key' is the key we are evaluating
        'not_founds' is the list in which we will put not found values  """
        self.__values      = values
        self.__key         = key
        self.__not_founds  = not_founds 
    def __getitem__(self, attr) :
        if not self.__values.has_key(attr) :
            self.__not_founds.append(attr)
            return 0 # We do not return None, so that cell['a1'] + cell['a2'] 
            # doesn't complain that NoneType doesn't support + when a1 not found
        return self.__values[attr]
    __getattr__ = __getitem__
allow_class(CalculatedValues)


class PDFForm(File):
    """
      This class allows to fill PDF Form with TALES expressions, 
      using a TALES expression for each cell.
    """
    meta_type = "ERP5 PDF Form"
    icon = "www/PDFForm.png"

    # Declarative Security
    security = ClassSecurityInfo()

    # Declarative properties
    property_sheets = ( PropertySheet.Base
                      , PropertySheet.SimpleItem
                      )
    
    # Constructors
    constructors =   (manage_addPDFForm, addPDFForm)

    manage_options =  (
        (
          {'label':'Edit Cell TALES', 'action':'manage_cells'}, 
          {'label':'Display Cell Names', 'action':'showCellNames'}, 
          {'label':'Test PDF generation', 'action':'generatePDF'},
          {'label':'View original', 'action':'viewOriginal'}, 
        ) + 
        filter(lambda option:option['label'] != "View", File.manage_options)
    )
    
    pdftk = PDFTk()
    
    def __init__ (self, id, title, pdf_file) :
        # holds all the cell informations, even those not related to this form
        self.all_cells        = PersistentMapping()
        # holds the cells related to this pdf form
        self.cells            = PersistentMapping()
        self.__display_zeros__ = ""
	self.__page_range__ = ""
	
        if not pdf_file :
            raise ValueError ("The pdf form file should not be empty")
        # File constructor will call manage_upload, so we don't need to call it 
        File.__init__(self, id, title, pdf_file)
      
    security.declareProtected('Change Images and Files', 'manage_upload')
    def manage_upload(self, file=None, REQUEST=None) : 
        """ Zope calls this when the content of the enclosed file changes.
        The 'cells' attribute is updated, but already defined cells are not 
        erased, they are saved in the 'all_cells' attribute so if the pdf 
        file is reverted, you do not loose the cells definitions.
        """
        if not file or not hasattr(file, "read") :
            raise ValueError ("The pdf form file should not be empty")
        
        file.seek(0) # file is always valid here
        values = self.pdftk.dumpDataFields(file)
        for v in values : 
            if v["FieldType"] != "Button" :
                k = v["FieldName"] 
                if not self.all_cells.has_key(k) :
                    self.cells[k] = "" 
                else :
                    self.cells[k] = self.all_cells[k]
        self.all_cells.update(self.cells)
        file.seek(0)
        File.manage_upload(self, file, REQUEST)
        if REQUEST:
            message="Saved changes."
            return self.manage_main(self,REQUEST,manage_tabs_message=message)

    security.declareProtected('View management screens', 'manage_cells')
    manage_cells = PageTemplateFile('www/PDFForm_manageCells', 
                                     globals(), __name__='manage_cells')
     
    security.declareProtected('View', 'viewOriginal')
    def viewOriginal(self, REQUEST=None, RESPONSE=None, *args, **kwargs) :
        """ publish original pdf """
        pdf = File.index_html(self, REQUEST, RESPONSE, *args, **kwargs)  
        RESPONSE.setHeader('Content-Type','application/pdf')
        RESPONSE.setHeader('Content-Disposition','inline;filename="%s.pdf"' 
            % (self.title_or_id()))
        return pdf

    security.declareProtected('View', 'showCellNames') 
    def showCellNames(self, REQUEST=None, RESPONSE=None, *args, **kwargs) : 
        """ generates a pdf with fields filled-in by their names, 
         usefull to fill in settings.
        """
        values = {}
        for cell in self.cells.keys() :
           values[cell] = cell
        pdf = self.pdftk.fillFormWithDict(str(self.data), values)
        if RESPONSE : 
            RESPONSE.setHeader('Content-Type','application/pdf')
            RESPONSE.setHeader('Content-Length',len(pdf))
            RESPONSE.setHeader('Content-Disposition',
                                'inline;filename="%s.template.pdf"'%(
				   self.title_or_id()))
        return pdf

    security.declareProtected('Change Images and Files', 'doEditCells')
    def doEditCells(self, REQUEST):
        """ This is the action to the 'Edit Cell TALES' tab. """
	if SUPPORTS_WEBDAV_LOCKS and self.wl_isLocked():
            raise ResourceLockedError, "File is locked via WebDAV"
        
        for k, v in self.cells.items() :
            self.setCellTALES(k, REQUEST.get(str(k), v))
        self.__display_zeros__ = REQUEST.get("__display_zeros__")
	self.__page_range__ = REQUEST.get("__page_range__")
	
        message = "Saved changes."
        if getattr(self, '_v_warnings', None):
            message = ("<strong>Warning:</strong> <i>%s</i>"
                    % '<br>'.join(self._v_warnings))
        return self.manage_cells(manage_tabs_message=message) 
        
    security.declareProtected('View', 'generatePDF')
    def generatePDF(self, REQUEST=None, RESPONSE=None, *args, **kwargs) : 
        """ generates the PDF with form filled in """
        values = self.calculateCellValues(REQUEST, *args, **kwargs)
 	
        context = {'here' : self, 'request' : REQUEST} 
	display_zeros = 0
        if self.__display_zeros__ not in ('', None) : 
            compiled_tales = getEngine().compile(self.__display_zeros__) 
            display_zeros = getEngine().getContext(context).evaluate(compiled_tales)
        if not display_zeros :
            for k, v in values.items():
                if v == 0 :
                    values[k] = ""

        data = str(self.data)
        if self.__page_range__ not in ('', None) : 
            compiled_tales = getEngine().compile(self.__page_range__) 
            page_range = getEngine().getContext(context).evaluate(compiled_tales)
            if page_range :
                data = self.pdftk.catPages(str(self.data), page_range)
        pdf = self.pdftk.fillFormWithDict(data, values)
        if RESPONSE : 
            RESPONSE.setHeader('Content-Type','application/pdf')
            RESPONSE.setHeader('Content-Length',len(pdf))
            RESPONSE.setHeader('Content-Disposition','inline;filename="%s.pdf"' 
                % (self.title_or_id()))
        return pdf
    index_html = generatePDF
    
    security.declareProtected('View', 'calculateCellValues')
    def calculateCellValues(self, REQUEST=None, *args, **kwargs) : 
        """ returns a dict of cell values """
        # values to be returned
        values = {}
        # list of values that need to be reevaluated (i.e. they depend on the 
        # value of a cell that was not already evaluated when evaluating them )
        uncalculated_values = []
        for cell_name in self.cells.keys() :
            not_founds = []
            value = self.evaluateCell(cell_name, REQUEST = REQUEST,
                    cell = SafeMapping(CalculatedValues(
                                            values, cell_name, not_founds)))
            if len(not_founds) != 0 :
                uncalculated_values.append(cell_name)
            else :
                values[cell_name] = value
        # now we iterate on the list of uncalculated values, trying
        # to evaluate them again, if an iteration doesn't decrement
        # the length of this list, there are some circular references
        # and we cannot continue.
        while 1 : 
            uncalculated_values_len = len(uncalculated_values)
            if uncalculated_values_len == 0 : 
                return values
            for cell_name in uncalculated_values :
                not_founds = []
                value = self.evaluateCell(cell_name, REQUEST = REQUEST,
                     cell = SafeMapping(CalculatedValues(
                                            values, cell_name, not_founds)))
                if len(not_founds) == 0 :
                    uncalculated_values.remove(cell_name)
                    values[cell_name] = value
            if len(uncalculated_values) == uncalculated_values_len :
                raise "Circular reference", "unable to evaluate cells " \
                    + `uncalculated_values`

    security.declareProtected('View', 'getCellNames') 
    def getCellNames(self, REQUEST=None) :
        """ returns a list of cell names """
        names = self.cells.keys()
        names.sort()
        return names
      
    security.declareProtected('Change Images and Files', 'setCellTALES') 
    def setCellTALES(self, cell_name, TALES):
        """ changes the TALES expression that will be used to evaluate 
        cell value """
        if type(TALES) != types.StringType :
            LOG("PDFForm", 100,
                 'TALES is not a string for cell "%s", it is = "%s"'
                  %(cell_name, `TALES`))
            raise ValueError, 'TALES must be a string'
        self.all_cells[str(cell_name)] = self.cells[str(cell_name)] = TALES
            
    security.declareProtected('View', 'getCellTALES') 
    def getCellTALES(self, cell_name):
        """ returns the TALES expression associated with this cell """
        return self.cells[str(cell_name)]
    
    security.declareProtected('View', 'evaluateCell')     
    def evaluateCell(self, cell_name, REQUEST=None, **kwargs):
        """ evaluate the TALES expression for this cell """
        cell_name = str(cell_name)
        # we don't pass empty strings in TALES engine
        # (and this also raises the KeyError for non existant cells)
        if not self.cells[cell_name] :
            return None
        context = {'here' : self, 'request' : REQUEST} 
        context.update (kwargs)
        
        compiled_tales = getEngine().compile(self.cells[cell_name]) 
        value = getEngine().getContext(context).evaluate(compiled_tales)
        return value
    
    security.declareProtected('Change Images and Files', 'setAllCellTALES') 
    def setAllCellTALES(self, new_cells) :
        """ set all cell values from a dict containing { name: TALES } """
        for cell_name, cell_TALES in new_cells.items() : 
            self.setCellTALES(cell_name, cell_TALES)

    security.declareProtected('View', 'getDisplayZerosTALES')
    def getDisplayZerosTALES(self):
        """ returns the TALES expression for the display zeros attribute """
	return self.__display_zeros__

    security.declareProtected('Change Images and Files', 'setDisplayZerosTALES')
    def setDisplayZerosTALES(self, TALES):
        """ sets TALES expression for the display zeros attribute """
	self.__display_zeros__ = str(TALES)
 
    security.declareProtected('View', 'getPageRangeTALES')
    def getPageRangeTALES(self):
        """ returns the TALES expression for the page range attribute """
	return self.__page_range__
    
    security.declareProtected('Change Images and Files', 'setPageRangeTALES')
    def setPageRangeTALES(self, TALES):
        """ sets TALES expression for the page range attribute """
	self.__page_range__ = str(TALES)
      
InitializeClass(PDFForm)

