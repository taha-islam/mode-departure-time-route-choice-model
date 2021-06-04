# -*- coding: utf-8 -*-
"""
Created on Fri May 29 12:59:46 2020

@author: islam

Example:
py .\metro3\metro\calibration\aimsun\datasets.py .\metro3\metro\calibration\aimsun\networks\network1.ini 890 0 1000 .\metro3\metro\calibration\aimsun\datasets\ .\metro3\metro\calibration\aimsun\networks\network1_detectors.csv -l info
"""
import os
import sys
if __name__ == "__main__":
    package_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                "../../../.."))
    #package_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    #                                            "../../../.."))
    sys.path.append(package_path)
    
from metro3.metro.tools.setup import mode as MODE
if MODE == 0:
	import metro3.metro.tools.site_packages
	import pandas as pd
	from metro3.metro.aimsun.calibration_data_gen import CalibrationDataModel
	from metro3.metro.aimsun.sim_outputs import simOutputs, objectIdsType
	from metro3.metro.aimsun.base import aimsunModelType
elif MODE == 1:
	import pickle
	import subprocess
else:
	sys.exit()

from metro3.metro.tools.setup_logging import setup_logging as setup_logging
from metro3.metro.tools.progress_bar import printProgressBar as printProgressBar
import argparse
import logging
import os
import random
import numpy as np
from configparser import ConfigParser, ExtendedInterpolation

# defining parameters ranges
simStepArray = np.arange(0.1, 1.6, 0.1)
CFAggressivenessMeanArray = np.arange(-1, 1.1, 0.1)
maxAccelMeanArray = np.arange(1, 4.1, 0.1)
normalDecelMeanArray = np.arange(1, 5.1, 0.1)
aggressivenessArray = np.arange(0, 101, 1)
cooperationArray = np.arange(0, 101, 1)
onRampMergingDistanceArray = np.arange(0, 301, 5)
distanceZone1Array = np.arange(200, 1001, 10)
distanceZone2Array = np.arange(100, 501, 10)
clearanceArray = np.arange(0.1, 2.1, 0.1)
paramEnabled = {'simStep': True,
				'CFAggressivenessMean': True,
				'maxAccelMean': True,
				'normalDecelMean': True,
				'aggressiveness': True,
				'cooperation': True,
				'onRampMergingDistance': False,
				'distanceZone1': False,
				'distanceZone2': False,
				'clearance':True}
