#
# Copyright 2023 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
# convertDoxygen.py
#
# A utility to convert Doxygen XML files into another format, such as
# Python docstrings.
#
# This utility is designed to make it easy to plug in new output
# formats. This is done by creating new cdWriterXXX.py modules. A
# writer module must provide a class called Writer with methods,
# getDocString() and generate(). See cdWriterDocstring.py for an example.
#

import importlib
import os
import pickle
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))
from doxygenlib.cdParser import *
from doxygenlib.cdUtils import *

#
# Parse the global command line arguments (plugin may have more)
#
xml_file      = GetArgValue(['--input', '-i'])
xml_file_dir  = GetArgValue(['--inputDir'])
xml_index_file  = GetArgValue(['--inputIndex'])
output_file   = GetArgValue(['--output', '-o'])
output_format = GetArgValue(['--format', '-f'], "Docstring")
python_path = GetArgValue(['--pythonPath'])
dll_path = GetArgValue(['--dllPath'])
use_cached_parsing = GetArg(['--cacheParsing', '-c'])

SetDebugMode(GetArg(['--debug', '-d']))

if not (xml_file or xml_index_file) or not output_file or GetArg(['--help', '-h']):
    Usage()

packageName = GetArgValue(['--package', '-p'])
modules = GetArgValue(['--module', '-m'])
if not packageName:
    Error("Required option --package not specified")
if not modules:
    Error("Required option --module not specified")


module_list = [x for x in modules.split(",") if x]
output_files = []
for moduleName in module_list:
    if len(module_list) == 1 and output_file.endswith(".py"):
        module_output_file = output_file
    else:
        # For multiple-module use-case (or if output_file doesn't end with .py),
        # assume output_file is really an output path for the parent dir
        # (e.g. lib/python/pxr)
        module_output_dir = os.path.join(output_file, moduleName)
        module_output_file = os.path.join(module_output_dir, "__DOC.py")
    output_files.append(module_output_file)
assert len(output_files) == len(module_list)

# Delete existing __DOC.py files first so later when we load the module we
# don't also load in the old docstrings
for module_output_file in output_files:
    if os.path.isfile(module_output_file):
        os.remove(module_output_file)

#
# If caller specified an additional path for python libs (for loading USD
# modules, for example) add the path to sys.path
#
if (python_path != None):
    sys.path.append(python_path)

if dll_path != None and os.name == "nt":
    dll_paths = dll_path.replace("/", os.sep).split(";")
    for path in dll_paths:
        if os.path.isdir(path):
            os.add_dll_directory(path)
#
# Try to import the plugin module that creates the desired output
#
try:
    cdWriterModule = importlib.import_module(".cdWriter" + output_format, package="doxygenlib")
except ImportError:
    Error("No writer plugin exists for format '%s'" % output_format)
else:
    Writer = cdWriterModule.Writer

print("Converting Doxygen comments to %s format..." % output_format)

#
# Create a parser object to read the doxygen XML.
#
parser = Parser()

docList = None

if xml_index_file != None:
    pickle_path = xml_index_file + ".pickle"
else:
    pickle_path = xml_file + ".pickle"
#
# Parse the XML file, generate the doc structures (the writer
# plugin formats the docs)
#
if use_cached_parsing and os.path.isfile(pickle_path):
    try:
        with open(pickle_path, "rb") as picklefile:
            docList = pickle.load(picklefile)
        Debug("Read pre-parsed file: '%s'" % pickle_path)
    except Exception:
        Debug("Error reading pre-parsed file: '%s'" % pickle_path)
        Debug(traceback.format_exc())

if docList is None:
    if xml_index_file != None:
        if not parser.parseDoxygenIndexFile(xml_index_file):
            Error("Could not parse XML index file: %s" % xml_index_file)
    else:
        if not parser.parse(xml_file):
            Error("Could not parse XML file: %s" % xml_file)

#
# Traverse the list of DocElements from the parsed XML,
# load provided python module(s) and find matching python
# entities, and write matches to python docs output
#
for moduleName, module_output_file in zip(module_list, output_files):
    # Loop through module list and create a Writer for each module to
    # load and generate the doc strings for the specific module

    # Writer's constructor will verify provided package + module can be loaded
    writer = Writer(packageName, moduleName)
    Debug("Processing module %s" % moduleName)
    # Parser.traverse builds the docElement tree for all the
    # doxygen XML files, so we only need to call it once if we're
    # processing multiple modules
    if (docList is None):
        docList = parser.traverse(writer)
        Debug("Processed %d DocElements from doxygen XML" % len(docList))
        if use_cached_parsing:
            with open(pickle_path, "wb") as picklefile:
                pickle.dump(docList, picklefile)
    writer.generate(module_output_file, docList)

