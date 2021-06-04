# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 06:47:55 2020

@author: islam
"""

import unittest
import os
from configparser import ConfigParser, ExtendedInterpolation

from metro.trip_assignment.fares import transitFares


class TestFares(unittest.TestCase):
	
	def setUp(self):
		self.iniFile = os.path.normpath(
							os.path.join(
								os.path.dirname(__file__),
								'fares/config.ini'))
		
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(self.iniFile)
		self._defaultFarePath = os.path.abspath(parser['Paths']['DEFAULT_FARE_FILE'])
		
		'''self.noOfZones = 2
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
								'407_2_e_000_000': 0.0}'''
		self.defaultFares = {'TTC':(1.98, 0),
							 'TTC_EXPRESS':(4.68, 0),
							 'GO':(4.07, 0.08),
							 'MIWAY':(1.98, 0)}
	
	def test_without_initialization(self):
		fares = transitFares()
		self.assertEqual(fares, {}, "Should be empty dictionary")
		print(str(fares))
		
	def test_defaults(self):
		fares = transitFares()
		fares.fillInDefaultFares()
		for key in self.defaultFares:
			self.assertTrue((fares[key] == self.defaultFares[key]),
								"Unable to read default fares")
		#fares.writeToFile(self._defaultFarePath)
	
	def test_read_from_file(self):
		fares = transitFares()
		fares.readFromFile(self._defaultFarePath)
		for key in self.defaultFares:
			self.assertTrue((fares[key] == self.defaultFares[key]),
								"Failed to transit fares from file")
	
	def test_write_to_file(self):
		fileTemp = os.path.join(os.path.dirname(self._defaultFarePath), 'fares.temp')
		fares = transitFares()
		fares.readFromFile(self._defaultFarePath)
		fares.writeToFile(fileTemp)
		fares2 = transitFares()
		fares2.readFromFile(fileTemp)
		os.remove(fileTemp)
		self.assertEqual(len(fares2.keys()), len(fares.keys()),
						   "Failed to write fares to file")
		for key in fares2:
			self.assertTrue((fares2[key] == fares[key]),
								"Failed to write fares to file")
		
if __name__ == '__main__':
	unittest.main()