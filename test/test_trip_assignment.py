# -*- coding: utf-8 -*-
"""
Created on Tue Dec 31 00:52:23 2019

@author: islam
"""

import os
import argparse
import logging
import logging.config
import sys
sys.path.append("..")
from metro3.metro.trip_assignment.trip_assignment import tripAssignmentModel, simulationMode
from metro3.metro.tools import setup_logging
#from trip_assignment.transit_fares import transitFares
#from trip_assignment.tolls import roadTolls

class TestTripAssignment(object):
	
	def setUp(self):
		pass
	
	def test_DUE_meso(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/meso.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		tripAssignment.run(calculateLOS = False, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		
		
	def test_DUE_meso_los(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/meso.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		los = tripAssignment.run(calculateLOS = True, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		los.saveTrafficOnly(os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/traffic_los_meso')))
		
	def test_DUE_micro(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/micro.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		tripAssignment.run(calculateLOS = False, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		
		
	def test_DUE_micro_los(self):
		iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/micro.ini'))
		tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
			
		los = tripAssignment.run(calculateLOS = True, mode = simulationMode.eDynamicTrafficAssignmentOnly)
		los.saveTrafficOnly(os.path.normpath(os.path.join(os.path.dirname(__file__),
												'trip_assignment/traffic_los_micro')))
		
	def test_SRC_meso(self):
		pass
		
	def test_SRC_micro(self):
		pass
		
	def test_PT(self):
		pass
	
	def test_DUE_meso_PT(self):
		pass
		
	def test_DUE_micro_PT(self):
		pass
		
	def test_SRC_meso_PT(self):
		pass
		
	def test_SRC_micro_PT(self):
		pass
		
if __name__ == '__main__':
	argParser = argparse.ArgumentParser()
	argParser.add_argument('testNumber', type=int, choices=range(0, 4))
	argParser.add_argument('-l', "--log_level", type = str.upper,
					choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					help="Set the logging level")
	args = argParser.parse_args()
	
	setup_logging.setup_logging(args.log_level)
	# create logger
	logger = logging.getLogger(__name__)

	model = TestTripAssignment()
	if args.testNumber == 0:
		model.test_DUE_meso()
	elif args.testNumber == 1:
		model.test_DUE_meso_los()
	elif args.testNumber == 2:
		model.test_DUE_micro()
	elif args.testNumber == 3:
		model.test_DUE_micro_los()
	print("Done...")
		