# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 14:43:30 2019

@author: islam
"""

#import collections
import logging
import numpy as np
import os
from configparser import ConfigParser, ExtendedInterpolation

			
class roadTolls(dict):
	'''A class that keeps records of time-based road tolls (cents/km) 
	in the model. 
	road		: string
	direction	: string from ['east', 'west', 'north', 'south', 'e', 'w', 'n', 's'] but only 
				  the first character of each direction is used as keys for toll entries
	zone		: int > 0
	time		: hhmm in [0000 : 2359]
	
	Toll is a dict of {(road, dir):np.array((noOfZones, noOfIntervalsPerDay)), ...}
	
	Another representation of tolls is {<road>_<zone>_<dir>_<staT>_<endT>:value, ...}
	This representation is used in AIMSUN experiment variables and may be used to store/retreive tolls to/from files
	'''
	def __init__(self,
				 iniFile,
				 intervalWidth=30):
		'''
		iniFile				: the initialization file
		intervalWidth		: tolling interval width in minutes
		'''
		self._logger = logging.getLogger(__name__)
		self._iniFile = iniFile
		self._roads = []
		self._roadsDir = {}
		self._intervalWidth = int(intervalWidth)
		self._numberOfIntervals = 24 * 60 // self._intervalWidth
		try:
			parser = ConfigParser(interpolation=ExtendedInterpolation())
			parser.read(iniFile)
			self._defaultTollPath = os.path.abspath(parser['Paths']['DEFAULT_TOLL_FILE'])
			self.fillInDefaultTolls()
		except:
			self._defaultTollPath = None
		
		
	# As loggers cannot be pickled, we have to exclude the logger before pickling any instance and
	# re-create a new one when unpickling again
	def __getstate__(self):
		d = dict(self.__dict__)
		del d['_logger']
		return d
	
	def __setstate__(self, d):
		self.__dict__.update(d)
		self._logger = logging.getLogger(__name__)
	
	def __str__(self):
		'''
		print as table of three columns: agency | boarding fare | distance fare
		'''
		roundingPrec = 2
		colWidth = max(map(len,['road','direction','zone']) + [roundingPrec]) + 1
		colSep = '|'
		rowSep = '+'.join(['-'*colWidth + '-'*colWidth + '-'*colWidth, 
							''.join(['-'*colWidth for i in range(self._numberOfIntervals)])]) + '\n'
		result = 'Road Tolls\n'
		result += colSep.join(['Road'.ljust(colWidth) + 'Direction'.ljust(colWidth) + 'Zone'.ljust(colWidth), 'Time of Day'.center(colWidth*self._numberOfIntervals)]) + '\n'
		result += colSep.join([''.ljust(colWidth) + ''.ljust(colWidth) + ''.ljust(colWidth), 
								''.join([self._intervalToTime(i).ljust(colWidth) for i in range(self._numberOfIntervals)])]) + '\n'
		result += rowSep
		for road in self._roads:
			for dir in self._roadsDir[road]:
				zone = 1
				for row in self[(road,dir)]:
					result += colSep.join([road.ljust(colWidth) + dir.ljust(colWidth) + str(zone).ljust(colWidth), 
											''.join(map(lambda x: str(np.round(x, roundingPrec)).ljust(colWidth),row))]) + '\n'
					zone += 1
				result += rowSep
		return result
				
	def fillInDefaultTolls(self):
		'''Based on 2018 values from https://www.407etr.com/en/index.html'''
		if self._defaultTollPath is None:
			self._logger.error('Cannot find default tolls file')
			return
		with open(self._defaultTollPath) as f:
			content = f.readlines()
		# remove extra whitespaces and comments
		content = [x.strip() for x in content if not x.strip().startswith('#')]
		for element in content:
			keyAndValue = element.split('=')
			if len(keyAndValue) != 2 or len(keyAndValue[0]) == 0 or len(keyAndValue[1]) == 0 or keyAndValue[0].count('_') != 4:
				# skip this line
				continue
			road, zone, dir, startTime, endTime = keyAndValue[0].split('_')
			self.addRoad(road, dir)
			self.addZone(road, dir, int(zone))
			self.setToll(float(keyAndValue[1]), road, dir, int(zone), timeT=(startTime,endTime))
		
	def readFromFile(self, tollFile):
		'''Based on 2018 values from https://www.407etr.com/en/index.html'''
		with open(tollFile) as f:
			content = f.readlines()
		# remove extra whitespaces and comments
		content = [x.strip() for x in content if not x.strip().startswith('#')]
		for element in content:
			keyAndValue = element.split('=')
			if len(keyAndValue) != 2 or len(keyAndValue[0]) == 0 or len(keyAndValue[1]) == 0 or keyAndValue[0].count('_') != 4:
				# skip this line
				continue
			road, zone, dir, startTime, endTime = keyAndValue[0].split('_')
			self.addRoad(road, dir)
			self.addZone(road, dir, int(zone))
			self.setToll(float(keyAndValue[1]), road, dir, int(zone), timeT=(startTime,endTime))
			
	def writeToFile(self, tollFile):
		'''
		# variable naming: <HWY>_<Z>_<D>_<Sta>_<End>
		#	HWY	:	highway number, e.g. 401, 407, gde (Gardiner Expressway), dvp
		#	Z	:	zone number
		#	D	:	direction (n, e, s, and w)
		#	Sta	:	start time (format hhmmm)
		#	End	:	end time (format hhmmm)
		# if Sta = End = 000 --> this is the default toll value
		'''
		with open(tollFile, 'w') as f:
			tollDict = self.toDict()
			for key in tollDict:
				f.write('='.join([key, str(tollDict[key])]) + '\n')

	def toDict(self):
		result = {}
		for road in self._roads:
			for dir in self._roadsDir[road]:
				for zone in range(np.shape(self[(road,dir)])[0]):
					staT = self._intervalToTime(0)
					value = self[(road,dir)][zone,0]
					for interval in range(1, np.shape(self[(road,dir)])[1]):
						# If next interval has the same value, append it to the previous interval.
						# Otherwise, the previous interval is written to an entry, and another interval is initiated
						if value != self[(road,dir)][zone,interval]:
							if staT == '000':
								# default toll
								endT = '000'
							else:
								endT = self._intervalToTime(interval)
							result['_'.join([road, str(zone+1), dir, staT, endT])] = value
							staT = self._intervalToTime(interval)
							value = self[(road,dir)][zone,interval]
					# in case of a single toll value all over the day
					if staT == '000':
						result['_'.join([road, str(zone+1), dir, staT, staT])] = self[(road,dir)][zone,interval]
					# if toll during the last interval is different than the default toll, create a new entry
					elif self[(road,dir)][zone,interval] != result['_'.join([road, str(zone+1), dir, '000', '000'])]:
						result['_'.join([road, str(zone+1), dir, staT, '2359'])] = self[(road,dir)][zone,interval]
		return result
		
	def fromDict(self, inDict):
		for key in inDict:
			if len(key) == 0 or key.count('_') != 4 or inDict[key] is None:
				# skip this entry
				continue
			road, zone, dir, startTime, endTime = key.split('_')
			self.addRoad(road, dir)
			self.addZone(road, dir, int(zone))
			self.setToll(inDict[key], road, dir, int(zone), timeT=(startTime,endTime))
	
	def _validateRoad(self, road):
		return isinstance(road, str) 
		
	def _validateRoadDir(self, dir):	
		if isinstance(dir, str):
			return dir.lower() in ['east', 'west', 'north', 'south', 'e', 'w', 'n', 's']
		else:
			return False
		
	def _timeToInterval(self, t):
		# convert time <t> from format hhmm [0000:2359] to interval [0,<_numberOfIntervals> - 1]
		timeString = str(t).strip()
		hour = int(timeString[:-2])
		if hour > 23 or hour < 0:
			hour = 0
			self._logger.warning('Invalid time %s capped at 0' %str(t))
		minute = int(timeString[-2:])
		if minute > 59 or minute < 0:
			minute = 0
			self._logger.warning('Invalid time %s capped at 0' %str(t))
		return (hour*60 + minute) // self._intervalWidth
		
	def _intervalToTime(self, interval):
		# convert <interval> [0,<_numberOfIntervals> - 1] to its start time in format hhmm [0000:2359]
		t = interval * self._intervalWidth
		return str(t//60) + str(t%60).zfill(2)
		
	def addRoad(self, road, directions, numberOfZones=1):
		'''
		add road on a specific direction if it doesn't already exist
		'''
		# validate road and diretion
		if not self._validateRoad(road):
			self._logger.error('Incorrect road format: %s' % type(road))
			return
		if not isinstance(directions, list):
			directions = [directions]
		for dir in directions:
			if not self._validateRoadDir(dir):
				self._logger.error('Incorrect road direction format: %s' % type(dir))
				return
		# get the first character of each direction
		directions = [dir[0] for dir in directions]
		# add road if it doesn't already exist
		if road not in self._roads:
			self._roads.append(road)
			self._roadsDir[road] = []
		# add new directions
		for dir in directions:
			if dir not in self._roadsDir[road]:
				self._roadsDir[road].append(dir)
				# initialize aero toll for all zones and time intervals
				self.addZone(road, dir, numberOfZones)

	def addZone(self, road, dir, numberOfZones=1):
		'''
		add zones to a specific road and direction.
		if current number of zones of this road-direction is already greater than the new number of zones, do nothing
		'''
		# only valid for existing roads and directions
		if road in self._roads and dir in self._roadsDir[road]:
			if (road, dir) in self:
				# expand the toll array for this road-direction if it's zones less than numberOfZones
				if np.shape(self[(road, dir)])[0] < numberOfZones:
					self[(road, dir)] = np.vstack((self[(road, dir)], np.zeros((numberOfZones-np.shape(self[(road, dir)])[0], self._numberOfIntervals))))
			else:
				self[(road, dir)] = np.zeros((numberOfZones, self._numberOfIntervals))
		else:
			self._logger.error('Cannot add zone for road (%s,%s)' %(str(road), str(dir)))

	def setToll(self, value, road, dir, zone, interval=None, timeT=None):
		'''
		set the toll of a specific road, direction, zone, and interval to <value>
		if only one argument is passed for interval, then it should be the interval index.
		if two arguments are passed for interval, then they are the start and end times in 
		fomrat hhmm [00:2359]. They may span over more than one interval
		'''
		if interval is not None:
			try:
				self[(road, dir)][zone-1,interval] = value
			except:
				self._logger.error('Cannot set the toll value for road %s-%s, zone %i, interval %i' %(road, dir, zone, interval))
		elif timeT is not None:
			if isinstance(timeT, int) or isinstance(timeT, float) or isinstance(timeT, str):
				startInterval = endInterval = self._timeToInterval(timeT)
			elif isinstance(timeT, tuple):
				startInterval = self._timeToInterval(timeT[0])
				endInterval = self._timeToInterval(timeT[1])
			else:
				self._logger.error('Invalid time %s' %str(timeT))
			if startInterval == 0 and endInterval == 0:
				# set default toll to replace any zero toll
				self[(road, dir)][zone-1][self[(road, dir)][zone-1] == 0] = value
			else:
				# set the toll of specific intervals one by one
				for interval in range(startInterval, endInterval):
					self.setToll(value, road, dir, zone, interval)
		else:
			self._logger.error('setToll takes five arguments (%4 given)')
			
	def getToll(self, road, dir, zone, interval=None, timeT=None):
		'''
		set the toll of a specific road, direction, zone, and interval to <value>
		if only one argument is passed for interval, then it should be the interval index.
		if two arguments are passed for interval, then they are the start and end times in 
		fomrat hhmm [00:2359]. They may span over more than one interval
		'''
		if interval is not None:
			try:
				value = self[(road, dir)][zone-1,interval]
				return value
			except:
				self._logger.error('Cannot set the toll value for road %s-%s, zone %i, interval %i' %(road, dir, zone, interval))
				return -1
		elif timeT is not None:
			if isinstance(timeT, int) or isinstance(timeT, float) or isinstance(timeT, str):
				try:
					value = self[(road, dir)][zone-1,self._timeToInterval(timeT)]
					return value
				except:
					self._logger.error('Cannot set the toll value for road %s-%s, zone %i, time %f' %(road, dir, zone, float(timeT)))
					return -1
			elif isinstance(timeT, tuple):
				try:
					value = self[(road, dir)][zone-1,self._timeToInterval(timeT[0])]
					return value
				except:
					self._logger.error('Cannot set the toll value for road %s-%s, zone %i, time %f' %(road, dir, zone, float(timeT[0])))
					return -1
			else:
				self._logger.error('Invalid time %s' %str(timeT))
				return -1
		else:
			self._logger.error('setToll takes four arguments (3 given)')
			return -1
