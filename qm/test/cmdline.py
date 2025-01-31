########################################################################
#
# File:   cmdline.py
# Author: Alex Samuel
# Date:   2001-03-16
#
# Contents:
#   QMTest command processing
#
# Copyright (c) 2001, 2002, 2003 by CodeSourcery, LLC.  All rights reserved. 
#
# For license terms see the file COPYING.
#
########################################################################

########################################################################
# Imports
########################################################################

from . import base
from . import database
import os
import qm
import qm.attachment
import qm.cmdline
import qm.platform
from   qm.extension import get_extension_class_name, get_class_description
from   qm.test import test
from   qm.test.result import Result
from   qm.test.context import *
from   qm.test.execution_engine import *
from   qm.test.result_stream import ResultStream
from   qm.test.runnable import Runnable
from   qm.test.suite import Suite
from   qm.test.report import ReportGenerator
from   qm.test.classes.dir_run_database import *
from   qm.test.expectation_database import ExpectationDatabase
from   qm.test.classes.previous_testrun import PreviousTestRun
from   qm.trace import *
from   qm.test.web.web import QMTestServer
import qm.structured_text
import qm.xmlutil
import queue
import random
from   .result import *
import signal
import string
import sys
import xml.sax

########################################################################
# Variables
########################################################################

_the_qmtest = None
"""The global 'QMTest' object."""

########################################################################
# Functions
########################################################################

def _make_comma_separated_string (items, conjunction):
    """Return a string consisting of the 'items', separated by commas.

    'items' -- A list of strings giving the items in the list.

    'conjunction' -- A string to use before the final item, if there is
    more than one.

    returns -- A string consisting all of the 'items', separated by
    commas, and with the 'conjunction' before the final item."""
    
    s = ""
    need_comma = 0
    # Go through almost all of the items, adding them to the
    # comma-separated list.
    for i in items[:-1]:
        # Add a comma if this isn't the first item in the list.
        if need_comma:
            s += ", "
        else:
            need_comma = 1
        # Add this item.
        s += "'%s'" % i
    # The last item is special, because we need to include the "or".
    if items:
        i = items[-1]
        if need_comma:
            s += ", %s " % conjunction
        s += "'%s'" % i

    return s

########################################################################
# Classes
########################################################################

