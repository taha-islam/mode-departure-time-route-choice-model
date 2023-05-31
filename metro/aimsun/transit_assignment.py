# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 15:32:41 2019

@author: islam
"""

import sys
SITEPACKAGES = 'C:\\Python27\\Lib\\site-packages'
if SITEPACKAGES not in sys.path:
	sys.path.append(SITEPACKAGES)

import os
import time
import logging
import numpy as np
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyQt5.QtCore import *
from configparser import ConfigParser, ExtendedInterpolation
import collections
from base import aimsunModel, aimsunModelType
from outputs import routeStats
from metro.tools.demand import centroidIdToEidDict, transitODList, ODMatrices
from fares import transitFares

class PTModel(aimsunModel):
	"""A class for Aimsun static public transit assignment"""

	def __init__(self, 
				iniFile, 
				ptExperimentId, 
				console=None, 
				model=None, 
				calculateLOS=False, 
				baseCaseModel=False, 
				fares=None,
				losDB=None):
		self._logger = logging.getLogger(__name__)
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		super(PTModel, self).__init__(iniFile, ptExperimentId, aimsunModelType.eTransit, 
										console, model, calculateLOS, baseCaseModel, losDB=losDB)
		#self._skimMatDir = parser['Paths']['SKIM_MATRICES_DIR']
		transitAssignmentParam = parser['Transit Assignment']
		self._noOfIter = int(transitAssignmentParam['NUMBER_OF_ITERATIONS'])
		self.ptSkimMatrixNames = transitAssignmentParam['ptSkimMatrixNames'].strip().split(',')
		self._ptSkimMatrixNamesInUse = transitAssignmentParam['ptSkimMatrixNamesInUse'].strip().split(',')
		self._ptLOSNamesInDB = dict(zip(self._ptSkimMatrixNamesInUse, 
			transitAssignmentParam['ptLOSNamesInDB'].strip().split(',')))
		self.distanceFareFun = int(transitAssignmentParam['DISTANCE_FARE_FUNCTION_ID'])
		self.ivttFun = int(transitAssignmentParam['IVTT_FUNCTION_ID'])
		ptUserClassNames = transitAssignmentParam['ptUserClassNames'].strip().split(',')
		self._ptUserClasses = {}	# dictionary <userClassName>:<userClassId>
		for userClassName in ptUserClassNames:
			self._ptUserClasses[userClassName] = int(transitAssignmentParam[userClassName])
		if baseCaseModel:
			self._ptExperimentsIds = [int(x) for x in parser['Transit Assignment']['base_ptExperimentsIds'].strip().split(',')]
		else:
			self._ptExperimentsIds = [int(x) for x in parser['Transit Assignment']['ptExperimentsIds'].strip().split(',')]
		if self._id in self._ptExperimentsIds:
			self._ptAssignmentIndex = self._ptExperimentsIds.index(self._id) + 1
		else:
			self._ptAssignmentIndex = None
		self._ODList = transitODList(iniFile)
		if fares is None:
			self._fares = transitFares()
			self._fares.fillInDefaultFares()
		else:
			self._fares = fares
		self._distanceFareFnId = 258
		self._ivttFnId = 250
		self._boardingCostFnId = 247
		self._waitTimeFnId = 256
		self._walkSpeed = 5	# km/h
		self._valueOfTime = 15	#$/hour
		self._keepStatsInMemory = True

	'''==================================================================================
	Basics
	'''
	def _checkValidReplication(self):
		experiment = self._getExperiment()
		return (experiment is not None) and (experiment.isA("MacroPTExperiment"))

	def run(self):
		'''This function runs PTExperiment with id self._id
		
		'''
		super(PTModel, self).run()
		if self._model is not None:
			macroPTExperiment = self._getExperiment()
			if not self._checkValidReplication():
				self._logger.error('Cannot find PT Experiment %i' % self._id)
				return -1
			else:
				# configure scenario's output data
				self.removeDatabase()
				scenario = macroPTExperiment.getScenario()
				scenario.getDemand().setFactor(str(self._demandMulFactor))
				outputDataConfig = scenario.getOutputData()
				outputDataConfig.enableStoreStatistics(self._keepStatsInMemory)
				outputDataConfig.setGroupStatistics(False)
				outputDataConfig.setActivatePathStatistics(self._calculateLOS)
				outputDataConfig.setGenerateSkims(False)
				scenario.setOutputData(outputDataConfig)
				# configure experiment's parameters
				experimentParam = macroPTExperiment.getParameters()
				experimentParam.setMaxIterations(self._noOfIter)
				#experimentParam.setTransferPenalty()
				#experimentParam.setIsMultiRouting()
				#experimentParam.setWalkingOnlyAllowed()
				#experimentParam.setRGap()
				# run the PT experiment
				selection = []
				self._logger.info('Starting PT experiment %i' % self._id)
				GKSystem.getSystem().executeAction("execute", macroPTExperiment,
											selection, time.strftime("%Y%m%d-%H%M%S"))
				self._outputsInMemory = self._keepStatsInMemory
				# store the skim matrices of this experiment
				#self.storePTSkimMatrices(macroPTExperiment)		
				self._logger.info('PT experiment %i is completed' % self._id)
			return 0
		else:
			self._logger.error('cannot run experiment %i' % self._id)
			return -1
	
	#------------------------------Transit LOS------------------------------#
	def getSkimMatrices(self, interval):
		'''
		This function returns ivtt, accT, egrT, fareand crowdedness OD Matrices with 
		user-class names and intervals as the indexes
		all statistics are extracted from the PT experiment path forest
		'''
		macroPTExperiment = self._model.getCatalog().find(self._id)
		if macroPTExperiment is None:
			self._logger.error('Cannot find PT Experiment %i' % self._id)
			return None
		if not macroPTExperiment.getScenario().getOutputData().getActivatePathStatistics():
			self._logger.error('Path statistics of PT Experiment %i were not collected' % self._id)
			return None
		ttcLayers = [728983, 728984, 728985, 728986, 728987, 728988, 52052, 47440]
		miWayLayers = [52053]

		self._logger.debug('Extracting skim matrices of PT experiment %i' % self._id)
		ivtt = ODMatrices(self._iniFile, name = 'Travel Time', modes = self._ptUserClasses.keys())
		accT = ODMatrices(self._iniFile, name = 'Accesss Time', modes = self._ptUserClasses.keys())
		egrT = ODMatrices(self._iniFile, name = 'Egresss Time', modes = self._ptUserClasses.keys())
		fare = ODMatrices(self._iniFile, name = 'Fare', modes = self._ptUserClasses.keys())
		crwd = ODMatrices(self._iniFile, name = 'Crowdedness', modes = self._ptUserClasses.keys())
		wait = ODMatrices(self._iniFile, name = 'Waiting Time', modes = self._ptUserClasses.keys())
		line1Load = ODMatrices(self._iniFile, name = 'Line 1 Load', modes = self._ptUserClasses.keys())
		centDict = centroidIdToEidDict(self._iniFile)
		usersNames = {}
		for key in self._ptUserClasses:
			usersNames[self._ptUserClasses[key]] = key
		forest = macroPTExperiment.getForest()
		for originId in forest.getOriginCentroids():
			originExtId = centDict[originId]
			originPos = forest.getOriginCentroidPos(originId)
			for destinationId in forest.getDestinationCentroids():
				destinationExtId = centDict[destinationId]
				destinationPos = forest.getDestinationCentroidPos(destinationId)
				for userId in forest.getUsers():
					odFare = 0
					odAccessT = 0
					odEgressT = 0
					odIvtt = 0
					userPos = forest.getUserPos(userId)
					odPair = forest.getPTODPair(userPos, originPos, destinationPos)
					for strategy in odPair.strategies():
						for path in strategy.paths():
							pathFare = pathAccessT = pathEgressT = pathIvtt = 0
							passingLine1 = False
							prevPTLine = None
							for pathLink in path.path():
								if pathLink.getLinkType() == 1:	#PTLink.LinkType.eSection:
									pathIvtt += pathLink.getInVehicleTime(userPos)
								elif pathLink.getLinkType() == 3:	#PTLink.LinkType.eAccess:
									pathAccessT += pathLink.getWalkingTime(userPos)
								elif pathLink.getLinkType() == 4:	#PTLink.LinkType.eEgress:
									pathEgressT += pathLink.getWalkingTime(userPos)
								elif pathLink.getLinkType() == 9:	#PTLink.LinkType.eBoarding:
									ptLine = self._model.getCatalog().find(pathLink.getObjectId())
									flatFareCompensation = 0
									if prevPTLine is not None:
										if (prevPTLine.getLayer().getId() in ttcLayers and ptLine.getLayer().getId() in ttcLayers):
											flatFareCompensation = self._fares['TTC'][0]
											if ptLine.getName() == 'LINE 1 (YONGE-UNIVERSITY) - DIRECTION: 0':
												passingLine1 = True
										elif(prevPTLine.getLayer().getId() in miWayLayers and ptLine.getLayer().getId() in miWayLayers):
											flatFareCompensation = self._fares['MIWAY'][0]
									pathFare += pathLink.getFare(userPos) - flatFareCompensation
									prevPTLine = ptLine
							odFare += pathFare * strategy.factor() * path.factor()
							odAccessT += pathAccessT * strategy.factor() * path.factor()
							odEgressT += pathEgressT * strategy.factor() * path.factor()
							odIvtt += pathIvtt * strategy.factor() * path.factor()
							if passingLine1:
								line1Load[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] += odPair.volume() * strategy.factor() * path.factor()
					# update for each user-class, interval, origin, and destination combination
					ivtt[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odIvtt
					accT[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odAccessT
					egrT[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odEgressT
					fare[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odFare
					crwd[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odPair.crowdingDiscomfort()
					wait[(usersNames[userId], interval)][originExtId-1][destinationExtId-1] = odPair.waitingTime()
		self._logger.debug('Finish extracting skim matrices of PT experiment %i' % self._id)
		line1Load.save(os.path.join(self._outputDir, 'line 1'), sparse=True, intervals=[interval])
		return ivtt, accT, egrT, fare, crwd, wait

	#------------------------------Fares Set up------------------------------#
	def setFare(self, fares):
		if isinstance(fares, transitFares):
			self._fares = fares
		else:
			self._logger.error('Invalid transit fare')
	
	def getFare(self):
		return self._fares
	
	def _setPTLinesFares(self, PTLineDescription, boardingFare, distanceFare, delayFunction, distanceFareFunction):
		count = 0
		#Get all objects of that type
		for types in self._model.getCatalog().getUsedSubTypesFromType(self._model.getType("GKPublicLine")):
			for PTLine in types.itervalues():
				if PTLine.getDescription() in PTLineDescription:
					PTLine.setBoardingFare(boardingFare)
					PTLine.setDistanceFare(distanceFare)
					stops = [x for x in PTLine.getStops() if x is not None]
					for stop1, stop2 in zip(stops, stops[1:]):
						if distanceFareFunction is not None:
							PTLine.setFareFunction(stop1, stop2, distanceFareFunction)
						if delayFunction is not None:
							PTLine.setDelayFunction(stop1, stop2, delayFunction)
					count += 1
		self._logger.debug('Fares of %i %s lines have been updated' %(count, PTLineDescription))
	
	def updateFares(self):
		distanceFareFn = self._model.getCatalog().find(self._distanceFareFnId)
		ivttFn = self._model.getCatalog().find(self._ivttFnId)
		# GO
		self._setPTLinesFares(["GO Rail"],
							self._fares['GO'][0], self._fares['GO'][1],
							ivttFn, distanceFareFn)
		# Downtown express
		self._setPTLinesFares(["TTC Bus - Downtown Express Routes with Extra Fares Required"], 
							self._fares['TTC_EXPRESS'][0], self._fares['TTC_EXPRESS'][1],
							ivttFn, distanceFareFn)
		# Regular TTC service
		self._setPTLinesFares(["Subway", "Streetcar", "TTC Bus - Regular Routes", "TTC Bus - Express Routes", "TTC Bus - Downtown Express Routes", "TTC Bus - Extra Fares Required", "TTC Bus - Blue Night Routes"], 
							self._fares['TTC'][0], self._fares['TTC'][1],
							ivttFn, distanceFareFn)
		# MiWay
		self._setPTLinesFares(["MiWay Bus - Islington Subway Station"],
							self._fares['MIWAY'][0], self._fares['MIWAY'][0],
							ivttFn, distanceFareFn)
		
	def updatePTStopWalkDistances(self, clearAllWalkingDistances=False):
		'''print 'Fares:'
		for key in self._fares:
			print self._fares[key]'''
		boardingCostFn = self._model.getCatalog().find(self._boardingCostFnId)
		waitTimeFn = self._model.getCatalog().find(self._waitTimeFnId)
		busStopType = self._model.getType("GKBusStop")
		flatFareCompensation = max(self._fares['TTC'][0], self._fares['MIWAY'][0])	# they have to be equal to have TP-Bi = 0
																	# this term is added to the walking time between stops
																	# but it'll problematic for transfers occurring at the same stop
		
		# create a dictionary/map of all existing stops in the model hashed by their extId, with the ext id as the key and a list of stops with this ext id is the value (to save space, it should be replaced by stop id)
		allStops = {}
		for types in self._model.getCatalog().getUsedSubTypesFromType(busStopType):
			for stop in types.itervalues():
				stopExtId = str(stop.getExternalId())
				if allStops.get(stopExtId) is None:
					allStops[stopExtId] = [stop]
				else:
					allStops[stopExtId].append(stop)
		# loop through all PT stops
		numberOfStops = 0
		for types in self._model.getCatalog().getUsedSubTypesFromType(busStopType):
			for stop in types.itervalues():
				numberOfStops += 1
				walkingTimeObject = GKWalkingTime()
				# clearing all walking times
				if clearAllWalkingDistances:
					stop.setWalkingTime(walkingTimeObject)
					continue

				# get the stops connected to this stop
				attr = busStopType.getColumn("connectingStops", GKType.eSearchOnlyThisType)
				connectingStops = str(stop.getDataValueString(attr)).split()
				# get this stop's agency
				attr = busStopType.getColumn("agencyIDs", GKType.eSearchOnlyThisType)
				agency = stop.getDataValueInt(attr)
				# for each connected stop
				for stopExtId in connectingStops:
					connectedStops = allStops.get(stopExtId)
					if connectedStops is None:
						continue
					# loop if more than one stop has the same ext id
					for connectedStop in connectedStops:
						# set the walking time to the centroid-to-stop distance / avg walking speed
						try:
							walkingTime = connectedStop.absolutePosition().distance3D(stop.absolutePosition()) / (self._walkSpeed * 1000.0 / 60)
						except:
							self._logger.error('stop %i, connectedStop %i' %(stop.getId(),connectedStop.getId()))
							self._logger.error('stop %s, connectedStop %s' %(stop.getName(),connectedStop.getName()))
							self._logger.error('stop %s, connectedStop %s' %(stop.getType().getName(),connectedStop.getType().getName()))
							stop = self._model.getCatalog().find(stop.getId())
							connectedStop = self._model.getCatalog().find(connectedStop.getId())
							self._logger.error('stop %s, connectedStop %s' %(stop.getType().getName(),connectedStop.getType().getName()))
						else:
							# if transferring between services, add compensation for the self._fares['TTC'][0] which is subtracted from all services' boarding fares
							connectedStopAgency = connectedStop.getDataValueInt(attr)
							if connectedStopAgency != agency:
								walkingTime += flatFareCompensation / self._valueOfTime * 60
							elif connectedStopAgency == 1:
								# to cancel negative transfer penalty and the boarding fare of the next vehicle
								walkingTime += (flatFareCompensation - self._fares['TTC'][0]) / self._valueOfTime * 60
							elif connectedStopAgency == 9:
								# to cancel negative transfer penalty and the boarding fare of the next vehicle
								walkingTime += (flatFareCompensation - self._fares['MIWAY'][0]) / self._valueOfTime * 60
							elif connectedStopAgency == 8:
								# to cancel negative transfer penalty
								# for GO the boarding fare is applied during transfers
								walkingTime += flatFareCompensation / self._valueOfTime * 60
						# set the walking time from stop to the connected stop
						walkingTimeObject.setWalkingTimes({connectedStop: walkingTime})
				try:
					# set all walking times
					stop.setWalkingTime(walkingTimeObject)
					# set the boarding cost function
					stop.setBoardingCostFunction(boardingCostFn)
					# set the waiting time function
					stop.setWaitingTimeFunction(waitTimeFn)
				except:
					self._logger.error('stop %i' %stop.getId())
		self._logger.debug('Walking distances between %i stops in PT experiment %i '
							'have been updated' %(numberOfStops, self._id))
	
	#------------------------------Transit Route Speed Set up------------------------------#
	def _getMeanOfSecionTimeSeries(self, DUEResult, section, stat, startTime, endTime):
		''' 
			DUEResult: the DTA UE result object
			section: the section object
			stat: string and takes one value of: flow, density, speed, count, etc.
			startTime, endTime: integer and equals to hour*3600 + min*60 + sec
				e.g, 6am --> 6*3600+0*60+0=21600
		'''
		# setting up the start and end times/dates
		simulationDate = DUEResult.getExperiment().getScenario().getDate()
		#simulationDate = QDate(year, month, day)
		startTimeHour = startTime/3600
		startTimeMinute = (startTime - startTimeHour * 3600)/60
		startTimeSecond = startTime - startTimeHour * 3600 - startTimeMinute * 60
		startTime = QDateTime(simulationDate)
		startTime.setTime(QTime(startTimeHour, startTimeMinute, startTimeSecond))
		endTimeHour = endTime/3600
		endTimeMinute = (endTime - endTimeHour * 3600)/60
		endTimeSecond = endTime - endTimeHour * 3600 - endTimeMinute * 60
		endTime = QDateTime(simulationDate)
		endTime.setTime(QTime(endTimeHour, endTimeMinute, endTimeSecond))

		sectionType = self._model.getType('GKSection')
		attName = 'DYNAMIC::GKSection_' + stat + '_' + str(DUEResult.getId()) + '_0'

		sectionAtt = sectionType.getColumn(attName, GKType.eSearchOnlyThisType)
		timeSeries = section.getDataValueTS(sectionAtt)
		if timeSeries is None:
			return None
		else:
			result = timeSeries.getMean(0, startTime, endTime, True)
			if result == -1:
				return None
			else:
				return result
	
	#------------------------------Statistics------------------------------#
	def _getSectionSpeedFromAttributeOverride(self, section, PTAssignmentIndex):
		sectionType = self._model.getType('GKSection')
		speedAtt = sectionType.getColumn('GKSection::speedAtt', GKType.eSearchOnlyThisType)		
		attributesOverrideName = 'PT Assignment - sections speed ' + str(PTAssignmentIndex)
		attOverride = self._model.getCatalog().findByName(attributesOverrideName, self._model.getType("GKNetworkAttributesOverride"))
		if attOverride.hasObject(section):
			sectionData = attOverride.getObjectData(section)
			for col in sectionData:
				if col == speedAtt:
					return sectionData[col]
		else:
			#self._logger.debug('Section %i does not exist in attribute override %i' %(section.getId(), attOverride.getId()))
			return -1
	
	def getSubpathOccupancy(self, id, ptLineId=0, vehicleId=0):
		sectionType = self._model.getType('GKSection')
		subPath = self._model.getCatalog().find(id)
		macroPTExperiment = self._model.getCatalog().find(self._id)
		occupancy = []
		space = []
		length = []
		speed = []
		for section in subPath.getRoute():
			attName = 'GKSection:Main#ptVCRatio;Originator#%i;PTLine#%i;VehicleType#%i' % (self._id, ptLineId, vehicleId)
			sectionAtt = sectionType.getColumn(attName, GKType.eSearchOnlyThisType)
			occupancy.append(section.getDataValueInTS(sectionAtt, GKTimeSerieIndex(0))[0])
			topObjects = section.getTopObjects()
			location = ''
			if topObjects is not None:
				for object in topObjects:
					if object.isA('GKBusStop'):
						location = object.getName()
			space.append(location)
			length.append(section.length3D()/1000)	# km
			sectionSpeed = self._getSectionSpeedFromAttributeOverride(section, self._ptAssignmentIndex)
			if sectionSpeed > 0:
				speed.append(sectionSpeed)	# km/h
			else:
				speed.append(section.getSpeed())	# km/h
		result = routeStats('Occupancy of %s' %subPath.getName())
		result.time = [macroPTExperiment.getScenario().getDemand().initialTime().toString()]
		result.space = space
		result.length = length
		result.speed = speed
		result.series = np.array(occupancy)
		return result
	
	def getSubpathCapacity(self, id, ptLineId=0, vehicleId=0):
		sectionType = self._model.getType('GKSection')
		subPath = self._model.getCatalog().find(id)
		macroPTExperiment = self._model.getCatalog().find(self._id)
		capacity = []
		space = []
		length = []
		speed = []
		for section in subPath.getRoute():
			attName = 'GKSection:Main#ptCapacity;Originator#%i;PTLine#%i;VehicleType#%i' % (self._id, 0, vehicleId)
			sectionAtt = sectionType.getColumn(attName, GKType.eSearchOnlyThisType)
			capacity.append(section.getDataValueInTS(sectionAtt, GKTimeSerieIndex(0))[0])
			topObjects = section.getTopObjects()
			location = ''
			if topObjects is not None:
				for object in topObjects:
					if object.isA('GKBusStop'):
						location = object.getName()
			space.append(location)
			length.append(section.length3D()/1000)	# km
			sectionSpeed = self._getSectionSpeedFromAttributeOverride(section, self._ptAssignmentIndex)
			if sectionSpeed > 0:
				speed.append(sectionSpeed)	# km/h
			else:
				speed.append(section.getSpeed())	# km/h
		result = routeStats('Capacity of %s' %subPath.getName())
		result.time = [macroPTExperiment.getScenario().getDemand().initialTime().toString()]
		result.space = space
		result.length = length
		result.speed = speed
		result.series = np.array(capacity)
		return result

	def getSubpathVolume(self, id, ptLineId=0, vehicleId=0):
		subPath = self._model.getCatalog().find(id)
		occupancy = self.getSubpathOccupancy(id, ptLineId, vehicleId)
		capacity = self.getSubpathCapacity(id, ptLineId, vehicleId)		
		result = routeStats('Volume of %s' %subPath.getName())
		result.time = occupancy.time
		result.space = occupancy.space
		result.length = occupancy.length
		result.speed = occupancy.speed
		result.series = occupancy.series * capacity.series / 100
		return result
	
	def getSubpathAdjustedOccupancy(self, id, ptLineId=0, vehicleId=0, prevExperiment = None):
		subPath = self._model.getCatalog().find(id)
		adjustedCapacity = self.getSubpathAdjustedCapacity(id, ptLineId, vehicleId, prevExperiment)
		adjustedVolume = self.getSubpathAdjustedVolume(id, ptLineId, vehicleId, prevExperiment)		
		result = routeStats('Adjusted Occupancy of %s' %subPath.getName())
		result.time = adjustedCapacity.time
		result.space = adjustedCapacity.space
		result.length = adjustedCapacity.length
		result.speed = adjustedCapacity.speed
		result.series = adjustedVolume.series / adjustedCapacity.series * 100
		return result
		
	def getSubpathAdjustedCapacity(self, id, ptLineId=0, vehicleId=0, prevExperiment = None):
		capacity = self.getSubpathCapacity(id, ptLineId, vehicleId)
		if prevExperiment is None:
			return capacity
		subPath = self._model.getCatalog().find(id)
		prevExperiment.retrieveOutput()
		prevCapacity = prevExperiment.getSubpathCapacity(id, ptLineId, vehicleId)
		
		result = routeStats('Adjusted Capacity of %s' %subPath.getName())
		result.time = capacity.time
		result.space = capacity.space
		result.length = capacity.length
		result.speed = capacity.speed
		maxShift = np.ones_like(prevCapacity.totalLength) * 0.5	# half hour or 30 minutes
		result.series = np.minimum(prevCapacity.totalLength/prevCapacity.avgSpeed, maxShift) / 0.5 * prevCapacity.series \
						+ (0.5 - np.minimum(capacity.totalLength/capacity.avgSpeed, maxShift)) / 0.5 * capacity.series
		return result
	
	def getSubpathAdjustedVolume(self, id, ptLineId=0, vehicleId=0, prevExperiment = None):
		volume = self.getSubpathVolume(id, ptLineId, vehicleId)
		if prevExperiment is None:
			return volume
		subPath = self._model.getCatalog().find(id)
		prevExperiment.retrieveOutput()
		prevVolume = prevExperiment.getSubpathVolume(id, ptLineId, vehicleId)
		
		result = routeStats('Adjusted Volume of %s' %subPath.getName())
		result.time = volume.time
		result.space = volume.space
		result.length = volume.length
		result.speed = volume.speed
		maxShift = np.ones_like(prevVolume.totalLength) * 0.5	# half hour or 30 minutes
		result.series = np.minimum(prevVolume.totalLength/prevVolume.avgSpeed, maxShift) / 0.5 * prevVolume.series \
						+ (0.5 - np.minimum(volume.totalLength/volume.avgSpeed, maxShift)) / 0.5 * volume.series
		return result
	
	#------------------------------Extras------------------------------#
	def getSkimMatricesFromSkimMatrices(self, interval):
		'''
		This function returns ivtt, ovtt, and fare OD Matrices with 
		user-class names and intervals (just one interval and the 
		others have zero cells) as the indexes
		ivtt, ovtt, and fare are extracted from the automatically created skim matrices
		'''
		ivtt = ODMatrices(self._iniFile, name = 'In-Vehicle Travel Time', modes = self._ptUserClasses.keys())
		ovtt = ODMatrices(self._iniFile, name = 'Out-of-Vehicle Travel Time', modes = self._ptUserClasses.keys())
		fare = ODMatrices(self._iniFile, name = 'Fare Cost', modes = self._ptUserClasses.keys())
		
		ptExperiment = self._model.getCatalog().find(self._id)
		for userClassName in self._ptUserClasses:
			userClassId = self._ptUserClasses[userClassName]
			skimMatrixFullName = ''.join(['PT Skim - In vehicle Time: ', str(userClassId), \
											': ', userClassName, ' - ', ptExperiment.getName()])
			ivttMatrix = self._model.getCatalog().findByName(skimMatrixFullName)
			skimMatrixFullName = ''.join(['PT Skim - Walking Time: ', str(userClassId), \
											': ', userClassName, ' - ', ptExperiment.getName()])
			ovttMatrix = self._model.getCatalog().findByName(skimMatrixFullName)
			skimMatrixFullName = ''.join(['PT Skim - Fare: ', str(userClassId), \
											': ', userClassName, ' - ', ptExperiment.getName()])
			fareMatrix = self._model.getCatalog().findByName(skimMatrixFullName)
			centroids = ivttMatrix.getCentroidConfiguration().getCentroids()
			for origin in centroids:
				for destination in centroids:
					ivtt[(userClassName, interval)][int(origin.getExternalId())-1][int(destination.getExternalId())-1] = \
							ivttMatrix.getTrips(origin, destination)
					ovtt[(userClassName, interval)][int(origin.getExternalId())-1][int(destination.getExternalId())-1] = \
							ovttMatrix.getTrips(origin, destination)
					fare[(userClassName, interval)][int(origin.getExternalId())-1][int(destination.getExternalId())-1] = \
							fareMatrix.getTrips(origin, destination)
		return ivtt, ovtt, fare
	
	def _findSubLayersIds(self, layer):
		''' find the ids of all sublayers in a given layer '''
		subLayersIds = []
		subLayers = layer.getLayers()
		#loop through all sublayers
		for subLayer in subLayers:
			subLayersIds.append(subLayer.getId())
			secondLevelLayersIds = self._findSubLayersIds(subLayer)
			if secondLevelLayersIds != None:
				subLayersIds = subLayersIds + secondLevelLayersIds
		return subLayersIds
	

from metro.tools import tools
import argparse
import pickle

def main():
	'''
		1. initialize fares and load from file if needed
		2. initialize PTModel
		3. load the PTModel
		4. run the PTModel
		5. calculate skim matrices (if needed) --> saved in sqlite Db
		6. unload the PTModel
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

	
	argParser = argparse.ArgumentParser(description = 'Run one-interval public transit assignment model')
	argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
	argParser.add_argument('-l', "--log_level", type = str.upper,
						choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
						help="Set the logging level")
	argParser.add_argument('id', type=int,
							help='The PT experiment Id')
	argParser.add_argument('-i', '--interval', type=int,
							help='The PT experiment Id')
	argParser.add_argument('-b', "--base_case", action='store_true')
	argParser.add_argument('-c', "--calculateLOS", action='store_true')
	argParser.add_argument('-d', "--losDb", default=None,
							help='Name of the level-of-service sqlite database')
	argParser.add_argument('-f', "--fareFile", default=None,
							help='File containing transit fares')
	args = argParser.parse_args()
	
	parser = ConfigParser(interpolation=ExtendedInterpolation())
	parser.read(args.iniFile)
	baseDir = parser['Paths']['BASE_DIR']
	setup_logging(args.log_level, path=os.path.join(baseDir, 'logging.yaml'))
	logger = logging.getLogger(__name__)
	logger.info(' '.join(sys.argv))
	
	fares = transitFares()
	if args.fareFile is not None:
		fares.readFromFile(args.tollFile)
	else:
		logger.info('The fares defined in the model will be used')
	
	ptUserClasses = parser['Transit Assignment']['ptUserClassNames'].strip().split(',')
	if args.base_case:
		DUEResultId = int(parser['Traffic Assignment']['BASE_DUE_RESULT_ID'])
		databaseTraffic = parser['Paths']['BASE_SQLITE_DB_OUTPUT_TRAFFIC']
		skimMatDir = parser['Paths']['BASE_SKIM_MATRICES_DIR']
	else:
		DUEResultId = int(parser['Traffic Assignment']['DUE_RESULT_ID'])
		databaseTraffic = parser['Paths']['SQLITE_DB_OUTPUT_TRAFFIC']
		skimMatDir = parser['Paths']['SKIM_MATRICES_DIR']
	
	transitModel = PTModel(args.iniFile, args.id,
							calculateLOS=args.calculateLOS,
							baseCaseModel=args.base_case,
							losDb=args.losDb)
	transitModel.loadNetwork()
	# updating speeds, fares, and transfers walk distances
	logger.debug('Updating fares of PT experiment %i' %args.id)
	transitModel.setFare(fares)
	transitModel.updateFares()
	logger.debug(str(transitModel.getFare()))
	logger.debug('Updating transfer walk distances for PT experiment %i' %args.id)
	transitModel.updatePTStopWalkDistances()
	transitModel.setSectionSpeedForPTAssignment(args.interval, DUEResultId, databaseTraffic)
	# run the simulation
	logger.debug('Start running PT experiment %i' %args.id)
	transitModel.run()
	if args.calculateLOS:
		# get transit level-of-Service matrices
		transitLOS = {}
		logger.debug('Extracting transit LOS of PT experiment %i' %args.id)
		if args.interval == 1:
			(transitLOS['ivtt'], transitLOS['accT'], transitLOS['egrT'], 
				transitLOS['fare'], transitLOS['crwd'], transitLOS['wait']) = transitModel.getSkimMatrices(args.interval)
		else:
			transitLOS['ivtt'] = ODMatrices(args.iniFile, name = 'Travel Time', modes = ptUserClasses)
			transitLOS['accT'] = ODMatrices(args.iniFile, name = 'Accesss Time', modes = ptUserClasses)
			transitLOS['egrT'] = ODMatrices(args.iniFile, name = 'Egresss Time', modes = ptUserClasses)
			transitLOS['fare'] = ODMatrices(args.iniFile, name = 'Fare', modes = ptUserClasses)
			transitLOS['crwd'] = ODMatrices(args.iniFile, name = 'Crowdedness', modes=ptUserClasses)
			transitLOS['wait'] = ODMatrices(args.iniFile, name = 'Waiting Time', modes=ptUserClasses)
			ivtt, accT, egrT, fare, crwd, wait = transitModel.getSkimMatrices(args.interval)
			for key in transitLOS:
				transitLOS[key].load(skimMatDir + '/Transit/' + key, sparse=True)
			transitLOS['ivtt'] += ivtt
			transitLOS['accT'] += accT
			transitLOS['egrT'] += egrT
			transitLOS['fare'] += fare
			transitLOS['crwd'] += crwd
			transitLOS['wait'] += wait
		for key in transitLOS:
			transitLOS[key].save(skimMatDir + '/Transit/' + key, sparse=True)
	#transitModel.saveNetwork()
	transitModel.unloadNetwork()

if __name__ == "__main__":
	sys.exit(main())	