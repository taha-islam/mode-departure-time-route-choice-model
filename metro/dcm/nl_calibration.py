# -*- coding: utf-8 -*-
"""
Created on Fri Nov 29 16:44:18 2019

@author: islam
"""

import sys
import numpy as np
from functools import partial
import argparse
import logging
from configparser import ConfigParser, ExtendedInterpolation

sys.path.append("..\..")
from metro3.tools import demand, setup_logging
import nl
from base import demandCalculationMethod

argParser = argparse.ArgumentParser(
	description = 'Calibrate the joint nested logit model of departure '
					'time and mode choice')
argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
argParser.add_argument('-i', '--numberOfIter', type=int, const=5, default=5, nargs='?',
						help='Number of iteration')
argParser.add_argument('-c', '--convTh', type=float, const=0.05, default=0.05, nargs='?',
						help='Convergence threshold')
argParser.add_argument('-l', "--log_level", type = str.upper,
					choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					help="Set the logging level")
argParser.add_argument('-s', "--skim_matrices", 
					help="Skim matrices directory")
args = argParser.parse_args()

setup_logging.setup_logging(args.log_level)
# create logger
logger = logging.getLogger(__name__)
logger.info(' '.join(sys.argv))

if args.numberOfIter <= 0:
	raise argparse.ArgumentTypeError("%s is an invalid positive int value" % args.numberOfIter)
if args.convTh <= 0:
	raise argparse.ArgumentTypeError("%s is an invalid positive float value" % args.convTh)

parser = ConfigParser(interpolation=ExtendedInterpolation())
parser.read(args.iniFile)
numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
intermModes = parser['Demand']['INTERM_MODES'].strip().split(',')

regionsDict = {}
for region, cenRange in parser.items('DCM Regions'):
	if region in parser.defaults():
		continue
	regionsDict[region] = tuple(map(int,cenRange.strip().split(',')))
# sort regions and their ranges (asc) based on the start of the range
regionsSorted = sorted(regionsDict.items(), key=lambda x: x[1][0])
regions = [i[0] for i in regionsSorted]
regionsCentroids = [i[1] for i in regionsSorted]
		
if args.skim_matrices:
	skimMatricesDir = args.skim_matrices
else:
	#skimMatricesDir = parser['Paths']['SKIM_MATRICES_DIR']
	skimMatricesDir = parser['Paths']['BASE_SKIM_MATRICES_DIR']
baseDemandDir = parser['Paths']['BASE_DEMAND_DIR']

log = open("nl_calibration.log", "w")
logDetailed = open("nl_calibration_detailed.log", "w")
# Base (reference) demand
dcmDemandBase = demand.IntermODMatrices(args.iniFile, name='Base Demand')
dcmDemandBase.load(baseDemandDir)
dcmDemandBaseSum = dcmDemandBase.sum(centroidRanges=regionsCentroids, centroidNames=regions)
logger.info(dcmDemandBaseSum)
'''for mode in dcmDemandBase.modes:
	for interval in range(1, dcmDemandBase._numberOfIntervals+1):
		for orig in range(625, 1497):
			for dest in range(625, 1497):
				dcmDemandBase[(mode, interval)][orig][dest] = 0
'''
# AIMSUN Traffic and Transit LOS
trafficLOS = {}
for matrix, name in zip(['ivtt', 'dist', 'toll'], ['Travel Time', 'Travel Distance', 'Toll Cost']):
	trafficLOS[matrix] = demand.ODMatrices(args.iniFile, name = name, modes = ['Car', 'HOV'])
	trafficLOS[matrix].load(skimMatricesDir + '/Traffic/' + matrix)
transitLOS = {}
for matrix, name in zip(['ivtt', 'fare', 'accT', 'egrT'], 
		['In-Vehicle Travel Time', 'Fare Cost', 'Access Time', 'Egress Time']):
	transitLOS[matrix] = demand.ODMatrices(args.iniFile, name = name, modes = ['Torontonians', 'Regional Commuters'])
	transitLOS[matrix].load(skimMatricesDir + '/Transit/' + matrix)

# initial adjustment factors
#adjFactor = [
#			[0,0,0,0,0,0,0,0],
#			[0,0,0,0,0,0,0,0],
#			[0,0,0,0,0,0,0,0],
#			[0,0,0,0,0,0,0,0],
#			[0,0,0,0,0,0,0,0]
#			]
adjFactor = demand.ODMatrices(args.iniFile,
						 name='Adjustment Factors',
						 modes=intermModes,
						 numberOfIntervals=numberOfIntervals,
						 numberOfCentroids=len(regions),
						 centroidNames=regions)
'''adjFactor =[
				[
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0]
				],
				[
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0]
				],
				[
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0]
				],
				[
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0],
					[0,0,0,0,0,0,0,0]
				]
			]'''
logger.info('Iteration'.ljust(12) + 'Max Error'.ljust(12))
print('Iteration'.ljust(12) + 'Max Error'.ljust(12), file = log)
norm1 = partial(np.linalg.norm, ord=1)
norm1.__name__ = 'norm1'
for i in range(1, args.numberOfIter + 1):
	logger.debug('Iteration #%i' %i)
	logger.debug(adjFactor)
	dcm = nl.nl(args.iniFile, adjFactor)
	# 3 --> 1st degree curve fitting
	dcm.updateTravelLOS(trafficLOS, transitLOS, gapFillingMethod=3)
	# simulate once for each group using the roullette wheel selcetion method
	dcmDemand = dcm.apply(useExpansionFactor=-2)
	dcmDemand.rename("Iteration #%i Demand" %i)
	
	dcmDemandSum = dcmDemand.sum(centroidRanges=regionsCentroids, centroidNames=regions)
	difference = (dcmDemandSum - dcmDemandBaseSum) / dcmDemandBaseSum 
	logger.debug(dcmDemandSum)
	maxValue = abs(difference).max(centroidRanges=[], centroidNames=[],
									modeRanges=[], modeNames=[],
									intervalRanges=[], intervalNames=[])
	if maxValue <= args.convTh:
		break
	# calculate new adjustment factors
	demandRatio = dcmDemandBaseSum / dcmDemandSum
	adjFactor = adjFactor + demandRatio.log()
	logger.info(str(i).ljust(12) + str(maxValue).ljust(12))
	print(str(i).ljust(12) + str(maxValue).ljust(12), file = log)
	print(difference.str(aggFun=norm1), file = logDetailed)

logger.info(dcmDemandSum)
print("_____________________________________________________________"
		"____________________________", file = log)
print(difference.str(aggFun=norm1), file = log)
print(str(adjFactor), file = log)
print("NL calibration done in %i iterations with max relative error "
		"in number of trips = %f" %(i, maxValue), file = log)
adjFactor.save('alternative specific constants')