# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 14:25:04 2019

@author: islam
"""

import sys
SITEPACKAGES = 'C:\\Python27\\Lib\\site-packages'
if SITEPACKAGES not in sys.path:
	sys.path.append(SITEPACKAGES)

import csv
import numpy as np
#from functools import partial
import time
import sqlite3
import logging
import os
from configparser import ConfigParser, ExtendedInterpolation
#import plot as plt

class accessStationDict(dict):
	"""A dictionary of centroids connected to stops in other centroids 
	centroid with eid <row[0]> is connected to a station in centroid with
	eid <row[1]>
	"""
	def __init__(self, iniFile):
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		inputDB = parser['Paths']['SQLITE_DB_INPUT']
		conn = sqlite3.connect(inputDB)
		cur = conn.cursor()
		cur.execute('SELECT cent1eId, cent2eId FROM ACCESS_STATION_DICT')
		for (cent1eId, cent2eId) in cur:
			self[int(cent1eId)] = int(cent2eId)
		

class centroidIdToEidDict(dict):
	""" A dictionary of centroids' id-->eid 
	A centroid with id <row[0]> has eid <row[1]>
	There's another hidden dict, GTA06-->eid, accessed using GTA06ToEId
	"""
	def __init__(self, iniFile):
		self._GTA06ToEId = {}
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		inputDB = parser['Paths']['SQLITE_DB_INPUT']
		conn = sqlite3.connect(inputDB)
		cur = conn.cursor()
		cur.execute('SELECT Id, ExtId, GTA06 FROM CENTROID_ID_TO_EID_DICT')
		for (id, extId, GTA06) in cur:
			self[int(id)] = int(extId)
			self._GTA06ToEId[int(GTA06)] = int(extId)
		
	def EIdToId(self, eId):
		for key in self:
			if self[key] == eId:
				return key
		return None
	
	def GTA06ToEId(self, GTA06):
		return self._GTA06ToEId[GTA06]

	def EIdToGTA06(self, eId):
		for key in self._GTA06ToEId:
			if self._GTA06ToEId[key] == eId:
				return key
		return None
	
	def GTA06ToId(self, GTA06):
		return self.EIdToId(self._GTA06ToEId[GTA06])

	
class odPairList(list):
	"""
	list of non-zero OD pairs
	origin <row[0]> and destination <row[1]>
	all centroid Ids in this list are external Ids
	"""
	def __init__(self, iniFile, demandType=0):
		"""
		demandType = 1	-->	traffic
		demandType = 2	-->	transit
		demandType = 0	-->	both
		"""
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		inputDB = parser['Paths']['SQLITE_DB_INPUT']
		conn = sqlite3.connect(inputDB)
		cur = conn.cursor()
		if demandType == 1:
			cur.execute('SELECT origin, destination FROM OD_PAIR_LIST WHERE trafficLOS = 1')
		elif demandType == 2:
			cur.execute('SELECT origin, destination FROM OD_PAIR_LIST WHERE transitLOS = 1') 
		else:
			cur.execute('SELECT origin, destination FROM OD_PAIR_LIST') 
		for (origin, destination) in cur:
			self.append((origin, destination))

			
class trafficODList(odPairList):
	"""list of traffic origin-destination pairs that have non-zero demand"""
	def __init__(self, iniFile):
		super(trafficODList, self).__init__(iniFile, 1)

			
class transitODList(odPairList):
	"""list of transit origin-destination pairs that have non-zero demand"""
	def __init__(self, iniFile):
		super(transitODList, self).__init__(iniFile, 2)


class ODMatricesAgg(dict):
	def __init__(self, numberOfIntervals, modes, name=None):
		self._numberOfIntervals = numberOfIntervals
		self._modes = modes
		if name is not None:
			self._name = name
		else:
			self._name = ''
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				self[(mode,interval)] = 0
				
	def __str__(self):
		cellWidth = 12
		roundingPrec = 4
		# space for modes written in the first column
		firstColumnWidth = max(list(map(len, self._modes + ['Total']))) + 2
		res = self._name.center(self._numberOfIntervals*cellWidth + firstColumnWidth) \
					+ '\n' + ' '.ljust(firstColumnWidth)
		for interval in range(1, self._numberOfIntervals+1):
			res += str(interval).ljust(cellWidth)
		res += 'Total'.ljust(cellWidth) + '\n'
		temporalSum = [0 for i in range(self._numberOfIntervals)]
		for mode in self._modes:
			modalSum = 0
			res += mode.ljust(firstColumnWidth)
			for interval in range(1, self._numberOfIntervals+1):
				res += str(round(self[(mode,interval)],roundingPrec)).ljust(cellWidth)
				temporalSum[interval-1] += self[(mode,interval)]
				modalSum += self[(mode,interval)]
			res += str(round(modalSum,roundingPrec)).ljust(cellWidth) + '\n'
		# last row (totals)
		modalSum = 0
		res += 'Total'.ljust(firstColumnWidth)
		for interval in range(1, self._numberOfIntervals+1):
			res += str(round(temporalSum[interval-1],roundingPrec)).ljust(cellWidth)
			modalSum += temporalSum[interval-1]
		res += str(round(modalSum,roundingPrec)).ljust(cellWidth) + '\n'
		res += '=' * (self._numberOfIntervals*cellWidth + firstColumnWidth)
		return res
			
	def __add__(self, other):
		if self._numberOfIntervals != other._numberOfIntervals or \
				self._modes != other._modes:
			return None
		result = ODMatricesAgg(self._numberOfIntervals, self._modes, 
					name = ' + '.join(['('+self._name+')', '('+other._name+')']))
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = self[(mode,interval)] + other[(mode,interval)]
		return result
		
	def __sub__(self, other):
		if self._numberOfIntervals != other._numberOfIntervals or \
				self._modes != other._modes:
			return None
		result = ODMatricesAgg(self._numberOfIntervals, self._modes, 
					name = ' - '.join(['('+self._name+')', '('+other._name+')']))
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = self[(mode,interval)] - other[(mode,interval)]
		return result
	
	def __mul__(self, other):
		if self._numberOfIntervals != other._numberOfIntervals or \
				self._modes != other._modes:
			return None
		result = ODMatricesAgg(self._numberOfIntervals, self._modes, 
					name = ' * '.join(['('+self._name+')', '('+other._name+')']))
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = self[(mode,interval)] * other[(mode,interval)]
		return result
	
	def __div__(self, other):
		'''if self._numberOfIntervals != other._numberOfIntervals or \
				self._modes != other._modes:
			return None
		result = ODMatricesAgg(self._numberOfIntervals, self._modes, 
					name = ' / '.join(['('+self._name+')', '('+other._name+')']))
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = self[(mode,interval)] / other[(mode,interval)]
		return result
		'''
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' / '.join(['('+self._name+')', str(other)])
			result = ODMatricesAgg(self._numberOfIntervals, self._modes, name = name)
			for mode in self._modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] / other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self._modes != other._modes:
				self._logger.error('TypeError: unsupported operand type(s) for /: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' / '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatricesAgg(self._numberOfIntervals, self._modes, name = name)
			for mode in self._modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] / other[(mode,interval)]
		return result
		
	def __floordiv__(self, other):
		return self.__div__(other)
	
	def __truediv__(self, other):
		return self.__div__(other)
		
	def max(self):
		return max(self.values())
		
	def min(self):
		return min(self.values())
	
	def abs(self):
		result = ODMatricesAgg(self._numberOfIntervals, self._modes)
		for mode in self._modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = abs(self[(mode,interval)])
		return result
				
	def rename(self, name):
		self._name = name
		
	def sum(self):
		return sum(self.values())

		
class ODMatrices(dict):
	"""
    | This class contains a set of OD matrices in dcitionary hierarchy.
	Within the dictionary, each OD matrix is indexed by tuple of (mode,interval).
	Mode names and number of intervals are imported from the ini file.
	Contents of any matrix (numpy 2D array) are indexed by the external Ids of 
	the origin centroid (row) and the destination centroid (column).
	| External files (for save and load) follow the following naming convention:
		<demand_dir>/<mode_name>_<interval_number>.csv
	"""
	def __init__(self,
				 iniFile,
				 modeNames=None,
				 name=None,
				 random=False,
				 modes=None,
				 numberOfIntervals=None,
				 intervalNames=None,
				 numberOfCentroids=None,
				 centroidNames=None,
				 demandDir=None):
		'''
		| iniFile				: the initialization file
		| modeNames			: name of group of modes as defined in <iniFile>
		| name				: name of the <ODMatrices>
		| random				: if True, initialize all matrices with random numbers. Otherwise fill them with zeros
		| modes				: list of names of modes, e.g. ['D','P','T','PR','KR']
		| numberOfIntervals	: number of departure-time intervals
		| intervalNames		: string names of departure-time intervals
		| numberOfCentroids	: number of centroids in each OD matrix
		| centroidNames		: string names of centroids
		| demandDir			: directory where the OD matrices are stored
		'''
		self._logger = logging.getLogger(__name__)
		if modeNames is None and modes is None and demandDir is None:
			errorMsg = 'You must provide at least one of:\n' \
						'\tmode names in the ini file, \n' \
						'\tlist of modes, or\n' \
						'\tpath to the OD matrices'
			self._logger.error(errorMsg)
			print(errorMsg)
			return
		self._iniFile = iniFile
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		if demandDir is None:
			self.demandDir = os.path.abspath(parser['Paths']['DEMAND_DIR'])
		else:
			self.demandDir = os.path.abspath(demandDir)
			modes, numberOfIntervals = self.identifyModesAndIntervals(demandDir)
		if name is not None:
			self._name = name
		else:
			self._name = ''
		# MODES
		self._modeNames = modeNames
		if modes is None:
			self.modes = parser['Demand'][modeNames].strip().split(',')
		else:
			self.modes = modes
		# DEPARTURE TIME INTERVALS
		if numberOfIntervals is None:
			self._numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		else:
			self._numberOfIntervals = numberOfIntervals
		if intervalNames is None or len(intervalNames) != self._numberOfIntervals:
			self._intervalNames = list(map(str,range(1,self._numberOfIntervals+1)))
		else:
			self._intervalNames = [str(i) for i in intervalNames]
		# CENTROIDS
		if numberOfCentroids is None:
			self.numberOfCentroids = int(parser['Demand']['numberOfCentroids'])
		else:
			self.numberOfCentroids = numberOfCentroids
		# TO DO: fix this (should be generic)
		self.numberOfCentroidsToronto = int(parser.get('Demand','numberOfCentroidsToronto', fallback=0))
		if centroidNames is None or len(centroidNames) != self.numberOfCentroids:
			self._centroidNames = list(map(str,range(1,self.numberOfCentroids+1)))
		else:
			self._centroidNames = centroidNames
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				if random:
					self[(mode,interval)] = np.random.random(
						(self.numberOfCentroids,self.numberOfCentroids))
				else:
					self[(mode,interval)] = np.zeros(
						(self.numberOfCentroids,self.numberOfCentroids))
	
	def append(self, other, dim=1):
		'''
		| dim :	1 --> append along <mode>
		| 		2 --> append along <interval>
		| 		3 --> append along <origin>
		| 		4 --> append along <destination>
		'''
		if isinstance(other, int) or isinstance(other, float):
			# convert the scalar <other> to a <ODMatrices> instance
			val = other
			if dim == 1:
				other = ODMatrices(self._iniFile, modes = ['New mode'],
							numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
							numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			elif dim == 2:
				other = ODMatrices(self._iniFile, modes = self.modes,
							numberOfIntervals=1, intervalNames=[str(self._numberOfIntervals+1)],
							numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			elif dim == 3:
				self._logger.warning('Appending along centroids is not implemented yet')
				return
			elif dim == 4:
				self._logger.warning('Appending along centroids is not implemented yet')
				return
			other.setAllTo(val)
		
		if dim == 1:
			# add matrices of new modes, but similar intervals, origins, and destinations
			if self.getNumberOfIntervals() != other.getNumberOfIntervals() or \
				self.getNumberOfCentroids() != other.getNumberOfCentroids():
				self._logger.error('Cannot append \'%s\' to \'%s\'' %(other.__class__.__name__,self.__class__.__name__))
				return
			# exclude common modes
			newModes = [i for i in other.modes if i not in self.modes]
			self.modes += newModes
			for mode in newModes:
				for interval in range(1, self._numberOfIntervals+1):
					if random:
						self[(mode,interval)] = other[(mode,interval)]
		elif dim == 2:
			# add matrices of new intervals (continuing the existing intervals), but similar modes, origins, and destinations
			if self.getModes() != other.getModes() or \
				self.getNumberOfCentroids() != other.getNumberOfCentroids():
				self._logger.error('Cannot append \'%s\' to \'%s\'' %(other.__class__.__name__,self.__class__.__name__))
				return
			for mode in self.modes:
				for interval in range(1, other._numberOfIntervals+1):
					self[(mode,self._numberOfIntervals+interval)] = other[(mode,interval)]
			self._numberOfIntervals += other._numberOfIntervals
			self._intervalNames += other._intervalNames
		elif dim == 3:
			self._logger.warning('Appending along centroids is not implemented yet')
		elif dim == 4:
			self._logger.warning('Appending along centroids is not implemented yet')

	# As loggers cannot be pickled during deepcopying the class, we have to exclude the logger before pickling
	# any instance and re-create a new one when unpickling again
	def __getstate__(self):
		d = dict(self.__dict__)
		del d['_logger']
		return d
	
	def __setstate__(self, d):
		self.__dict__.update(d)
		self._logger = logging.getLogger(__name__)
	
	def getModes(self):
		return self.modes
	
	def getNumberOfIntervals(self):
		return self._numberOfIntervals
		
	def getIntervalNames(self):
		return self._intervalNames
		
	def getNumberOfCentroids(self):
		return self.numberOfCentroids
		
	def getCentroidNames(self):
		return self._centroidNames
		
	def __str__(self):
		return self.str(np.sum)
	
	def str(self, aggFun=np.sum, aggPrint=True, grandAggPrint=True, roundingPrec=2):
		verSep = '|'
		horSep1 = '-'
		horSep2 = '+'
		secondHeader = True # for centroid names
		if len(self._centroidNames) > 10:
			self._logger.warning('OD matrix %s has more than 10 rows/columns. '
					'Only the first 10 rows/columns will be printd' %self._name)
			cenNumber = 10
		else:
			cenNumber = len(self._centroidNames)
		if cenNumber == 1:
			aggPrint = False
			verSep = horSep1 = horSep2 = ''
			secondHeader = False
		if aggPrint or grandAggPrint:
			try:
				aggFunName = aggFun.__name__
			except:
				aggFunName = ' '
			aggFunNameLen = len(aggFunName)
		else:
			aggFunNameLen = 0
		
		# a giant 2D array
		fullMatrix = np.empty((0, cenNumber*self._numberOfIntervals))
		fullRow = np.empty((cenNumber, 0))
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				fullRow = np.hstack((fullRow, self[(mode,interval)]))
			fullMatrix = np.vstack((fullMatrix, fullRow))
			fullRow = np.empty((cenNumber, 0))
		fullMatrix = np.round(fullMatrix, roundingPrec)
		# cell width
		fullMatrixStr = [list(map(str, row)) for row in np.around(fullMatrix, decimals=roundingPrec)]
		cellWidth = max(np.max([list(map(len, row)) for row in fullMatrixStr]),
						max(list(map(len,self._centroidNames)))
						) + 2
		# column header width
		firstColumnWidth = max(list(map(len, self.modes)) + [aggFunNameLen]) + 2
		secondColumnWidth = (max(list(map(len, self._centroidNames[:cenNumber])) + [aggFunNameLen]) + 2) * secondHeader
		# each short line (row in a matrix) has cenNumber cells + aggregation cell (if applicable)
		lineWidthShort = cellWidth*(cenNumber+aggPrint)
		# the horizontal separator
		if len(horSep1) > 0:
			horSep = horSep2.join([horSep1*(firstColumnWidth+secondColumnWidth)] + \
									[horSep1*lineWidthShort] * self._numberOfIntervals + \
									[horSep1*cellWidth] * grandAggPrint
									) + '\n'
		else:
			horSep = ''
		# forming the printed string
		result = self._name + '\n'
		# first row header
		result += verSep.join([' '*(firstColumnWidth+secondColumnWidth)] + \
					[i.center(lineWidthShort) for i in self._intervalNames] +\
					[aggFunName.ljust(cellWidth)]*grandAggPrint) + '\n'
		# second row header
		if secondHeader:
			result += verSep.join([' '*(firstColumnWidth+secondColumnWidth)] + \
					[''.join([i.ljust(cellWidth) for i in self._centroidNames+[aggFunName]])]*self._numberOfIntervals +\
					[' '*cellWidth]*grandAggPrint) + '\n'
		result += horSep
		# row by row
		for row in range(np.shape(fullMatrix)[0]):
			# first column header
			if row%cenNumber == round((cenNumber-1)/2.0):
				result += self.modes[row//cenNumber].ljust(firstColumnWidth)
			else:
				result += ' ' * firstColumnWidth
			# second column header
			if secondHeader:
				result += self._centroidNames[row%cenNumber].ljust(secondColumnWidth)
			# data columns
			for col in range(self._numberOfIntervals):
				slice = fullMatrix[row,col*cenNumber:(col+1)*cenNumber].tolist()
				# local column aggregation
				if aggPrint:
					slice.append(aggFun(fullMatrix[row,col*cenNumber:(col+1)*cenNumber]))
				slice = np.round(slice, roundingPrec)
				result += verSep + ''.join([i.ljust(cellWidth) for i in list(map(str, slice))])
			# last (grand aggregation) column
			if grandAggPrint:
				result += verSep + str(np.round(aggFun(fullMatrix[row,]), roundingPrec)).ljust(cellWidth)
			result += '\n'
			# end of a mode. print local aggregation row and horizontal separator if applicable
			if (row+1) % cenNumber == 0:
				if aggPrint:
					# first column header
					result += ' '.ljust(firstColumnWidth)
					# second column header
					if secondHeader:
						result += aggFunName.ljust(secondColumnWidth)
					# aggregate per column
					aggregation = aggFun(fullMatrix[row-cenNumber+1:row+1,], axis=0)
					for col in range(self._numberOfIntervals):
						slice = aggregation[col*cenNumber:(col+1)*cenNumber].tolist()
						slice.append(aggFun(aggregation[col*cenNumber:(col+1)*cenNumber]))
						slice = np.round(slice, roundingPrec)
						result += verSep + ''.join([i.ljust(cellWidth) for i in list(map(str, slice))])
					# last (grand aggregation) column
					if grandAggPrint:
						result += verSep + str(np.round(aggFun(aggregation), roundingPrec)).ljust(cellWidth) 
					result += '\n'
				# horizontal separator between modes
				result += horSep
		# last (grand aggregation) row
		if grandAggPrint:
			# first and second column headers
			result += aggFunName.ljust(firstColumnWidth+secondColumnWidth)
			# aggregate the whole matrix per column
			aggregation = aggFun(fullMatrix,axis=0)
			for col in range(self._numberOfIntervals):
				slice = aggregation[col*cenNumber:(col+1)*cenNumber].tolist()
				# local column aggregation
				if aggPrint:
					slice.append(aggFun(aggregation[col*cenNumber:(col+1)*cenNumber]))
				slice = np.round(slice, roundingPrec)
				result += verSep + ''.join([i.ljust(cellWidth) for i in list(map(str, slice))])
			result += verSep + str(np.round(aggFun(aggregation), roundingPrec)).ljust(cellWidth) + '\n'
		return result
	
	'''==================================================================================
	arithmetic operations
	'''
	def __add__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' + '.join([self._name, str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] + other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for +: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' + '.join([self._name, other._name])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] + other[(mode,interval)]
		return result
		
	def __sub__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' - '.join([self._name, str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] - other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for -: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' - '.join([self._name, other._name])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] - other[(mode,interval)]
		return result
	
	def __mul__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' * '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] * other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for *: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' * '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] * other[(mode,interval)]
		return result
	
	def __div__(self, other):
		'''
		true division with zero output where the denominator is zero
		'''
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' / '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] / other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for /: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' / '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					#result[(mode,interval)] = self[(mode,interval)] / other[(mode,interval)]
					result[(mode,interval)] = np.true_divide(self[(mode,interval)],
																other[(mode,interval)],
																out=np.zeros_like(other[(mode,interval)]),
																where=other[(mode,interval)]!=0)
		return result
		
	def __floordiv__(self, other):
		return self.__div__(other)
	
	def __truediv__(self, other):
		return self.__div__(other)
		
	def __neg__(self):
		if self._name is not None:
			name = ' - ' + self._name
		result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = -self[(mode,interval)]
		return result
		
	def __abs__(self):
		if self._name is not None:
			name = 'abs(' + self._name + ')'
		result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = np.abs(self[(mode,interval)])
		return result
		
	def log(self):
		if self._name is not None:
			name = 'log(' + self._name + ')'
		result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = np.log(self[(mode,interval)],
											out=np.zeros_like(self[(mode,interval)]),
											where=self[(mode,interval)]>0)
		return result
		
	'''==================================================================================
	comparisons and stats
	'''
	def __lt__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' < '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] < other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for <: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' < '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] < other[(mode,interval)]
		return result
	
	def __le__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' <= '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] <= other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for <=: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' <= '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] <= other[(mode,interval)]
		return result
	
	def __eq__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' == '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] == other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for ==: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' == '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] == other[(mode,interval)]
		return result
	
	def __ne__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' != '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] != other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for !=: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' != '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] != other[(mode,interval)]
		return result
	
	def __ge__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' >= '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] >= other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for >=: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' >= '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] >= other[(mode,interval)]
		return result
	
	def __gt__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			if self._name is not None:
				name = ' > '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] > other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for >: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' > '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] > other[(mode,interval)]
		return result
	
	def __and__(self, other):
		if isinstance(other, bool):
			if self._name is not None:
				name = ' and '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] > other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for and: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' and '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] & other[(mode,interval)]
		return result
	
	def __or__(self, other):
		if isinstance(other, bool):
			if self._name is not None:
				name = ' or '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] > other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for or: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' or '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] | other[(mode,interval)]
		return result
	
	def __xor__(self, other):
		if isinstance(other, bool):
			if self._name is not None:
				name = ' xor '.join(['('+self._name+')', str(other)])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] > other
		else:
			if self._numberOfIntervals != other._numberOfIntervals or \
					self.modes != other.modes:
				self._logger.error('TypeError: unsupported operand type(s) for xor: \'%s\' and \'%s\'' \
					% (self.__class__.__name__, other.__class__.__name__))
				return None
			if self._name is not None and other._name is not None:
				name = ' xor '.join(['('+self._name+')', '('+other._name+')'])
			result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes,
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
			for mode in self.modes:
				for interval in range(1, self._numberOfIntervals+1):
					result[(mode,interval)] = self[(mode,interval)] ^ other[(mode,interval)]
		return result
	
	def __not__(self):
		result = ODMatrices(iniFile=self._iniFile, name = 'not( ' + self._name + ' )',
						modeNames = self._modeNames, modes=self.modes, 
						numberOfIntervals=self._numberOfIntervals, intervalNames=self._intervalNames,
						numberOfCentroids=self.numberOfCentroids, centroidNames=self._centroidNames)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = not(self[(mode,interval)])
		return result
		
	def relDiff(self, other, method = 'first', fillZerosWithNan = True):
		# relative difference between two sets of OD matrices defined as:
		# abs(x-y) / ((x+y)/2)
		if self._numberOfIntervals != other._numberOfIntervals or \
				self.modes != other.modes:
			return None
		if self._name is not None and other._name is not None:
			name = 'relative difference(' + self._name + ', ' + other._name + ')'
		result = ODMatrices(self._iniFile, self._modeNames, name = name, modes = self.modes)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				if method == 'first':
					result[(mode,interval)] = np.abs(self[(mode,interval)] - other[(mode,interval)]) / \
						self[(mode,interval)]
				elif method == 'second':
					result[(mode,interval)] = np.abs(self[(mode,interval)] - other[(mode,interval)]) / \
						other[(mode,interval)]
				elif method == 'mean':
					result[(mode,interval)] = np.abs(self[(mode,interval)] - other[(mode,interval)]) / \
						(self[(mode,interval)] + other[(mode,interval)]) * 2
				elif method == 'max':
					result[(mode,interval)] = np.abs(self[(mode,interval)] - other[(mode,interval)]) / \
						np.maximum(self[(mode,interval)], other[(mode,interval)])
				elif method == 'min':
					result[(mode,interval)] = np.abs(self[(mode,interval)] - other[(mode,interval)]) / \
						np.minimum(self[(mode,interval)] + other[(mode,interval)])
				else:
					print('Invalid method of calculating relative difference')
					result = None
					return
				if fillZerosWithNan:
					result[(mode,interval)][self[(mode,interval)] == 0] = np.nan
					result[(mode,interval)][other[(mode,interval)] == 0] = np.nan
		return result
	
	'''
	ranges	: None			: No aggregation along this dimension	
			  []			: Full aggregation along this dimension
			  [(,),(,),...]	: Custom aggregation along this dimension
					or		  the first for the centroids (start,end), and 
			  [[.],[.],...]	  the latter the modes and intervals as a list
	names	: None			: No aggregation along this dimension
			  [] or ['.']	: Full aggregation along this dimension
			  ['.','.',...]	: Custom aggregation along this dimension
	if names doesn't match the ranges along any specific dimension, trust the ranges and update the names based on them
	'''
	# centroidRanges is a list of tuples of ranges, e.g. [(1,53),(57,62),(120,257)] will generate
	# a sum over 3 bands 1:53, 57:62, 120:257
	def _checkCentroidRanges(self, centroidRanges, centroidNames):
		if centroidRanges is None:
			centroidRanges = [(i,i) for i in range(1,self.numberOfCentroids+1)]
		elif len(centroidRanges) == 0:
			centroidRanges = [(1,self.numberOfCentroids)]
			if centroidNames is None or len(centroidNames) == 0:
				centroidNames = ['All Centroids']
		if centroidNames is None or len(centroidNames) != len(centroidRanges):
			centroidNames = [str(i) if i==j else '%i-%i'%(i,j) for i,j in centroidRanges]
		return centroidRanges, centroidNames
	
	def _checkModeRanges(self, modeRanges, modeNames):
		if modeRanges is None:
			modeRanges = [[i] for i in self.modes]
		elif len(modeRanges) == 0:
			modeRanges = [self.modes]
			if modeNames is None or len(modeNames) == 0:
				modeNames = ['All Modes']
		if modeNames is None or len(modeNames) != len(modeRanges):
			modeNames = [','.join(i) for i in modeRanges]
		return modeRanges, modeNames
	
	def _checkIntervalRanges(self, intervalRanges, intervalNames):
		if intervalRanges is None:
			intervalRanges = [[i] for i in range(1, self._numberOfIntervals+1)]
		elif len(intervalRanges) == 0:
			intervalRanges = [range(1, self._numberOfIntervals+1)]
			if intervalNames is None or len(intervalNames) == 0:
				intervalNames = ['All Intervals']
		if intervalNames is None or len(intervalNames) != len(intervalRanges):
			intervalNames = [','.join(list(map(str,i))) for i in intervalRanges]
		return intervalRanges, intervalNames
	
	def sum(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='sum(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						temp += self[(mode,interval)]
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.sum(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
		
	def mean(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='mean(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						temp += self[(mode,interval)]
				temp = temp / (len(modeRanges[modeInd]) * len(intervalRanges[intervalInd]))
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.mean(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nonzeromean(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nonzeromean(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		tempNonzeroCount = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						temp += self[(mode,interval)]
						tempNonzeroCount += (self[(mode,interval)] != 0)				
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						numerator = np.sum(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
						denominator = np.sum(tempNonzeroCount[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = np.asscalar(
																					np.true_divide(
																						numerator,
																						denominator,
																						out=np.zeros_like(denominator),
																						where=denominator!=0
																					))
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
				tempNonzeroCount = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nanmean(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nanmean(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		tempNotnanCount = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						# add arrays together ignoring nan
						temp = np.nansum(np.dstack((temp,self[(mode,interval)])),2)
						# count non-nan cells
						tempNotnanCount += np.logical_not(np.isnan(self[(mode,interval)]))
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						numerator = np.sum(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
						denominator = np.sum(tempNotnanCount[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = np.asscalar(
																					np.true_divide(
																						numerator,
																						denominator,
																						out=np.zeros_like(denominator),
																						where=denominator!=0
																					))
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
				tempNotnanCount = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def min(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='min(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						# find cell-by-cell min in two 2D arrays
						temp = np.min(np.dstack((temp,self[(mode,interval)])),2)
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.min(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nanmin(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nanmin(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						# find cell-by-cell min in two 2D arrays
						temp = np.nanmin(np.dstack((temp,self[(mode,interval)])),2)
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.nanmin(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nonzeromin(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nonzeromin(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						for rowInd in range(len(centroidRanges)):
							for colInd in range(len(centroidRanges)):
								if result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] == 0:
									result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
										np.min(self[(mode,interval)][np.nonzero(self[(mode,interval)])])
								else:
									result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
										min(np.min(self[(mode,interval)][np.nonzero(self[(mode,interval)])]),
											result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd])
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def max(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='max(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						# find cell-by-cell min in two 2D arrays
						temp = np.max(np.dstack((temp,self[(mode,interval)])),2)
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.max(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nanmax(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nanmax(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						# find cell-by-cell min in two 2D arrays
						temp = np.nanmax(np.dstack((temp,self[(mode,interval)])),2)
				for rowInd in range(len(centroidRanges)):
					for colInd in range(len(centroidRanges)):
						result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
							np.nanmax(temp[centroidRanges[rowInd][0]-1:centroidRanges[rowInd][1],centroidRanges[colInd][0]-1:centroidRanges[colInd][1]])
				temp = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def nonzeromax(self, 
			centroidRanges=[], centroidNames=[],
			modeRanges=None, modeNames=None,
			intervalRanges=None, intervalNames=None):
		centroidRanges, centroidNames = self._checkCentroidRanges(centroidRanges, centroidNames)
		modeRanges, modeNames = self._checkModeRanges(modeRanges, modeNames)
		intervalRanges, intervalNames = self._checkIntervalRanges(intervalRanges, intervalNames)
		result = ODMatrices(self._iniFile, name='nonzeromax(%s)'%self._name, modes=modeNames, 
							numberOfIntervals=len(intervalNames),
							intervalNames=intervalNames,
							numberOfCentroids=len(centroidNames),
							centroidNames=centroidNames)
		for modeInd in range(len(modeRanges)):
			for intervalInd in range(len(intervalRanges)):
				for mode in modeRanges[modeInd]:
					for interval in intervalRanges[intervalInd]:
						for rowInd in range(len(centroidRanges)):
							for colInd in range(len(centroidRanges)):
								if result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] == 0:
									result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
										np.max(self[(mode,interval)][np.nonzero(self[(mode,interval)])])
								else:
									result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd] = \
										max(np.min(self[(mode,interval)][np.nonzero(self[(mode,interval)])]),
											result[(modeNames[modeInd],intervalInd+1)][rowInd,colInd])
		# return scalar if aggregating everything over all dimensions
		if len(modeRanges)==1 and len(intervalRanges)==1 and len(centroidRanges)==1:
			result = result[(modeNames[0],1)][0,0]
		return result
	
	def percentile(self, q):
		#return the mean of each OD matrix
		result = ODMatricesAgg(self._numberOfIntervals, self.modes, 
					name = 'percentile( ' + self._name + ', ' + str(q) +  ' )')
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = np.percentile(self[(mode,interval)], q)
		return result
		
	def nanpercentile(self, q):
		#return the mean of each OD matrix
		result = ODMatricesAgg(self._numberOfIntervals, self.modes, 
					name = 'percentile( ' + self._name + ', ' + str(q) +  ' )')
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = np.nanpercentile(self[(mode,interval)], q)
		return result
	
	def count_nonzero(self):
		result = ODMatricesAgg(self._numberOfIntervals, self.modes, 
					name = 'nonzero_counts( ' + self._name + ' )')
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				result[(mode,interval)] = np.count_nonzero(self[(mode,interval)])
		return result
	
	def count_if(self, cond):
		# cond is a string, such as ">= 9", '!=-1', etc.
		result = ODMatricesAgg(self._numberOfIntervals, self.modes, 
					name = 'countif( ' + self._name + ' ' + cond + ' )')
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				for row in self[(mode,interval)]:
					for cell in row:
						if np.isnan(cell):
							continue
						if eval(str(cell)+cond):
							result[(mode,interval)] += 1
		return result
		
	def match(self, other):
		result = (self != 0) & (other != 0)
		result.rename('matching(%s,%s)' %(self._name, other._name))
		return result
		
	def mismatch(self, other):
		result = (self != 0) ^ (other != 0)
		result.rename('mismatch(%s,%s)' %(self._name, other._name))
		return result
		
	'''==================================================================================
	utils
	'''
	def rename(self, name):
		self._name = name

	def head(self, mode, interval):
		lastIdx = 10
		if len(self) < 10:
			lastIdx = len(self)
		return self[(mode, interval)][0:lastIdx][0:lastIdx]

	def tail(self, mode, interval):
		lastIdx = -10
		if len(self) < 10:
			lastIdx = 0
		return self[(mode, interval)][lastIdx:][lastIdx:]
		
	def setAllTo(self, val):
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				self[(mode,interval)].fill(float(val))
				#self[(mode,interval)] = np.full(
				#		(self.numberOfCentroids,self.numberOfCentroids), float(val))
		
	def replaceAllValues(self, val1, val2):
		#replace all elements (in all matrices) equal to val1 with val2
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				self[(mode,interval)][self[(mode,interval)] == val1] = val2
		
	def save(self, path=None, centId=1, sparse=False, intervals=None, modes=None):
		# str, [[]]
		if path is not None:
			# update demand directory for these set of matrices (if given a new directory)
			self.demandDir = os.path.abspath(path)
		if not os.path.exists(self.demandDir):
			# create the target directory if it does noot exist
			try:
				os.makedirs(self.demandDir)
			except OSError as exc:
				if exc.errno != errno.EEXIST:
					raise
		# save all intervals if not given specific sequence
		# if given specific sequence, check if there are corresponding matrices
		if intervals is None:
			intervals = range(1, self._numberOfIntervals+1)
		else:
			intervals = [x for x in intervals if x in range(1, self._numberOfIntervals+1)]
		# save all modes if not given specific sequence
		# if given specific sequence, check if there are corresponding matrices
		if modes is None:
			modes = self.modes
		else:
			modes = [x for x in modes if x in self.modes]
		self._logger.info('Saving OD matrices (%s) to %s' %(self._name, self.demandDir))
		for mode in modes:
			for interval in intervals:
				fullName = os.path.join(self.demandDir, mode+'_'+str(interval)+'.csv')
				with open(fullName, 'w', newline='') as fp:
					writer = csv.writer(fp, delimiter=',')
					if sparse:
						# write non-zero cells only
						writer.writerow(['origin','destination','value'])	# writing the header
						nonzeroIdxs = np.nonzero(self[(mode, interval)])
						for origin, destination in zip(nonzeroIdxs[0], nonzeroIdxs[1]):
							if np.isnan(self[(mode, interval)][origin,destination]):
								continue
							writer.writerow([str(origin+1),str(destination+1),str(self[(mode, interval)][origin,destination])])
					else:
						# write full matrix
						#writer.writerow(self.baseODMatrixRow0)	# writing the header
						writer.writerow(['eid'] + self._centroidNames)	# writing the header
						#for centroidEID, row in zip(self.baseODMatrixCol0, self[(mode, interval)]):
						for centroidEID, row in zip(self._centroidNames, self[(mode, interval)]):
							writer.writerow([centroidEID] + row.tolist())	# first cell is the origin's eid

	def saveFig(self, figName=None, path=None, figType=0, intervals=None, modes=None):
		''' 
		plot the OD matrices to file whose name is <figName>
		if <figName> is None check the given <path>. If <path> is given, save the plot to <path>\<self._name>_<origin>_<destination>
		If <path> is not given, save the plot to <self.demandDir>\<self._name>_<origin>_<destination>
		figType	: 0 : regular line graph
				  1 : bar chart
				  2 : stacked bar chart
		'''
		raise NotImplementedError("This function is not implemented in Python 3!")
		'''if figName is None:
			if path is not None:
				# update demand directory for these set of matrices (if given a new directory)
				self.demandDir = os.path.abspath(path)
			if not os.path.exists(self.demandDir):
				# create the target directory if it does noot exist
				try:
					os.makedirs(self.demandDir)
				except OSError as exc:
					if exc.errno != errno.EEXIST:
						raise
		# save the valid intervals from the given sequence, or save all intervals if not given specific sequence
		if intervals is None:
			intervals = range(1, self._numberOfIntervals+1)
		else:
			intervals = [x for x in intervals if x in range(1, self._numberOfIntervals+1)]
		# save the valid modes from the given sequence, or save all modes if not given specific sequence
		if modes is None:
			modes = self.modes
		else:
			modes = [x for x in modes if x in self.modes]
		self._logger.info('Saving OD matrices (%s) figures to %s' %(self._name, self.demandDir))
		# save the first 5 centroids if number of centroids is more than 1
		if self.numberOfCentroids > 1:
			numberOfCentroids = 5
		else:
			numberOfCentroids = 1
		# plot figures for each otigin-destination pair
		for origin in range(numberOfCentroids):
			for destination in range(numberOfCentroids):
				matrix = np.array([[self[(m,i)][origin, destination] for i in intervals] for m in modes])
				if figName is None:
					figName = os.path.join(self.demandDir,'_'.join([self._name, self._centroidNames[origin],
																	'to', self._centroidNames[destination]]))
				if figType == 0:
					plt.lineChart(figName, matrix, intervals, modes)
				elif figType == 1:
					plt.barChart(figName, matrix, intervals, modes)
				elif figType == 2:
					plt.stackedbarChart(figName, matrix, intervals, modes)
		'''
			
	def load(self, path=None, centId=1, sparse=False):
		'''
		load OD matrices from csv files stored in the demand directory defined in the ini file
		centId	:	0 --> detect automatically from the first cell in file
					1 --> extId
					2 --> id
					3 --> GTA06
		sparse	:	True --> only non-zero cells are stored
		'''
		if path is not None:
			self.demandDir = os.path.abspath(path)
		self._logger.debug('Loading OD matrices (%s) from %s' %(self._name, self.demandDir))
		# set all matrices to 0
		self.setAllTo(0)
		for mode in self.modes:
			for interval in range(1, self._numberOfIntervals+1):
				fullName = os.path.join(self.demandDir, mode+'_'+str(interval)+'.csv')
				try:
					file = open(fullName, 'r')
				except IOError:
					self._logger.error('No such file %s' %fullName)
					raise
				else:
					with file:
						reader = csv.reader(file)
						firstrow = reader.next()
						if sparse or firstrow==['origin', 'destination', 'value']:
							for row in reader:
								self[(mode,interval)][int(row[0])-1, int(row[1])-1] = float(row[2] or '0')
						else:
							self._centroidNames = firstrow[1:]
							if centId == 0:
								if firstrow[0] == 'eid':
									centIdInThisFile = 1
								elif firstrow[0] == 'id':
									centIdInThisFile = 2
									header = list(map(int, firstrow[1:]))
								elif firstrow[0] == 'GTA06':
									centIdInThisFile = 3
									header = list(map(int, firstrow[1:]))
								else:
									self._logger.error('Cannot recognize centroids Ids in file %s' %fullName)
									return
							else:
								centIdInThisFile = centId
							
							if centIdInThisFile == 1:
								# if already stored with extId, read the cells directly
								index = 0
								for row in reader:
									self[(mode,interval)][index] = [float(x or '0') for x in row[1:]]
									index += 1
								continue
							elif centIdInThisFile == 2:
								# if stored with Aimsun id
								centDict = centroidIdToEidDict(self._iniFile)
								indices = [centDict[i] for i in header]
							elif centIdInThisFile == 3:
								# if stored with GTA06
								centDict = centroidIdToEidDict(self._iniFile)
								indices = list(map(centDict.GTA06ToEId, header))
							rowIndex = 0
							for row in reader:
								origin = indices[0]
								for colIndex in range(1, len(row)):
									self[(mode,interval)][indices[rowIndex]-1][indices[colIndex-1]-1] = float(row[colIndex] or '0')
								rowIndex += 1
					
	def identifyModesAndIntervals(self, dir):
		''' identify mode names and number of intervals by traversing the contents
		of a given path. Files are considereed only if in the following format:
		<mode>_<interval>.csv
		'''
		intervals = {}
		# file names split with '_'
		files = [f[:-4].split('_') for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f)) and f.endswith('.csv')]
		# file names have at least a single '_'
		files = [f for f in files if len(f) > 1]
		for f in files:
			try:
				interval = int(f[-1])
				if interval <= 0:
					continue
			except:
				continue
			mode = ''.join(f[:-1])
			if mode in intervals.keys():
				intervals[mode].append(int(interval))
			else:
				intervals[mode] = [int(interval)]
		numberOfIntervals = -1
		for mode in intervals.keys():
			intervals[mode].sort()
			if len(intervals[mode]) == intervals[mode][-1]:
				# if there's no gaps
				maxIndex = intervals[mode][-1]
			else:
				# in case of gaps
				maxIndex = [intervals[mode][i]==i+1 for i in range(len(intervals[mode]))].index(False)
			if maxIndex == 0:
				del intervals[mode]
				continue
			if numberOfIntervals == -1 or maxIndex < numberOfIntervals:
				numberOfIntervals = maxIndex
		return intervals.keys(), numberOfIntervals
	
	def printSumByMode(self):
		for mode in self.modes:
			sum = 0
			for interval in range(1, self._numberOfIntervals+1):
				sum += np.sum(self[(mode,interval)])
			print('Sum of trips of mode %s = %f' %(mode, sum))

	def printSumByInterval(self):
		for interval in range(1, self._numberOfIntervals+1):
			sum = 0
			for mode in self.modes:
				sum += np.sum(self[(mode,interval)])
			print('Sum of trips during interval %i = %f' %(interval, sum))

						
class IntermODMatrices(ODMatrices):
	"""intermediate OD matrices (output of the discrete choice model)"""
	def __init__(self, iniFile, name=None, random=False):
		super(IntermODMatrices, self).__init__(iniFile, 'INTERM_MODES', name, random)


class FinalODMatrices(ODMatrices):
	"""final OD matrices (input to Aimsun)"""
	def __init__(self, iniFile, name=None, random=False):
		super(FinalODMatrices, self).__init__(iniFile, 'FINAL_MODES', name, random)
		# masking trips between Toronto centroids only
		self.TTCDemandMask = np.array([[1 for x in range(self.numberOfCentroidsToronto)]
			+ [0 for x in range(self.numberOfCentroids-self.numberOfCentroidsToronto)] 
					for x in range(self.numberOfCentroidsToronto)]
			+ [[0 for x in range(self.numberOfCentroids)] 
					for x in range(self.numberOfCentroids-self.numberOfCentroidsToronto)])
		# masking trips from outside Toronto to Toronto and the other way (but not outside to outside)
		self.RegionalDemandMask = np.array([[0 for x in range(self.numberOfCentroidsToronto)]
			+ [1 for x in range(self.numberOfCentroids-self.numberOfCentroidsToronto)]
					for x in range(self.numberOfCentroidsToronto)]
			+ [[1 for x in range(self.numberOfCentroidsToronto)] 
				+ [0 for x in range(self.numberOfCentroids-self.numberOfCentroidsToronto)] 
						for x in range(self.numberOfCentroids-self.numberOfCentroidsToronto)])


class trafficSkimMatrices(ODMatrices):
	"""
	traffic skim matrices (output of the DTA model)
	sorted by centroid (Aimsun) id
	"""
	def __init__(self, iniFile, name=None, random=False):
		super(trafficSkimMatrices, self).__init__(iniFile, 'TRAFFIC_SKIM_MATRICES', name, random)
						

class transitSkimMatrices(ODMatrices):
	"""
	transit skim matrices (output of the transit assignment model)
	sorted by centroid (Aimsun) id
	"""
	def __init__(self, iniFile, name=None, random=False):
		super(transitSkimMatrices, self).__init__(iniFile, 'TRANSIT_SKIM_MATRICES', name, random)


class demandEval(object):
	"""A class for converting the intermediate OD matrices obtained 
	from the discrete choice model to OD matrices compatible with Aimsun
	"""
	def __init__(self, iniFile):
		self.iniFile = iniFile
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self.demandDir = parser['Paths']['DEMAND_DIR']
		self.CONVERGENCE_THRESHOLD = float(parser['Convergence']['CONVERGENCE_THRESHOLD'])
		self._numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
		self.numberOfCentroids = int(parser['Demand']['numberOfCentroids'])
		self.HOV_FACTOR = int(parser['Demand']['HOV_FACTOR'])
		# first row and column (origins & destinations) in finalODMatrices
		self.baseODMatrixRow0 = self.baseODMatrixCol0 = ['eid'] + range(self.numberOfCentroids)
		# traffic and transit sums for convergence test
		self._prevTrafficDemandSum = [0 for x in range(self._numberOfIntervals)]
		self._prevTransitDemandSum = [0 for x in range(self._numberOfIntervals)]
		# dictionary of centroids connected to stops in other centroids
		self.accessStationDict = accessStationDict(iniFile)
		
	def writeODMatrix(self, demandFileName, ODMatrix):
		# str, [[]]
		fullName = self.demandDir + demandFileName
		with open(fullName, 'w', newline='') as fp:
			writer = csv.writer(fp)
			writer.writerow(self.baseODMatrixRow0)	# writing the header
			for centroidEID, row in zip(self.baseODMatrixCol0, ODMatrix):
				writer.writerow([centroidEID] + row)	# first cell is the origin's eid

	def splitODMatrix(self, baseMat):
		# split <baseMat> into <trafficMat> and <transitMat>
		# baseMat : 2D matrix, i.e. np.array([[]])
		# assuming access time is less than 30 min and won't shift the start time of transit trip
		trafficMat = np.zeros((self.numberOfCentroids,self.numberOfCentroids))
		transitMat = baseMat
		for centroid in self.accessStationDict:
			# all the PR or KR demand originating from centroid will go to ACCESS_STATION_DICT[centroid]
			# to access the transit station there
			# so, the demand will be traffic demand between centroid --> ACCESS_STATION_DICT[centroid] and
			# transit demand from ACCESS_STATION_DICT[centroid] --> original destinations
			# note that all lists start with index 0 (not dictionaries)
			trafficMat[centroid-1][self.accessStationDict[centroid]-1] += np.sum(baseMat[centroid-1])
			transitMat[self.accessStationDict[centroid]-1] += baseMat[centroid-1]
			transitMat[centroid-1] = [0 for x in range(self.numberOfCentroids)]
		return trafficMat, transitMat

	def calculateAimsunDemand(self, intermODMatrices):
		#converged = True
		finalODMatrices = FinalODMatrices(self.iniFile)
		for interval in range(1, self._numberOfIntervals+1):
			# split PR and KR trips into two sets of matrices traffic + transit according to the access station
			# should we calculate the arrival time at the transit station and shift some transit demand to the following interval?
			PRTrafficMat, PRTransitMat = self.splitODMatrix(intermODMatrices[('PR',interval)] * \
						(finalODMatrices.TTCDemandMask + finalODMatrices.RegionalDemandMask))
			KRTrafficMat, KRTransitMat = self.splitODMatrix(intermODMatrices[('KR',interval)] * \
						(finalODMatrices.TTCDemandMask + finalODMatrices.RegionalDemandMask))
			# split traffic demand into SOV and HOV
			finalODMatrices[('HOV',interval)] = self.HOV_FACTOR \
								* (intermODMatrices[('P',interval)] + KRTrafficMat)
			finalODMatrices[('SOV',interval)] = intermODMatrices[('D',interval)] \
								+ PRTrafficMat - finalODMatrices[('HOV',interval)]
			finalODMatrices[('SOV',interval)][finalODMatrices[('SOV',interval)] < 0] = 0
			# split the transit demand according to the origin and dest to TTC and Regional
			finalODMatrices[('TTC',interval)] = finalODMatrices.TTCDemandMask * \
				(intermODMatrices[('T',interval)] + PRTransitMat + KRTransitMat)
			finalODMatrices[('Regional',interval)] = finalODMatrices.RegionalDemandMask * \
				(intermODMatrices[('T',interval)] + PRTransitMat + KRTransitMat)
		return finalODMatrices
	'''		# traffic and transit sums for convergence test
			trafficDemandSum = np.sum(finalODMatrices[('SOV',interval)]) \
								+ np.sum(finalODMatrices[('HOV',interval)])
			transitDemandSum = np.sum(finalODMatrices[('TTC',interval)]) \
								+ np.sum(finalODMatrices[('Regional',interval)])
			#=======================================================#
			#				DCM-Aimsun Convergence Test				#
			#=======================================================#
			if converged and \
				self._prevTrafficDemandSum[interval-1] != 0 and \
				self._prevTransitDemandSum[interval-1] != 0:
				relDiffTrafficDemand = abs(trafficDemandSum - self._prevTrafficDemandSum[interval-1])\
										/self._prevTrafficDemandSum[interval-1]
				relDiffTransitDemand = abs(transitDemandSum - self._prevTransitDemandSum[interval-1])\
										/self._prevTransitDemandSum[interval-1]
				if (relDiffTrafficDemand > self.CONVERGENCE_THRESHOLD) or\
					(relDiffTransitDemand > self.CONVERGENCE_THRESHOLD):
					converged = False
			self._prevTrafficDemandSum[interval-1] = trafficDemandSum
			self._prevTransitDemandSum[interval-1] = transitDemandSum
		return converged, finalODMatrices'''
		
if __name__ == "__main__":
	# check number of arguments
	if len(sys.argv) < 2:
		print('Usage: aconsole -script %s INI_FILE' % sys.argv[0])
		sys.exit(-1)
	# Start calculating execution time
	start_time = time.time()
	intermODMatrices = IntermODMatrices(sys.argv[1], True)
	intermODMatrices.save()
	demandCalculations = demand(sys.argv[1])
	converged, finalMats = demandCalculations.calculateAimsunDemand(intermODMatrices)
	finalMats.save()
	print("--- Demand calculations finished in %s seconds ---" % (time.time() - start_time))
	
	''' output for random intermediate demand
	--- Demand calculations finished in 213.014999866 seconds ---
	'''