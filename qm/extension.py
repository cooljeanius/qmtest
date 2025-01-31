########################################################################
#
# File:   extension.py
# Author: Mark Mitchell
# Date:   07/31/2002
#
# Contents:
#   Extension
#
# Copyright (c) 2002, 2003 by CodeSourcery, LLC.  All rights reserved. 
#
########################################################################

########################################################################
# Imports
########################################################################

import os.path
import qm
from qm.fields import Field
import io
import tokenize
import xml

########################################################################
# Classes
########################################################################

class Extension(object, metaclass=Type):
    """A class derived from 'Extension' is a QM extension.

    A variety of different classes are derived from 'Extension'.  All
    of these classes can be derived from by users to produce
    customized QM extensions.

    'Extension' is an abstract class."""

    class Type(type):

        def __init__(cls, name, bases, dict):
            """Generate an '_argument_dictionary' holding all the
            'Field' objects.  Then replace 'Field' objects by their
            values for convenient use inside the code."""

            # List all base classes that are themselves of type Extension.
            #
            # 'Extension' isn't known at this point so all we can do to find
            # Extension base classes is test whether __metaclass__ is defined
            # and if so, whether it is a base class of the metaclass of cls.
            type = cls.__metaclass__
            def is_extension(base):
                metaclass = getattr(base, '__metaclass__', None)
                return metaclass and issubclass(type, metaclass)

            hierarchy = [base for base in bases if is_extension(base)]

            parameters = {}
            for c in hierarchy:
                parameters.update(c._argument_dictionary)
            # Now set parameters from class variables of type 'Field'.
            for key, field in dict.items():
                if isinstance(field, Field):
                    field.SetName(key)
                    parameters[key] = field

            # For backward compatibility, inject all members of the
            # 'arguments' list into the dict, if it is indeed a list of fields.
            arguments = dict.get('arguments', [])
            if (type(arguments) is list and
                len(arguments) > 0 and
                isinstance(arguments[0], Field)):
                for field in arguments:
                    # Only allow name collisions between arguments and
                    # class variables if _allow_arg_names_matching_class_vars
                    # evaluates to True.
                    if (hasattr(cls, field.GetName())
                        and field.GetName() not in cls._argument_dictionary
                        and not cls._allow_arg_names_matching_class_vars):
                        raise qm.common.QMException(qm.error("ext arg name matches class var",
                                       class_name = name,
                                       argument_name = field.GetName()))
                    parameters[field.GetName()] = field

            setattr(cls, '_argument_dictionary', parameters)
            setattr(cls, '_argument_list', list(parameters.values()))

            # Finally set default values.
            for i in parameters:
                setattr(cls, i, parameters[i].GetDefaultValue())

    
    arguments = []
    """A list of the arguments to the extension class.

    Each element of this list should be an instance of 'Field'.  The
    'Field' instance describes the argument.

    Derived classes may redefine this class variable.  However,
    derived classes should not explicitly include the arguments from
    base classes; QMTest will automatically combine all the arguments
    found throughout the class hierarchy."""

    kind = None
    """A string giving kind of extension is implemented by the class.

    This field is used in an application-specific way; for example,
    QMTest has 'test' and 'target' extension classes."""
    
    _argument_list = None
    """A list of all the 'Field's in this class.

    This list combines the complete list of 'arguments'.  'Field's
    appear in the order reached by a pre-order breadth-first traversal
    of the hierarchy, starting from the most derived class."""
    
    _argument_dictionary = None
    """A map from argument names to 'Field' instances.

    A map from the names of arguments for this class to the
    corresponding 'Field'."""

    _allow_arg_names_matching_class_vars = None
    """True if it is OK for fields to have the same name as class variables.

    If this variable is set to true, it is OK for the 'arguments' to
    contain a field whose name is the same as a class variable.  That
    makes the 'default_value' handling for fields fail, and is
    generally confusing.

    This module no longer allows such classes, unless this variable is
    set to true.  That permits legacy extension classes to continue
    working, while preventing new extension classes from making the
    same mistake."""

    
    def __init__(self, **args):
        """Construct a new 'Extension'.

        'args': Keyword arguments providing values for Extension parameters.
        The values should be appropriate for the corresponding fields.
        Derived classes must pass along any unrecognized keyword
        arguments to this method so that additional arguments
        can be added in the future without necessitating changes to
        derived classes.  

        This method will place all of the arguments into this objects
        instance dictionary.
        
        Derived classes may override this method, but should call this
        method during their processing."""

        # Make sure that all the arguments actually correspond to
        # 'Field's for this class.
        if __debug__:
            dictionary = get_class_arguments_as_dictionary(self.__class__)
            for a, v in list(args.items()):
                if a not in dictionary:
                    raise AttributeError(a)
        
        # Remember the arguments provided.
        self.__dict__.update(args)

    def __getattr__(self, name):

        # Perhaps a default value for a class argument should be used.
        field = get_class_arguments_as_dictionary(self.__class__).get(name)
        if field is None:
            raise AttributeError(name)
        return field.GetDefaultValue()


    def GetClassName(self):
        """Return the name of the extension class.

        returns -- A string giving the name of this etension class."""

        return get_extension_class_name(self.__class__)

        
    def GetExplicitArguments(self):
        """Return the arguments to this extension instance.

        returns -- A dictionary mapping argument names to their
        values.  Computed arguments are ommitted from the
        dictionary."""
        
        # Get all of the arguments.
        arguments = get_class_arguments_as_dictionary(self.__class__)
        # Determine which subset of the 'arguments' have been set
        # explicitly.
        explicit_arguments = {}
        for name, field in list(arguments.items()):
            # Do not record computed fields.
            if field.IsComputed():
                continue
            if name in self.__dict__:
                explicit_arguments[name] = self.__dict__[name]

        return explicit_arguments

        
    def MakeDomElement(self, document, element = None):
        """Create a DOM node for 'self'.

        'document' -- The DOM document that will contain the new
        element.
        
        'element' -- If not 'None' the extension element to which items
        will be added.  Otherwise, a new element will be created by this
        function.
        
        returns -- A new DOM element corresponding to an instance of the
        extension class.  The caller is responsible for attaching it to
        the 'document'."""

        return make_dom_element(self.__class__,
                                self.GetExplicitArguments(),
                                document, element)


    def MakeDomDocument(self):
        """Create a DOM document for 'self'.

        'extension_class' -- A class derived from 'Extension'.

        'arguments' -- The arguments to the extension class.
        
        returns -- A new DOM document corresponding to an instance of the
        extension class."""
        
        document = qm.xmlutil.create_dom_document(
            public_id = "Extension",
            document_element_tag = "extension"
            )
        self.MakeDomElement(document, document.documentElement)
        return document


    def Write(self, file):
        """Write an XML description of 'self' to a file.
        
        'file' -- A file object to which the data should be written."""
        
        document = self.MakeDomDocument()
        document.writexml(file)
                                
        
                
