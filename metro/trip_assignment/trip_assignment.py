# -*- coding: utf-8 -*-
#import sys
import pickle
import subprocess
import os
#from datetime import datetime
#import time
from configparser import ConfigParser, ExtendedInterpolation
import logging
#from multiprocessing import Process
#from outputs import routeStats
from .transit_fares import transitFares
from .tolls import roadTolls
#from metro3.tools.demand import ODMatrices
from ..tools.los import levelOfServiceAttributes as LOS
import sqlite3


class simulationMode:
	eDynamicTrafficAndTransitAssignment = 0
	eDynamicTrafficAssignmentOnly = 1
	eDynamicTransitAssignmentOnly = 2
	
class tripAssignmentModel(object):
	'''
	Class for simulation-based dynamic traffic and transit assignment model
	'''
	def __init__(self, iniFile, fares=None, tolls=None, baseCaseModel=False):
		self._iniFile = iniFile
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self._traffic_cmd = os.path.normpath(os.path.join(os.path.dirname(__file__),'../aimsun/traffic_assignment.py'))
		self._transit_cmd = os.path.normpath(os.path.join(os.path.dirname(__file__),'../aimsun/transit_assignment.py'))
		# read config parameters
		self._aimsunExe = os.path.join(parser['Paths']['AIMSUN_DIR'],'aconsole.exe') \
							if parser.has_option('Paths','AIMSUN_DIR') else ''
		self._baseDir = parser.get('Paths','BASE_DIR', fallback='')
		if baseCaseModel:
			self._DUEResultId = int(parser.get('Traffic Assignment','BASE_DUE_RESULT_ID', fallback=-1))
			if parser.has_option('Transit Assignment','base_ptExperimentsIds'):
				self._ptExperimentsIds = [int(x) for x in parser['Transit Assignment']['base_ptExperimentsIds'].strip().split(',')]
			else:
				self._ptExperimentsIds = []
			self._databaseTraffic = parser.get('Paths','BASE_SQLITE_DB_OUTPUT_TRAFFIC', fallback='')
		else:
			self._DUEResultId = int(parser.get('Traffic Assignment','DUE_RESULT_ID', fallback=-1))
			if parser.has_option('Transit Assignment','ptExperimentsIds'):
				self._ptExperimentsIds = [int(x) for x in parser['Transit Assignment']['ptExperimentsIds'].strip().split(',')]
			else:
				self._ptExperimentsIds = []
			self._databaseTraffic = parser.get('Paths','SQLITE_DB_OUTPUT_TRAFFIC', fallback='')
		self._dtaUserClasses = parser['Traffic Assignment']['dtaUserClassNames'].strip().split(',') \
								if parser.has_option('Traffic Assignment','dtaUserClassNames') else []
		self._ptUserClasses = parser['Transit Assignment']['ptUserClassNames'].strip().split(',') \
								if parser.has_option('Transit Assignment','ptUserClassNames') else []
		self._numberOfIntervals = int(parser.get('Demand','numberOfIntervals', fallback=-1))
		self._skimMatDir = parser.get('Paths','SKIM_MATRICES_DIR', fallback='')
		self._losDb = parser.get('Trip Assignment','LOS_DB', fallback='')
		
		self._logger = logging.getLogger(__name__)
		# self.fares is a list of <transitFares>
		if fares is None:
			self.fares = []
			for i in range(self._numberOfIntervals):
				self.fares.append(transitFares())
				self.fares[-1].fillInDefaultFares()
		else:
			self.fares = fares
		# self.tolls is an instance of <roadTolls>
		if tolls is None:
			self.tolls = roadTolls(self._iniFile)
		else:
			self.tolls = tolls
		self._baseCaseModel = baseCaseModel
		self._console = None
		self._model = None
		
		self.deleteLOSDatabase()
		self.createLOSDatabase()
		
	def run(self, calculateLOS = False, mode = 0):
		''' 
		Run simulation within AIMSUN running using original python.exe
		calculateLOS:	determine whether to return traffic and/or transit LOS matrices or not
		mode		:	a valid value from class simulationMode
		'''
		self._logger.info('Running the trip assignment model using python.exe')
		'''logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
		logLevel = 'DEBUG'
		for level in logLevels:
			if self._logger.getEffectiveLevel() == eval('.'.join(['logging',level])):
				logLevel = level'''
		logLevel = logging.getLevelName(self._logger.getEffectiveLevel())
		# print system info
		cmd = [self._aimsunExe, '-log_file', 'aimsun.log', '-script']
		cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),'../tools/system_info.py')))
		self._logger.debug('Running command: %s' %' '.join(cmd))
		ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		los = LOS(self._iniFile, loadGoogleLos=False)
		#los.loadGoogleLOS()
		#======================================================#
		#				The Traffic Assignment				#
		#======================================================#
		if mode == simulationMode.eDynamicTrafficAndTransitAssignment or \
			mode == simulationMode.eDynamicTrafficAssignmentOnly:
			cmd = [self._aimsunExe, '-log_file', 'aimsun.log', '-script']
			#cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),'../ext/run_due.py')))
			cmd.append(self._traffic_cmd)
			cmd.append('-l')
			cmd.append(logLevel)
			if calculateLOS:
				cmd.append('-c')
			if self._losDb != '':
				cmd.append('-d')
				cmd.append(self._losDb)
			cmd.append('-t')
			self._logger.debug(self.tolls)
			self.tolls.writeToFile('tolls.temp')
			cmd.append('tolls.temp')
			cmd.append(self._iniFile)
			cmd.append(str(self._DUEResultId))
			self._logger.debug('Running command: %s' %' '.join(cmd))
			ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
			stdout, stderr = ps.communicate()
			#ps.communicate(pickle.dumps(self.tolls))
			#output = ps.communicate()[0]
			#print 'Main: %s' %output
			ps.wait()
			if calculateLOS:
				# update los to read from sqlite DB instead of csv files (ODMatrix)
				#los.loadTrafficOnly(self._skimMatDir, sparse=True)
				los.loadTrafficOnlyDB(self._losDb)
		#======================================================#
		#				The Transit Assignment				#
		#	(including updating section speeds from the DTA)	#
		#======================================================#
		if mode == simulationMode.eDynamicTrafficAndTransitAssignment or \
			mode == simulationMode.eDynamicTransitAssignmentOnly:
			for ptExperimentId, interval in zip(self._ptExperimentsIds, range(1,self._numberOfIntervals+1)):
				cmd = [self._aimsunExe, '-log_file', 'aimsun.log', '-script']
				#cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),'../ext/run_pt.py')))
				cmd.append(self._transit_cmd)
				cmd.append(self._iniFile)
				cmd.append(str(ptExperimentId))
				if calculateLOS:
					cmd.append('-c')
				cmd.append('-l')
				cmd.append(logLevel)
				cmd.append('-i')
				cmd.append(str(interval))
				#cmd.append('-f')
				#cmd.append(str(self.fares[interval-1]['TTC'][0]))
				#cmd.append(pickle.dumps(self.fares[interval-1]))
				self._logger.info(str(self.fares[interval-1]))
				self._logger.debug('Running command: %s' %' '.join(cmd))
				ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
				ps.communicate(pickle.dumps(self.fares[interval-1]))
				ps.wait()
			if calculateLOS:
				los.loadTransitOnly(self._skimMatDir, sparse=True)
		return los
	
	# fares is a list of <transitFares>
	@property
	def fares(self):
		return self._fares
		
	@fares.setter
	def fares(self, value):
		self._fares = value
	
	@fares.deleter
	def fares(self):
		del self._fares

	# tolls is an instance of <roadTolls>
	@property
	def tolls(self):
		return self._tolls
		
	@tolls.setter
	def tolls(self, value):
		self._tolls = value
	
	@tolls.deleter
	def tolls(self):
		del self._tolls

	def createLOSDatabase(self):
		conn = sqlite3.connect(self._losDb)
		c = conn.cursor()
		# TO DO: define traffic and transit LOS keys separately, maybe in __init__
		c.execute('''CREATE TABLE IF NOT EXISTS LOS
				([id] INTEGER PRIMARY KEY,[origin] INTEGER, [destination] INTEGER,
				[interval] INTEGER, [user_class] text, [traffic_ivtt] REAL,
				[traffic_dist] REAL, [traffic_toll] REAL, [transit_ivtt] REAL,
				[transit_accT] REAL, [transit_egrT] REAL, [transit_fare] REAL,
				[transit_wait] REAL, [transit_crwd] REAL)''')
		conn.commit()

	def deleteLOSDatabase(self):
		try:
			os.remove(self._losDb)
			self._logger.debug('%s has been removed' %self._losDb)
		except OSError:
			self._logger.debug('Cannot remove database: %s' %self._losDb)
	

