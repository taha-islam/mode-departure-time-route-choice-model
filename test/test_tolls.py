# -*- coding: utf-8 -*-
"""
Created on Sun Dec 29 13:42:38 2019

@author: islam
"""

import unittest
import os
import numpy as np
from configparser import ConfigParser, ExtendedInterpolation

from metro.trip_assignment.tolls import roadTolls


class TestTolls(unittest.TestCase):
	
	def setUp(self):
		self.iniFile = os.path.normpath(
							os.path.join(
								os.path.dirname(__file__),
								'tolls/config.ini'))
		
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(self.iniFile)
		self._defaultTollPath = os.path.abspath(parser['Paths']['DEFAULT_TOLL_FILE'])
		
		self.noOfZones = 2
		self.noOfIntervals = 24*2
		self.defaultTolls = {('407','e'): np.zeros((self.noOfZones, self.noOfIntervals))}
		self.defaultTolls[('407','e')][:,12:14] = 1.0
		self.defaultTolls[('407','e')][:,14:18] = 2.0
		self.defaultTolls[('407','e')][:,18:20] = 3.0
		self.defaultTolls[('407','e')][:,20:29] = 4.0
		
		self.defaultTollsDict ={'407_1_e_600_700': 1.0,
								'407_1_e_700_900': 2.0,
								'407_1_e_900_1000': 3.0,
								'407_1_e_1000_1430': 4.0,
								'407_1_e_000_000': 0.0,
								'407_2_e_600_700': 1.0,
								'407_2_e_700_900': 2.0,
								'407_2_e_900_1000': 3.0,
								'407_2_e_1000_1430': 4.0,
								'407_2_e_000_000': 0.0}
	
	def test_without_initialization(self):
		tolls = roadTolls('')
		self.assertEqual(tolls, {}, "Should be empty dictionary")
		
	def test_defaults(self):
		tolls = roadTolls(self.iniFile)
		for key in self.defaultTolls:
			self.assertTrue((tolls[key] == self.defaultTolls[key]).all(),
								"Unable to read default tolls")
	
	def test_read_from_file(self):
		tolls = roadTolls('')
		tolls.readFromFile(self._defaultTollPath)
		for key in self.defaultTolls:
			self.assertTrue((tolls[key] == self.defaultTolls[key]).all(),
								"Failed to read tolls from file")
	
	def test_write_to_file(self):
		fileTemp = os.path.join(os.path.dirname(self._defaultTollPath), 'tolls.temp')
		tolls = roadTolls(self.iniFile)
		tolls.writeToFile(fileTemp)
		tolls2 = roadTolls('')
		tolls2.readFromFile(fileTemp)
		os.remove(fileTemp)
		self.assertEqual(len(tolls2.keys()), len(tolls.keys()),
						   "Failed to write tolls to file")
		for key in tolls2:
			self.assertTrue((tolls2[key] == tolls[key]).all(),
								"Failed to write tolls to file")
		
	def test_from_dict(self):
		tolls = roadTolls(self.iniFile)
		tolls2 = roadTolls('')
		tolls2.fromDict(self.defaultTollsDict)
		self.assertEqual(len(tolls2.keys()), len(tolls.keys()),
						   "Failed to load tolls from dictionary")
		for key in tolls2:
			self.assertTrue((tolls2[key] == tolls[key]).all(),
							"Failed to load tolls from dictionary")
		
	def test_to_dict(self):
		tolls = roadTolls(self.iniFile)
		self.assertDictEqual(tolls.toDict(), self.defaultTollsDict,
							"Failed to save tolls to dictionary")
		
if __name__ == '__main__':
	unittest.main()