########################################################################
#
# File:   temporary.py
# Author: Alex Samuel
# Date:   2001-04-06
#
# Contents:
#   Actions to manage temporary files and directories.
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
import qm.fields
import tempfile

########################################################################
# classes
########################################################################

class TempDirectoryAction:
    """Action class to manage a temporary directory.

    An instance of this action creates a temporary directory during
    setup, and deletes it during cleanup.  The full path to the
    directory is available to tests via a context property."""

    fields = [
        qm.fields.TextField(
            name="dir_path_property",
            title="Directory Path Property Name",
            description="The name of the context property which is "
            "set to the path to the temporary directory.",
            default_value="temp_dir_path"
            ),

        qm.fields.IntegerField(
            name="delete_recursively",
            title="Delete Directory Recursively",
            description="If non-zero, the contents of the temporary "
            "directory are deleted recursively during cleanup. "
            "Otherwise, the directory must be empty on cleanup.",
            default_value=0
            ),

        ]


    def __init__(self,
                 dir_path_property,
                 delete_recursively):
        self.__dir_path_property = dir_path_property
        self.__delete_recursively = delete_recursively
    

    def DoSetup(self, context):
        # FIXME: Security.
        # Generate a temporary file name.
        dir_path = tempfile.mktemp()
        # Create the directory.
        os.mkdir(dir_path, 0700)
        # Store the path to the directory where tests can get at it. 
        context[self.__dir_path_property] = dir_path
    

    def DoCleanup(self, context):
        # Extract the path to the directory.
        dir_path = context[self.__dir_path_property]
        # Make sure it's a directory.
        assert os.path.isdir(dir_path)
        # Clean up the directory.
        if self.__delete_recursively:
            qm.remove_directory_recursively(dir_path)
        else:
            os.rmdir(dir_path)



########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
