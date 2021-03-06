#!/usr/bin/python
#
# LC
#
# base class for the fingerprint plugin classes
#

import os
from subprocess import PIPE, Popen
import StringIO
import re

from FingerPrint.swirl import SwirlFile, Dependency, Provide
from FingerPrint.plugins import PluginManager
from FingerPrint.utils import getOutputAsList

"""This is the implementation for ELF files
Requirements:
 - /usr/lib/rpm/find-requires /usr/lib/rpm/find-provides from rpm
 - lsconfig in the path

"""


class ElfPlugin(PluginManager):
    """this plugin manages all ELF file format"""

    pluginName="ELF"

    #internal
    _ldconfig_64bits = "x86-64"
    _pathCache = {}

    #may in the future we could also use 
    #objdump -p
    _RPM_FIND_DEPS=os.path.dirname( globals()["__file__"] ) + "/find-requires"
    _RPM_FIND_PROV=os.path.dirname( globals()["__file__"] ) + "/find-provides"


    @classmethod
    def isDepsatisfied(cls, dependency):
        """verify that the dependency passed can be satified on this system
        and return True if so
        """
        if cls.getPathToLibrary(dependency):
            return True
        else:
            return False


    @classmethod
    def getPathToLibrary(cls, dependency):
        """ given a dependency it find the path of the library which provides 
        that dependency """
        soname = dependency.getBaseName()
        if dependency.depname in cls._pathCache :
            return cls._pathCache[dependency.depname]
        #for each library we have in the system
        for line in getOutputAsList(["/sbin/ldconfig","-p"])[0]:
            # if dependency is 64 and library is 64 of
            # dependency is 32 and library is 32:
            if len(line) > 0 and soname in line and \
                ( (dependency.is64bits() and cls._ldconfig_64bits in line) or \
                (dependency.is32bits() and not cls._ldconfig_64bits in line) ):
                temp = line.split('=>')
                if len(temp) == 2:
                    provider=temp[1].strip()
                    if cls._checkMinor(provider, dependency.depname):
                        cls._pathCache[dependency.depname] = provider
                        return provider
        pathToScan = cls.systemPath
        if "LD_LIBRARY_PATH" in os.environ:
            #we need to scan the LD_LIBRARY_PATH too
            pathToScan += os.environ["LD_LIBRARY_PATH"].split(':')
        for path in pathToScan:
            provider = path + '/' + soname
            if os.path.isfile(provider) and \
                cls._checkMinor(provider, dependency.depname):
                #we found the soname and minor are there return true
                cls._pathCache[dependency.depname] = provider
                return provider
        #the dependency could not be located
        return None



    @classmethod
    def _checkMinor(cls, libPath, depName):
        """ check if libPath provides the depName (major and minor) """
        realProvider = os.path.realpath(libPath)
        for line in getOutputAsList(['bash', cls._RPM_FIND_PROV], realProvider)[0]:
            if len(line) > 0 and depName in line:
                return True
        return False


    @classmethod
    def _setDepsRequs(cls, swirlFile):
        """given a SwirlFile object it add to it all the dependency and all 
        the provides to it """

        #find deps
        for line in getOutputAsList(['bash', cls._RPM_FIND_DEPS], swirlFile.path)[0]:
            if len(line) > 0:
                newDep = Dependency( line )
                newDep.setPluginName( cls.pluginName )
                swirlFile.addDependency( newDep )
                #i need to take the parenthesis out of the game
                tempList = re.split('\(|\)',line)
                if len(tempList) > 3:
                    #set the 32/64 bits 
                    #probably unecessary
                    if tempList[3].find("64bit") >= 0 :
                        newDep.set64bits()
                    elif tempList[3].find("32bit") >= 0 :
                        #this should never happen
                        newDep.set32bits()
                else:
                    #no parenthesis aka 32 bit 
                    newDep.set32bits()
                p = cls.getPathToLibrary( newDep )
                if p:
                    newDep.pathList.append( p )
        
        #find provides
        for line in getOutputAsList(['bash', cls._RPM_FIND_PROV], swirlFile.path)[0]:
            if len(line) > 0 :
                newProv = Provide(line)
                newProv.setPluginName( cls.pluginName )
                swirlFile.addProvide(newProv)
        

    @classmethod
    def getDependeciesFromPath(cls, fileName):
        """given a file name it returns a Provide object with all the goodies in it
        """
        returnValue = []
        for line in getOutputAsList(['bash', cls._RPM_FIND_PROV], fileName)[0]:
            if len(line) == 0:
                continue
            newDep = Dependency( line )
            newDep.setPluginName( cls.pluginName )
            newDep.pathList.append( fileName )
            #i need to take the parenthesis out of the game
            tempList = re.split( '\(|\)', line )
            if len( tempList ) > 3:
                #set the 32/64 bits
                #probably unecessary
                if tempList[3].find( "64bit" ) >= 0 :
                    newDep.set64bits()
                elif tempList[3].find( "32bit" ) >= 0 :
                    #this should never happen
                    newDep.set32bits()
            else:
                #no parenthesis aka 32 bit
                newDep.set32bits()
            returnValue.append( newDep )
        return returnValue


    @classmethod
    def getSwirl(cls, fileName):
        """helper function given a filename it return a SwirlFile
        if the given plugin does not support the given fileName should just 
        return None
        ATT: only one plugin should return a SwirlFile for a given file
        """
        fd=open(fileName)
        magic = fd.read(4)
        if magic == '\x7f\x45\x4c\x46':
            #it's an elf see specs
            #http://www.sco.com/developers/gabi/1998-04-29/ch4.eheader.html#elfid
            swirlFile = SwirlFile( fileName )
            swirlFile.setPluginName( cls.pluginName )
            swirlFile.dyn = True
        else:
            #not an elf
            return None
        bitness = fd.read(1)
        if bitness == '\x01':
            swirlFile.set32bits()
        elif bitness == '\x02':
            swirlFile.set64bits()
        swirlFile.type = 'ELF'
        cls._setDepsRequs(swirlFile)
        return swirlFile

       
