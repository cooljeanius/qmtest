########################################################################
#
# File:   web.py
# Author: Alex Samuel
# Date:   2001-04-09
#
# Contents:
#   Common code for QMTest web user interface.
#
# Copyright (c) 2001 by CodeSourcery, LLC.  All rights reserved. 
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
########################################################################

########################################################################
# imports
########################################################################

import os
import qm
import qm.attachment
import qm.web

########################################################################
# classes
########################################################################

class DefaultDtmlPage(qm.web.DtmlPage):
    """Subclass of DTML page class for QMTest pages."""

    html_generator = "QMTest"


    def __init__(self, dtml_template, **attributes):
        # Initialize the base class.
        apply(qm.web.DtmlPage.__init__, (self, dtml_template), attributes)


    def GetName(self):
        """Return the name of the application."""

        return self.html_generator


    def MakeListingUrl(self):
        return qm.web.WebRequest("dir", base=self.request).AsUrl()


    def GenerateStartBody(self, decorations=1):
        if decorations:
            # Include the navigation bar.
            navigation_bar = DtmlPage("navigation-bar.dtml")
            return "<body>%s<br>" % navigation_bar(self.request)
        else:
            return "<body>"


    def GetMainPageUrl(self):
        return self.MakeListingUrl()


    def FormatId(self, id, type, style="basic"):
        script = "show-" + type
        request = qm.web.WebRequest(script, base=self.request, id=id)
        url = request.AsUrl()
        parent_suite_id, name = qm.label.split(id)

        if style == "plain":
            return '<span class="id">%s</span>' % id

        elif style == "basic":
            return '<a href="%s"><span class="id">%s</span></a>' % (url, id)

        elif style == "navigation":
            if parent_suite_id == qm.label.root:
                parent = ""
            else:
                parent = self.FormatId(parent_suite_id, "suite", style) \
                         + qm.label.sep
            return parent \
                   + '<a href="%s"><span class="id">%s</span></a>' \
                   % (url, name)

        elif style == "tree":
            return "&nbsp;&nbsp;&nbsp;" \
                   * (len(qm.label.split_fully(id)) - 1) \
                   + '<a href="%s"><span class="id">%s</span></a>' \
                   % (url, name)

        else:
            assert style



class DtmlPage(DefaultDtmlPage):
    """Convenience DTML subclass that finds QMTest page templates.

    Use this 'DtmlPage' subclass for QMTest-specific pages.  This class
    automatically looks for template files in the 'test' subdirectory."""

    def __init__(self, dtml_template, **attributes):
        # QMTest DTML templates are in the 'test' subdirectory.
        dtml_template = os.path.join("test", dtml_template)
        # Initialize the base class.
        apply(DefaultDtmlPage.__init__, (self, dtml_template), attributes)



########################################################################
# functions
########################################################################

def make_server(database, port, address, log_file=None):
    """Create and bind an HTTP server.

    'database' -- The test database to serve.

    'port' -- The port number on which to accept HTTP requests.

    'address' -- The local address to which to bind the server.  An
    empty string indicates all local addresses.

    'log_file' -- A file object to which the server will log requests.
    'None' for no logging.

    returns -- A web server.  The server is bound to the specified
    address.  Call its 'Run' method to start accepting requests."""

    import qm.test.web.dir
    import qm.test.web.run
    import qm.test.web.show
    import qm.test.web.suite

    # Base URL path for QMTest stuff.
    script_base = "/test/"
    # Create a new server instance.  Enable XML-RPM.
    server = qm.web.WebServer(port,
                              address,
                              log_file=log_file)
    # Register all our web pages.
    for name, function in [
        ( "create-resource", qm.test.web.show.handle_show ),
        ( "create-suite", qm.test.web.suite.handle_create ),
        ( "create-test", qm.test.web.show.handle_show ),
        ( "delete-resource", qm.test.web.show.handle_delete ),
        ( "delete-suite", qm.test.web.suite.handle_delete ),
        ( "delete-test", qm.test.web.show.handle_delete ),
        ( "dir", qm.test.web.dir.handle_dir ),
        ( "edit-resource", qm.test.web.show.handle_show ),
        ( "edit-suite", qm.test.web.suite.handle_edit ),
        ( "edit-test", qm.test.web.show.handle_show ),
        ( "new-resource", qm.test.web.show.handle_new_resource ),
        ( "new-suite", qm.test.web.suite.handle_new ),
        ( "new-test", qm.test.web.show.handle_new_test ),
        ( "run-tests", qm.test.web.run.handle_run_tests ),
        ( "show-resource", qm.test.web.show.handle_show ),
        ( "show-suite", qm.test.web.suite.handle_show ),
        ( "show-test", qm.test.web.show.handle_show ),
        ( "shutdown", handle_shutdown ),
        ( "submit-resource", qm.test.web.show.handle_submit ),
        ( "submit-suite", qm.test.web.suite.handle_submit ),
        ( "submit-test", qm.test.web.show.handle_submit ),
        ]:
        server.RegisterScript(script_base + name, function)
    server.RegisterPathTranslation(
        "/stylesheets", qm.get_share_directory("web", "stylesheets"))
    server.RegisterPathTranslation(
        "/images", qm.get_share_directory("web", "images"))
    server.RegisterPathTranslation(
        "/static", qm.get_share_directory("web", "static"))
    # Register the QM manual.
    server.RegisterPathTranslation(
        "/manual", qm.get_doc_directory("manual", "html"))
    
    # The global temporary attachment store processes attachment data
    # uploads.
    temporary_attachment_store = qm.attachment.temporary_store
    server.RegisterScript(qm.fields.AttachmentField.upload_url,
                          temporary_attachment_store.HandleUploadRequest)
    # The DB's attachment store processes download requests for
    # attachment data.
    attachment_store = database.GetAttachmentStore()
    server.RegisterScript(qm.fields.AttachmentField.download_url,
                          attachment_store.HandleDownloadRequest)

    # Bind the server to the specified address.
    try:
        server.Bind()
    except qm.web.AddressInUseError, address:
        raise RuntimeError, qm.error("address in use", address=address)
    except qm.web.PrivilegedPortError:
        raise RuntimeError, qm.error("privileged port", port=port)

    return server


def handle_shutdown(request):
    """Handle a request to shut down the server."""

    raise SystemExit, None


########################################################################
# initialization
########################################################################

def __initialize_module():
    # Use our 'DtmlPage' subclass even when generating generic
    # (non-QMTest) pages.
    qm.web.DtmlPage.default_class = DefaultDtmlPage


__initialize_module()

########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