########################################################################
# Functions
########################################################################

def get_class_arguments(extension_class):
    """Return the arguments associated with 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.
    
    returns -- A list of 'Field' objects containing all of the
    arguments in the class hierarchy."""

    assert issubclass(extension_class, Extension)
    return extension_class._argument_list        


def get_class_arguments_as_dictionary(extension_class):
    """Return the arguments associated with 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.

    returns -- A dictionary mapping argument names to 'Field'
    objects.  The dictionary contains all of the arguments in the
    class hierarchy."""

    assert issubclass(extension_class, Extension)
    return extension_class._argument_dictionary
        

def get_class_description(extension_class, brief=0):
    """Return a brief description of the extension class 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.
    
    'brief' -- If true, return a brief (one-line) description of the
    extension class.
    
    returns -- A structured text description of 'extension_class'."""

    assert issubclass(extension_class, Extension)

    # Extract the class's doc string.
    doc_string = extension_class.__doc__
    if doc_string is not None:
        if brief:
            doc_string = qm.structured_text.get_first(doc_string)
        return doc_string
    else:
        return "&nbsp;"
    

def get_extension_class_name(extension_class):
    """Return the name of 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.
    
    returns -- The name of 'extension_class'.  This is the name that
    is used when users refer to the class."""

    assert issubclass(extension_class, Extension)

    module = extension_class.__module__.split(".")[-1]
    return module + "." + extension_class.__name__
    
    
def validate_arguments(extension_class, arguments):
    """Validate the 'arguments' to the 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.

    'arguments' -- A dictionary mapping argument names (strings) to
    values (strings).

    returns -- A dictionary mapping 'Field's to values.
    
    Check that each of the 'arguments' is a valid argument to
    'extension_class'.  If so, the argumets are converted as required
    by the 'Field', and the dictionary returned contains the converted
    values.  Otherwise, an exception is raised."""

    assert issubclass(extension_class, Extension)

    # We have not converted any arguments yet.
    converted_arguments = {}
    
    # Check that there are no arguments that do not apply to this
    # class.
    class_arguments = get_class_arguments_as_dictionary(extension_class)
    for name, value in list(arguments.items()):
        field = class_arguments.get(name)
        if not field:
            raise qm.QMException(qm.error("unexpected extension argument",
                           name = name,
                           class_name \
                               = get_extension_class_name(extension_class)))
        if field.IsComputed():
            raise qm.QMException(qm.error("value provided for computed field",
                           name = name,
                           class_name \
                               = get_extension_class_name(extension_class)))
        converted_arguments[name] = field.ParseTextValue(value)

    return converted_arguments


