# -*- coding: utf-8 -*-
"""
Created on Fri Nov 29 16:42:14 2019

@author: islam
"""

import numpy as np
import logging
from configparser import ConfigParser, ExtendedInterpolation
from metro.tools.demand import accessStationDict, centroidIdToEidDict
from metro.tools.los import levelOfServiceAttributes as LOS

class losMulFactor(dict):
	def __init__(self):
		# for traffic modes: coefficients of [time, fuel_cost, toll], NOTE: fuel cost = distance multiplied by some constant
		# for transit modes: coefficients of [IVTT, fare, ovtt]
		for mode in ['D', 'P', 'T', 'PR', 'KR']:
			for interval in range(1,9):
				self[(mode, interval)] = np.array([1.0, 1.0, 1.0])
	
	def _setCoefficient(self, coefficient, value, 
						modes=['D', 'P', 'T', 'PR', 'KR'],
						intervals=range(1,9)):
		for mode in modes:
			for interval in intervals:
				self[(mode, interval)][coefficient] = value
				
	def setIVTT(self, value,
				modes=['D', 'P', 'T', 'PR', 'KR'],
				intervals=range(1,9)):
		self._setCoefficient(0, value, modes, intervals)
		
	def setCost(self, value,
				modes=['D', 'P', 'T', 'PR', 'KR'],
				intervals=range(1,9)):
		self._setCoefficient(1, value, modes, intervals)
	
	def setToll(self, value,
				modes=['D', 'P'],
				intervals=range(1,9)):
		self._setCoefficient(2, value, modes, intervals)

	def setOVTT(self, value,
				modes=['T', 'PR', 'KR'],
				intervals=range(1,9)):
		self._setCoefficient(2, value, modes, intervals)

class selectionMethod:
	'''
	The selection method used to simulate the decision making process
	'''
	eRouletteWheel = 0
	eMaximum = 1
	
class demandCalculationMethod:
	'''
	encoded as: transit | traffic
		0 --> ignore
		1 --> maintain base case mode and departure-time interval
		2 --> calculate
	'''
	eIgnoreTrafficIgnoreTransit = 0
	eMaintainTrafficIgnoreTransit = 1
	eCalculateTrafficIgnoreTransit = 2
	
	eIgnoreTrafficMaintainTransit = 10
	eMaintainTrafficMaintainTransit = 11
	eCalculateTrafficMaintainTransit = 12
	
	eIgnoreTrafficCalculateTransit = 20
	eMaintainTrafficCalculateTransit = 21
	eCalculateTrafficCalculateTransit = 22
	
class depTimeAndModeChModel(object):
	'''
	This is the base class for discrete choice models of travel mode and
	departure time choice
	'''
	def __init__(self, 
				iniFile, 
				useGoogleLos = False, 
				demandStructure1 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure2 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure3 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure4 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				gapFillingMethod = 0):
		self._iniFile = iniFile
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self._inputDB = parser['Paths']['SQLITE_DB_INPUT']
		self._adjFactorDir = parser['Paths']['CALIBRATED_ASC_DIR']
		self._driveWalkSpeedRatio = int(parser['Discrete Choice Model']['driveWalkSpeedRatio'])
		self._fuelCostPer100km = float(parser['Discrete Choice Model']['fuelCostPer100km'])
		# initialize the pseudo random generator
		self._randomSeed = float(parser['Discrete Choice Model']['randomSeed'])
		self._numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		self._intermModes = parser['Demand']['INTERM_MODES'].strip().split(',')
		self._numberOfCentroids = int(parser['Demand']['numberOfCentroids'])
		self._numberOfCentroidsToronto = int(parser['Demand']['numberOfCentroidsToronto'])
		self._accessStationDict = accessStationDict(iniFile)
		self._centroidIdToEidDict = centroidIdToEidDict(iniFile)
		
		self._logger = logging.getLogger(__name__)
		self._useGoogleLos = useGoogleLos
		# initialize the LOS with the ini file, use Google LOS flag, and gap filling method
		self.los = LOS(iniFile, useGoogleLos, gapFillingMethod=gapFillingMethod)
		self._demandStructure1 = demandStructure1
		self._demandStructure2 = demandStructure2
		self._demandStructure3 = demandStructure3
		self._demandStructure4 = demandStructure4

	def _getODTransitLOS(self, originEId, destinationEId, interval = None, transitMode = ['T','PR','KR']):
		'''
		returns	: a dict of {(mode, interval) : list of [ivtt, fare, ovtt]}
		zero ivtt and ovtt are replaced with the corresponding values from TILOS database
				and fare is extrapolated/interpolated using the available fare values at other
				intervals and the fare structure used in the model ***TO DO***
		what if all intervals have 0-stats? ***TO DO***
		'''
		return self.los.getODTransitLOS(originEId, destinationEId, interval, transitMode)
		
	def _getODTrafficLOS(self, originEId, destinationEId, interval = None, trafficMode = ['D','P']):
		'''
		returns	: a dict of {(mode, interval) : list of [time, distance, toll]}
		trafficMode	:	1 --> SOV/D
						2 --> HOV/P
		zero ivtt and distance are replaced with the corresponding values from TILOS database
				and toll is extrapolated/interpolated using the available toll values at other
				intervals and the toll structure used in the model ***TO DO***
		what if all intervals have 0-stats? ***TO DO***
		'''
		return self.los.getODTrafficLOS(originEId, destinationEId, interval, trafficMode)
		
	def _makeaDecision(self, utility, maxUtility):
		""" simulate an individual's decision based on her utilities """
		pass
		
	def apply(self):
		""" 
		Apply the discrete choice model on the <demand> stored in 
		the input DB <SQLITE_DB_INPUT> to get <IntermODMatrices>
		"""
		pass
		
	def updateTravelLOS(self, trafficLOS, transitLOS):
		self.los.setTravelLOS(trafficLOS, transitLOS)
	
	def getTravelLOS(self):
		return self.los.getTravelLOS()

	def setLOS(self, los):
		self.los = los
	
	def getLOS(self):
		return self.los
