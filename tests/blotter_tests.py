

import unittest
import subprocess
import os
import glob
from datetime import datetime


from FingerPrint.plugins import PluginManager
from FingerPrint.blotter import Blotter
from FingerPrint.swirl import Swirl
from FingerPrint.utils import getOutputAsList
import FingerPrint.sergeant
from FingerPrint.utils import which

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        """setup for your unittest"""
        import sys
        sys.path.append("../")
        self.files = ["/bin/ls", "/etc/passwd", "/etc/hosts"]
        temp = which("find")
        if temp:
            self.files.append(temp)
        temp = which("dbus-daemon")
        if temp:
            self.files.append(temp)
        self.files += glob.glob("/lib*/libcryptsetup.so.*")
        self.files += glob.glob("/lib*/libdmraid.so.*")
        self.files += glob.glob("/lib*/libnss_nis*")
        #a python file
        cmdFile = getOutputAsList(["python", "-c", "import urllib;print urllib.__file__"])[0][0]
        #print cmdFile
        if cmdFile.endswith(".pyc") or cmdFile.endswith(".pyo"):
            cmdFile = cmdFile[0:-1]
        self.files.append( cmdFile )
        #print "File list: ", self.files
        self.availablePlugin = 2


    def test_plugin(self):
        print "\n     -----------------------     Testing pluging manager via API  -------------------------\n"
        self.swirl = Swirl("test", datetime.now())
        for i in self.files:
            swirlFile = PluginManager.getSwirl(i)
            self.swirl.addFile(swirlFile)
        p = PluginManager.get_plugins()
        print "plugins: ", p
        self.assertEqual(len(p), self.availablePlugin,
            msg="Plugin manager did not load all the available plugins (available %d, detected %d) " 
            % (len(p) , self.availablePlugin) )
        
    def test_hash(self):
        """ test hash function """
	file = 'tests/files/Ubuntu_12.04_x86_64/libsmbclient.so.0'
	hash = 'a1264218dc707b5b510ef12548564edc'
        self.assertEqual(FingerPrint.sergeant.getHash(file, 'ELF'), hash)



    def test_commandline(self):
        """ """
        #test empty command line
        print "\n     -----------------------     Running fingerprint command line   -------------------------\n"
        self.assertNotEqual(subprocess.call(['python', './bin/fingerprint']), 0,
            msg="fingerprint: empty command line should fail but it did not")
        #lets create a command wtih input file on the command line with default output filename
        outputfilename='output.swirl'
        self.assertEqual( 
            subprocess.call(['python', './bin/fingerprint', '-c'] + self.files), 0,
            msg="fingerprint-create: failed to analize the files: " + str(self.files))
        self.assertTrue( os.path.isfile(outputfilename), 
            msg="fingerprint-create: the output file %s was not created properly" % outputfilename )
        #let's verify that swirl, the test must pass!!
        self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-y'] ), 0,
            msg="fingerprint-verify: failed to verify swirl created on this system %s" % outputfilename)
        #let's test the integrity of the dependency
        self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-i'] ), 0,
            msg="fingerprint-verify: failed to verify the integrity of the swirl created on this system %s" % outputfilename)
        self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-q', '-S', '/usr/libsomeweirdlib.so.2'] ), 1,
            msg="fingerprint-query: failed to query swirl for non existent library")
        os.remove(outputfilename)
        #let's create a swirl with input file list taken from a file
        filelist='filelist'
        fd=open(filelist,'w')
        for i in self.files:
            fd.write(i + '\n')
        fd.close()
        self.assertEqual( 
            subprocess.call(['python', './bin/fingerprint', '-c', '-f', outputfilename, '-l', filelist]), 0,
            msg="fingerprint-create: failed to load filelist: " + filelist)
        self.assertTrue( os.path.isfile(outputfilename), 
            msg="fingerprint-create: the output file %s was not created properly" % outputfilename )
        #let's check the csv file creation
        csvfile = 'test.csv'
        self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-i', '-s', csvfile]), 0,
            msg="fingerprint-verify: failed to create csv file %s" % csvfile)
        self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-y', '-s', csvfile]), 0,
            msg="fingerprint-verify: failed to create csv file %s" % csvfile)
        os.remove(csvfile)
        os.remove(outputfilename)
        os.remove(filelist)


    def test_predefinedBinaries(self):
        #that how we get the platform name
        print "\n     -----------------------     Running fingerprint on predefined set of files   -------------------------\n"
        import platform
        dist = platform.dist()
        arch = platform.machine()
        platformname = dist[0] + "_" + dist[1] + "_" + arch
        print "System path is: ", platformname
        basedir = os.path.dirname( globals()["__file__"] )
        basedir += '/files/'
        testPlatforms = os.listdir(basedir)
        for testPlat in testPlatforms:
            testPlatPath = basedir + testPlat
            fileList = [os.path.join(testPlatPath, f) for f in os.listdir(testPlatPath)]
            self.assertEqual( subprocess.call(['python', './bin/fingerprint', '-c', 
                '-f', testPlat + '.swirl'] + fileList), 0, 
                msg="fingerprint-create: failed to create swirl for platform %s\n Input file %s"
                % (testPlatPath, fileList))
            if testPlat == platformname:
                #verification should succeed
                result = 0
                error = "pass"
            else:
                result = 1
                error = "fail"
            returncode = subprocess.call(['python', './bin/fingerprint', '-y', '-v',
                '-f', testPlat + '.swirl'])
            self.assertEqual( returncode, result,
                msg="fingerprint-verify: failed verification for swirl %s was supposed to %s"
                % (testPlat + '.swirl', error))
            os.remove(testPlat + '.swirl')


   
		
		


	



if __name__ == '__main__':
    unittest.main()

