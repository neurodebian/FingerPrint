#!/usr/bin/python

from distutils.core import setup

#
# courtesy of Darren
# http://da44en.wordpress.com/2002/11/22/using-distutils/
#
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin, walk
import os

class TestCommand(Command):
    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        '''
        Finds all the tests modules in tests/, and runs them.
        '''
        testfiles = [ ]
        for t in glob(pjoin(self._dir, 'tests', '*.py')):
            if not t.endswith('__init__.py'):
                testfiles.append('.'.join(
                    ['tests', splitext(basename(t))[0]])
                )

        tests = TestLoader().loadTestsFromNames(testfiles)
        t = TextTestRunner(verbosity = 1)
        t.run(tests)


# 
# main configuration of distutils
# 
setup(
    name = 'FingerPrint',
    version = '1.00',
    description = 'This is my Python module.',

    author = 'Phil Papadopoulos',
    author_email =  'philip.papadopoulos@gmail.com',
    maintainer = 'Luca Clementi',
    maintainer_email =  'luca.clementi@gmail.com',
    #main package, most of the code is inside here
    packages = ['FingerPrint'],
    package_dir = {'FingerPrint': 'FingerPrint'},
    #needs this for detecting file type
    py_modules=['magic'],
    #the command line called by users    
    scripts=['scripts/fingerprint'],
    #additional command to build this distribution
    cmdclass = { 'test': TestCommand,  }
)