''' unavailable in Python 3
	from transit_assignment import PTModel
	def getPTRouteAdjustedOccupancy(self, ptPathsIds):
		start_time = time.time()
		adjustedOccupancy = [[] for i in range(len(ptPathsIds))]	# list of subpaths; each has a list of routeSpaceStat
		# loop over all PT Experiments
		prevExperimentId = None
		for ptExperimentId, interval in zip(self._ptExperimentsIds, range(1, len(self._ptExperimentsIds)+1)):
			transitModel = PTModel(self._iniFile, ptExperimentId, baseCaseModel=self._baseCaseModel)
			transitModel.loadNetwork()
			transitModel.retrieveOutput()
			for pathId, pathIdx in zip(ptPathsIds, range(len(ptPathsIds))):
				adjustedOccupancy[pathIdx].append(transitModel.getSubpathAdjustedOccupancy(pathId, prevExperimentId = prevExperimentId))
			transitModel.unloadNetwork()
			prevExperimentId = ptExperimentId
		subPathsAdjustedOccupancy = []	# list of routeStats; one for each subpath
		for pathId, pathIdx in zip(ptPathsIds, range(len(ptPathsIds))):
			fullAdjustedOccupancy = routeStats('Adjusted Occupancy of %s' %adjustedOccupancy[pathIdx][0].name)
			fullAdjustedOccupancy.time = [x.time[0] for x in adjustedOccupancy[pathIdx]]
			fullAdjustedOccupancy.space = adjustedOccupancy[pathIdx][0].space
			fullAdjustedOccupancy.length = adjustedOccupancy[pathIdx][0].length
			fullAdjustedOccupancy.speed = adjustedOccupancy[pathIdx][0].speed
			fullAdjustedOccupancy.series = np.array([x.series for x in adjustedOccupancy[pathIdx]])
			subPathsAdjustedOccupancy.append(fullAdjustedOccupancy)
			#logger.debug(fullAdjustedOccupancy)
			#logger.debug(fullAdjustedOccupancy.max())
			#logger.debug(fullAdjustedOccupancy.max(1))
		logger.info('--- Retrieving PT routes stats finished in %s seconds ---' % (time.time() - start_time))
		return subPathsAdjustedOccupancy
'''