# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:00:38 2019

@author: islam
"""

import sys
sys.path.append("..\..")
from metro3.trip_assignment.trip_assignment import tripAssignmentModel #, simulationMode
#from metro.aimsun.traffic_assignment import DUEModel
#from metro.aimsun.transit_assignment import PTModel
from metro3.trip_assignment.transit_fares import transitFares
from metro3.tools import setup_logging
#from metro.tools.demand import ODMatrices
#from metro.tools.los import levelOfServiceAttributes as LOS

import time
import argparse
import logging
import logging.config
from configparser import ConfigParser, ExtendedInterpolation


argParser = argparse.ArgumentParser(
	description = 'Test the traffic and transit assignment model in AIMSUN, '
					'which includes updating the tolls and fares, if applicable, '
					'running DUE simulation, and finally running different transit '
					'assignment models based on the travel times from the DUE model')
argParser.add_argument('testNumber', type=int, choices=range(0, 3),
						help='0\t: traffic and transit assignment\n'
							'1\t: traffic assignment only\n'
							'2\t: transit assignment only\n')
argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
argParser.add_argument('-l', "--log_level", type = str.upper,
					choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					help="Set the logging level")
argParser.add_argument('-b', "--base_case", action='store_true')
argParser.add_argument('-f', "--fares", action='store_true')
args = argParser.parse_args()

setup_logging.setup_logging(args.log_level)
# create logger
logger = logging.getLogger(__name__)

parser = ConfigParser(interpolation=ExtendedInterpolation())
parser.read(args.iniFile)
if args.base_case:
	skimMatDir = parser['Paths']['BASE_SKIM_MATRICES_DIR']
else:
	skimMatDir = parser['Paths']['SKIM_MATRICES_DIR']
numberOfIntervals = int(parser['Demand']['numberOfIntervals'])

'''
mode =	0 --> simulationMode.eDynamicTrafficAndTransitAssignment
		1 --> simulationMode.eDynamicTrafficAssignmentOnly
		2 --> simulationMode.eDynamicTransitAssignmentOnly
'''
logger.info('______________________________________________________________________________________')
logger.info('Start testing the \'Trip Assignment\' model...')
start_time = time.time()
tripAssignment = tripAssignmentModel(args.iniFile, baseCaseModel=args.base_case)
if args.fares:
	# default fares for all intervals
	fares = []
	for i in range(numberOfIntervals):
		fares.append(transitFares())
		fares[-1].fillInDefaultFares()
	# update fares
	'''fareMulFactors = tools.calculatePricingStructure(0.5,1,numberOfIntervals,(4,))
	for i in range(len(fareMulFactors)):
		fares[i]['TTC'] = (fares[i]['TTC'][0] * fareMulFactors[i], fares[i]['TTC'][1])'''
	tripAssignment.fares = fares
	
los = tripAssignment.run(calculateLOS = True, mode = args.testNumber)
#los = tripAssignment.run(calculateLOS = False, mode = args.testNumber)
'''los.save(skimMatDir, sparse=True)
trafficLOS, transitLOS = los.getTravelLOS()
for key in trafficLOS:
	logger.info(trafficLOS[key].sum())
for key in transitLOS:
	logger.info(transitLOS[key].sum())'''
logger.info("Trip assignment finished in %s seconds" % (time.time() - start_time))

