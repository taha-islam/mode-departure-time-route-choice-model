# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:00:38 2019

@author: islam
"""

import unittest
import os

from trip_assignment.trip_assignment import tripAssignmentModel, simulationMode
#from trip_assignment.transit_fares import transitFares
#from trip_assignment.tolls import roadTolls

class TestTripAssignment(unittest.TestCase):
	
	def setUp(self):
		pass
	
	def test_DUE_meso(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/traffic.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		tripAssignment.run(calculateLOS = False, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_DUE_meso_los(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/traffic.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		los = tripAssignment.run(calculateLOS = True, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_DUE_micro(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_SRC_meso(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_SRC_micro(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_PT(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
	
	def test_DUE_meso_PT(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_DUE_micro_PT(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_SRC_meso_PT(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
	def test_SRC_micro_PT(self):
		self.assertEqual({}, {}, "Should be empty dictionary")
		
if __name__ == '__main__':
	unittest.main()
