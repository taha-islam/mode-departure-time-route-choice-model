# -*- coding: utf-8 -*-
#import sys
import os
import numpy as np
import sqlite3
import logging
from configparser import ConfigParser, ExtendedInterpolation
from .demand import accessStationDict, centroidIdToEidDict, ODMatrices #, IntermODMatrices

class levelOfServiceAttributes(object):
	'''
	This is the base class for traffic and travel level of service (LOS) attributes.
	'''
	def __init__(self, 
				iniFile, 
				useGoogleLos=False,
				gapFillingMethod=1,
				loadGoogleLos=True):
		'''
		| gapFillingMethod	: how to fill in the gaps in the LOS matrices obtained from AIMSUN with the GOOGLE LOS
		| 	0	: without transformation
		| 	1	: with nonzeromean-to-fullnonzeromean ratio (nonzeromean of the whole GOOGLE LOS matrix)
		| 	2	: with nonzeromean-to-matchingnonzeromean ratio 
		| 	3	: with first degree curve fitting
		'''
		self._iniFile = iniFile
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self._inputDB = parser.get('Paths','SQLITE_DB_INPUT', fallback='')
		self._tilosSkimMatDir = parser.get('Paths','TILOS_SKIM_MATRICES_DIR', fallback='')
		self._adjFactorDir = parser.get('Paths','CALIBRATED_ASC_DIR', fallback='')
		self._driveWalkSpeedRatio = int(parser.get('Discrete Choice Model','driveWalkSpeedRatio', fallback=0))
		self._fuelCostPer100km = float(parser.get('Discrete Choice Model','fuelCostPer100km', fallback=0))
		self._numberOfIntervals = int(parser.get('Demand','numberOfIntervals', fallback=0))
		self._intermModes = parser.get('Demand','INTERM_MODES', fallback='').strip().split(',')
		self._numberOfCentroids = int(parser.get('Demand','numberOfCentroids', fallback=0))
		self._numberOfCentroidsToronto = int(parser.get('Demand','numberOfCentroidsToronto', fallback=0))
		# TO DO: fix this
		try:
			self._accessStationDict = accessStationDict(iniFile)
		except:
			self._accessStationDict = {}
		try:
			self._centroidIdToEidDict = centroidIdToEidDict(iniFile)
		except:
			self._centroidIdToEidDict = {}
		self._logger = logging.getLogger(__name__)
		self._useGoogleLos = useGoogleLos
		self._gapFillingMethod = gapFillingMethod
		
		dtaUserClassNames = parser.get('Traffic Assignment','dtaUserClassNames', fallback='').strip().split(',')
		if dtaUserClassNames == ['']:
			# TO DO: better handling
			self._trafficLOS = {}
			self._trafficTILOS = {}
		else:
			self._trafficLOS = {'ivtt':ODMatrices(self._iniFile, name='Travel Time', modes=dtaUserClassNames),
								'dist':ODMatrices(self._iniFile, name='Travel Distance', modes=dtaUserClassNames),
								'toll':ODMatrices(self._iniFile, name='Toll Cost', modes=dtaUserClassNames)}
			self._trafficTILOS={'ivtt':ODMatrices(self._iniFile, name='Travel Time', modes=dtaUserClassNames),
								'dist':ODMatrices(self._iniFile, name='Travel Distance', modes=dtaUserClassNames),
								'toll':ODMatrices(self._iniFile, name='Toll Cost', modes=dtaUserClassNames)}
		# transformation to be used a long with GOOGLE LOS to compensate the differences between GOOGLE and AIMSUN LOS
		self._trafficLOSTransformation = {key:dict() for key in self._trafficTILOS}
		
		ptUserClassNames = parser.get('Transit Assignment','ptUserClassNames', fallback='').strip().split(',')
		if ptUserClassNames == ['']:
			# TO DO: better handling
			self._transitLOS = {}
			self._transitTILOS = {}
		else:
			self._transitLOS = {'ivtt':ODMatrices(self._iniFile, name='Travel Time', modes=ptUserClassNames),
								'accT':ODMatrices(self._iniFile, name='Accesss Time', modes=ptUserClassNames),
								'egrT':ODMatrices(self._iniFile, name='Egresss Time', modes=ptUserClassNames),
								'fare':ODMatrices(self._iniFile, name='Fare', modes=ptUserClassNames),
								'crwd':ODMatrices(self._iniFile, name='Crowdedness', modes=ptUserClassNames),
								'wait':ODMatrices(self._iniFile, name='Waiting Time', modes=ptUserClassNames)}
			# 'crwd' (Crowdedness) and 'wait' are AIMSUN-generated sets of matrices and do not exist in TILOS/Google LOS
			self._transitTILOS={'ivtt':ODMatrices(self._iniFile, name='Travel Time', modes=ptUserClassNames),
								'accT':ODMatrices(self._iniFile, name='Accesss Time', modes=ptUserClassNames),
								'egrT':ODMatrices(self._iniFile, name='Egresss Time', modes=ptUserClassNames),
								'fare':ODMatrices(self._iniFile, name='Fare', modes=ptUserClassNames)}
		# transformation to be used a long with GOOGLE LOS to compensate the differences between GOOGLE and AIMSUN LOS
		self._transitLOSTransformation = {key:dict() for key in self._transitTILOS}
		# load GOOGLE LOS
		if loadGoogleLos:
			self.loadGoogleLOS()	
			
		self._centroidsSorted = {}
	
	@property
	def gapFillingMethod(self):
		return self._gapFillingMethod
		
	@gapFillingMethod.setter
	def gapFillingMethod(self, value):
		self._gapFillingMethod = value
	
	@gapFillingMethod.deleter
	def gapFillingMethod(self):
		del self._gapFillingMethod
	
	def loadGoogleLOS(self, traffic=True, transit=True):
		'''
		load GOOGLE LOS
		'''
		if traffic:
			for key in self._trafficTILOS.keys():
				self._trafficTILOS[key].load(self._tilosSkimMatDir + '/Traffic/' + key)
		if transit:
			for key in self._transitTILOS.keys():
				self._transitTILOS[key].load(self._tilosSkimMatDir + '/Transit/' + key)
		
	
	def getTrasnitModeInAimsun(self, originEId, destinationEId):
		'''
		returns the transit mode/user-class in AIMSUN, which is defined by the origin and destination centroids.
		Commuters within Toronto are "Torontonians"
		Commuters from outside Toronto to inside or vice versa are "Regional Commuters"
		Commuters from outside Toronto going to anywhere outside Toronto are not included in AIMSUN
		'''
		if originEId > self._numberOfCentroidsToronto and destinationEId > self._numberOfCentroidsToronto:
			# out of Toronto to out of Toronto
			mode = None
		elif originEId <= self._numberOfCentroidsToronto and destinationEId <= self._numberOfCentroidsToronto:
			mode = 'Torontonians'
		else:
			mode = 'Regional Commuters'
		return mode
		
	def getTrafficModeInAimsun(self, DCMMode):
		'''
		returns the traffic mode/user-class in AIMSUN
		'''
		if DCMMode == 'D':
			mode = 'Car'
		elif DCMMode == 'P':
			mode = 'HOV'
		else:
			mode = None
		return mode
	
	def _getODTransitLOSUnique(self, originEId, destinationEId, interval):
		'''
		returns an array of in-vehicle travel time, fare, access time, and egress time
		for specific OD pair at a given interval (find the corresponding user class 
		based on the origin and destination)
		'''
		mode = self.getTrasnitModeInAimsun(originEId, destinationEId)
		if mode is None:
			# out of Toronto to out of Toronto
			conn = sqlite3.connect(self._inputDB)
			cur = conn.cursor()
			row = cur.execute(
				"SELECT ivtt, fare, accT, egrT FROM transit_los_tilos "
				"WHERE origin_extid = ? AND destination_extid = ? AND interval = ? "
				"LIMIT 1",
				(originEId, destinationEId, interval)).fetchone()
			if row is None:
				# return high ivtt, fare, and wt to decrease the probability
				# of choosing this alternative
				row = np.array([0, 0, 0, 0])
			(ivtt, fare, accT, egrT) = row
			conn.close()
			return np.array([ivtt, fare, accT, egrT])
		
		if self._useGoogleLos or mode is None:
			ivtt = 0
			fare = 0
			accT = 0
			egrT = 0
		else:
			ivtt = self._transitLOS['ivtt'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
			fare = self._transitLOS['fare'][(mode, interval)][originEId-1][destinationEId-1]	# $
			accT = self._transitLOS['accT'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
			egrT = self._transitLOS['egrT'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
		if ivtt == 0:
			# retrieve Google LOS and update <self._transitLOS> matrices
			for key in self._transitTILOS:
				self._transitLOS[key][(mode, interval)][originEId-1][destinationEId-1] = max(1,
					self._transitLOSTransformation[key][(mode, interval)](self._transitTILOS[key][(mode, interval)][originEId-1][destinationEId-1]))
			ivtt = self._transitLOS['ivtt'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
			fare = self._transitLOS['fare'][(mode, interval)][originEId-1][destinationEId-1]	# $
			accT = self._transitLOS['accT'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
			egrT = self._transitLOS['egrT'][(mode, interval)][originEId-1][destinationEId-1]	# minutes
		return np.array([ivtt, fare, accT, egrT])
		
	def getODTransitLOS(self, originEId, destinationEId, interval = None, transitMode = ['T','PR','KR']):
		'''
		returns	: a dict of {(mode, interval) : list of [ivtt, fare, ovtt]}
		zero fare, ivtt, and ovtt are replaced with the corresponding values from TILOS database (after possible adjustment)
		implemented specifically for nl.py (and some functions in fitness_calculations.py)
		'''
		if interval is None:
			interval = range(1, self._numberOfIntervals + 1)
		result = {}
		if isinstance(interval, list) and isinstance(transitMode, list):
			for mode in transitMode:
				for ent in interval:
					result.update(self.getODTransitLOS(originEId, destinationEId, ent, mode))
		elif isinstance(interval, list):
			for ent in interval:
				result.update(self.getODTransitLOS(originEId, destinationEId, ent, transitMode))
		elif isinstance(transitMode, list):
			for mode in transitMode:
				result.update(self.getODTransitLOS(originEId, destinationEId, interval, mode))
		else:
			# just one interval and one mode
			if transitMode == 'T':
				los = self._getODTransitLOSUnique(originEId, destinationEId, interval)
			elif not self._useGoogleLos and originEId in self._accessStationDict.keys():
				accStationCentEId = self._accessStationDict[originEId]
				los = self._getODTransitLOSUnique(accStationCentEId, destinationEId, interval)
				# update the access time with the appropriate driving access time
				if transitMode == 'PR':
					los[2] = self.getODTrafficLOS(originEId, accStationCentEId, interval, 'D')[('D',interval)][0]
				elif transitMode == 'KR':
					los[2] = self.getODTrafficLOS(originEId, accStationCentEId, interval, 'P')[('P',interval)][0]
			else:
				# the access station is within the origin centroid
				los = self._getODTransitLOSUnique(originEId, destinationEId, interval)
				# update the access time with approximate driving access time
				los[2] = los[2] / self._driveWalkSpeedRatio
				'''try:
					accStationCentEId = self._accessStationDict[originEId]
					los = self._getODTransitLOSUnique(
						accStationCentEId, destinationEId, interval)
					# update the access time with the appropriate driving access time
					if transitMode == 'PR':
						los[2] = self.getODTrafficLOS(originEId, accStationCentEId, interval, 'D')[0]
					elif transitMode == 'KR':
						los[2] = self.getODTrafficLOS(originEId, accStationCentEId, interval, 'P')[0]
				except KeyError:
					# the access station is within the origin centroid
					los = self._getODTransitLOSUnique(
						originEId, destinationEId, interval)
					# update the access time with approximate driving access time
					los[2] = los[2] / self._driveWalkSpeedRatio'''
				# adding the cost of driving to station to the fare
				if transitMode == 'PR':
					los[1] += los[2] * (4.5/60) * self._fuelCostPer100km / 100	# $
				elif transitMode == 'KR':
					los[1] += los[2] * (4.5/60) * self._fuelCostPer100km / 200	# $
			# returning array of ivtt, fare, and ovtt (ovtt = accT + egrT)
			result[(transitMode, interval)] = np.array([los[0], los[1], los[2]+los[3]])
		return result
		
	def _getODTrafficLOSUnique(self, originEId, destinationEId, interval, trafficMode):
		mode = self.getTrafficModeInAimsun(DCMMode=trafficMode)
		if mode is None:
			self._logger.error('Invalid mode %s' %trafficMode)
			return None
		if self._useGoogleLos:
			time = 0
			distance = 0
			toll = 0
		else:
			time = self._trafficLOS['ivtt'][(mode, interval)][originEId-1][destinationEId-1]		# minutes
			distance = self._trafficLOS['dist'][(mode, interval)][originEId-1][destinationEId-1]	# meters
			toll = self._trafficLOS['toll'][(mode, interval)][originEId-1][destinationEId-1]		# $
		if time == 0:
			for key in self._trafficTILOS:
				self._trafficLOS[key][(mode, interval)][originEId-1][destinationEId-1] = max(1,
					self._trafficLOSTransformation[key][(mode, interval)](self._trafficTILOS[key][(mode, interval)][originEId-1][destinationEId-1]))
			time = self._trafficLOS['ivtt'][(mode, interval)][originEId-1][destinationEId-1]		# minutes
			distance = self._trafficLOS['dist'][(mode, interval)][originEId-1][destinationEId-1]	# meters
			toll = self._trafficLOS['toll'][(mode, interval)][originEId-1][destinationEId-1]		# $
		return np.array([time, distance, toll])
		
	def getODTrafficLOS(self, originEId, destinationEId, interval = None, trafficMode = ['D','P']):
		'''
		returns	: a dict of {(mode, interval) : list of [time, distance, toll]}
		trafficMode	:	1 --> SOV/D
						2 --> HOV/P
		zero ivtt, distance, and toll are replaced with the corresponding values from TILOS database (after possible adjustment)
		implemented specifically for nl.py (and some functions in fitness_calculations.py)
		'''
		if interval is None:
			interval = range(1, self._numberOfIntervals + 1)
		result = {}
		if isinstance(interval, list) and isinstance(trafficMode, list):
			for mode in trafficMode:
				for ent in interval:
					result.update(self.getODTrafficLOS(originEId, destinationEId, ent, mode))
		elif isinstance(interval, list):
			for ent in interval:
				result.update(self.getODTrafficLOS(originEId, destinationEId, ent, trafficMode))
		elif isinstance(trafficMode, list):
			for mode in trafficMode:
				result.update(self.getODTrafficLOS(originEId, destinationEId, interval, mode))
		else:
			# just one interval and one mode
			result[(trafficMode, interval)] = self._getODTrafficLOSUnique(originEId, destinationEId, interval, trafficMode)
			# Passengers experience half the cost (which is based on distance) and
			# half the toll (which is divided by the original distance (not half the distance);
			# hence the toll is divided by 4 instead of 2)
			if trafficMode == 'P':
				result[(trafficMode, interval)][1] /= 2
				result[(trafficMode, interval)][2] /= 4
		return result
	
	def _fillTrafficLOSGaps(self):
		for key in self._trafficTILOS:
			self._logger.debug(self._trafficLOS[key].nonzeromean().str(np.mean))
			if self.gapFillingMethod == 1:
				ratio = self._trafficLOS[key].nonzeromean()/self._trafficTILOS[key].nonzeromean()
				ratio.replaceAllValues(0,1)
			elif self.gapFillingMethod == 2:
				ratio = self._trafficLOS[key].nonzeromean()/(self._trafficLOS[key]/self._trafficLOS[key]*self._trafficTILOS[key]).nonzeromean()
				ratio.replaceAllValues(0,1)
			for matrixKey in self._trafficLOS[key]:
				if self.gapFillingMethod == 0:
					coefficients = np.array([1,0])
				elif self.gapFillingMethod == 1 or self.gapFillingMethod == 2:
					coefficients = np.array([np.asscalar(ratio[matrixKey]),0])
				elif self.gapFillingMethod == 3:
					nonzeroInd = np.nonzero(self._trafficLOS[key][matrixKey])
					coefficients = np.polyfit(self._trafficTILOS[key][matrixKey][nonzeroInd],
											self._trafficLOS[key][matrixKey][nonzeroInd],1)
				else:
					self._logger.warning('Invalid transformation to fill LOS gaps %s. Google LOS '
										'will be used without any transformation.' %str(self.gapFillingMethod))
					coefficients = np.array([1,0])
				self._logger.debug('Transformation for %s, %s, %s is %fx%+f' %(key, 
									matrixKey[0], matrixKey[1], coefficients[0], coefficients[1]))
				self._trafficLOSTransformation[key][matrixKey] = np.poly1d(coefficients)
	
	def _fillTransitLOSGaps(self):
		for key in self._transitTILOS:
			self._logger.debug(self._transitLOS[key].nonzeromean().str(np.mean))
			if self.gapFillingMethod == 1:
				ratio = self._transitLOS[key].nonzeromean()/self._transitTILOS[key].nonzeromean()
				ratio.replaceAllValues(0,1)
			elif self.gapFillingMethod == 2:
				ratio = self._transitLOS[key].nonzeromean()/(self._transitLOS[key]/self._transitLOS[key]*self._transitTILOS[key]).nonzeromean()
				ratio.replaceAllValues(0,1)
			for matrixKey in self._transitLOS[key]:
				if self.gapFillingMethod == 0:
					coefficients = np.array([1,0])
				elif self.gapFillingMethod == 1 or self.gapFillingMethod == 2:
					coefficients = np.array([np.asscalar(ratio[matrixKey]),0])
				elif self.gapFillingMethod == 3:
					nonzeroInd = np.nonzero(self._transitLOS[key][matrixKey])
					coefficients = np.polyfit(self._transitTILOS[key][matrixKey][nonzeroInd],
											self._transitLOS[key][matrixKey][nonzeroInd],1)
				else:
					self._logger.warning('Invalid transformation to fill LOS gaps %s. Google LOS '
										'will be used without any transformation.' %str(self.gapFillingMethod))
					coefficients = np.array([1,0])
				self._logger.debug('Transformation for %s, %s, %s is %fx%+f' %(key, 
									matrixKey[0], matrixKey[1], coefficients[0], coefficients[1]))
				self._transitLOSTransformation[key][matrixKey] = np.poly1d(coefficients)
	
	def setTravelLOS(self, trafficLOS=None, transitLOS=None):
		# updating traffic LOS
		if trafficLOS is not None:
			for key in trafficLOS.keys():
				if key in self._trafficLOS:
					self._trafficLOS[key] = trafficLOS[key]
				else:
					self._logger.warning('Invalid LOS key %s' %key)
			self._fillTrafficLOSGaps()
		# updating transit LOS
		if transitLOS is not None:
			for key in transitLOS.keys():
				if key in self._transitLOS:
					self._transitLOS[key] = transitLOS[key]
				else:
					self._logger.warning('Invalid LOS key %s' %key)
			self._fillTransitLOSGaps()

	def getTravelLOS(self):
		return self._trafficLOS, self._transitLOS

	'''
	Loading LOS OD matrices where they have to in <path>\traffic\<key> and/or <path>\transit\<key>
	'''
	def loadTrafficOnly(self, path, sparse=True):
		for key in self._trafficLOS:
			self._trafficLOS[key].load(os.path.join(path, 'Traffic', key), sparse=sparse)
		self._fillTrafficLOSGaps()
		
	def loadTransitOnly(self, path, sparse=True):
		for key in self._transitLOS:
			self._transitLOS[key].load(os.path.join(path, 'Transit', key), sparse=sparse)
		self._fillTransitLOSGaps()
		
	def load(self, path, sparse=True):
		self.loadTrafficOnly(path, sparse)
		self.loadTransitOnly(path, sparse)
		
	def saveTrafficOnly(self, path, sparse=True):
		for key in self._trafficLOS:
			self._trafficLOS[key].save(os.path.join(path, 'Traffic', key), sparse=sparse)
			
	def saveTransitOnly(self, path, sparse=True):
		for key in self._transitLOS:
			self._transitLOS[key].save(os.path.join(path, 'Transit', key), sparse=sparse)
			
	def save(self, path, sparse=True):
		self.saveTrafficOnly(path, sparse)
		self.saveTransitOnly(path, sparse)

	def loadTrafficOnlyDB(self, path):
		conn = sqlite3.connect(path)
		cur = conn.cursor()
		
		rows = cur.execute('SELECT DISTINCT(origin) FROM LOS')
		uniqueOrigins = [x[0] for x in list(rows)]
		rows = cur.execute('SELECT DISTINCT(destination) FROM LOS')
		uniqueDestinations = [x[0] for x in list(rows)]
		centroids = uniqueOrigins + list(set(uniqueDestinations) - set(uniqueOrigins))
		self._centroidsSorted = {x:y for x,y in zip(sorted(centroids), range(len(centroids)))}
		
		rows = cur.execute('select * from LOS LIMIT 1')
		keysFull = [description[0] 
				for description in rows.description 
				if description[0].startswith('traffic')]
		keys = [''.join(key.split('_')[1:]) for key in keysFull]
		noOfKeys = len(keys)
		for key in keys:
			self._trafficLOS[key].setAllTo(0)
		rows = cur.execute("SELECT %s, origin, destination, interval, user_class FROM LOS" %",".join(keysFull))
		for row in rows:
			for i in range(noOfKeys):
				origin = row[noOfKeys]
				destination = row[noOfKeys+1]
				interval = row[noOfKeys+2]
				userClass = row[noOfKeys+3]
				self._trafficLOS[keys[i]][(userClass, interval)][self._centroidsSorted[origin]][self._centroidsSorted[destination]] = row[i]
		self._fillTrafficLOSGaps()
		conn.close()
		
	def loadTransitOnlyDB(self, path):
		conn = sqlite3.connect(path)
		cur = conn.cursor()
		
		rows = cur.execute('SELECT DISTINCT(origin) FROM LOS')
		uniqueOrigins = [x[0] for x in list(rows)]
		rows = cur.execute('SELECT DISTINCT(destination) FROM LOS')
		uniqueDestinations = [x[0] for x in list(rows)]
		centroids = uniqueOrigins + list(set(uniqueDestinations) - set(uniqueOrigins))
		self._centroidsSorted = {x:y for x,y in zip(sorted(centroids), range(len(centroids)))}
		
		rows = cur.execute('select * from LOS LIMIT 1')
		keysFull = [description[0] 
				for description in rows.description 
				if description[0].startswith('transit')]
		keys = [''.join(key.split('_')[1:]) for key in keysFull]
		noOfKeys = len(keys)
		for key in keys:
			self._transitLOS[key].setAllTo(0)
		rows = cur.execute("SELECT %s, origin, destination, interval, user_class FROM LOS" %",".join(keysFull))
		for row in rows:
			for i in range(noOfKeys):
				origin = row[noOfKeys]
				destination = row[noOfKeys+1]
				interval = row[noOfKeys+2]
				userClass = row[noOfKeys+3]
				self._transitLOS[keys[i]][(userClass, interval)][self._centroidsSorted[origin]][self._centroidsSorted[destination]] = row[i]
		self._fillTransitLOSGaps()
		conn.close()
		
	def loadDB(self, path):
		self.loadTrafficOnlyDB(path)
		self.loadTransitOnlyDB(path)
		
	