class QMTest:
    """An instance of QMTest."""

    __extension_kinds_string \
         = _make_comma_separated_string(base.extension_kinds, "or")
    """A string listing the available extension kinds."""

    db_path_environment_variable = "QMTEST_DB_PATH"
    """The environment variable specifying the test database path."""

    summary_formats = ("brief", "full", "stats", "batch", "none")
    """Valid formats for result summaries."""

    context_file_name = "context"
    """The default name of a context file."""
    
    expectations_file_name = "expectations.qmr"
    """The default name of a file containing expectations."""
    
    results_file_name = "results.qmr"
    """The default name of a file containing results."""

    target_file_name = "targets"
    """The default name of a file containing targets."""
    
    help_option_spec = (
        "h",
        "help",
        None,
        "Display usage summary."
        )

    version_option_spec = (
        None,
        "version",
        None,
        "Display version information."
        )
    
    db_path_option_spec = (
        "D",
        "tdb",
        "PATH",
        "Path to the test database."
        )

    extension_output_option_spec = (
        "o",
        "output",
        "FILE",
        "Write the extension to FILE.",
        )

    extension_id_option_spec = (
        "i",
        "id",
        "NAME",
        "Write the extension to the database as NAME.",
        )
        
    output_option_spec = (
        "o",
        "output",
        "FILE",
        "Write test results to FILE (- for stdout)."
        )

    no_output_option_spec = (
        None,
        "no-output",
        None,
        "Don't generate test results."
        )

    outcomes_option_spec = (
        "O",
        "outcomes",
        "FILE",
        "Use expected outcomes in FILE."
        )

    expectations_option_spec = (
        "e",
        "expectations",
        "FILE",
        "Use expectations in FILE."
        )

    context_option_spec = (
        "c",
        "context",
        "KEY=VALUE",
        "Add or override a context property."
        )

    context_file_spec = (
        "C",
        "load-context",
        "FILE",
        "Read context from a file (- for stdin)."
        )

    daemon_option_spec = (
        None,
        "daemon",
        None,
        "Run as a daemon."
        )
        
    port_option_spec = (
        "P",
        "port",
        "PORT",
        "Server port number."
        )

    address_option_spec = (
        "A",
        "address",
        "ADDRESS",
        "Local address."
        )

    log_file_option_spec = (
        None,
        "log-file",
        "PATH",
        "Log file name."
        )

    no_browser_option_spec = (
        None,
        "no-browser",
        None,
        "Do not open a new browser window."
        )

    pid_file_option_spec = (
        None,
        "pid-file",
        "PATH",
        "Process ID file name."
        )
    
    concurrent_option_spec = (
        "j",
        "concurrency",
        "COUNT",
        "Execute tests in COUNT concurrent threads."
        )

    targets_option_spec = (
        "T",
        "targets",
        "FILE",
        "Use FILE as the target specification file."
        )

    random_option_spec = (
        None,
        "random",
        None,
        "Run the tests in a random order."
        )

    rerun_option_spec = (
        None,
        "rerun",
        "FILE",
        "Rerun the tests that failed."
        )
    
    seed_option_spec = (
        None,
        "seed",
        "INTEGER",
        "Seed the random number generator."
        )

    format_option_spec = (
        "f",
        "format",
        "FORMAT",
        "Specify the summary format."
        )

    result_stream_spec = (
        None,
        "result-stream",
        "CLASS-NAME",
        "Specify the results file format."
        )
        
    annotation_option_spec = (
        "a",
        "annotate",
        "NAME=VALUE",
        "Set an additional annotation to be written to the result stream(s)."
        )

    tdb_class_option_spec = (
        "c",
        "class",
        "CLASS-NAME",
        "Specify the test database class.",
        )

    attribute_option_spec = (
        "a",
        "attribute",
        "NAME",
        "Get an attribute of the extension class."
        )

    set_attribute_option_spec = (
        "a",
        "attribute",
        "KEY=VALUE",
        "Set an attribute of the extension class."
        )

    extension_kind_option_spec = (
        "k",
        "kind",
        "EXTENSION-KIND",
        "Specify the kind of extension class."
        )

    report_output_option_spec = (
        "o",
        "output",
        "FILE",
        "Write test report to FILE (- for stdout)."
        )

    report_flat_option_spec = (
        "f",
        "flat",
        None,
        """Generate a flat listing of test results, instead of reproducing the
        database directory tree in the report."""
        )

    results_option_spec = (
        "R",
        "results",
        "DIRECTORY",
        "Read in all results (*.qmr) files from DIRECTORY."
        )

    list_long_option_spec = (
        "l",
        "long",
        None,
        "Use a detailed output format."
        )

    list_details_option_spec = (
        "d",
        "details",
        None,
        "Display details for individual items."
        )

    list_recursive_option_spec = (
        "R",
        "recursive",
        None,
        "Recursively list the contents of directories."
        )
    
    # Groups of options that should not be used together.
    conflicting_option_specs = (
        ( output_option_spec, no_output_option_spec ),
        ( concurrent_option_spec, targets_option_spec ),
        ( extension_output_option_spec, extension_id_option_spec ),
        ( expectations_option_spec, outcomes_option_spec ),
        )

    global_options_spec = [
        help_option_spec,
        version_option_spec,
        db_path_option_spec,
        ]

    commands_spec = [
        ("create",
         "Create (or update) an extension.",
         "EXTENSION-KIND CLASS-NAME(ATTR1 = 'VAL1', ATTR2 = 'VAL2', ...)",
         """Create (or update) an extension.

         The EXTENSION-KIND indicates what kind of extension to
         create; it must be one of """ + __extension_kinds_string + """.

         The CLASS-NAME indicates the name of the extension class, or
         the name of an existing extension object.  If the CLASS-NAME
         is the name of a extension in the test database, then the 

         In the former case, it must have the form 'MODULE.CLASS'.  For
         a list of available extension classes use "qmtest extensions".
         If the extension class takes arguments, those arguments can be
         specified after the CLASS-NAME as show above.  In the latter
         case,

         Any "--attribute" options are processed before the arguments
         specified after the class name.  Therefore, the "--attribute"
         options can be overridden by the arguments provided after the
         CLASS-NAME.  If no attributes are specified, the parentheses
         following the 'CLASS-NAME' can be omitted.

         If the "--id" option is given, the extension is written to the
         database.  Otherwise, if the "--output" option is given, the
         extension is written as XML to the file indicated.  If neither
         option is given, the extension is written as XML to the
         standard output.""",
         ( set_attribute_option_spec,
           help_option_spec,
           extension_id_option_spec,
           extension_output_option_spec
           ),
         ),
           
        ("create-target",
         "Create (or update) a target specification.",
         "NAME CLASS [ GROUP ]",
         "Create (or update) a target specification.",
         ( set_attribute_option_spec,
           help_option_spec,
           targets_option_spec
           )
         ),

        ("create-tdb",
         "Create a new test database.",
         "",
         "Create a new test database.",
         ( help_option_spec,
           tdb_class_option_spec,
           set_attribute_option_spec)
         ),

        ("gui",
         "Start the QMTest GUI.",
         "",
         "Start the QMTest graphical user interface.",
         (
           address_option_spec,
           concurrent_option_spec,
           context_file_spec,
           context_option_spec,
           daemon_option_spec,
           help_option_spec,
           log_file_option_spec,
           no_browser_option_spec,
           pid_file_option_spec,
           port_option_spec,
           outcomes_option_spec,
           targets_option_spec,
           results_option_spec
           )
         ),

        ("extensions",
         "List extension classes.",
         "",
         """
List the available extension classes.

Use the '--kind' option to limit the classes displayed to test classes,
resource classes, etc.  The parameter to '--kind' can be one of """  + \
         __extension_kinds_string + "\n",
         (
           extension_kind_option_spec,
           help_option_spec,
         )
        ),

        ("describe",
         "Describe an extension.",
         "EXTENSION-KIND NAME",
         """Display details for the specified extension.""",
         (
           attribute_option_spec,
           list_long_option_spec,
           help_option_spec,
         )
        ),

        ("help",
         "Display usage summary.",
         "",
         "Display usage summary.",
         ()
         ),

        ("ls",
         "List database contents.",
         "[ NAME ...  ]",
         """
         List items stored in the database.

         If no arguments are provided, the contents of the root
         directory of the database are displayed.  Otherwise, each of
         the database is searched for each of the NAMEs.  If the item
         found is a directory then the contents of the directory are
         displayed.
         """,
         (
           help_option_spec,
           list_long_option_spec,
           list_details_option_spec,
           list_recursive_option_spec,
         ),
         ),
         
        ("register",
         "Register an extension class.",
         "KIND CLASS",
         """
Register an extension class with QMTest.  KIND is the kind of extension
class to register; it must be one of """ + __extension_kinds_string + """

The CLASS gives the name of the class in the form 'module.class'.

QMTest will search the available extension class directories to find the
new CLASS.  QMTest looks for files whose basename is the module name and
whose extension is either '.py', '.pyc', or '.pyo'.

QMTest will then attempt to load the extension class.  If the extension
class cannot be loaded, QMTest will issue an error message to help you
debug the problem.  Otherwise, QMTest will update the 'classes.qmc' file
in the directory containing the module to mention your new extension class.
         """,
         (help_option_spec,)
         ),
        
        ("remote",
         "Run QMTest as a remote server.",
         "",
         """
Runs QMTest as a remote server.  This mode is only used by QMTest
itself when distributing tests across multiple machines.  Users
should not directly invoke QMTest with this option.
         """,
         (help_option_spec,)
         ),

        ("report",
         "Generate report from one or more test results.",
         "[ result [-e expected] ]+",
         """
Generates a test report. The arguments are result files each optionally
followed by '-e' and an expectation file. This command attempts to reproduce
the test database structure, and thus requires the '--tdb' option. To generate
a flat test report specify the '--flat' option.
         """,
         (help_option_spec,
          report_output_option_spec,
          report_flat_option_spec)
         ),

        ("run",
         "Run one or more tests.",
         "[ ID ... ]",
         """
Runs tests.  Optionally, generates a summary of the test run and a
record of complete test results.  You may specify test IDs and test
suite IDs to run; omit arguments to run the entire test database.

Test results are written to "results.qmr".  Use the '--output' option to
specify a different output file, or '--no-output' to supress results.

Use the '--format' option to specify the output format for the summary.
Valid formats are %s.
         """ % _make_comma_separated_string(summary_formats, "and"),
         (
           annotation_option_spec,
           concurrent_option_spec,
           context_file_spec,
           context_option_spec,
           format_option_spec,
           help_option_spec,
           no_output_option_spec,
           outcomes_option_spec,
           expectations_option_spec,
           output_option_spec,
           random_option_spec,
           rerun_option_spec,
           result_stream_spec,
           seed_option_spec,
           targets_option_spec,
           )
         ),

        ("summarize",
         "Summarize results from a test run.",
         "[FILE [ ID ... ]]",
         """
Loads a test results file and summarizes the results.  FILE is the path
to the results file.  Optionally, specify one or more test or suite IDs
whose results are shown.  If none are specified, shows all tests that
did not pass.

Use the '--format' option to specify the output format for the summary.
Valid formats are %s.
         """ % _make_comma_separated_string(summary_formats, "and"),
         ( help_option_spec,
           format_option_spec,
           outcomes_option_spec,
           expectations_option_spec,
           output_option_spec,
           result_stream_spec)
         ),

        ]

    __version_output = \
        ("QMTest %s\n" 
         "Copyright (C) 2002 - 2007 CodeSourcery, Inc.\n"
         "QMTest comes with ABSOLUTELY NO WARRANTY\n"
         "For more information about QMTest visit http://www.qmtest.com\n")
    """The string printed when the --version option is used.

    There is one fill-in, for a string, which should contain the version
    number."""
    
    def __init__(self, argument_list, path):
        """Construct a new QMTest.

        Parses the argument list but does not execute the command.

        'argument_list' -- The arguments to QMTest, not including the
        initial argv[0].

        'path' -- The path to the QMTest executable."""

        global _the_qmtest
        
        _the_qmtest = self
        
        # Use the stadard stdout and stderr streams to emit messages.
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        
        # Build a trace object.
        self.__tracer = Tracer()

        # Build a command-line parser for this program.
        self.__parser = qm.cmdline.CommandParser(
            "qmtest",
            self.global_options_spec,
            self.commands_spec,
            self.conflicting_option_specs)
        # Parse the command line.
        components = self.__parser.ParseCommandLine(argument_list)
        # Unpack the results.
        ( self.__global_options,
          self.__command,
          self.__command_options,
          self.__arguments
          ) = components

        # If available, record the path to the qmtest executable.
        self.__qmtest_path = path
        
        # We have not yet computed the set of available targets.
        self.targets = None

        # The result stream class used for results files is the pickling
        # version.
        self.__file_result_stream_class_name \
            = "pickle_result_stream.PickleResultStream"
        # The result stream class used for textual feed back.
        self.__text_result_stream_class_name \
            = "text_result_stream.TextResultStream"
        # The expected outcomes have not yet been loaded.
        self.__expected_outcomes = None


    def __del__(self):
        """Clean up global variables."""
        
        test.set_targets([])


    def HasGlobalOption(self, option):
        """Return true if 'option' was specified as a global command.

        'command' -- The long name of the option, but without the
        preceding "--".

        returns -- True if the option is present."""

        return option in [x[0] for x in self.__global_options]
    
        
    def GetGlobalOption(self, option, default=None):
        """Return the value of global 'option', or 'default' if omitted."""

        for opt, opt_arg in self.__global_options:
            if opt == option:
                return opt_arg
        return default


    def HasCommandOption(self, option):
        """Return true if command 'option' was specified."""

        for opt, opt_arg in self.__command_options:
            if opt == option:
                return 1
        return 0
    

    def GetCommandOption(self, option, default = None):
        """Return the value of command 'option'.

        'option' -- The long form of an command-specific option.

        'default' -- The default value to be returned if the 'option'
        was not specified.  This option should be the kind of an option
        that takes an argument.

        returns -- The value specified by the option, or 'default' if
        the option was not specified."""

        for opt, opt_arg in self.__command_options:
            if opt == option:
                return opt_arg
        return default


    def Execute(self):
        """Execute the command.

        returns -- 0 if the command was executed successfully.  1 if
        there was a problem or if any tests run had unexpected outcomes."""

        # If --version was given, print the version number and exit.
        # (The GNU coding standards require that the program take no
        # further action after seeing --version.)
        if self.HasGlobalOption("version"):
            self._stdout.write(self.__version_output % qm.version)
            return 0
        # If the global help option was specified, display it and stop.
        if (self.GetGlobalOption("help") is not None 
            or self.__command == "help"):
            self._stdout.write(self.__parser.GetBasicHelp())
            return 0
        # If the command help option was specified, display it and stop.
        if self.GetCommandOption("help") is not None:
            self.__WriteCommandHelp(self.__command)
            return 0

        # Make sure a command was specified.
        if self.__command == "":
            raise qm.cmdline.CommandError(qm.error("missing command"))

        # Look in several places to find the test database:
        #
        # 1. The command-line.
        # 2. The QMTEST_DB_PATH environment variable.
        # 3. The current directory.
        db_path = self.GetGlobalOption("tdb")
        if not db_path:
            if self.db_path_environment_variable in os.environ:
                db_path = os.environ[self.db_path_environment_variable]
            else:
                db_path = "."
        # If the path is not already absolute, make it into an
        # absolute path at this point.
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        # Normalize the path so that it is easy for the user to read
        # if it is emitted in an error message.
        self.__db_path = os.path.normpath(db_path)
        database.set_path(self.__db_path)

        error_occurred = 0
        
        # Dispatch to the appropriate method.
        if self.__command == "create-tdb":
            return self.__ExecuteCreateTdb(db_path)
        
        method = {
            "create" : self.__ExecuteCreate,
            "create-target" : self.__ExecuteCreateTarget,
            "describe" : self.__ExecuteDescribe,
            "extensions" : self.__ExecuteExtensions,
            "gui" : self.__ExecuteServer,
            "ls" : self.__ExecuteList,
            "register" : self.__ExecuteRegister,
            "remote" : self.__ExecuteRemote,
            "run" : self.__ExecuteRun,
            "report" : self.__ExecuteReport,
            "summarize": self.__ExecuteSummarize,
            }[self.__command]

        return method()


    def GetDatabase(self):
        """Return the test database to use.

        returns -- The 'Database' to use for this execution.  Raises an
        exception if no 'Database' is available."""

        return database.get_database()


    def GetDatabaseIfAvailable(self):
        """Return the test database to use.

        returns -- The 'Database' to use for this execution, or 'None'
        if no 'Database' is available."""

        try:
            return self.GetDatabase()
        except:
            return None

    
    def GetTargetFileName(self):
        """Return the path to the file containing target specifications.

        returns -- The path to the file containing target specifications."""

        # See if the user requested a specific target file.
        target_file_name = self.GetCommandOption("targets")
        if target_file_name:
            return target_file_name
        # If there was no explicit option, use the "targets" file in the
        # database directory.
        return os.path.join(self.GetDatabase().GetConfigurationDirectory(),
                            self.target_file_name)
    

    def GetTargetsFromFile(self, file_name):
        """Return the 'Target's specified in 'file_name'.

        returns -- A list of the 'Target' objects specified in the
        target specification file 'file_name'."""

        try:
            document = qm.xmlutil.load_xml_file(file_name)
            targets_element = document.documentElement
            if targets_element.tagName != "targets":
                raise QMException(qm.error("could not load target file",
                               file = file_name))
            targets = []
            for node in targets_element.getElementsByTagName("extension"):
                # Parse the DOM node.
                target_class, arguments \
                    = (qm.extension.parse_dom_element
                       (node,
                        lambda n: get_extension_class(n, "target",
                                                      self.GetDatabase())))
                # Build the target.
                target = target_class(self.GetDatabase(), arguments)
                # Accumulate targets.
                targets.append(target)

            return targets
        except Context:
            raise QMException(qm.error("could not load target file",
                           file=file_name))

        
        
    def GetTargets(self):
        """Return the 'Target' objects specified by the user.

        returns -- A sequence of 'Target' objects."""

        if not test.get_targets():
            file_name = self.GetTargetFileName()
            if os.path.exists(file_name):
                test.set_targets(self.GetTargetsFromFile(file_name))
            else:
                # The target file does not exist.
                concurrency = self.GetCommandOption("concurrency")
                if concurrency is None:
                    # No concurrency specified.  Run single-threaded.
                    concurrency = 1
                else:
                    # Convert the concurrency to an integer.
                    try:
                        concurrency = int(concurrency)
                    except ValueError:
                        raise qm.cmdline.CommandError(qm.error("concurrency not integer",
                                       value=concurrency))
                # Construct the target.
                arguments = {}
                arguments["name"] = "local"
                arguments["group"] = "local"
                if concurrency > 1:
                    class_name = "thread_target.ThreadTarget"
                    arguments["threads"] = concurrency
                else:
                    class_name = "serial_target.SerialTarget"
                target_class = get_extension_class(class_name,
                                                   'target', self.GetDatabase())
                test.set_targets([target_class(self.GetDatabase(), arguments)])
            
        return test.get_targets()
        

    def GetTracer(self):
        """Return the 'Tracer' associated with this instance of QMTest.

        returns -- The 'Tracer' associated with this instance of QMTest."""

        return self.__tracer

    
    def MakeContext(self):
        """Construct a 'Context' object for running tests."""

        context = Context()

        # First, see if a context file was specified on the command
        # line.
        use_implicit_context_file = 1
        for option, argument in self.__command_options:
            if option == "load-context":
                use_implicit_context_file = 0
                break

        # If there is no context file, read the default context file.
        if (use_implicit_context_file
            and os.path.isfile(self.context_file_name)):
            context.Read(self.context_file_name)
                
        for option, argument in self.__command_options:
            # Look for the '--load-context' option.
            if option == "load-context":
                context.Read(argument)
            # Look for the '--context' option.
            elif option == "context":
                # Parse the argument.
                name, value = qm.common.parse_assignment(argument)
            
                try:
                    # Insert it into the context.
                    context[name] = value
                except ValueError as msg:
                    # The format of the context key is invalid, but
                    # raise a 'CommandError' instead.
                    raise qm.cmdline.CommandError(msg)

        return context


    def GetExecutablePath(self):
        """Return the path to the QMTest executable.

        returns -- A string giving the path to the QMTest executable.
        This is the path that should be used to invoke QMTest
        recursively.  Returns 'None' if the path to the QMTest
        executable is uknown."""

        return self.__qmtest_path
    

    def GetFileResultStreamClass(self):
        """Return the 'ResultStream' class used for results files.

        returns -- The 'ResultStream' class used for results files."""

        return get_extension_class(self.__file_result_stream_class_name,
                                   "result_stream",
                                   self.GetDatabaseIfAvailable())

    def GetTextResultStreamClass(self):
        """Return the 'ResultStream' class used for textual feedback.

        returns -- the 'ResultStream' class used for textual
        feedback."""

        return get_extension_class(self.__text_result_stream_class_name,
                                   "result_stream",
                                   self.GetDatabaseIfAvailable())
        

    def __GetAttributeOptions(self, expect_value = True):
        """Return the attributes specified on the command line.

        'expect_value' -- True if the attribute is to be parsed as
        an assignment.

        returns -- A dictionary. If expect_value is True, it
        maps attribute names (strings) to values (strings).
        Else it contains the raw attribute strings, mapping to None.
        There is an entry for each attribute specified with
        '--attribute' on the command line."""

        # There are no attributes yet.
        attributes = {}

        # Go through the command line looking for attribute options.
        for option, argument in self.__command_options:
            if option == "attribute":
                if expect_value:
                    name, value = qm.common.parse_assignment(argument)
                    attributes[name] = value
                else:
                    attributes[argument] = None
        return attributes
    

    def __GetAnnotateOptions(self):
        """Return all annotate options.

        returns -- A dictionary containing the annotation name / value pairs."""

        annotations = {}
        for option, argument in self.__command_options:
            if option == "annotate":
                name, value = qm.common.parse_assignment(argument)
                annotations[name] = value
        return annotations
    

    def __ExecuteCreate(self):
        """Create a new extension file."""

        # Check that the right number of arguments are present.
        if len(self.__arguments) != 2:
            self.__WriteCommandHelp("create")
            return 2

        # Figure out what database (if any) we are using.
        database = self.GetDatabaseIfAvailable()
        
        # Get the extension kind.
        kind = self.__arguments[0]
        self.__CheckExtensionKind(kind)

        extension_id = self.GetCommandOption("id")
        if extension_id is not None:
            if not database:
                raise QMException(qm.error("no db specified"))
            if not database.IsModifiable():
                raise QMException(qm.error("db not modifiable"))
            extension_loader = database.GetExtension
        else:
            extension_loader = None

        class_loader = lambda n: get_extension_class(n, kind, database)
        
        # Process the descriptor.
        (extension_class, more_arguments) \
             = (qm.extension.parse_descriptor
                (self.__arguments[1], class_loader, extension_loader))

        # Validate the --attribute options.
        arguments = self.__GetAttributeOptions()
        arguments = qm.extension.validate_arguments(extension_class,
                                                    arguments)
        # Override the --attribute options with the arguments provided
        # as part of the descriptor.
        arguments.update(more_arguments)

        if extension_id is not None:
            # Create the extension instance.  Objects derived from
            # Runnable require magic additional arguments.
            if issubclass(extension_class, (Runnable, Suite)):
                extras = { extension_class.EXTRA_ID : extension_id, 
                           extension_class.EXTRA_DATABASE : database }
            else:
                extras = {}
            extension = extension_class(arguments, **extras)
            # Write the extension to the database.
            database.WriteExtension(extension_id, extension)
        else:
            # Figure out what file to use.
            filename = self.GetCommandOption("output")
            if filename is not None:
                file = open(filename, "w")
            else:
                file = sys.stdout
            # Write out the file.
            qm.extension.write_extension_file(extension_class, arguments,
                                              file)

        return 0
    
        
    def __ExecuteCreateTdb(self, db_path):
        """Handle the command for creating a new test database.

        'db_path' -- The path at which to create the new test database."""

        if len(self.__arguments) != 0:
            self.__WriteCommandHelp("create-tdb")
            return 2
        
        # Create the directory if it does not already exists.
        if not os.path.isdir(db_path):
            os.mkdir(db_path)
        # Create the configuration directory.
        config_dir = database.get_configuration_directory(db_path)
        if not os.path.isdir(config_dir):
            os.mkdir(config_dir)

        # Reformulate this command in terms of "qmtest create".  Start by
        # adding "--output <path>".
        self.__command_options.append(("output",
                                       database.get_configuration_file(db_path)))
        # Figure out what database class to use.
        class_name \
            = self.GetCommandOption("class", "xml_database.XMLDatabase")
        # Add the extension kind and descriptor.
        self.__arguments.append("database")
        self.__arguments.append(class_name)
        # Now process this just like "qmtest create".
        self.__ExecuteCreate()
        # Print a helpful message.
        self._stdout.write(qm.message("new db message", path=db_path) + "\n")

        return 0

    
    def __ExecuteCreateTarget(self):
        """Create a new target file."""

        # Make sure that the arguments are correct.
        if (len(self.__arguments) < 2 or len(self.__arguments) > 3):
            self.__WriteCommandHelp("create-target")
            return 2

        # Pull the required arguments out of the command line.
        target_name = self.__arguments[0]
        class_name = self.__arguments[1]
        if (len(self.__arguments) > 2):
            target_group = self.__arguments[2]
        else:
            target_group = ""

        # Load the database.
        database = self.GetDatabase()

        # Load the target class.
        target_class = get_extension_class(class_name, "target", database)

        # Get the dictionary of class arguments.
        field_dictionary \
            = qm.extension.get_class_arguments_as_dictionary(target_class)

        # Get the name of the target file.
        file_name = self.GetTargetFileName()
        # If the file already exists, read it in.
        if os.path.exists(file_name):
            # Load the document.
            document = qm.xmlutil.load_xml_file(file_name)
            # If there is a previous entry for this target, discard it.
            targets_element = document.documentElement
            duplicates = []
            for target_element \
                in targets_element.getElementsByTagName("extension"):
                for attribute \
                    in target_element.getElementsByTagName("argument"):
                    if attribute.getAttribute("name") == "name":
                        name = field_dictionary["name"].\
                               GetValueFromDomNode(attribute.childNodes[0],
                                                   None)
                        if name == target_name:
                            duplicates.append(target_element)
                            break
            for duplicate in duplicates:
                targets_element.removeChild(duplicate)
                duplicate.unlink()
        else:
            document = (qm.xmlutil.create_dom_document
                        (public_id = "QMTest/Target",
                         document_element_tag = "targets"))
            targets_element = document.documentElement
            
        # Get the attributes.
        attributes = self.__GetAttributeOptions()
        attributes["name"] = target_name
        attributes["group"] = target_group
        attributes = qm.extension.validate_arguments(target_class,
                                                     attributes)
        
        # Create the target element.
        target_element = qm.extension.make_dom_element(target_class,
                                                       attributes,
                                                       document)
        targets_element.appendChild(target_element)

        # Write out the XML file.
        document.writexml(open(self.GetTargetFileName(), "w"))
        
        return 0

    
    def __ExecuteExtensions(self):
        """List the available extension classes."""

        # Check that the right number of arguments are present.
        if len(self.__arguments) != 0:
            self.__WriteCommandHelp("extensions")
            return 2

        database = self.GetDatabaseIfAvailable()

        # Figure out what kinds of extensions we're going to list.
        kind = self.GetCommandOption("kind")
        if kind:
            self.__CheckExtensionKind(kind)
            kinds = [kind]
        else:
            kinds = base.extension_kinds

        for kind in kinds:
            # Get the available classes.
            names = qm.test.base.get_extension_class_names(kind,
                                                           database,
                                                           self.__db_path)
            # Build structured text describing the classes.
            description = "** Available %s classes **\n\n" % kind
            for n in names:
                description += "  * " + n + "\n\n    "
                # Try to load the class to get more information.
                try:
                    extension_class = get_extension_class(n, kind, database)
                    description \
                        += qm.extension.get_class_description(extension_class,
                                                              brief=1)
                except:
                    description += ("No description available: "
                                    "could not load class.")
                description += "\n\n"
                
            self._stdout.write(qm.structured_text.to_text(description))

        return 0
            

    def __ExecuteDescribe(self):
        """Describe an extension."""

        # Check that the right number of arguments are present.
        if len(self.__arguments) != 2:
            self.__WriteCommandHelp("describe")
            return 2

        kind = self.__arguments[0]
        long_format = self.GetCommandOption("long") != None

        database = self.GetDatabaseIfAvailable()
        class_ = get_extension_class(self.__arguments[1], kind, database)

        attributes = (self.__GetAttributeOptions(False)
                      or class_._argument_dictionary)

        print("")
        print("class name:", get_extension_class_name(class_))
        print("  ", get_class_description(class_, brief=not long_format))
        print("")
        print("class attributes:")
        tab = max([len(name) for name in attributes])
        for name in attributes:
            field = class_._argument_dictionary.get(name)
            if not field:
                self._stderr.write("Unknown attribute '%s'.\n"%name)
                return 2
            value = field.GetDefaultValue()
            description = field.GetDescription()
            if not long_format:
                description = qm.structured_text.get_first(description)
            print("   %-*s     %s"%(tab, name, description))


    def __ExecuteList(self):
        """List the contents of the database."""

        database = self.GetDatabase()

        long_format = self.HasCommandOption("long")
        details_format = self.HasCommandOption("details")
        recursive = self.HasCommandOption("recursive")

        # If no arguments are specified, list the root directory.
        args = self.__arguments or ("",)

        # Get all the extensions to list.
        extensions = {}
        for arg in args:
            extension = database.GetExtension(arg)
            if not extension:
                raise QMException(qm.error("no such ID", id = arg))
            if isinstance(extension, qm.test.suite.Suite):
                if recursive:
                    test_ids, suite_ids = extension.GetAllTestAndSuiteIds()
                    extensions.update([(i, database.GetExtension(i))
                                       for i in test_ids + suite_ids])
                else:
                    ids = extension.GetTestIds() + extension.GetSuiteIds()
                    extensions.update([(i, database.GetExtension(i))
                                       for i in ids])
            else:
                extensions[arg] = extension

        # Get the labels for the extensions, in alphabetical order.
        ids = list(extensions.keys())
        ids.sort()

        # In the short format, just print the labels.
        if not long_format:
            for id in ids:
                print(id, file=sys.stdout)
            return 0

        # In the long format, print three columns: the extension kind,
        # class name, and the label.  We make two passes over the
        # extensions so that the output will be tidy. In the first pass,
        # calculate the width required for the first two columns in the
        # output.  The actual output occurs in the second pass.
        longest_kind = 0
        longest_class = 0
        for i in (0, 1):
            for id in ids:
                extension = extensions[id]
                if isinstance(extension,
                              qm.test.directory_suite.DirectorySuite):
                    kind = "directory"
                    class_name = ""
                else:
                    kind = extension.__class__.kind
                    class_name = extension.GetClassName()
                    
                if i == 0:
                    kind_len = len(kind) + 1
                    if kind_len > longest_kind:
                        longest_kind = kind_len
                    class_len = len(class_name) + 1
                    if class_len > longest_class:
                        longest_class = class_len
                else:
                    print("%-*s%-*s%s" % (longest_kind, kind,
                                          longest_class, class_name, id), file=sys.stdout)
                    if details_format:
                        tab = max([len(name)
                                   for name in extension._argument_dictionary])
                        for name in extension._argument_dictionary:
                            value = str(getattr(extension, name))
                            print("   %-*s     %s"%(tab, name, value))

        return 0
        
        
    def __ExecuteRegister(self):
        """Register a new extension class."""

        # Make sure that the KIND and CLASS were specified.
        if (len(self.__arguments) != 2):
            self.__WriteCommandHelp("register")
            return 2
        kind = self.__arguments[0]
        class_name = self.__arguments[1]

        # Check that the KIND is valid.
        self.__CheckExtensionKind(kind)

        # Check that the CLASS_NAME is well-formed.
        if class_name.count('.') != 1:
            raise qm.cmdline.CommandError(qm.error("invalid class name",
                           class_name = class_name))
        module, name = class_name.split('.')

        # Try to load the database.  It may provide additional
        # directories to search.
        database = self.GetDatabaseIfAvailable()
        # Hunt through all of the extension class directories looking
        # for an appropriately named module.
        found = None
        directories = get_extension_directories(kind, database,
                                                self.__db_path)
        for directory in directories:
            for ext in (".py", ".pyc", ".pyo"):
                file_name = os.path.join(directory, module + ext)
                if os.path.exists(file_name):
                    found = file_name
                    break
            if found:
                break

        # If we could not find the module, issue an error message.
        if not found:
            raise qm.QMException(qm.error("module does not exist",
                           module = module))

        # Inform the user of the location in which QMTest found the
        # module.  (Sometimes, there might be another module with the
        # same name in the path.  Telling the user where we've found
        # the module will help the user to deal with this situation.)
        self._stdout.write(qm.structured_text.to_text
                           (qm.message("loading class",
                                       class_name = name,
                                       file_name = found)))
        
        # We have found the module.  Try loading it.
        extension_class = get_extension_class_from_directory(class_name,
                                                             kind,
                                                             directory,
                                                             directories)

        # Create or update the classes.qmc file.
        classes_file_name = os.path.join(directory, "classes.qmc")
        
        # Create a new DOM document for the class directory.
        document = (qm.xmlutil.create_dom_document
                    (public_id = "Class-Directory",
                     document_element_tag="class-directory"))
        
        # Copy entries from the old file to the new one.
        extensions = get_extension_class_names_in_directory(directory)
        for k, ns in extensions.items():
            for n in ns:
                # Remove previous entries for the class being added.
                if k == kind and n == class_name:
                    continue
                element = document.createElement("class")
                element.setAttribute("kind", k)
                element.setAttribute("name", n)
                document.documentElement.appendChild(element)

        # Add an entry for the new element.
        element = document.createElement("class")
        element.setAttribute("kind", kind)
        element.setAttribute("name", class_name)
        document.documentElement.appendChild(element)        

        # Write out the file.
        document.writexml(open(classes_file_name, "w"),
                          addindent = " ", newl = "\n")

        return 0

        
    def __ExecuteSummarize(self):
        """Read in test run results and summarize."""

        # If no results file is specified, use a default value.
        if len(self.__arguments) == 0:
            results_path = self.results_file_name
        else:
            results_path = self.__arguments[0]

        database = self.GetDatabaseIfAvailable()

        # The remaining arguments, if any, are test and suite IDs.
        id_arguments = self.__arguments[1:]
        # Are there any?
        # '.' is an alias for <all>, and thus shadows other selectors.
        if len(id_arguments) > 0 and not '.' in id_arguments:
            ids = set()
            # Expand arguments into test/resource IDs.
            if database:
                for id in id_arguments:
                    extension = database.GetExtension(id)
                    if not extension:
                        raise qm.cmdline.CommandError(qm.error("no such ID", id = id))
                    if extension.kind == database.SUITE:
                        ids.update(extension.GetAllTestAndSuiteIds()[0])
                    else:
                        ids.add(id)
            else:
                ids = set(id_arguments)
        else:
            # No IDs specified.  Show all test and resource results.
            # Don't show any results by test suite though.
            ids = None

        # Get an iterator over the results.
        try:
            results = base.load_results(results_path, database)
        except Exception as exception:
            raise QMException(qm.error("invalid results file",
                           path=results_path,
                           problem=str(exception)))

        any_unexpected_outcomes = 0

        # Load expectations.
        expectations = (self.GetCommandOption('expectations') or
                        self.GetCommandOption('outcomes'))
        expectations = base.load_expectations(expectations,
                                              database,
                                              results.GetAnnotations())
        # Compute the list of result streams to which output should be
        # written.
        streams = self.__CreateResultStreams(self.GetCommandOption("output"),
                                             results.GetAnnotations(),
                                             expectations)

        resource_results = {}
        for r in results:
            if r.GetKind() != Result.TEST:
                if ids is None or r.GetId() in ids:
                    for s in streams:
                        s.WriteResult(r)
                elif r.GetKind() == Result.RESOURCE_SETUP:
                    resource_results[r.GetId()] = r
                continue
            # We now known that r is test result.  If it's not one
            # that interests us, we're done.
            if ids is not None and r.GetId() not in ids:
                continue
            # If we're filtering, and this test was not run because it
            # depended on a resource that was not set up, emit the
            # resource result here.
            if (ids is not None
                and r.GetOutcome() == Result.UNTESTED
                and Result.RESOURCE in r):
                rid = r[Result.RESOURCE]
                rres = resource_results.get(rid)
                if rres:
                    del resource_results[rid]
                    for s in streams:
                        s.WriteResult(rres)
            # Write out the test result.             
            for s in streams:
                s.WriteResult(r)
                if (not any_unexpected_outcomes
                    and r.GetOutcome() != expectations.Lookup(r.GetId())):
                    any_unexpected_outcomes = 1
        # Shut down the streams.            
        for s in streams:
            s.Summarize()

        return any_unexpected_outcomes
        

    def __ExecuteRemote(self):
        """Execute the 'remote' command."""

        database = self.GetDatabase()

        # Get the target class.  For now, we always run in serial when
        # running remotely.
        target_class = get_extension_class("serial_target.SerialTarget",
                                           'target', database)
        # Build the target.
        target = target_class(database, { "name" : "child" })

        # Start the target.
        response_queue = queue.Queue(0)
        target.Start(response_queue)
        
        # Read commands from standard input, and reply to standard
        # output.
        while 1:
            # Read the command.
            command = cPickle.load(sys.stdin)
            
            # If the command is just a string, it should be
            # the 'Stop' command.
            if isinstance(command, bytes):
                assert command == "Stop"
                target.Stop()
                break

            # Decompose command.
            method, id, context = command
            # Get the descriptor.
            descriptor = database.GetTest(id)
            # Run it.
            target.RunTest(descriptor, context)
            # There are no results yet.
            results = []
            # Read all of the results.
            while 1:
                try:
                    result = response_queue.get(0)
                    results.append(result)
                except queue.Empty:
                    # There are no more results.
                    break
            # Pass the results back.
            cPickle.dump(results, sys.stdout)
            # The standard output stream is bufferred, but the master
            # will block waiting for a response, so we must flush
            # the buffer here.
            sys.stdout.flush()

        return 0


    def __ExecuteReport(self):
        """Execute a 'report' command."""

        output = self.GetCommandOption("output")
        flat = self.GetCommandOption("flat") != None

        # Check that at least one result file is present.
        if not output or len(self.__arguments) < 1:
            self.__WriteCommandHelp("report")
            return 2

        # If the database can be loaded, use it to find all
        # available tests. The default (non-flat) format requires a database.
        if flat:
            database = self.GetDatabaseIfAvailable()
        else:
            database = self.GetDatabase()

        report_generator = ReportGenerator(output, database)
        report_generator.GenerateReport(flat, self.__arguments)
        

    def __ExecuteRun(self):
        """Execute a 'run' command."""
        
        database = self.GetDatabase()

        # Handle the 'seed' option.  First create the random number
        # generator we will use.
        seed = self.GetCommandOption("seed")
        if seed:
            # A seed was specified.  It should be an integer.
            try:
                seed = int(seed)
            except ValueError:
                raise qm.cmdline.CommandError(qm.error("seed not integer", seed=seed))
            # Use the specified seed.
            random.seed(seed)

        # Figure out what tests to run.
        if len(self.__arguments) == 0:
            # No IDs specified; run the entire test database.
            self.__arguments.append("")
        elif '.' in self.__arguments:
            # '.' is an alias for <all>, and thus shadows other selectors.
            self.__arguments = [""]

        # Expand arguments in test IDs.
        try:
            test_ids, test_suites \
                      = self.GetDatabase().ExpandIds(self.__arguments)
        except (qm.test.database.NoSuchTestError,
                qm.test.database.NoSuchSuiteError) as exception:
            raise qm.cmdline.CommandError(str(exception))
        except ValueError as exception:
            raise qm.cmdline.CommandError(qm.error("no such ID", id=str(exception)))

        # Handle the --annotate options.
        annotations = self.__GetAnnotateOptions()

        # Load expectations.
        expectations = (self.GetCommandOption('expectations') or
                        self.GetCommandOption('outcomes'))
        expectations = base.load_expectations(expectations,
                                              database,
                                              annotations)
        # Filter the set of tests to be run, eliminating any that should
        # be skipped.
        test_ids = self.__FilterTestsToRun(test_ids, expectations)
        
        # Figure out which targets to use.
        targets = self.GetTargets()
        # Compute the context in which the tests will be run.
        context = self.MakeContext()

        # Handle the --output option.
        if self.HasCommandOption("no-output"):
            # User specified no output.
            result_file_name = None
        else:
            result_file_name = self.GetCommandOption("output")
            if result_file_name is None:
                # By default, write results to a default file.
                result_file_name = self.results_file_name

        # Compute the list of result streams to which output should be
        # written.
        result_streams = self.__CreateResultStreams(result_file_name,
                                                    annotations,
                                                    expectations)

        if self.HasCommandOption("random"):
            # Randomize the order of the tests.
            random.shuffle(test_ids)
        else:
            test_ids.sort()

        # Run the tests.
        engine = ExecutionEngine(database, test_ids, context, targets,
                                 result_streams,
                                 expectations)
        if engine.Run():
            return 1

        return 0
                                                    

    def __ExecuteServer(self):
        """Process the server command."""

        database = self.GetDatabase()

        # Get the port number specified by a command option, if any.
        # Otherwise use a default value.
        port_number = self.GetCommandOption("port", default=0)
        try:
            port_number = int(port_number)
        except ValueError:
            raise qm.cmdline.CommandError(qm.error("bad port number"))
        # Get the local address specified by a command option, if any.
        # If not was specified, use the loopback address.  The loopback
        # address is used by default for security reasons; it restricts
        # access to the QMTest server to users on the local machine.
        address = self.GetCommandOption("address", default="127.0.0.1")

        # If a log file was requested, open it now.
        log_file_path = self.GetCommandOption("log-file")
        if log_file_path == "-":
            # A hyphen path name means standard output.
            log_file = sys.stdout
        elif log_file_path is None:
            # No log file.
            log_file = None
        else:
            # Otherwise, it's a file name.  Open it for append.
            log_file = open(log_file_path, "a+")

        # If a PID file was requested, create it now.
        pid_file_path = self.GetCommandOption("pid-file")
        if pid_file_path is not None:
            # If a PID file was requested, but no explicit path was
            # given, use a default value.
            if not pid_file_path:
                pid_file_path = qm.common.rc.Get("pid-file",
                                                 "/var/run/qmtest.pid",
                                                 "qmtest")
            try:
                pid_file = open(pid_file_path, "w")
            except IOError as e:
                raise qm.cmdline.CommandError(str(e))
        else:
            pid_file = None
            
        # Create a run database, if requested.
        run_db = None
        directory = self.GetCommandOption("results", default="")
        if directory:
            directory = os.path.normpath(directory)
            run_db = DirRunDatabase(directory, database)

        # Load expectations. Only support the 'outcome' option here,
        # as 'expectations' in general are unsupported with this GUI.
        expectations = self.GetCommandOption('outcomes')
        expectations = base.load_expectations(expectations, database)
        # Make sure this is either an ExpectationDatabase or a
        # PreviousRun
        if not type(expectations) in (ExpectationDatabase, PreviousTestRun):
            raise qm.cmdline.CommandError('not a valid results file')
        # Figure out which targets to use.
        targets = self.GetTargets()
        # Compute the context in which the tests will be run.
        context = self.MakeContext()
        # Set up the server.
        server = QMTestServer(database,
                              port_number, address,
                              log_file, targets, context,
                              expectations,
                              run_db)
        port_number = server.GetServerAddress()[1]
        
        # Construct the URL to the main page on the server.
        if address == "":
            url_address = qm.platform.get_host_name()
        else:
            url_address = address
        if run_db:
            url = "http://%s:%d/report/dir" % (url_address, port_number)
        else:
            url = "http://%s:%d/test/dir" % (url_address, port_number)
            
        if not self.HasCommandOption("no-browser"):
            # Now that the server is bound to its address, start the
            # web browser.
            qm.platform.open_in_browser(url)
            
        message = qm.message("server url", url=url)
        sys.stderr.write(message + "\n")

        # Become a daemon, if appropriate.
        if self.GetCommandOption("daemon") is not None:
            # Fork twice.
            if os.fork() != 0:
                os._exit(0)
            if os.fork() != 0:
                os._exit(0)
            # This process is now the grandchild of the original
            # process.

        # Write out the PID file.  The correct PID is not known until
        # after the transformation to a daemon has taken place.
        try:
            if pid_file:
                pid_file.write(str(os.getpid()))
                pid_file.close()
                
            # Accept requests.
            try:
                server.Run()
            except qm.platform.SignalException as se:
                if se.GetSignalNumber() == signal.SIGTERM:
                    # If we receive SIGTERM, shut down.
                    pass
                else:
                    # Other signals propagate outwards.
                    raise
            except KeyboardInterrupt:
                # If we receive a keyboard interrupt (Ctrl-C), shut down.
                pass
        finally:
            if pid_file:
                os.remove(pid_file_path)
                
        return 0


    def __WriteCommandHelp(self, command):
        """Write out help information about 'command'.

        'command' -- The name of the command for which help information
        is required."""

        self._stderr.write(self.__parser.GetCommandHelp(command))

    def __FilterTestsToRun(self, test_ids, expectations):
        """Return those tests from 'test_ids' that should be run.

        'test_ids' -- A sequence of test ids.

        'expectations' -- An ExpectationDatabase.

        returns -- Those elements of 'test_names' that are not to be
        skipped.  If 'a' precedes 'b' in 'test_ids', and both 'a' and
        'b' are present in the result, 'a' will precede 'b' in the
        result."""

        # The --rerun option indicates that only failing tests should
        # be rerun.
        rerun_file_name = self.GetCommandOption("rerun")
        if rerun_file_name:
            # Load the outcomes from the file specified.
            outcomes = base.load_outcomes(rerun_file_name,
                                          self.GetDatabase())
            # Filter out tests that have unexpected outcomes.
            test_ids = [t for t in test_ids
                        if outcomes.get(t, Result.PASS)
                        != expectations.Lookup(t).GetOutcome()]
        
        return test_ids


    def __CheckExtensionKind(self, kind):
        """Check that 'kind' is a valid extension kind.

        'kind' -- A string giving the name of an extension kind.  If the
        'kind' does not name a valid extension kind, an appropriate
        exception is raised."""

        if kind not in base.extension_kinds:
            raise qm.cmdline.CommandError(qm.error("invalid extension kind",
                           kind = kind))

                       
    def __CreateResultStreams(self, output_file, annotations, expectations):
        """Return the result streams to use.

        'output_file' -- If not 'None', the name of a file to which
        the standard results file format should be written.

        'annotations' -- A dictionary with annotations for this test run.

        'expectations' -- An ExpectationDatabase.
        
        returns -- A list of 'ResultStream' objects, as indicated by the
        user."""

        database = self.GetDatabaseIfAvailable()

        result_streams = []

        arguments = {}
        arguments['expected_outcomes'] = expectations.GetExpectedOutcomes()

        # Look up the summary format.
        format = self.GetCommandOption("format", "")
        if format and format not in self.summary_formats:
            # Invalid format.  Complain.
            valid_format_string = string.join(
                ['"%s"' % f for f in self.summary_formats], ", ")
            raise qm.cmdline.CommandError(qm.error("invalid results format",
                           format=format,
                           valid_formats=valid_format_string))
        if format != "none":
            args = { "format" : format }
            args.update(arguments)
            stream = self.GetTextResultStreamClass()(args)
            result_streams.append(stream)

        f = lambda n: get_extension_class(n, "result_stream", database)
        
        # Look for all of the "--result-stream" options.
        for opt, opt_arg in self.__command_options:
            if opt == "result-stream":
                ec, args = qm.extension.parse_descriptor(opt_arg, f)
                args.update(arguments)
                result_streams.append(ec(args))

        # If there is an output file, create a standard results file on
        # that file.
        if output_file is not None:
            rs = (self.GetFileResultStreamClass()
                  ({ "filename" : output_file}))
            result_streams.append(rs)

        for name, value in annotations.items():
            for rs in result_streams:
                rs.WriteAnnotation(name, value)

        return result_streams
    
########################################################################
# Functions
########################################################################

def get_qmtest():
    """Returns the global QMTest object.

    returns -- The 'QMTest' object that corresponds to the currently
    executing thread.

    At present, there is only one QMTest object per process.  In the
    future, however, there may be more than one.  Then, this function
    will return different values in different threads."""

    return _the_qmtest
    
########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
