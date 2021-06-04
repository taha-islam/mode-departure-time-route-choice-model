# -*- coding: utf-8 -*-
"""
Created on Fri May  8 15:27:27 2020

@author: islam
"""

import unittest
import metro.tools.det_data as det_data

#prefixes = []	# 3 letters indicating which freeway
#suffixes = []	# indicating direction and link's type
#prefixes = ['QEW']
#suffixes = ['DES', 'DWS']
#prefixes = ['QEW']
#suffixes = ['DES']

#files = None
#files = ['QEWDE0300DSR.csv']
#files = ['QEWDE0010DES.csv','QEWTN0050TES.csv','QEWDE0030DER.csv','QEWDE0040DER.csv','QEWDN0060DNS.csv','QEWDN0120DER.csv','QEWDE0020DES.csv','QEWDE0295DSR.csv','QEWDE0030DES.csv']

# TO DO: change for the desired output file's absolute path
#outputFileName = None	# print to the standard output
#outputFileName = 'C:\Aimsun Projects\CATTS\Real Data Sets\QEW.csv'	# output file's absolute path
#outputFileName = 'C:\Aimsun Projects\CATTS\Calibration_final\observed_data_5min.csv'	# output file's absolute path
#outputFileName = 'C:\\Computer\\work\\detector_data\\observed_data_5min.csv'	# output file's absolute path

# TO DO: change to the directory that contains speed, occ and Full_Details folders
#inputPath = 'C:\Aimsun Projects\CATTS\ITSoS Data\QEW'
#inputPath = 'C:\\Computer\\work\\detector_data\\2019_03\\2019_03'

# first day is Oct 4, 2016. It may be extracted automatically from the file.
#firstDay = 4 - 1	# index starts at 0

class TestDetectors(unittest.TestCase):
	
    def setUp(self):
        self.inputPath = 'C:\\Computer\\work\\detector_data\\2019_03'
        self.outputFileName = 'C:\\Computer\\work\\detector_data\\observed_data_2019_3.csv'	# output file's absolute path
        self.firstDay = 5 - 1
        #self.inputPath = 'C:\\Computer\\work\\detector_data\\2020_03'
        #self.outputFileName = 'C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv'	# output file's absolute path
        #self.firstDay = 3 - 1
        self.startTime=0
        self.endTime=86400
        self.intervalLen=900
        self.files=None
        self.prefixes = ['QEW']
        self.suffixes = ['DES']
        
    def test_detectors(self):
        det_data.process_det_data(self.inputPath, self.outputFileName,
                     self.firstDay, self.startTime, self.endTime, self.intervalLen,
                     self.files, self.prefixes, self.suffixes)
        #self.assertEqual({}, {}, "Should be empty dictionary")
		
if __name__ == '__main__':
    unittest.main()