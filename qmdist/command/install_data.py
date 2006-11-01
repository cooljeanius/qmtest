########################################################################
#
# File:   install_data.py
# Author: Stefan Seefeld
# Date:   2003-09-01
#
# Contents:
#   command to install data files
#
# Copyright (c) 2003 by CodeSourcery, LLC.  All rights reserved. 
#
# For license terms see the file COPYING.
#
########################################################################

########################################################################
# Imports
########################################################################

from   distutils.command import install_data as base
import glob
import os, sys
from   qmdist.command import get_relative_path

########################################################################
# Classes
########################################################################

class install_data(base.install_data):
    """Extends 'install_data' by generating a config module.

    This module contains data only available at installation time,
    such as installation paths for data files."""

    def initialize_options(self):

        base.install_data.initialize_options(self)
        # Expand glob expressions in 'data_files'.
        new_data_files = []
        for f in self.data_files:
            if type(f) == str:
                f = glob.glob(f)
            else:
                dir, fs = f
                new_fs = []
                for f in fs:
                    new_fs.extend(glob.glob(f))
                f = (dir, new_fs)
            new_data_files.append(f)
        self.data_files = new_data_files
        self.distribution.data_files = new_data_files


    def run(self):
        
        # Do the standard installation.
        base.install_data.run(self)
        
        i = self.distribution.get_command_obj('install')
        il = self.distribution.get_command_obj('install_lib')
        config = os.path.join(il.install_dir, 'qm', 'config.py')
        self.announce("generating %s" %(config))
        outf = open(config, "w")
        outf.write("version='%s'\n"%self.distribution.get_version())
        prefix = i.root or i.prefix
        outf.write('prefix=%s\n'%repr(prefix))
        outf.write('data_dir=%s\n'%repr(os.path.join('share', 'qmtest')))
        outf.write('doc_dir=%s\n'%repr(os.path.join('share', 'doc', 'qmtest')))
        extension_dir = os.path.join('share',
                                     'qmtest',
                                     'site-extensions-%d.%d'%sys.version_info[:2])
        outf.write('extension_path=%s\n'%repr(extension_dir))

        outf.close()
        self.outfiles.append(config)
