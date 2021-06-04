# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 15:07:14 2019

@author: islam
"""

import sys
SITEPACKAGES = 'C:\\Python27\\Lib\\site-packages'
if SITEPACKAGES not in sys.path:
	sys.path.append(SITEPACKAGES)

import os
import time
import sqlite3
import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyQt5.QtCore import *
from .aimsun_network import aimsunNetwork

class aimsunModelType:
	eNone = -1
	eMicro = 0
	eMeso = 1
	eMacro = 2
	eTransit = 3

class aimsunModel(aimsunNetwork):
	''' 
	A base class for Aimsun models
	initialized with .ini file + id + model type + optional(console, model, and calculateLOS)
	loadNetwork			:	to load the model given in the ini file
	unloadNetwork		:	to unload Aimsun model
	run					:	run the simulation
	calculateLOS		:	get traffic or transit LOS OD matrices with 
							user-class names and intervals as the indexes
	'''
	def __init__(self, 
				iniFile, 
				id, 
				modelType, 
				console=None, 
				model=None, 
				calculateLOS=False,
				baseCaseModel=False,
				angFile=None,
				losDb=None):
		self._id = id	# AIMSUN unique id of replication/result/PT experiment
		self._type = modelType
		self._calculateLOS = calculateLOS
		self._baseCaseModel = baseCaseModel
		self._losDb = losDb
		
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self._inputDB = parser['Paths']['SQLITE_DB_INPUT']
		self._outputDir = parser['Paths']['OUTPUT_DIR']
		self._demandDir = parser['Paths']['DEMAND_DIR']
		self._numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		self._numberOfCentroids = int(parser['Demand']['numberOfCentroids'])
		#self._numberOfCentroidsToronto = int(parser['Demand']['numberOfCentroidsToronto'])
		self._simStartTime = int(parser['Trip Assignment']['SIMULATION_START_TIME'])
		self._outputExtId = int(parser.get('Trip Assignment','OUTPUT_EXTERNAL_ID', fallback=1))
		if modelType == aimsunModelType.eMicro or \
			modelType == aimsunModelType.eMeso or \
			modelType == aimsunModelType.eMacro:
			self._demandMulFactor = float(parser['Traffic Assignment']['DEMAND_MULTIPLICATION_FACTOR'])
			if self._baseCaseModel:
				self._database = parser['Paths']['BASE_SQLITE_DB_OUTPUT_TRAFFIC']
			else:
				self._database = parser['Paths']['SQLITE_DB_OUTPUT_TRAFFIC']
			'''try:
				self._expVarFileName = parser['Paths']['TOLLS_FILE']
			except:
				self._expVarFileName = os.path.join(self._baseDir, 'tolls.txt')
			else:
				if self._expVarFileName == '':
					self._expVarFileName = os.path.join(self._baseDir, 'tolls.txt')'''
		elif modelType == aimsunModelType.eTransit:
			self._simPTInterval = int(parser['Transit Assignment']['PT_SIMULATION_INTERVAL'])
			self._demandMulFactor = float(parser['Transit Assignment']['DEMAND_MULTIPLICATION_FACTOR'])
			if self._baseCaseModel:
				self._database = '_'.join([parser['Paths']['BASE_SQLITE_DB_OUTPUT_TRANSIT'],str(self._id)])
			else:
				self._database = '_'.join([parser['Paths']['SQLITE_DB_OUTPUT_TRANSIT'],str(self._id)])
			'''try:
				self._expVarFileName = parser['Paths']['FARES_FILE']
			except:
				self._expVarFileName = os.path.join(self._baseDir, 'fares.txt')
			else:
				if self._expVarFileName == '':
					self._expVarFileName = os.path.join(self._baseDir, 'fares.txt')'''
		self._logger = logging.getLogger(__name__)
		self._outputsInMemory = False	# set to True after running simulation while choosing to keep stats in memory
										# or at the end of a successful call for retrieveOutput
		super(aimsunModel, self).__init__(iniFile, console, model, angFile)
		
	def _checkValidId(self):
		return self._id > 0
	
	def loadNetwork(self):
		'''
	    Loads Aimsun's console and model and sets demand directory and output 
        database

	    Returns
	    -------
	    console instance
	        Active Aimsun console.
	    model instance
	        Active Aimsun model.

	    '''
		super(aimsunModel, self).loadNetwork()
		# set demand directories and outputs database
		if self._checkValidId():
			self.setDemandDir()
			self.setDatabase()
		return (self._console, self._model)
		
	def _getExperiment(self):
		if self._type == aimsunModelType.eMicro or \
			self._type == aimsunModelType.eMeso or \
			self._type == aimsunModelType.eMacro:
			replication = self._model.getCatalog().find(self._id)
			return replication.getExperiment()
		elif self._type == aimsunModelType.eTransit:
			return self._model.getCatalog().find(self._id)
	
	def _getScenario(self):
		return self._getExperiment().getScenario()
		
	def _getTrafficDemand(self):
		return self._getScenario().getDemand()
	
	def setDatabase(self, databaseName=None):
		if self._console is None or self._model is None:
			self.loadNetwork()
		if databaseName is not None:
			self._database = databaseName
		if self._database == '':
			return
		scenario = self._getScenario()
		# get the scenario's DB info
		dbInfo = scenario.getDB(False)
		# custom DB
		dbInfo.setUseProjectDB(False)
		dbInfo.setAutomatic(False)
		# create if it doesn't exist
		dbInfo.setAutomaticallyCreated(True)
		# SQLite DB
		dbInfo.setDriverName('QSQLITE')
		# DB Full Name
		dbInfo.setDatabaseName(self._database)
		# assign it to the scenario
		scenario.setDB(dbInfo)
		self._logger.debug('Database of scenario %i has been changed to %s' %(scenario.getId(), self._database))
	
	def removeDatabase(self):
		try:
			os.remove(self._database)
			self._logger.debug('%s has been removed' %self._database)
		except OSError:
			self._logger.debug('Cannot remove database: %s' %self._database)
	
	def setDemandDir(self, dirName=None):
		if self._console is None or self._model is None:
			self.loadNetwork()
		if dirName is not None:
			self._demandDir = dirName
		if self._demandDir == '':
			return
		scenario = self._getScenario()
		demand = scenario.getDemand()
		# loop over all demand schedules/items (by time and vehicle type) of this scenario
		for demandScheduleItem in demand.getSchedule():
			trafficDemandItem = demandScheduleItem.getTrafficDemandItem()
			# get the current file name
			fileName = os.path.basename(trafficDemandItem.getLocation())
			oldLoc = trafficDemandItem.getLocation()
			# set the demand directory to the new location (the same file name)
			trafficDemandItem.setLocation(os.path.join(self._demandDir, fileName))
			#demandScheduleItem.setTrafficDemandItem(trafficDemandItem)
			self._logger.debug('Location of demand of scenario %i has been changed:\n%s --> %s' %(scenario.getId(),
					oldLoc, trafficDemandItem.getLocation()))
	
	def setDemandFactor(self, mul_factor=None):
		if mul_factor is None:
			mul_factor = self._demandMulFactor
		self._getScenario().getDemand().setFactor(str(mul_factor))
    
	'''
	def setExperimentVars(self, fileName=None):
		# read variables (tolls) from a file and store them as experiment variables
		if self._console is None or self._model is None:
			self.loadNetwork()
		if fileName is not None:
			self._expVarFileName = fileName
		self._logger.debug('Setting experiment variables...')
		experiment = self._getExperiment()
		with open(self._expVarFileName) as f:
			content = f.readlines()
		# remove extra whitespaces and comments
		content = [x.strip() for x in content if not x.strip().startswith('#')]
		variables = {}
		for element in content:
			keyAndValue = element.split('=')
			if len(keyAndValue) != 2 or len(keyAndValue[0]) == 0 or len(keyAndValue[1]) == 0:
				# skip this line
				continue
			variables[keyAndValue[0]] = keyAndValue[1]
			self._logger.debug('='.join(keyAndValue))
		experiment.setVariables(variables)
		self._logger.info('%i variables have been imported to experiment %i' %(len(variables), experiment.getId()))
	'''
	
	def setExperimentVars(self, **kwargs):
		if self._console is None or self._model is None:
			self.loadNetwork()
		self._logger.debug('Setting experiment variables...')
		vars = {key:str(kwargs[key]) for key in kwargs}
		self._logger.debug(vars)
		experiment = self._getExperiment()
		experiment.setVariables(vars)
		self._logger.info('%i variables have been imported to experiment %i' %(len(kwargs), experiment.getId()))
	
	def run(self):
		''' load the model if it's not already loaded
		and run the model (the rest of the function is implemented in each model
		'''
		self.loadNetwork()
		
	def getSkimMatrices(self):
		''' get traffic or transit LOS OD matrices with 
		user-class names and intervals as the indexes
		'''
		pass
		
	def retrieveMacroOutput(self):
		self._logger.error('This function has been deprecated. Please, use retrieveOutput() instead!')
		return 0
		
	def retrieveMesoOutput(self):
		self._logger.error('This function has been deprecated. Please, use retrieveOutput() instead!')
		return 0
		
	def retrieveMicroOutput(self):
		self._logger.error('This function has been deprecated. Please, use retrieveOutput() instead!')
		return 0
		
	def retrieveOutput(self):
		if not self._outputsInMemory:
			if self._console is None or self._model is None:
				self._logger.error('No Aimsun instance is running')
				return -1
			
			if self._type == aimsunModelType.eMicro or self._type == aimsunModelType.eMeso:
				simObject = self._model.getCatalog().find(self._id)
			elif self._type == aimsunModelType.eMacro or self._type == aimsunModelType.eTransit:
				simObject = self._getExperiment()
			else:
				self._logger.error('Undefined Aimsun model type %s' %self._type)
				return -1
			
			if simObject is None:
				self._logger.error('Invalid experiment/replication %i' %self._id)
				return -1
			
			start_time = time.time()
			selection = []
			GKSystem.getSystem().executeAction('retrieve', simObject,
										selection, 'Retrieve %s' %simObject.getName())
			self._outputsInMemory = True
			self._logger.debug('Loading experiment/replication #%i took %s seconds' % (self._id, (time.time() - start_time)))
			return 0

	'''==================================================================================
	Updating transit lines speeds
	'''
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
	
	def setSectionSpeedForPTAssignment(self, interval, DUEResultId, database):
		'''
		Update speed of all road sections in the model based on the results of
		a previous DTA simulation
		Sections statistics (table "MESECT") must be collected during the DTA simulation
		'''
		if self._console is None or self._model is None:
			self.loadNetwork()
		sectionType = self._model.getType('GKSection')
		speedAtt = sectionType.getColumn('GKSection::speedAtt', GKType.eSearchOnlyThisType)
		attributesOverrideName = 'PT Assignment - sections speed ' + str(interval)
		print(attributesOverrideName)
		AttOverride = self._model.getCatalog().findByName(attributesOverrideName, self._model.getType("GKNetworkAttributesOverride"))
		AttOverride.clear()
		self._logger.debug('Connecting to traffic database: %s' %database)
		conn = sqlite3.connect(database)
		cur = conn.cursor()
		rows = cur.execute(
			"SELECT oid, speed "
			"FROM MESECT "
			"WHERE did = ? AND ent = ? AND speed <> -1",
			(self._id, interval))
		for (sectionId, speed) in rows:
			section = self._model.getCatalog().find(sectionId)
			AttOverride.add(section, speedAtt, QVariant(speed))
		self._logger.debug("Attribute override <%s> has been updated" % attributesOverrideName)

	def setSectionSpeedForPTAssignment2(self, PTAssignmentIndex, DUEResultId, loadDUEResult = True):
		'''
		Update speed of all road sections in the model based on the results of
		a previous DTA simulation
		Sections statistics must be collected during the DTA simulation
		'''
		if self._console is None or self._model is None:
			self.loadNetwork()
		DUEResult = self._model.getCatalog().find(DUEResultId)
		if loadDUEResult:
			if DUEResultId == self._id:
				if self.retrieveOutput() != 0:
					self._logger.error('Cannot retrieve data of the DUE result #%i' %DUEResultId)
			else:
				trafficModel = DUEModel(self._iniFile, DUEResultId, self._console, self._model)
				if trafficModel.retrieveOutput() != 0:
					self._logger.error('Cannot retrieve data of the DUE result #%i' %DUEResultId)
		startTime = self._simStartTime + (PTAssignmentIndex-1) * self._simPTInterval
		endTime = startTime + self._simPTInterval
		stat = 'speed'
		sectionType = self._model.getType('GKSection')
		noOfPTLinesAtt = sectionType.getColumn('GKSection::numberOfPTLinesAtt', GKType.eSearchOnlyThisType)
		speedAtt = sectionType.getColumn('GKSection::speedAtt', GKType.eSearchOnlyThisType)
		layerId = 724747		# railway
		layers = [layerId] + self._findSubLayersIds(self._model.getCatalog().find(layerId))

		for types in self._model.getCatalog().getUsedSubTypesFromType(sectionType):
			for section in types.itervalues():
				# skip updating railway sections (GO trains and TTC subway)
				if section.getLayer().getId() in layers:
					continue
				# only update sections that carry PT vehicles
				if section.getDataValueInt(noOfPTLinesAtt) > 0:
					attributesOverrideName = 'PT Assignment - sections speed ' + str(PTAssignmentIndex)
					AttOverride = self._model.getCatalog().findByName(attributesOverrideName, self._model.getType("GKNetworkAttributesOverride"))
					attValue = self._getMeanOfSecionTimeSeries(DUEResult, section, stat, startTime, endTime)
					if attValue is not None:
						AttOverride.add(section, speedAtt, QVariant(attValue))
		self._logger.debug("Attribute override <%s> has been updated" % attributesOverrideName)

