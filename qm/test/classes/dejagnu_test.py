########################################################################
#
# File:   dejagnu_test.py
# Author: Mark Mitchell
# Date:   04/16/2003
#
# Contents:
#   DejaGNUTest
#
# Copyright (c) 2003 by CodeSourcery, LLC.  All rights reserved. 
#
# For license terms see the file COPYING.
#
########################################################################

########################################################################
# Imports
########################################################################

from   dejagnu_base import DejaGNUBase
import os
import qm
from   qm.common import QMException
from   qm.executable import RedirectedExecutable
from   qm.test.test import Test
from   qm.test.result import Result

########################################################################
# Classes
########################################################################

class DejaGNUTest(Test, DejaGNUBase):
    """A 'DejaGNUTest' emulates a DejaGNU test.

    See 'framework.exp' in the DejaGNU distribution for more
    information."""

    arguments = [
        qm.fields.AttachmentField(
            name="source_file",
            title="Source File",
            description="""The source file."""),
        ]

    PASS = "PASS"
    FAIL = "FAIL"
    XPASS = "XPASS"
    XFAIL = "XFAIL"
    WARNING = "WARNING"
    ERROR = "ERROR"
    UNTESTED = "UNTESTED"
    UNRESOLVED = "UNRESOLVED"
    UNSUPPORTED = "UNSUPPORTED"

    dejagnu_outcomes = (
        PASS, FAIL, XPASS, XFAIL, WARNING, ERROR, UNTESTED,
        UNRESOLVED, UNSUPPORTED
        )
    """The DejaGNU test outcomes."""
    
    outcome_map = {
        PASS : Result.PASS,
        FAIL : Result.FAIL,
        XPASS : Result.PASS,
        XFAIL : Result.FAIL,
        WARNING : Result.PASS,
        ERROR : Result.ERROR,
        UNTESTED : Result.UNTESTED,
        UNRESOLVED : Result.UNTESTED,
        UNSUPPORTED : Result.UNTESTED
        }
    """A map from DejaGNU outcomes to QMTest outcomes."""

    executable_timeout = 300
    """The number of seconds a program is permitted to run on the target."""

    RESULT_PREFIX = "DejaGNUTest.result_"
    """The prefix for DejaGNU result annotations.

    All results that would be generated by DejaGNU are inserted into
    the QMTest result as annotations beginning with this prefix.  The
    prefix is followed by an 1-indexed integer; earlier results are
    inserted with lower numbers."""

    class BuildExecutable(RedirectedExecutable):
        """A 'BuildExecutable' runs on the build machine.

        Classes derived from 'DejaGNUTest' may provide derived
        versions of this class."""

        def _StderrPipe(self):

            # Combine stdout/stderr into a single stream.
            return None


    def _GetTargetEnvironment(self, context):
        """Return additional environment variables to set on the target.

        'context' -- The 'Context' in which this test is running.
        
        returns -- A map from strings (environment variable names) to
        strings (values for those variables).  These new variables are
        added to the environment when a program executes on the
        target."""

        return {}
    

    def _RunBuildExecutable(self, context, result, file, args = [],
                            dir = None):
        """Run 'file' on the target.

        'context' -- The 'Context' in which this test is running.
        
        'result' -- The 'Result' of this test.
        
        'file' -- The path to the executable file.

        'args' -- The arguments to the 'file'.

        'dir' -- The directory in which the program should execute.

        returns -- A pair '(status, output)'.  The 'status' is the
        exit status from the command; the 'output' is the combined
        results of the standard output and standard error streams."""

        executable = self.BuildExecutable(self.executable_timeout)
        command = [file] + args
        index = self._RecordCommand(result, command)
        status = executable.Run(command, None, dir)
        output = executable.stdout
        self._RecordCommandOutput(result, index, status, output)

        return status, output

    
    def _RunTargetExecutable(self, context, result, file):
        """Run 'file' on the target.

        'context' -- The 'Context' in which this test is running.
        
        'result' -- The 'Result' of this test.
        
        'file' -- The path to the executable file.

        returns -- One of the 'dejagnu_outcomes'."""

        host = context['CompilerTable.target']
        index = self._RecordCommand(result, [file])
        environment = self._GetTargetEnvironment(context)
        status, output = host.Run(file, [], environment)
        self._RecordCommandOutput(result, index, status, output)
        # Figure out whether the execution was successful.
        if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
            outcome = self.PASS
        else:
            outcome = self.FAIL

        return outcome
        
        
    def _RecordDejaGNUOutcome(self, result, outcome, message,
                              expectation = None):
        """Record a DejaGNU outcome.

        'result' -- A 'Result' object.

        'outcome' -- One of the 'dejagnu_outcomes'.

        'message' -- A string, explaining the outcome.

        'expectation' -- If not 'None, the DejaGNU outcome that was
        expected."""

        # If the test was expected to fail, transform PASS or FAIL
        # into XPASS or XFAIL, respectively.
        if expectation == self.FAIL:
            if outcome == self.PASS:
                outcome = self.XPASS
            elif outcome == self.FAIL:
                outcome = self.XFAIL

        # Create an annotation corresponding to the DejaGNU outcome.
        key = "%s%d" % (self.RESULT_PREFIX, self.__next_result)
        self.__next_result += 1
        result[key] = outcome + ": " + message
        # If the test was passing until now, give it a new outcome.
        new_outcome = self.outcome_map[outcome]
        if (new_outcome
            and new_outcome != Result.PASS
            and result.GetOutcome() == Result.PASS):
            result.SetOutcome(new_outcome)
            result[Result.CAUSE] = message
        

    def _Unresolved(self, result, message):
        """Record an 'unresolved' DejaGNU outcome.

        This function is identical to 'RecordDejaGNUOutcome', except
        that the 'outcome' is always 'UNRESOLVED'."""

        self._RecordDejaGNUOutcome(result, self.UNRESOLVED, message)

        
        
    def _Error(self, message):
        """Raise an exception indicating an error in the test.

        'message' -- A description of the problem.

        This function is used when the original Tcl code in DejaGNU
        would have used the Tcl 'error' primitive.  These situations
        indicate problems with the test itself, such as incorrect
        usage of special test commands."""

        raise DejaGNUError, message

        
    def _GetSourcePath(self):
        """Return the path to the primary source file.

        returns -- A string giving the path to the primary source
        file."""

        return self.source_file.GetDataFile()


    def _GetBuild(self, context):
        """Return the GNU triplet corresponding to the build machine.
        
        'context' -- The 'Context' in which the test is running.
        
        returns -- The GNU triplet corresponding to the target
        machine, i.e,. the machine on which the compiler will run."""

        return context.get("DejaGNUTest.build") or self._GetTarget(context)

    
    def _GetTarget(self, context):
        """Return the GNU triplet corresponding to the target machine.

        'context' -- The 'Context' in which the test is running.
        
        returns -- The GNU triplet corresponding to the target
        machine, i.e,. the machine on which the programs generated by
        the compiler will run."""

        return context["DejaGNUTest.target"]
    

    def _IsNative(self, context):
        """Returns true if the build and target machines are the same.

        'context' -- The 'Context' in which this test is running.

        returns -- True if this test is runing "natively", i.e., if
        the build and target machines are the same."""

        return self._GetTarget(context) == self._GetBuild(context)
    
        
    def _SetUp(self, context):
        """Prepare to run a test.

        'context' -- The 'Context' in which this test will run.

        This method may be overridden by derived classes, but they
        must call this version."""

        super(DejaGNUTest, self)._SetUp(context)
        # The next DejaGNU result will be the first.
        self.__next_result = 1

        
    def _ParseTclWords(self, s, variables = {}):
        """Separate 's' into words, in the same way that Tcl would.

        's' -- A string.

        'variables' -- A map from variable names to values.  If Tcl
        variable substitutions are encountered in 's', the
        corresponding value from 'variables' will be used.

        returns -- A sequence of strings, each of which is a Tcl
        word.

        Command substitution is not supported and results in an
        exceptions.  Invalid inputs (like the string consisting of a
        single quote) also result in exceptions.
        
        See 'Tcl and the Tk Toolkit', by John K. Ousterhout, copyright
        1994 by Addison-Wesley Publishing Company, Inc. for details
        about the syntax of Tcl."""

        # There are no words yet.
        words = []
        # There is no current word.
        word = None
        # We are not processing a double-quoted string.
        in_double_quoted_string = 0
        # Nor are we processing a brace-quoted string.
        in_brace_quoted_string = 0
        # Iterate through all of the characters in s.
        n = 0
        while n < len(s):
            # See what the next character is.
            c = s[n]
            # A "$" indicates variable substitution.
            if c == "$" and not in_brace_quoted_string:
                k = n + 1
                if s[k] == "{":
                    # The name of the variable is enclosed in braces.
                    start = k + 1
                    finish = s.index("}", start)
                    n = finish + 1
                    var = s[start:finish]
                    v = variables[var]
                else:
                    # The following letters, numbers, and underscores make
                    # up the variable name.
                    start = k
                    while (k < len(s)
                           and (s[k].isalnum() or s[k] == "_")):
                        k += 1
                    n = k
                    finish = k
                    if start < finish:
                        var = s[start:finish]
                        v = variables[var]
                    else:
                        v = "$"
                if word is None:
                    word = v
                else:
                    word += v
                continue
            # A "[" indicates command substitution.
            elif (c == "[" and not in_brace_quoted_string
                  and n < len(s) + 1 and s[n + 1] != "]"):
                raise QMException, "Tcl command substitution is unsupported."
            # A double-quote indicates the beginning of a double-quoted
            # string.
            elif c == '"' and not in_brace_quoted_string:
                # We are now entering a new double-quoted string, or
                # leaving the old one.
                in_double_quoted_string = not in_double_quoted_string
                # Skip the quote.
                n += 1
                # The quote starts the word.
                if word is None:
                    word = ""
            # A "{" indicates the beginning of a brace-quoted string.
            elif c == '{' and not in_double_quoted_string:
                # If that's not the opening quote, add it to the
                # string.
                if in_brace_quoted_string:
                    if word is not None:
                        word = word + "{"
                    else:
                        word = "{"
                # The quote starts the word.
                if word is None:
                    word = ""
                # We are entering a brace-quoted string.
                in_brace_quoted_string += 1
                # Skip the brace.
                n += 1
            elif c == '}' and in_brace_quoted_string:
                # Leave the brace quoted string.
                in_brace_quoted_string -= 1
                # Skip the brace.
                n += 1
                # If that's not the closing quote, add it to the
                # string.
                if in_brace_quoted_string:
                    if word is not None:
                        word = word + "}"
                    else:
                        word = "}"
            # A backslash-newline is translated into a space.
            elif c == '\\' and len(s) > 1 and s[1] == '\n':
                # Skip the backslash and the newline.
                n += 2
                # Now, skip tabs and spaces.
                while n < len(s) and (s[n] == ' ' or s[n] == '\t'):
                    n += 1
                # Now prepend one space.
                n -= 1
                s[n] = " "
            # A backslash indicates backslash-substitution.
            elif c == '\\' and not in_brace_quoted_string:
                # There should be a character following the backslash.
                if len(s) == 1:
                    raise QMException, "Invalid Tcl string."
                # Skip the backslash.
                n += 1
                # See what the next character is.
                c = s[n]
                # If it's a control character, use the same character
                # in Python.
                if c in ["a", "b", "f", "n", "r", "t", "v"]:
                    c = eval('"\%s"' % c)
                    n += 1
                # "\x" indicates a hex literal.
                elif c == "x":
                    if (n < len(s)
                        and s[n + 1] in ["0", "1", "2", "3", "4", "5",
                                         "6", "7", "8", "9", "a", "b",
                                         "c", "d", "e", "f"]):
                        raise QMException, "Unsupported Tcl escape."
                    n += 1
                # "\d" where "d" is a digit indicates an octal literal.
                elif c.isdigit():
                    raise QMException, "Unsupported Tcl escape."
                # Any other character just indicates the character
                # itself.
                else:
                    n += 1
                # Add it to the current word.
                if word is not None:
                    word = word + c
                else:
                    word = c
            # A space or tab indicates a word separator.
            elif ((c == ' ' or c == '\t')
                  and not in_double_quoted_string
                  and not in_brace_quoted_string):
                # Add the current word to the list of words.
                if word is not None:
                    words.append(word)
                # Skip over the space.
                n += 1
                # Keep skipping while the leading character of s is
                # a space or tab.
                while n < len(s) and (s[n] == ' ' or s[n] == '\t'):
                    n += 1
                # Start the next word.
                word = None
            # Any other character is just added to the current word.
            else:
                if word is not None:
                    word = word + c
                else:
                    word = c
                n += 1

        # If we were working on a word when we reached the end of
        # the string, add it to the list.
        if word is not None:
            words.append(word)

        return words
