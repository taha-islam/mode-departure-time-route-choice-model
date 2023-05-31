# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 14:49:26 2019

@author: islam
"""

import sys
import time
import sqlite3
import numpy as np
import logging
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyNSPManager import *
from configparser import ConfigParser, ExtendedInterpolation
from .base import aimsunModel, aimsunModelType
from .tolls import roadTolls
import metro3.metro.tools.site_packages
#from metro3.tools.demand import ODMatrices

class DUEModel(aimsunModel):
	"""A class for DUE Mesoscopic Aimsun models"""
	
	def __init__(self, 
				iniFile, 
				replicationId, 
				console=None, 
				model=None, 
				calculateLOS=False, 
				baseCaseModel=False,
				tolls=None,
				losDb=None):
		self._logger = logging.getLogger(__name__)
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		modelType = parser.get('Traffic Assignment','MODEL_TYPE', fallback='MESO').upper()
		if modelType == 'MICRO':
			modelType = aimsunModelType.eMicro
		else:
			modelType = aimsunModelType.eMeso
		super(DUEModel, self).__init__(iniFile, replicationId, modelType, 
											console, model, calculateLOS,
											baseCaseModel, losDb=losDb)
		self._noOfIter = int(parser.get('Traffic Assignment','NUMBER_OF_ITERATIONS', fallback=1))
		self._noOfThreads = int(parser.get('Traffic Assignment','NUMBER_OF_THREADS', fallback=1))
		
		self._rcCycle = int(parser.get('Traffic Assignment','ROUTE_CHOICE_CYCLE', fallback=10))
		self._aggInterval = int(parser.get('Traffic Assignment','AGGREGATION_INTERVAL', fallback=10))
		self._tollFunctionId = int(parser.get('Traffic Assignment','TOLL_FUNCTION_ID', fallback=-1))
		try:
			dtaUserClassNames = parser['Traffic Assignment']['dtaUserClassNames'].strip().split(',')
			self._dtaUserClasses = {}	# dictionary <userClassName>:<userClassId>
			for userClassName in dtaUserClassNames:
				self._dtaUserClasses[userClassName] = int(parser['Traffic Assignment'][userClassName])
		except:
			pass
		
		if tolls is None:
			self.tolls = roadTolls(self._iniFile)
		else:
			self.tolls = tolls
			
		if self._type == aimsunModelType.eMicro:
			self._databasePrefix = 'MI'
		elif self._type == aimsunModelType.eMeso:
			self._databasePrefix = 'ME'
		

	def _checkValidReplication(self):
		replication = self._model.getCatalog().find(self._id)
		if self._type == aimsunModelType.eMicro:
			return (replication is not None) and \
				(replication.isA("GKReplication")) and \
				(self._getExperiment().getSimulatorEngine() == GKExperiment.eMicro)
		elif self._type == aimsunModelType.eMeso:
			return (replication is not None) and \
				(replication.isA("GKReplication")) and \
				(self._getExperiment().getSimulatorEngine() == GKExperiment.eMeso)
		return False

	def run(self):
		'''
		This function runs DUE result whose id is self._id
		1. remove output Db
		2. set demand factor, number of iterations, and number of threads
		3. update tolls (write them as experiment variables in Aimsun)
		4. execute the simulation
		'''
		def print_sim_info():
			conn = sqlite3.connect(self._database)
			cur = conn.cursor()
			vOut, vIn, vWait = cur.execute('SELECT vOut, vIn, vWait '
								'FROM %sSYS WHERE '
								'ent = 0 AND sid = 0 AND did = ?' %self._databasePrefix,
								(self._id,)).fetchone()
			return vOut, vIn, vWait
		super(DUEModel, self).run()
		if self._model is not None:
			replication = self._model.getCatalog().find(self._id)
			if not self._checkValidReplication():
				self._console.getLog().addError("Cannot find DUE replication")
				self._logger.error("Cannot find DUE replication %i" % self._id)
				return -1
			else:
				# delete simulation output database
				self.removeDatabase()
				
				#experiment = replication.getExperiment()
				#scenario = experiment.getScenario()
				experiment = self._getExperiment()
				scenario = self._getScenario()
				# initialize scenario's parameters
				#scenario.getDemand().setFactor(str(self._demandMulFactor))
				self.setDemandFactor()
				# initialize the experiment's parameters
				if experiment.getEngineMode() == GKExperiment.eIterative:
					experiment.setStoppingCriteriaIterations(self._noOfIter)
				experiment.setNbThreadsPaths(self._noOfThreads)
				# set tolls
				self.updateTolls()
				# run the simulation
				selection = []
				self._logger.info('Starting DUE result %i' % self._id)
				GKSystem.getSystem().executeAction("execute", replication,
										selection, time.strftime("%Y%m%d-%H%M%S"))
				self._outputsInMemory = scenario.getInputData().getKeepHistoryStat()
				# load the results
				#plugin.readResult(replication, False, False)
				self._logger.info('DUE result %i is completed' % self._id)
				vOut, vIn, vWait = print_sim_info()
				self._logger.info('Number of vehicles reached their destination = %f\n'
								'Number of vehicles still in the network = %f\n'
								'Number of vehicles waiting to enter the network = %f' %(vOut, vIn, vWait))
			return 0
		else:
			self._logger.error('cannot load network')
			return -1
	
	#------------------------------Traffic LOS------------------------------#
	def getODTravelTimeDistance(self):
		'''
		extract travel times and distances
		'''
		#ivtt = ODMatrices(self._iniFile, name = 'Travel Time', modes = self._dtaUserClasses.keys())
		#dist = ODMatrices(self._iniFile, name = 'Travel Distance', modes = self._dtaUserClasses.keys())
		self._logger.debug('Connecting to traffic database: %s' %self._database)
		conn = sqlite3.connect(self._database)
		cur = conn.cursor()
		
		connLOS = sqlite3.connect(self._losDb)
		curLOS = connLOS.cursor()
		curLOS.execute("UPDATE LOS SET traffic_ivtt=0, traffic_dist=0")
		'''rows = cur.execute(
			"SELECT pos, oid, oname "
			"FROM META_SUB_INFO "
			"WHERE tname = ? AND did = ?",
			(self._databasePrefix+'CENT_O', self._id))'''
		rows = cur.execute(
			"SELECT pos, oid, oname "
			"FROM META_SUB_INFO "
			"WHERE did = ?",
			(self._id,))
		usableUserClasses = {}
		for (userClassIdx, userClassId, userClassName) in rows:
			if userClassName in self._dtaUserClasses.keys():
				usableUserClasses[userClassIdx] = userClassName
		self._logger.debug(usableUserClasses)
		# should it be nbveh or input_count
		# filter out unneeded user classes sid
		rows = cur.execute(
			"SELECT eid, oid, destination, sid, ent, ttime, travel/nbveh "
			"FROM %sCENT_O "
			"WHERE did = ? AND ent > ? AND ent < ? AND destination <> ?" %self._databasePrefix,
			(self._id, 0, self._numberOfIntervals+1, 0))
		for (originExtId, originId, destinationId, userClassIdx, interval, travelTime, travelDistance) in rows:
			if userClassIdx in usableUserClasses.keys():
				# save outputs indexed with centroid's Id or extId
				if self._outputExtId:
					origId = int(originExtId)
					destId = self._centDict[destinationId]
				else:
					origId = int(originId)
					destId = int(destinationId)
				if travelTime == -1:
					travelTime = 0
					travelDistance = 0
					continue   # only store ODs with demand
				#ivtt[(usableUserClasses[userClassIdx], interval)][originExtId-1][destinationExtId-1] = travelTime / 60			# minutes
				#dist[(usableUserClasses[userClassIdx], interval)][originExtId-1][destinationExtId-1] = travelDistance * 1000	# meters
				curLOS.execute('''UPDATE LOS SET traffic_ivtt=?, traffic_dist=? 
							   WHERE origin=? AND destination=? AND interval=? AND user_class=?''',
							   (travelTime/60, travelDistance*1000, origId, destId, interval, usableUserClasses[userClassIdx]))
				if curLOS.rowcount == 0:
					curLOS.execute('''INSERT INTO LOS (origin, destination, interval, user_class, traffic_ivtt, traffic_dist) 
								VALUES (?, ?, ?, ?, ?, ?)''',
								(origId, destId, interval, usableUserClasses[userClassIdx], travelTime/60, travelDistance*1000))
		connLOS.commit()
		#return ivtt, dist
	
	def _toSeconds(self, qDateTime):
		return qDateTime.time().hour()*3600 + qDateTime.time().minute()*60 + qDateTime.time().second()

	def _getToll(self, section, timeSta):
		''' 
		This function returns toll in cent/km for sections that have a valid attribute
		<GKSection::tollGroupAtt> according to the toll defined	over time (startTime 
		and endTime) and space (zone and direction).
		WARNING: make sure not to change self.toll between running the simulation and 
		extracting the tolls; otherwisem, the results will be incorrect
		'''
		try:
			tollGroupAtt = section.getType().getColumn("GKSection::tollGroupAtt", 1)
			road, zone, dir = section.getDataValueString(tollGroupAtt).split('_')
			return self.toll.getToll(road, dir, zone, timeSta)
		except:
			return 0
	
	def _getToll2(self, section, timeSta):
		''' 
		This function returns toll in cent/km for sections that have a valid attribute
		<GKSection::tollGroupAtt> and have some experiment variables defining the toll
		over time (startTime and endTime) and space (zone and direction)
		'''
		defaultToll = 0
		replication = self._model.getCatalog().find(self._id)
		experiment = replication.getExperiment()
		# get toll variables from the experiment's vars (or maybe from an external file)
		experimentVars = experiment.getVariables()
		# select the relevant toll variables from the experiment's pool of variables
		#prefixes = tuple(['_'.join([highway, zone, i]) for i in direction])
		tollGroupAtt = section.getType().getColumn("GKSection::tollGroupAtt", 1)
		prefix = section.getDataValueString(tollGroupAtt)
		if prefix != '':
			varNames = [i for i in experimentVars.keys() if i.startswith(prefix)]
			for varName in varNames:
				hwy, z, d, startTime, endTime = varName.split('_')
				startTime = int(startTime[:-2])*3600 + int(startTime[-2:])*60	# start time in sec
				endTime = int(endTime[:-2])*3600 + int(endTime[-2:])*60	# end time in sec
				tollPrice = float(experimentVars[varName])
				if startTime == 0 and endTime == 0:
					defaultToll = tollPrice
				elif timeSta > startTime and timeSta <= endTime:
					return tollPrice
		return defaultToll
	
	def _getWarmupIntervals(self, experiment):
		warmUpIntervals = 0
		warmUp = experiment.getWarmupTime() #  GKTimeDuration
		if warmUp.toSeconds()[0] > 0: # there is warm-up
			if experiment.getEngineMode() == GKExperiment.eOneShot:
				cycle = GKTimeDuration(0,0,0).addSecs(experiment.getDataValueIntByID(GKExperiment.cycleTimeAtt))
				warmUpIntervals = int((warmUp.toSeconds()[0] / cycle.toSeconds()[0]) + 0.5)
			else: # in a DUE there is only one path calculation for the whole warm-up
				warmUpIntervals = 1
		return warmUpIntervals
	
	def getODToll(self):	
		# get OD toll matrices from AIMSUN path assignment forest
		#toll = ODMatrices(self._iniFile, name = 'Toll Cost', modes = self._dtaUserClasses.keys())
		connLOS = sqlite3.connect(self._losDb)
		curLOS = connLOS.cursor()
		curLOS.execute("UPDATE LOS SET traffic_toll=0")
		if self._tollFunctionId == -1:
			connLOS.commit()
			return
		
		replication = self._model.getCatalog().find(self._id)
		experiment = replication.getExperiment()
		warmUpIntervals = self._getWarmupIntervals(experiment)
		forest = replication.getPathsForest()
		if forest is None:
			self._logger.error('Cannot retrieve the forest')
			#return toll
			return
		reader = NSPReader()
		reader.setForest(forest)
		userClassIds = reader.getVehicleIds() # list of int ids of user classes
		intervals = reader.getIntervals() # list of QDateTime
		self._logger.debug('The path file contains %i user class(es) and %i interval(s), '
							'of which %i for warm-up' % (len(userClassIds), len(intervals), warmUpIntervals))
		if len(userClassIds) != 0 and len(intervals) != 0:
			# loop over all user-classes
			for userClassIndex in range(0, len(userClassIds)):
				userClassName = None
				for key in self._dtaUserClasses:
					if self._model.getCatalog().find(userClassIds[userClassIndex]).getVehicle().getId() == self._dtaUserClasses[key]:
						userClassName = key
				# skip unwanted user-classes, e.g. subway vehicles and buses
				if key is None:
					continue
				# convert these intervals from based on cycle time (shortest path calculations) (e.g. 10 min)
				# to be based on statistics collection interval (e.g. 30 min)
				noOfIntervals = 0
				# should replace self._aggInterval with scenario.getInputData().getStatisticalInterval().toMinutes()
				intervalPerAggregationInterval = self._aggInterval / self._rcCycle
				tolls = np.zeros((self._numberOfCentroids, self._numberOfCentroids))
				volumes = np.zeros((self._numberOfCentroids, self._numberOfCentroids))
				# loop over all (aggregation) intervals for this specific user-class
				for intervalIndex in range(warmUpIntervals, len(intervals)):
					self._logger.debug('Processing interval %i for user-class %s' %(intervalIndex, userClassName))
					trips = reader.getODtrips(userClassIndex, intervalIndex)
					self._logger.debug('%i OD pairs have paths in interval %i' %(len(trips), intervalIndex))
					for j in range(0, len(trips)):
						originId = trips[j][0]
						originExtId = self._centDict[originId]
						destinationId = trips[j][1]
						destinationExtId = self._centDict[destinationId]
						# skip Toronto-to-Toronto trips (they don't use 407)
						#if originExtId <= self._numberOfCentroidsToronto and destinationExtId <= self._numberOfCentroidsToronto:
						#	continue
						pathIds = reader.getPathIds(originId, -1, destinationId, -1, userClassIndex, intervalIndex)
						#self._logger.debug('%i paths between OD %i-%i' %(len(pathIds), originExtId, destinationExtId))
						for pathId in pathIds:
							path = reader.getPath(pathId)
							volume = path.assignedVolume
							tollValue = 0.0
							for i in range(len(path.sectionIds)-1):
								section = self._model.getCatalog().find(path.sectionIds[i])
								toNode = section.getDestination()
								if toNode != None:
									nextSection = self._model.getCatalog().find(path.sectionIds[i+1])
									turn = toNode.getTurning(section, nextSection)
									costFunction = turn.getDataValueObjectByID(turn.dynamicFunctionAtt)
									if costFunction != None and costFunction.getId() == self._tollFunctionId:
										tollRate = self._getToll(section, self._toSeconds(intervals[intervalIndex])) / 100.0 # $/km
										tollValue += section.length3D() / 1000.0 * tollRate # $
							'''if tollValue != 0:
								self._logger.debug('tollValue*volume = %f' %(tollValue*volume))'''
							tolls[originExtId-1][destinationExtId-1] += tollValue*volume
							volumes[originExtId-1][destinationExtId-1] += volume
					noOfIntervals += 1
					if noOfIntervals % intervalPerAggregationInterval == 0:
						statsCollectionInterval = noOfIntervals/intervalPerAggregationInterval
						#toll[(userClassName, statsCollectionInterval)] = \
						#	np.divide(tolls, volumes, out=np.zeros_like(tolls), where=volumes!=0)
						for origin in range(volumes.shape[0]):
							for destination in range(volumes.shape[1]):
								if volumes[origin,destination] == 0:
									continue
								finalToll = tolls[origin,destination]/volumes[origin,destination]
								# save outputs indexed with centroid's Id or extId
								if self._outputExtId:
									origId = origin+1
									destId = destination+1
								else:
									origId = self._centDict.EIdToId(origin+1)
									destId = self._centDict.EIdToId(destination+1)
				
								curLOS.execute('''UPDATE LOS SET traffic_toll=? 
											   WHERE origin=? AND destination=? AND interval=? AND user_class=?''',
											   (finalToll, origId, destId, statsCollectionInterval, userClassName))
								if curLOS.rowcount == 0:
									curLOS.execute('''INSERT INTO LOS (origin, destination, interval, user_class, traffic_toll) 
													VALUES (?, ?, ?, ?, ?)''',
													(origId, destId, statsCollectionInterval, userClassName, finalToll))
						tolls = np.zeros((self._numberOfCentroids, self._numberOfCentroids))
						volumes = np.zeros((self._numberOfCentroids, self._numberOfCentroids))
						if statsCollectionInterval == self._numberOfIntervals:
							# ignore intervals in the network clearance period
							break
		connLOS.commit()
		#self._logger.debug(toll.keys())
		#return toll
	
	def getODToll2(self):
		# get OD toll matrices from database
		def getToll(tollGroupAtt, timeSta):
			''' 
			This function returns toll in cent/km for sections that have a valid attribute
			<GKSection::tollGroupAtt> and have some experiment variables defining the toll
			over time (startTime and endTime) and space (zone and direction)
			'''
			replication = self._model.getCatalog().find(self._id)
			experiment = replication.getExperiment()
			experimentVars = experiment.getVariables()
			defaultToll = 0
			# select the relevant toll variables from the tolls file
			#prefixes = tuple(['_'.join([highway, zone, i]) for i in direction])
			if tollGroupAtt != '':
				varNames = [i for i in experimentVars.keys() if i.startswith(tollGroupAtt)]
				for varName in varNames:
					hwy, z, d, startTime, endTime = varName.split('_')
					startTime = int(startTime[:-2])*3600 + int(startTime[-2:])*60	# start time in sec
					endTime = int(endTime[:-2])*3600 + int(endTime[-2:])*60	# end time in sec
					tollPrice = float(experimentVars[varName])
					if startTime == 0 and endTime == 0:
						defaultToll = tollPrice
					elif timeSta > startTime and timeSta <= endTime:
						return tollPrice
			return defaultToll
		
		toll = ODMatrices(self._iniFile, name = 'Toll Cost', modes = self._dtaUserClasses.keys())
		volume = ODMatrices(self._iniFile, name = 'Volume', modes = self._dtaUserClasses.keys())
		conn = sqlite3.connect(self._database)
		cur = conn.cursor()
		cur.execute("ATTACH DATABASE ? AS db2", (self._inputDB,))
		rows = cur.execute(
			"SELECT main.MEVEHSECTTRAJECTORY.oid, main.MEVEHSECTTRAJECTORY.exitTime-main.MEVEHSECTTRAJECTORY.travelTime AS start_time, "
			"main.VEHTRAJECTORY.sid AS user_class_id, (CAST(main.VEHTRAJECTORY.generationTime/1800 AS INT) + 1) AS dep_time, main.VEHTRAJECTORY.origin, main.VEHTRAJECTORY.destination, "
			"db2.tolled_sections.length, db2.tolled_sections.tollGroupAtt "
			"FROM main.MEVEHSECTTRAJECTORY "
			"INNER JOIN db2.tolled_sections ON main.MEVEHSECTTRAJECTORY.sectionId = db2.tolled_sections.id "
			"INNER JOIN main.VEHTRAJECTORY ON main.MEVEHSECTTRAJECTORY.oid = main.VEHTRAJECTORY.oid "
			"WHERE main.MEVEHSECTTRAJECTORY.did = ? "
			"ORDER BY main.MEVEHSECTTRAJECTORY.oid ASC",
			(self._id,))
		self._logger.debug('Finished extracting tolls from the traffic database')
		count = 0
		oidPrev = 0
		for (oid, start_time, userClassId, interval, originId, destinationId, sectionLen, tollGroupAtt) in rows:
			if interval > self._numberOfIntervals:
				continue
			userClassName = None
			for key in self._dtaUserClasses:
				if userClassId == self._dtaUserClasses[key]:
					userClassName = key
			if userClassName is None:
				self._logger.error('Cannot identify user-class id %i' %userClassId)
				continue
			originExtId = self._centDict[originId]
			destinationExtId = self._centDict[destinationId]
			toll[(userClassName, interval)][originExtId-1, destinationExtId-1] += getToll(tollGroupAtt, start_time) / 100.0 * (sectionLen/1000) # $
			if oid != oidPrev:
				# processing a new vehicle
				volume[(userClassName, interval)][originExtId-1, destinationExtId-1] += 1
				count += 1
				oidPrev = oid
		self._logger.debug('%i vehicles paying tools have been processed' %count)
		for userClassName in self._dtaUserClasses:
			for interval in range(1, self._numberOfIntervals+1):
				toll[(userClassName, interval)] = np.divide(toll[(userClassName, interval)],
														volume[(userClassName, interval)],
														out=np.zeros_like(volume[(userClassName, interval)]),
														where=volume[(userClassName, interval)]!=0)
		return toll
	
	def getSkimMatrices(self):
		'''
		This function returns ivtt, dist, and toll OD Matrices with 
		user-class names and intervals as the indexes
		ivtt and dist are extracted from MECENT_O table in DUE output database
		toll is extracted from the DUE path forest
		'''
		self._logger.debug('Extracting skim matrices of DUE result %i' % self._id)
		# get ivtt and dist
		#ivtt, dist = self.getODTravelTimeDistance()
		self.getODTravelTimeDistance()
		self._logger.debug('Finished extracting ivtt and distance')
		# get tolls
		#toll2 = self.getODToll2()
		#self._logger.debug('getODToll2')
		#self._logger.debug(toll2.sum())
		#toll = self.getODToll()
		self.getODToll()
		#self._logger.debug('getODToll')
		#self._logger.debug(toll.sum())
		self._logger.debug('Finish extracting skim matrices of DUE result %i' % self._id)
		#return ivtt, dist, toll
	
	#------------------------------Tolls Set up------------------------------#
	@property
	def tolls(self):
		return self._tolls
		
	@tolls.setter
	def tolls(self, value):
		self._tolls = value
	
	@tolls.deleter
	def tolls(self):
		del self._tolls
		
	def updateTolls(self):
		'''
		Nothing is added to the experiment's variables in case of empty tolls (dict)
		'''
		self._logger.debug('Updating tolls in AIMSUN model')
		self.setExperimentVars(**self.tolls.toDict())


import argparse
import os

def main():
	'''
		1. initialize tolls and load from file if needed
		2. initialize DUEModel
		3. load the DUEModel
		4. run the DUEModel
		5. calculate skim matrices (if needed) --> saved in sqlite Db
		6. unload the DUEModel
	'''
	
	def setup_logging(level,path='logging.yaml',):
		"""
		Setup logging configuration
		"""
		if os.path.exists(path):
			with open(path, 'rt') as f:
				config = yaml.safe_load(f.read())
			logging.config.dictConfig(config)
			if level is not None:
				logging.root.setLevel(getattr(logging, level))
		else:
			if level is None:
				logging.basicConfig(logging.INFO)
			else:
				logging.basicConfig(level=getattr(logging, level))

	
	argParser = argparse.ArgumentParser(description = 'Run DUE traffic assignment model')
	argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
	argParser.add_argument('-l', "--log_level", type = str.upper,
						choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
						help="Set the logging level")
	argParser.add_argument('id', type=int,
							help='The PT experiment Id')
	argParser.add_argument('-b', "--base_case", action='store_true')
	argParser.add_argument('-c', "--calculateLOS", action='store_true')
	argParser.add_argument('-d', "--losDb", default=None,
							help='Name of the level-of-service sqlite database')
	argParser.add_argument('-t', "--tollFile", default=None,
							help='File containing road tolls')
	args = argParser.parse_args()
		
	parser = ConfigParser(interpolation=ExtendedInterpolation())
	parser.read(args.iniFile)
	baseDir = parser['Paths']['BASE_DIR']
	setup_logging(args.log_level, path=os.path.join(baseDir, 'logging.yaml'))
	logger = logging.getLogger(__name__)
	logger.info(' '.join(sys.argv))
	
	
	tolls = roadTolls('')
	if args.tollFile is not None:
		tolls.readFromFile(args.tollFile)
	trafficModel = DUEModel(args.iniFile, args.id,
							calculateLOS=args.calculateLOS,
							baseCaseModel=args.base_case,
							tolls=tolls,
							losDb=args.losDb)
	trafficModel.loadNetwork()
	# checking road tolls
	logger.debug('Tolls of DUE result %i' %args.id)
	logger.debug(str(trafficModel.tolls))
	# run the simulation
	logger.debug('Start running DUE result %i' %args.id)
	trafficModel.run()
	#trafficLOSUpdate = None
	if args.calculateLOS:
		trafficModel.getSkimMatrices()
		'''trafficLOS = {}
		# get traffic level-of-Service matrices
		logger.debug('Extract traffic LOS of DUE result %i' %args.id)
		(trafficLOS['ivtt'], trafficLOS['dist'], trafficLOS['toll']) = trafficModel.getSkimMatrices()
		for key in trafficLOS:
			trafficLOS[key].save(skimMatDir + '/Traffic/' + key, sparse=True)'''
	
	'''trafficModel.saveNetwork()
	logger.debug('Finished saving AIMSUN model')'''
	trafficModel.unloadNetwork()

if __name__ == "__main__":
	sys.exit(main())