def make_dom_element(extension_class, arguments, document, element = None):
    """Create a DOM node for an instance of 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.

    'arguments' -- The arguments to the extension class.

    'document' -- The DOM document that will contain the new
    element.

    'element' -- If not 'None' the extension element to which items
    will be added.  Otherwise, a new element will be created by this
    function.

    returns -- A new DOM element corresponding to an instance of the
    extension class.  The caller is responsible for attaching it to
    the 'document'."""

    # Get the dictionary of 'Field's for this extension class.
    field_dictionary = get_class_arguments_as_dictionary(extension_class)

    # Create the element.
    if element:
        extension_element = element
    else:
        extension_element = document.createElement("extension")
    # Create an attribute describing the kind of extension.
    if extension_class.kind:
        extension_element.setAttribute("kind", extension_class.kind)
    # Create an attribute naming the extension class.
    extension_element.setAttribute("class",
                                   get_extension_class_name(extension_class))
    # Create an element for each of the arguments.
    for argument_name, value in list(arguments.items()):
        # Skip computed arguments.
        field = field_dictionary[argument_name]
        if field.IsComputed():
            continue
        # Create a node for the argument.
        argument_element = document.createElement("argument")
        # Store the name of the field.
        argument_element.setAttribute("name", argument_name)
        # Store the value.
        argument_element.appendChild(field.MakeDomNodeForValue(value,
                                                               document))
        # Add the attribute node to the target.
        extension_element.appendChild(argument_element)

    return extension_element


def make_dom_document(extension_class, arguments):
    """Create a DOM document for an instance of 'extension_class'.

    'extension_class' -- A class derived from 'Extension'.

    'arguments' -- The arguments to the extension class.

    returns -- A new DOM document corresponding to an instance of the
    extension class."""

    document = qm.xmlutil.create_dom_document(
            public_id = "Extension",
            document_element_tag = "extension"
            )
    make_dom_element(extension_class, arguments, document,
                     document.documentElement)
    return document
    
        

def write_extension_file(extension_class, arguments, file):
    """Write an XML description of an extension to 'file'.

    'extension_class' -- A class derived from 'Extension'.

    'arguments' -- A dictionary mapping argument names to values.

    'file' -- A file object to which the data should be written."""

    document = make_dom_document(extension_class, arguments)
    document.writexml(file)

    
    
def parse_dom_element(element, class_loader, attachment_store = None):
    """Parse a DOM node representing an instance of 'Extension'.

    'element' -- A DOM node, of the format created by
    'make_dom_element'.

    'class_loader' -- A callable.  The callable will be passed the
    name of the extension class and must return the actual class
    object.

    'attachment_store' -- The 'AttachmentStore' in which attachments
    can be found.

    returns -- A pair ('extension_class', 'arguments') containing the
    extension class (a class derived from 'Extension') and the
    arguments (a dictionary mapping names to values) stored in the
    'element'."""

    # Determine the name of the extension class.
    class_name = element.getAttribute("class")
    # DOM nodes created by earlier versions of QMTest encoded the
    # class name in a separate element, so look there for backwards
    # compatbility.
    if not class_name:
        class_elements = element.getElementsByTagName("class")
        if not class_elements:
            class_elements = element.getElementsByTagName("class-name")
        class_element = class_elements[0]
        class_name = qm.xmlutil.get_dom_text(class_element)
    # Load it.
    extension_class = class_loader(class_name)

    # Get the dictionary of 'Field's for this extension class.
    field_dictionary = get_class_arguments_as_dictionary(extension_class)

    # Collect the arguments to the extension class.
    arguments = {}
    for argument_element in element.getElementsByTagName("argument"):
        name = argument_element.getAttribute("name")
        # Find the corresponding 'Field'.
        field = field_dictionary[name]
        # Get the DOM node for the value.  It is always a element.
        value_node \
            = [e for e in argument_element.childNodes if e.nodeType == xml.dom.Node.ELEMENT_NODE][0]
        # Parse the value.
        value = field.GetValueFromDomNode(value_node, attachment_store)
        # Python does not allow keyword arguments to have Unicode
        # values, so we convert the name to an ordinary string.
        arguments[str(name)] = value
    
    return (extension_class, arguments)


