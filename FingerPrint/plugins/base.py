#!/usr/bin/python
#
# LC
#
# base class for the fingerprint plugin classes
#

import os
import magic
from subprocess import PIPE, Popen
import StringIO
import re
import ctypes


from FingerPrint.swirl import *



"""This is the base class that implement the interface that all the plugins subclasses 
should implement
"""



class PluginMount(type):
    """
    Insipired by Marty Alchin
    http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    """
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            cls.plugins = {}
        else:
            # This must be a plugin implementation, which should be registered.
            # we use a dictionary here for fast lookup during dependecy verification
            cls.plugins[cls.pluginName] = cls

    def get_plugins(cls):
        return cls.plugins


class PluginManager(object):
    """
    Super class of the various plugins. All the plugins should inherit from this class

    Plugins implementing this reference should provide the following attributes:

    pluginName: this must be a unique string representing the plugin name
    

    TODO write this 

    """

    __metaclass__ = PluginMount
    systemPath = []


    @classmethod
    def addSystemPaths(self, paths):
        """add additional path to the search for dependency """
        self.systemPath += paths

    @classmethod
    def isDepsatisfied(self, dependency):
        """verify that the dependency passed can be satified on this system
        and return True if so
        """
        #let get the plugin
        #TODO catch exception key not found
        plugin = self.plugins[dependency.getPluginName()]
        return plugin.isDepsatisfied( dependency )

    @classmethod
    def getSwirl(self, fileName):
        """helper function given a filename it return a Swirl 
        if the given plugin does not support the given fileName should just 
        return None
        ATT: only one plugin should return a SwirlFile for a given file
        """
        for key, plugin in self.plugins.iteritems():
            temp = plugin.getSwirl(fileName)
            if temp != None:
                return temp
        #nobady claimed the file let's make it a Data fil
        swirlFile = SwirlFile(fileName)
        swirlFile.type="Data"
        return swirlFile
 


class ElfPlugin(PluginManager):
    """this plugin manages all ELF file format"""

    pluginName="ELF"
 
    @classmethod
    def isDepsatisfied(self, dependency):
        """verify that the dependency passed can be satified on this system
        and return True if so
        """
        soname = dependency.depname.split('(')[0]
        try:
            #TODO this verify only the soname we need to check for version too!
            ctypes.cdll.LoadLibrary(soname) 
            return True
        except OSError:
            return False

        

    @classmethod
    def setDepsRequs(self, swirlFile):
        """given a SwirlFile object it add to it all the dependency and all 
        the provides to it """

        #may in the future we could also use 
        #objdump -p
        RPM_FIND_DEPS="/usr/lib/rpm/find-requires"
        RPM_FIND_PROV="/usr/lib/rpm/find-provides"

        #find deps
        p = Popen([RPM_FIND_DEPS], stdin=PIPE, stdout=PIPE)
        grep_stdout = p.communicate(input=swirlFile.path)[0]
        for line in grep_stdout.split('\n'):
            if len(line) > 0:
                newDep = Dependency( line )
                newDep.setPluginName( self.pluginName )
                swirlFile.addDependency( newDep )
                #i need to take the parenthesis out of the game
                tempList = re.split('\(|\)',line)
                if len(tempList) > 2:
                    #set the 32/64 bits 
                    #probably unecessary
                    if tempList[3].find("64bit") >= 0 :
                        newDep.set64bits()
                    elif tempList[3].find("32bit") >= 0 :
                        newDep.set32bits()
        #find provides
        p = Popen([RPM_FIND_PROV], stdin=PIPE, stdout=PIPE)
        grep_stdout = p.communicate(input=swirlFile.path)[0]
        for line in grep_stdout.split('\n'):
            if len(line) > 0 :
                newProv = Provide(line)
                newProv.setPluginName( self.pluginName )
                swirlFile.addProvide(newProv)
        


    @classmethod
    def getSwirl(self, fileName):
        """helper function given a filename it return a Swirl 
        if the given plugin does not support the given fileName should just 
        return None
        ATT: only one plugin should return a SwirlFile for a given file
        """
        m=magic.Magic()
        typeStr=m.from_file( fileName )
        #for now all the files are dynamic
        if typeStr.startswith( 'ELF ' ):
            swirlFile = SwirlFile( fileName )
            swirlFile.setPluginName( self.pluginName )
            swirlFile.dyn = True
        else:
            #this is not our business
            return None
        #do we really need this?
        if typeStr.startswith('ELF 64-bit LSB executable'): #and os.access(fileName, os.X_OK):
            #ELF 64 bit
            swirlFile.set64bits()
            swirlFile.setExecutable()
        elif typeStr.startswith('ELF 32-bit LSB executable'):
            #ELF 32 bit
            swirlFile.set32bits()
            swirlFile.setExecutable()
        elif typeStr.startswith('ELF 64-bit LSB shared object'):
            #shared library 64
            swirlFile.set64bits()
            swirlFile.setShared()
        elif typeStr.startswith('ELF 32-bit LSB shared object'):
            #shared library 32
            swirlFile.set32bits()
            swirlFile.setShared()
        #add deps and provs
        self.setDepsRequs(swirlFile)
        return swirlFile

       
