########################################################################
#
# File:   cmdline.py
# Author: Alex Samuel
# Date:   2001-03-16
#
# Contents:
#   QMTest command processing
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

import base
import os
import qm.cmdline
import qm.xmlutil
import string
import sys
import web.web
import xmldb

########################################################################
# classes
########################################################################

class Command:
    """A QMTest command."""

    db_path_environment_variable = "QMTEST_DB_PATH"

    help_option_spec = (
        "h",
        "help",
        None,
        "Display usage summary."
        )

    verbose_option_spec = (
        "v",
        "verbose",
        None,
        "Display informational messages."
        )

    db_path_option_spec = (
        "D",
        "db-path",
        "PATH",
        "Path to the test database."
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

    summary_option_spec = (
        "s",
        "summary",
        "FILE",
        "Write test summary to FILE (- for stdout)."
        )

    no_summary_option_spec = (
        "S",
        "no-summary",
        None,
        "Don't generate test summary."
        )

    outcomes_option_spec = (
        "O",
        "outcomes",
        "FILE",
        "Load expected outcomes from FILE."
        )

    context_option_spec = (
        "c",
        "context",
        "KEY=VALUE",
        "Add or override a context property.  You may specify this "
        "option more than once."
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

    # Groups of options that should not be used together.
    conflicting_option_specs = (
        ( output_option_spec, no_output_option_spec ),
        ( summary_option_spec, no_summary_option_spec ),
        )

    global_options_spec = [
        help_option_spec,
        verbose_option_spec,
        db_path_option_spec,
        ]

    commands_spec = [
        ("edit",
         "Edit a test.",
         "ID",
         "This command edits a test.",
         ( help_option_spec, )
         ),

        ("run",
         "Run one or more tests.",
         "ID ...",
         "This command runs tests, prints their outcomes, and writes "
         "test results.  Specify one or more test IDs and "
         "suite IDs as arguments.",
         ( help_option_spec, output_option_spec, no_output_option_spec,
           summary_option_spec, no_summary_option_spec,
           outcomes_option_spec, context_option_spec )
         ),

        ("server",
         'Start the web GUI server.',
         '',
         "Start the QMTest web GUI server.",
         [ help_option_spec, port_option_spec, address_option_spec,
           log_file_option_spec ]
         ),

        ("template",
         "Create a template for a new test.",
         "CLASS ID",
         "Creates a template for a new class, and starts editing it.",
         ( help_option_spec, )
         ),

        ]


    def __init__(self, program_name, argument_list):
        """Initialize a command.

        Parses the argument list but does not execute the command.

        'program_name' -- The name of the program, as invoked by the
        user.

        'argument_list' -- A sequence conaining the specified argument
        list."""

        # Build a command-line parser for this program.
        self.__parser = qm.cmdline.CommandParser(program_name,
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


    def GetGlobalOption(self, option, default=None):
        """Return the value of global 'option', or 'default' if omitted."""

        for opt, opt_arg in self.__global_options:
            if opt == option:
                return opt_arg
        return default


    def GetCommandOption(self, option, default=None):
        """Return the value of command 'option', or 'default' if ommitted."""

        for opt, opt_arg in self.__command_options:
            if opt == option:
                return opt_arg
        return default


    def Execute(self, output):
        """Execute the command.

        'output' -- The file object to send output to."""

        # If the global help option was specified, display it and stop.
        if self.GetGlobalOption("help") is not None:
            output.write(self.__parser.GetBasicHelp())
            return
        # If the command help option was specified, display it and stop.
        if self.GetCommandOption("help") is not None:
            output.write(self.__parser.GetCommandHelp(self.__command))
            return

        # Handle the verbose option.  The verbose level is the number of
        # times the verbose option was specified.
        self.__verbose = self.__global_options.count(("verbose", ""))

        # Make sure a command was specified.
        if self.__command == "":
            raise qm.cmdline.CommandError, qm.error("missing command")

        # Figure out the path to the test database.
        db_path = self.GetGlobalOption("db-path")
        if db_path is None:
            # The db-path option wasn't specified.  Try the environment
            # variable.
            try:
                db_path = os.environ[self.db_path_environment_variable]
            except KeyError:
                raise RuntimeError, \
                      qm.error("no db specified",
                               envvar=self.db_path_environment_variable)
        base._database = xmldb.Database(db_path)

        # Dispatch to the appropriate method.
        method = {
            "edit": self.__ExecuteEdit,
            "run" : self.__ExecuteRun,
            "server": self.__ExecuteServer,
            "template": self.__ExecuteTemplate,
            }[self.__command]
        method(output)


    def GetDatabase(self):
        """Return the test database to use."""
        
        return base.get_database()


    def MakeContext(self):
        """Construct a 'Context' object for running tests."""

        context = base.Context(
            path=qm.rc.Get("path", os.environ["PATH"])
            )

        # Look for all occurrences of the '--context' option.
        for option, argument in self.__command_options:
            if option == "context":
                # Make sure the argument is correctly-formatted.
                if not "=" in argument:
                    raise qm.cmdline.CommandError, \
                          qm.error("invalid context assignment",
                                   argument=argument)
                # Parse the assignment.
                name, value = string.split(argument, "=", 1)
                try:
                    # Insert it into the context.
                    context[name] = value
                except ValueError, msg:
                    # The format of the context key is invalid, but
                    # raise a 'CommandError' instead.
                    raise qm.cmdline.CommandError, msg

        return context


    def __ExecuteRun(self, output):
        """Execute a 'run' command."""
        
        # Handle result options.
        result_file_name = self.GetCommandOption("output")
        if result_file_name is None:
            # By default, no result output.
            result_file = None
        elif result_file_name == "-":
            # Use standard output.
            result_file = sys.stdout
        else:
            # A named file.
            result_file = open(result_file_name, "w")

        # Handle summary options.
        summary_file_name = self.GetCommandOption("summary")
        # The default is generate a summary to standard output.
        if self.GetCommandOption("no-summary") is not None:
            # User asked to supress summary.
            summary_file = None
        elif summary_file_name is None:
            # User didn't specify anything, so by default write summary
            # to standard output.
            summary_file = sys.stdout
        elif summary_file_name == "-":
            # User specified standard output explicitly.
            summary_file = sys.stdout
        else:
            summary_file = open(summary_file_name, "w")

        # Handle the outcome option.
        outcomes_file_name = self.GetCommandOption("outcomes")
        if outcomes_file_name is not None:
            outcomes = base.load_outcomes(outcomes_file_name)
        else:
            outcomes = None

        database = self.GetDatabase()
        # Make sure some arguments were specified.  The arguments are
        # the IDs of tests and suites to run.
        if len(self.__arguments) == 0:
            raise qm.cmdline.CommandError, qm.error("no ids specified")
        try:
            test_ids = []
            # Validate test IDs and expand test suites in the arguments.
            base.expand_and_validate_ids(database,
                                         self.__arguments,
                                         test_ids)

            # Set up a test engine for running tests.
            engine = base.Engine(database)
            context = self.MakeContext()
            self.__output = output
            if self.__verbose > 0:
                # If running verbose, specify a callback function to
                # display test results while we're running.
                callback = self.__ProgressCallback
            else:
                # Otherwise no progress messages.
                callback = None
                
            # Run the tests.
            results = engine.RunTests(test_ids, context, callback)

            run_test_ids = results.keys()
            # Summarize outcomes.
            if summary_file is not None:
                self.__WriteSummary(test_ids, results, outcomes, summary_file)
                # Close it unless it's standard output.
                if summary_file is not sys.stdout:
                    summary_file.close()
            # Write out results.
            if result_file is not None:
                self.__WriteResults(test_ids, results, result_file)
                # Close it unless it's standard output.
                if result_file is not sys.stdout:
                    result_file.close()
        except ValueError, test_id:
            raise RuntimeError, qm.error("missing test id", test_id=test_id)
                                                    

    def __ProgressCallback(self, message):
        """Display testing progress.

        'message' -- A message indicating testing progress."""

        self.__output.write(message)
        self.__output.flush()


    def __ExecuteEdit(self, output):
        """Handle the edit command."""
        
        # FIXME: This assumes the database is an 'XmlDatabase'.  That's
        # OK for now, since we'll have a GUI editing system later.

        database = self.GetDatabase()

        # Make sure an argument was specified.  The argument is the ID
        # of test to edit.
        if len(self.__arguments) != 1:
            raise qm.cmdline.CommandError, qm.error("no id for edit")
        # Make sure the argument corresponds to an existing test.
        test_id = self.__arguments[0]
        if not database.HasTest(test_id):
            raise qm.cmdline.CommandError, qm.error("unknown id",
                                                    test_id=test_id)
        self.__EditTest(test_id)


    def __EditTest(self, test_id):
        """Start an editing operation on test 'test_id'."""
        
        database = self.GetDatabase()
        # Obtain the full path to the test file.
        test_path = database.TestIdToPath(test_id, absolute=1)

        # If the user specified an 'xml_editor' in the rc file, use
        # that.
        editor = qm.rc.Get("xml_editor", None)
        if editor is not None:
            pass
        # Extract the user's perferred editor from the environment, if
        # it's specified there.
        elif os.environ.has_key("EDITOR"):
            # FIXME: Do something else on Windows?  Perhaps look up the
            # association with .txt or .xml files in the registry?
            editor = os.environ["EDITOR"]
        else:
            # Otherwise use the One True Program.
            # FIXME: Use notepad for Windows?
            editor = "/usr/bin/emacs"

        # Invoke the editor in the usual way, passing the edited file's
        # path as the command argument.
        os.system("%s %s" % (editor, test_path))


    def __ExecuteServer(self, output):
        """Process the server command."""

        # Get the port number specified by a command option, if any.
        # Otherwise use a default value.
        port_number = self.GetCommandOption("port", default=8000)
        try:
            port_number = int(port_number)
        except ValueError:
            raise qm.cmdline.CommandError, qm.error("bad port number")
        # Get the local address specified by a command option, if any.
        # If not was specified, use the empty string, which corresponds
        # to all local addresses.
        address = self.GetCommandOption("address", default="")
        # Was a log file specified?
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
        # Start the server.
        web.web.start_server(port_number, address, log_file)
    
    
    def __ExecuteTemplate(self, output):
        database = self.GetDatabase()
        # Make sure two arguments were specified.  The arguments are the
        # class name and the ID of the new test.
        if len(self.__arguments) != 2:
            raise qm.cmdline.CommandError, qm.error("missing arg for template")
        test_class_name, test_id = self.__arguments
        try:
            # Construct an empty test instance.
            test = base.make_new_test(test_class_name, test_id)
        except ValueError:
            raise RuntimeError, qm.error("test class not fully specified")
        except ImportError:
            raise RuntimeError, qm.error("invalid class",
                                         class_name=test_class_name)
        # Write it out.
        database.WriteTest(test, comments=1)
        # Let the user edit it immediately.
        self.__EditTest(test_id)


    def __WriteSummary(self, test_ids, results, expected_outcomes, output):
        """Generate test result summary.

        'test_ids' -- The test IDs that were requested for the test run.

        'results' -- A mapping from test ID to result for tests that
        were actually run.

        'expected_outcomes' -- A map from test IDs to expected outcomes,
        or 'None' if there are no expected outcomes.

        'output' -- A file object to which to write the summary."""

        def divider(text):
            return "--- %s %s\n\n" % (text, "-" * (73 - len(text)))

        output.write("\n")
        output.write(divider("STATISTICS"))
        num_tests = len(results)
        output.write("  %6d        tests total\n\n" % num_tests)

        if expected_outcomes is not None:
            # Initialize a map with which we will count the number of
            # tests with each unexpected outcome.
            count_by_unexpected = {}
            for outcome in base.Result.outcomes:
                count_by_unexpected[outcome] = 0
            # Also, we'll count the number of tests that resulted in the
            # expected outcome, and the number for which we have no
            # expected outcome.
            count_expected = 0
            count_no_outcome = 0
            # Count tests by expected outcome.
            for test_id in results.keys():
                result = results[test_id]
                outcome = result.GetOutcome()
                # Do we have an expected outcome for this test?
                if expected_outcomes.has_key(test_id):
                    # Yes.
                    expected_outcome = expected_outcomes[test_id]
                    if outcome == expected_outcome:
                        # Outcome as expected.
                        count_expected = count_expected + 1
                    else:
                        # Unexpected outcome.  Count by actual (not
                        # expected) outcome.
                        count_by_unexpected[outcome] = \
                            count_by_unexpected[outcome] + 1
                else:
                    # No expected outcome for this test.
                    count_no_outcome = count_no_outcome + 1

            output.write("  %6d (%3.0f%%) tests as expected\n"
                         % (count_expected,
                            (100. * count_expected) / num_tests))
            for outcome in base.Result.outcomes:
                count = count_by_unexpected[outcome]
                if count > 0:
                    output.write("  %6d (%3.0f%%) tests unexpected %s\n"
                                 % (count, (100. * count) / num_tests,
                                    outcome))
            if count_no_outcome > 0:
                output.write("  %6d (%3.0f%%) tests with no "
                             "expected outcomes\n"
                             % (count_no_outcome,
                                (100. * count_no_outcome) / num_tests))
            output.write("\n")

        # Initialize a map with which we will count the number of tests
        # with each outcome.
        count_by_outcome = {}
        for outcome in base.Result.outcomes:
            count_by_outcome[outcome] = 0
        # Count tests by outcome.
        for result in results.values():
            outcome = result.GetOutcome()
            count_by_outcome[outcome] = count_by_outcome[outcome] + 1
        # Summarize these counts.
        for outcome in base.Result.outcomes:
            count = count_by_outcome[outcome]
            if count > 0:
                output.write("  %6d (%3.0f%%) tests %s\n"
                             % (count, (100. * count) / num_tests, outcome))
        output.write("\n")

        # If we have been provided with expected outcomes, report each
        # test whose outcome doesn't match the expected outcome.
        unexpected_count = 0
        if expected_outcomes is not None:
            output.write(divider("TESTS WITH UNEXPECTED OUTCOMES"))
            # Scan over tests.
            for test_id in results.keys():
                result = results[test_id]
                outcome = result.GetOutcome()
                if not expected_outcomes.has_key(test_id):
                    # No expected outcome for this test; skip it.
                    continue
                expected_outcome = expected_outcomes[test_id]
                if outcome == expected_outcome:
                    # The outcome of this test is as expected; move on.
                    continue
                # Keep track of the number of tests with unexpected
                # outcomes. 
                unexpected_count = unexpected_count + 1
                # This test produced an unexpected outcome, so report it.
                output.write("  %-32s: %-8s [expected %s]\n"
                             % (test_id, outcome, expected_outcome))
            if unexpected_count == 0:
                output.write("  (None)\n")
            output.write("\n")

        output.write(divider("TESTS THAT DID NOT PASS"))
        non_passing_count = 0
        for test_id in results.keys():
            result = results[test_id]
            outcome = result.GetOutcome()
            extra = ""
            if outcome == base.Result.PASS:
                # Don't list tests that passed.
                continue
            # Keep count of how many didn't pass.
            non_passing_count = non_passing_count + 1
            if outcome == base.Result.UNTESTED:
                # If the test was not run, try to give some indication
                # of why.
                if result.has_key("failed_prerequisite"):
                    prerequisite = result["failed_prerequisite"]
                    prerequisite_outcome = results[prerequisite].GetOutcome()
                    extra = "[%s was %s]" \
                            % (prerequisite, prerequisite_outcome)
                elif result.has_key("failed_setup_action"):
                    action_id = result["failed_setup_action"]
                    extra = "[setup %s failed]" % action_id
            elif outcome == base.Result.FAIL \
                 or outcome == base.Result.ERROR:
                # If the result has a cause property, use it.
                if result.has_key("cause"):
                    extra = "[%s]" % result["cause"]
            output.write("  %-32s: %-8s %s\n" % (test_id, outcome, extra))

        if non_passing_count == 0:
            output.write("  (None)\n")
        output.write("\n")


    def __WriteResults(self, test_ids, results, output):
        """Generate full test results in XML format.

        'test_ids' -- The test IDs that were requested for the test run.

        'results' -- A mapping from test ID to result for tests that
        were actually run.

        'output' -- A file object to which to write the results."""

        document = qm.xmlutil.create_dom_document(
            public_id="-//Software Carpentry//QMTest Result V0.1//EN",
            dtd_file_name="result.dtd",
            document_element_tag="results"
            )
        # Add a result element for each test that was run.
        for test_id in results.keys():
            result = results[test_id]
            result_element = result.MakeDomNode(document)
            document.documentElement.appendChild(result_element)
        # Generate output.
        qm.xmlutil.write_dom_document(document, output)



########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