if MODE == 0:
	def main():
		'''
		Run simulation within AIMSUN running using aconsole
		example:
		'C:\Program Files\Aimsun\Aimsun Next 8.3\aconsole.exe' -script generate_calibration_data.py 
		'C:/Aimsun Projects/Calibration Using Neural Networks/generate_calibration_data.ini' 
		890 10000 
		'C:/Aimsun Projects/Calibration Using Neural Networks/dataset/' 
		'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv' 
		-l info
		'''
		global simStepArray, CFAggressivenessMeanArray, maxAccelMeanArray
		global normalDecelMeanArray, aggressivenessArray, cooperationArray
		global onRampMergingDistanceArray, distanceZone1Array, distanceZone2Array
		global clearanceArray, paramEnabled
		simStep = None
		CFAggressivenessMean = None
		maxAccelMean = None
		normalDecelMean = None
		aggressiveness = None
		cooperation = None
		onRampMergingDistance = None
		distanceZone1 = None
		distanceZone2 = None
		clearance = None
		
		argParser = argparse.ArgumentParser(
			description = 'Run DUE traffic assignment model')
		argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
		argParser.add_argument('id', type=int,
								help='Aimsun replication Id')
		argParser.add_argument('index', type=int,
								help='Index of the first generated sample')
		argParser.add_argument('datasetSize', type=int,
								help='Size of the generated calibration dataset')
		argParser.add_argument('datasetDir', help='Path to where the output dataset will be stored')
		# 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv'
		argParser.add_argument('objectsFile', help='File of objects whose stats would be collected')
		argParser.add_argument('-l', "--log_level", type = str.upper,
							choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
							help="Set the logging level")
		args = argParser.parse_args()
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(args.iniFile)
		numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		#baseDir = parser['Paths']['BASE_DIR']
		setup_logging(args.log_level)#, path=os.path.join(baseDir, 'logging.yaml'))
		logger = logging.getLogger(__name__)
		logger.info(' '.join(sys.argv))
		
		# initialize an Aimsun model
		trafficModel = CalibrationDataModel(args.iniFile, args.id, aimsunModelType.eMicro)
		# read data of objects used to collect stats
		statObjects = pd.read_csv(args.objectsFile, index_col=False)
		statObjects.rename(columns = {statObjects.columns.values[0]:'id'})
		# loop over samples, run simulation for each one, and collect the resulting outputs
		for i in range(args.index, args.datasetSize + args.index):
			if args.datasetSize>10 and i%(args.datasetSize/100) == 0:
				logger.debug('%i out of %i' %(i, args.datasetSize))
			if args.datasetSize>10 and i%(args.datasetSize/10) == 0:
				logger.info('%i out of %i' %(i, args.datasetSize))
			# choose random sample
			if paramEnabled['simStep']:
				simStep = random.sample(simStepArray, 1)[0].item()
			if paramEnabled['CFAggressivenessMean']:
				CFAggressivenessMean = random.sample(CFAggressivenessMeanArray, 1)[0].item()
			if paramEnabled['maxAccelMean']:
				maxAccelMean = random.sample(maxAccelMeanArray, 1)[0].item()
			if paramEnabled['normalDecelMean']:
				normalDecelMean = random.sample(normalDecelMeanArray, 1)[0].item()
			if paramEnabled['aggressiveness']:
				aggressiveness = random.sample(aggressivenessArray, 1)[0].item()
			if paramEnabled['cooperation']:
				cooperation = random.sample(cooperationArray, 1)[0].item()
			if paramEnabled['onRampMergingDistance']:
				onRampMergingDistance = random.sample(onRampMergingDistanceArray, 1)[0].item()
			if paramEnabled['distanceZone1']:
				distanceZone1 = random.sample(distanceZone1Array, 1)[0].item()
			if paramEnabled['distanceZone2']:
				distanceZone2 = min(random.sample(distanceZone2Array, 1), distanceZone1)
			if paramEnabled['clearance']:
				clearance = random.sample(clearanceArray, 1)[0].item()
			# load the network
			_, model = trafficModel.loadNetwork()
			# set calibration parameters
			trafficModel.setParams( simStep,
									CFAggressivenessMean,
									maxAccelMean,
									normalDecelMean,
									aggressiveness,
									cooperation,
									onRampMergingDistance,
									distanceZone1,
									distanceZone2,
									clearance)
			# run the simulation
			trafficModel.run()
			logger.debug('finish running')
			#trafficModel.retrieveOutput()
			# extract detectors' data
			outputs = simOutputs(args.iniFile, model, args.id)
			#outputs.setObjects("GKDetector", objectIdsType.eName, objList=[])
			outputs.setObjects("GKDetector", objectIdsType.eId, inputFileName = args.objectsFile)
			outputs.calculate(numberOfIntervals=numberOfIntervals)
			# save x & y of this sample
			logger.debug('Printing x')
			logger.debug(outputs.stats)
			logger.debug(statObjects)
			x = pd.merge(outputs.stats, statObjects, how='inner', on='id')
			x.to_csv(os.path.join(args.datasetDir, 'x'+str(i)+'.csv'), index=False)
			y = pd.DataFrame( [ simStep,
								CFAggressivenessMean,
								maxAccelMean,
								normalDecelMean,
								aggressiveness,
								cooperation,
								onRampMergingDistance,
								distanceZone1,
								distanceZone2,
								clearance])
			y.to_csv(os.path.join(args.datasetDir, 'y'+str(i)+'.csv'), index=False, header=False)
			# unload the network
			trafficModel.unloadNetwork()
