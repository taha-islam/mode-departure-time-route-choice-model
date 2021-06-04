# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 08:20:34 2019

@author: islam
"""

import sys
import time
import argparse
import logging
import numpy as np
from configparser import ConfigParser, ExtendedInterpolation

sys.path.append("..\..")
from metro3.dcm import nl, mnl, cnl
from metro3.dcm.base import demandCalculationMethod, losMulFactor
from metro3.tools import demand, setup_logging

argParser = argparse.ArgumentParser(
	description = 'Validate and test the joint model of departure time and mode choice '
					'by applying it to the whole population usign GOOGLE LOS data'
					' and comparing the result demand with the base case demand')
argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
argParser.add_argument('expand_demand', type=int, choices=range(-2, 2),
						help='-2\t: calculate once and expand\n'
							'-1\t: calculate (maximum) once and expand\n'
							'0\t: calculate once and do not expand\n'
							'1\t: calculate and expand for each individual\n')
argParser.add_argument('-m', '--model', type=str.upper, 
						choices=['NL', 'MNL', 'CNL'],
						help='Model to be validated')
argParser.add_argument('-g', "--Google", action='store_true')
argParser.add_argument('-b', "--base_case", action='store_true')
argParser.add_argument('-l', "--log_level", type = str.upper, 
					choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					help="Set the logging level")
argParser.add_argument('-o', "--output_dir",
						help="Path to store the calculated demand")
argParser.add_argument('-f', '--gap_filling_method', type=int, choices=range(0, 4),
						const=0, default=0, nargs='?',
						help='Method of filling gaps in AIMSUN LOS matrices')
args = argParser.parse_args()

setup_logging.setup_logging(args.log_level)
# create logger
logger = logging.getLogger(__name__)

logger.info(' '.join(sys.argv))

parser = ConfigParser(interpolation=ExtendedInterpolation())
parser.read(args.iniFile)
if args.base_case:
	skimMatricesDir = parser['Paths']['BASE_SKIM_MATRICES_DIR']
else:
	skimMatricesDir = parser['Paths']['SKIM_MATRICES_DIR']
baseDemandDir = parser['Paths']['BASE_DEMAND_DIR']
regions = []
regionsCentroids = []
for region, ranges in parser.items('Regions'):
	if region in parser.defaults():
		continue
	regions.append(region)
	regionsCentroids.append(tuple(map(int,ranges.strip().split(','))))


if args.model == 'NL':
	start_time = time.time()
	# test changes in different components
	mulFactor=losMulFactor()
	#mulFactor.setCost(0.5,['T','PR','KR'],[1])
	#mulFactor.setCost(0.625,['T','PR','KR'],[2])
	#mulFactor.setCost(0.75,['T','PR','KR'],[3])
	#mulFactor.setCost(0.875,['T','PR','KR'],[4])
	mulFactor.setCost(2.0,['T','PR','KR'],[5])
	#mulFactor.setCost(0.833,['T','PR','KR'],[6])
	#mulFactor.setCost(0.667,['T','PR','KR'],[7])
	#mulFactor.setCost(0.5,['T','PR','KR'],[8])
	#mulFactor.factors['transit'][1] = 0.5
	#mulFactor.temporalDist = np.array([0,0.5,1,1.5,1.5,1,0.5,0])
	#logger.debug(mulFactor.factors)
	
	adjFactor = None
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
	dcm = nl.nl(args.iniFile, adjFactor, useGoogleLos=args.Google,mulFactor=mulFactor, gapFillingMethod=args.gap_filling_method)
	#			demandStructure4 = demandCalculationMethod.eMaintainTrafficMaintainTransit,
				
	# AIMSUN Traffic and Transit LOS
	if not args.Google:
		trafficLOS = {}
		for matrix, name in zip(['ivtt', 'dist', 'toll'], ['Travel Time', 'Travel Distance', 'Toll Cost']):
			trafficLOS[matrix] = demand.ODMatrices(args.iniFile, name = name, modes = ['Car', 'HOV'])
			trafficLOS[matrix].load(skimMatricesDir + '/Traffic/' + matrix)
		transitLOS = {}
		for matrix, name in zip(['ivtt', 'fare', 'accT', 'egrT'], 
				['In-Vehicle Travel Time', 'Fare Cost', 'Access Time', 'Egress Time']):
			transitLOS[matrix] = demand.ODMatrices(args.iniFile, name = name, modes = ['Torontonians', 'Regional Commuters'])
			transitLOS[matrix].load(skimMatricesDir + '/Transit/' + matrix)
		dcm.updateTravelLOS(trafficLOS, transitLOS)
	
	dcmDemand = dcm.apply(useExpansionFactor=args.expand_demand)
	logger.info('--- NL calculations finished in %s seconds ---' % (time.time() - start_time))
	if args.output_dir:
		dcmDemand.save(path=args.output_dir, sparse=True)
	dcmDemand.rename('NL Demand')
	dcmDemandSum = dcmDemand.sum()
	dcmDemandProbabilities = dcmDemandSum/dcmDemand.sum(centroidRanges=[], centroidNames=[],
														modeRanges=[], modeNames=[],
														intervalRanges=[], intervalNames=[])
	#dcmDemandProbabilities = dcmDemandSum/dcmDemandSum.sum()
	dcmDemandProbabilities.rename('NL demand probabilities')
	logger.info(dcmDemandSum)
	logger.info(dcmDemandProbabilities)
	dcmDemandNonzero = (dcmDemand != 0)
	logger.info(dcmDemandNonzero.sum())
	
	dcmDemandBase = demand.IntermODMatrices(args.iniFile, name='Base Demand')
	dcmDemandBase.load(baseDemandDir)
	dcmDemandBaseSum = dcmDemandBase.sum()
	dcmDemandBaseProbabilities = dcmDemandBaseSum/dcmDemandBase.sum(centroidRanges=[], centroidNames=[],
																	modeRanges=[], modeNames=[],
																	intervalRanges=[], intervalNames=[])
	#dcmDemandBaseProbabilities = dcmDemandBaseSum/dcmDemandBaseSum.sum()
	dcmDemandBaseProbabilities.rename('Base demand probabilities')
	logger.info(dcmDemandBaseSum)
	logger.info(dcmDemandBaseProbabilities)
	dcmDemandBaseNonzero = (dcmDemandBase != 0)
	logger.info(dcmDemandBaseNonzero.sum())

	difference = (dcmDemandBaseProbabilities - dcmDemandProbabilities) / dcmDemandBaseProbabilities
	#difference.rename('Difference in Demand')
	logger.info(difference)
	
	logger.info(dcmDemandBase.sum(centroidRanges=regionsCentroids, centroidNames=regions,
									modeRanges=[['D','P'],['T','PR','KR']], modeNames=['Traffic','Transit'],
									intervalRanges=[range(1,9)], intervalNames=['AM Peak']))
	logger.info(dcmDemand.match(dcmDemandBase).sum(centroidRanges=regionsCentroids, centroidNames=regions,
									modeRanges=[['D','P'],['T','PR','KR']], modeNames=['Traffic','Transit'],
									intervalRanges=[range(1,9)], intervalNames=['AM Peak']))
	logger.info(dcmDemand.mismatch(dcmDemandBase).sum(centroidRanges=regionsCentroids, centroidNames=regions,
									modeRanges=[['D','P'],['T','PR','KR']], modeNames=['Traffic','Transit'],
									intervalRanges=[range(1,9)], intervalNames=['AM Peak']))
									
	'''demandCalculations = demand.demandEval(args.iniFile)
	converged, finalDemand = demandCalculations.calculateAimsunDemand(intermDemand)
	if converged:
		print "converged..."
	else:
		print "not converged"
	'''
	'''
--- NL calculations finished in 3845.95899987 seconds ---
Sum of trips of mode D = 581992.450000
Sum of trips of mode P = 504366.230000
Sum of trips of mode T = 655929.240000
Sum of trips of mode PR = 203725.640000
Sum of trips of mode KR = 179196.640000
Sum of trips during interval 1 = 121578.730000
Sum of trips during interval 2 = 211425.620000
Sum of trips during interval 3 = 358876.680000
Sum of trips during interval 4 = 368116.190000
Sum of trips during interval 5 = 428165.230000
Sum of trips during interval 6 = 265160.460000
Sum of trips during interval 7 = 240722.980000
Sum of trips during interval 8 = 131164.310000
Sum of trips of mode D = 1621487.880000
Sum of trips of mode P = 146708.340000
Sum of trips of mode T = 424890.350000
Sum of trips of mode PR = 59265.700000
Sum of trips of mode KR = 42604.880000
Sum of trips during interval 1 = 132790.510000
Sum of trips during interval 2 = 178303.740000
Sum of trips during interval 3 = 322234.630000
Sum of trips during interval 4 = 372568.490000
Sum of trips during interval 5 = 527348.420000
Sum of trips during interval 6 = 360120.930000
Sum of trips during interval 7 = 263974.100000
Sum of trips during interval 8 = 137616.330000
	'''

if args.model == 'MNL':
	logger.warning('Not implemented yet!')
	'''start_time = time.time()
	discreteChoiceModel = mnl.mnl(sys.argv[2])
	intermODMatrices = discreteChoiceModel.apply()
	logger.info('--- MNL calculations finished in %s seconds ---' % (time.time() - start_time))'''
	
if args.model == 'CNL':
	logger.warning('Not implemented yet!')
	'''start_time = time.time()
	discreteChoiceModel = cnl.cnl(sys.argv[2])
	intermODMatrices = discreteChoiceModel.apply()
	logger.info('--- CNL calculations finished in %s seconds ---' % (time.time() - start_time))'''