def read_extension_file(file, class_loader, attachment_store = None):
    """Parse a file describing an extension instance.

    'file' -- A file-like object from which the extension instance
    will be read.

    'class_loader' --  A callable.  The callable will be passed the
    name of the extension class and must return the actual class
    object.
    
    'attachment_store' -- The 'AttachmentStore' in which attachments
    can be found.

    returns -- A pair ('extension_class', 'arguments') containing the
    extension class (a class derived from 'Extension') and the
    arguments (a dictionary mapping names to values) stored in the
    'element'."""

    document = qm.xmlutil.load_xml(file)
    return parse_dom_element(document.documentElement,
                             class_loader,
                             attachment_store)


def parse_descriptor(descriptor, class_loader, extension_loader = None):
    """Parse a descriptor representing an instance of 'Extension'.

    'descriptor' -- A string representing an instance of 'Extension'.
    The 'descriptor' has the form 'class(arg1 = "val1", arg2 = "val2",
    ...)'.  The arguments and the parentheses are optional.

    'class_loader' -- A callable that, when passed the name of the
    extension class, will return the actual Python class object.

    'extension_loader' -- A callable that loads an existing extension
    given the name of that extension and returns a tuple '(class,
    arguments)' where 'class' is a class derived from 'Extension'.  If
    'extension_loader' is 'None', or if the 'class' returned is
    'None', then if a file exists named 'class', the extension is read
    from 'class' as XML.  Any arguments returned by the extension
    loader or read from the file system are overridden by the
    arguments explicitly provided in the descriptor.

    returns -- A pair ('extension_class', 'arguments') containing the
    extension class (a class derived from 'Extension') and the
    arguments (a dictionary mapping names to values) stored in the
    'element'.  The 'arguments' will have already been processed by
    'validate_arguments' by the time they are returned."""

    # Look for the opening parenthesis.
    open_paren = descriptor.find('(')
    if open_paren == -1:
        # If there is no opening parenthesis, the descriptor is simply
        # the name of an extension class.
        class_name = descriptor
    else:
        # The class name is the part of the descriptor up to the
        # parenthesis.
        class_name = descriptor[:open_paren]

    # Load the extension, if it already exists.
    extension_class = None
    if extension_loader:
        extension = extension_loader(class_name)
        if extension:
            extension_class = extension.__class__
            orig_arguments = extension.GetExplicitArguments()
    if not extension_class:
        if os.path.exists(class_name):
            extension_class, orig_arguments \
                = read_extension_file(open(filename), class_loader)
        else:
            extension_class = class_loader(class_name)
            orig_arguments = {}

    arguments = {}
    
    # Parse the arguments.
    if open_paren != -1:
        # Create a file-like object for the remainder of the string.
        arguments_string = descriptor[open_paren:]
        s = io.StringIO(arguments_string)
        # Use the Python tokenizer to process the remainder of the
        # string.
        g = tokenize.generate_tokens(s.readline)
        # Read the opening parenthesis.
        tok = next(g)
        assert tok[0] == tokenize.OP and tok[1] == "("
        need_comma = 0
        # Keep going until we find the closing parenthesis.
        while 1:
            tok = next(g)
            if tok[0] == tokenize.OP and tok[1] == ")":
                break
            # All arguments but the first must be separated by commas.
            if need_comma:
                if tok[0] != tokenize.OP or tok[1] != ",":
                    raise qm.QMException(qm.error("invalid descriptor syntax",
                                   start = arguments_string[tok[2][1]:]))
                tok = next(g)
            # Read the argument name.
            if tok[0] != tokenize.NAME:
                raise qm.QMException(qm.error("invalid descriptor syntax",
                               start = arguments_string[tok[2][1]:]))
            name = tok[1]
            # Read the '='.
            tok = next(g)
            if tok[0] != tokenize.OP or tok[1] != "=":
                raise qm.QMException(qm.error("invalid descriptor syntax",
                               start = arguments_string[tok[2][1]:]))
            # Read the value.
            tok = next(g)
            if tok[0] != tokenize.STRING:
                raise qm.QMException(qm.error("invalid descriptor syntax",
                               start = arguments_string[tok[2][1]:]))
            # The token string will have surrounding quotes.  By
            # running it through "eval", we get at the underlying
            # value.
            value = eval(tok[1])
            arguments[name] = value
            # The next argument must be preceded by a comma.
            need_comma = 1
        # There shouldn't be anything left at this point.
        tok = next(g)
        if not tokenize.ISEOF(tok[0]):
            raise qm.QMException(qm.error("invalid descriptor syntax",
                           start = arguments_string[tok[2][1]:]))
    
    # Process the arguments.
    arguments = validate_arguments(extension_class, arguments)
    # Use the explict arguments to override any specified in the file.
    orig_arguments.update(arguments)
    
    return (extension_class, orig_arguments)