if MODE == 1:
	def main():
		'''
		Run simulation within AIMSUN running using original python.exe
		example:
		py -m metro3.metro.calibration.aimsun.datasets .\metro3\metro\calibration\aimsun\networks\network1.ini 890 0 5 .\metro3\metro\calibration\aimsun\datasets\ .\metro3\metro\calibration\aimsun\networks\network1_detectors.csv -l info
		'''
		global simStepArray, CFAggressivenessMeanArray, maxAccelMeanArray
		global normalDecelMeanArray, aggressivenessArray, cooperationArray
		global onRampMergingDistanceArray, distanceZone1Array, distanceZone2Array
		global clearanceArray, paramEnabled
		simStep = None
		CFAggressivenessMean = None
		maxAccelMean = None
		normalDecelMean = None
		aggressiveness = None
		cooperation = None
		onRampMergingDistance = None
		distanceZone1 = None
		distanceZone2 = None
		clearance = None
		argParser = argparse.ArgumentParser(
			description = 'Run DUE traffic assignment model')
		argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
		argParser.add_argument('id', type=int,
								help='Aimsun replication Id')
		argParser.add_argument('index', type=int,
								help='Index of the first generated sample')
		argParser.add_argument('datasetSize', type=int,
								help='Size of the generated calibration dataset')
		argParser.add_argument('datasetDir', help='Path to where the output dataset will be stored')
		# 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv'
		argParser.add_argument('objectsFile', help='File of objects whose stats would be collected')
		argParser.add_argument('-l', "--log_level", type = str.upper,
							choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
							help="Set the logging level")
		argParser.add_argument('-s', "--seed", type = float, default=-1,
                           help="Number of threads (parallel simulations)")
		args = argParser.parse_args()
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(args.iniFile)
		#numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		#baseDir = parser['Paths']['BASE_DIR']
		aimsunExe = os.path.join(parser['Paths']['AIMSUN_DIR'],'aconsole.exe')
		setup_logging(args.log_level)#, path=os.path.join(baseDir, 'logging.yaml'))
		logger = logging.getLogger(__name__)
		logger.info(' '.join(sys.argv))
		
		# print system info
		cmd = [aimsunExe, '-log_file', 'aimsun.log', '-script']
		cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),'../../tools/system_info.py')))
		logger.debug('Running command: %s' %' '.join(cmd))
		ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		logLevel = logging.getLevelName(logger.getEffectiveLevel())
		ps.wait()
		printProgressBar(0, args.datasetSize, prefix = 'Progress:', 
						suffix = 'Complete', length = 50)
		for i in range(args.index, args.datasetSize + args.index):
			# debug/info messages
			if args.datasetSize>10 and (i-args.index)%(args.datasetSize/100) == 0:
				logger.debug('%i out of %i' %(i, args.datasetSize))
			if args.datasetSize>10 and (i-args.index)%(args.datasetSize/10) == 0:
				logger.info('%i out of %i' %(i, args.datasetSize))
			# choose random sample
			# construct and run aconsole command
			cmd = [aimsunExe, '-log_file', 'aimsun.log', '-script']
			cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                            'sim_data.py')))
			cmd.append(args.iniFile)
			cmd.append(str(args.id))
			cmd.append(args.datasetDir)
			cmd.append(args.objectsFile)
			cmd.append('--index')
			cmd.append(str(i))
			cmd.append('-l')
			cmd.append(logLevel)
			if paramEnabled['simStep']:
				simStep = round(random.sample(list(simStepArray), 1)[0].item(), 2)
				cmd.append('--simStep')
				cmd.append(str(simStep))
			if paramEnabled['CFAggressivenessMean']:
				CFAggressivenessMean = round(random.sample(list(CFAggressivenessMeanArray), 1)[0].item(), 2)
				cmd.append('--CFAggressivenessMean')
				cmd.append(str(CFAggressivenessMean))
			if paramEnabled['maxAccelMean']:
				maxAccelMean = round(random.sample(list(maxAccelMeanArray), 1)[0].item(), 2)
				cmd.append('--maxAccelMean')
				cmd.append(str(maxAccelMean))
			if paramEnabled['normalDecelMean']:
				normalDecelMean = round(random.sample(list(normalDecelMeanArray), 1)[0].item(), 2)
				cmd.append('--normalDecelMean')
				cmd.append(str(normalDecelMean))
			if paramEnabled['aggressiveness']:
				aggressiveness = round(random.sample(list(aggressivenessArray), 1)[0].item(), 2)
				cmd.append('--aggressiveness')
				cmd.append(str(aggressiveness))
			if paramEnabled['cooperation']:
				cooperation = round(random.sample(list(cooperationArray), 1)[0].item(), 2)
				cmd.append('--cooperation')
				cmd.append(str(cooperation))
			if paramEnabled['onRampMergingDistance']:
				onRampMergingDistance = round(random.sample(list(onRampMergingDistanceArray), 1)[0].item(), 2)
				cmd.append('--onRampMergingDistance')
				cmd.append(str(onRampMergingDistance))
			if paramEnabled['distanceZone1']:
				distanceZone1 = round(random.sample(list(distanceZone1Array), 1)[0].item(), 2)
				cmd.append('--distanceZone1')
				cmd.append(str(distanceZone1))
			if paramEnabled['distanceZone2']:
				distanceZone2 = round(min(random.sample(list(distanceZone2Array), 1), distanceZone1), 2)
				cmd.append('--distanceZone2')
				cmd.append(str(distanceZone2))
			if paramEnabled['clearance']:
				clearance = round(random.sample(list(clearanceArray), 1)[0].item(), 2)
				cmd.append('--clearance')
				cmd.append(str(clearance))
			logger.debug('Running command: %s' %' '.join(cmd))
			ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
			stdout, stderr = ps.communicate()
			#print(stdout)
			#ps.wait()
			printProgressBar(i-args.index+1, args.datasetSize, 
						prefix = 'Progress:', suffix = 'Complete', length = 50)
		
else:
	def main():
		print('Unrecognizable executable')


if __name__ == "__main__":
    sys.exit(main())