########################################################################
#
# File:   index.py
# Author: Alex Samuel
# Date:   2001-02-08
#
# Contents:
#   Web form for main QMTrack web page.
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

"""Web form for QMTrack menu page."""

########################################################################
# imports
########################################################################

import qm.web
import web

########################################################################
# classes
########################################################################

class IndexPage(web.DtmlPage):
    """Main QMTrack index page."""

    def __init__(self):
        # Initialize the base class.
        web.DtmlPage.__init__(self, "index.dtml")


    def GetIssueClasses(self):
        return self.request.GetSession().idb.GetIssueClasses()


    def GetDefaultIssueClass(self):
        return self.request.GetSession().idb.GetDefaultIssueClass()


    def MakeLogoutForm(self):
        request = qm.web.WebRequest("logout", base=self.request)
        request["_redirect_url"] = self.request.GetUrl()
        return request.AsForm(name="logout_form")



########################################################################
# functions
########################################################################

def handle_index(request):
    """Handle a request for the index page."""

    # Make a new page instance, so the list of issue classes is
    # refreshed. 
    return IndexPage()(request)


########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
