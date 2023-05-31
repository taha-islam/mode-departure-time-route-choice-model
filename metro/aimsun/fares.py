# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 13:49:06 2020

@author: islam
"""

import collections
import logging

fareType = {'B':0,'b':0,
			'D':1,'d':1}
fareTypeRecip = {0:'B',1:'D'}
agencies = ['TTC','TTC_EXPRESS','GO','MIWAY']
			
class transitFares(collections.MutableMapping):
	'''A class that keeps records of fares of all transit agencies 
	in the model. A fare entry should be in the following format:
	transit agency : (boarding fare, per-distance fare)
	'''
	def __init__(self, *args, **kwargs):
		self._logger = logging.getLogger(__name__)
		self.store = dict()
		for value in args:
			if not self._validateKeyType(value[0]):
				self._logger.error('Invalid transit agency entry %s. It has to be a String' % str(value[0]))
				return
			if not self._validateValueType(value[1]):
				self._logger.error('Invalid fare entry %s. It has to be in format: '
									'(boarding fare, per-distance fare)' % str(value[1]))
				return
		for key in kwargs:
			if not self._validateKeyType(key):
				self._logger.error('Invalid transit agency entry %s. It has to be a String' % str(value[0]))
				return
			if not self._validateValueType(kwargs[key]):
				self._logger.error('Invalid fare entry %s. It has to be in format: '
									'(boarding fare, per-distance fare)' % str(value[1]))
				return
		self.update(dict(*args, **kwargs))

	def __getitem__(self, key):
		return self.store[self.__keytransform__(key)]

	def __setitem__(self, key, value):
		if not self._validateKeyType(key):
			self._logger.error('Invalid transit agency entry %s. It has to be a String' % str(value[0]))
			return
		if not self._validateValueType(value):
			self._logger.error('Invalid fare entry %s. It has to be in format: '
								'(boarding fare, per-distance fare)' % str(value[1]))
			return
		self.store[self.__keytransform__(key)] = value

	def __delitem__(self, key):
		del self.store[self.__keytransform__(key)]

	def __iter__(self):
		return iter(self.store)

	def __len__(self):
		return len(self.store)

	def __keytransform__(self, key):
		return key
		
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
		result = 'Transit Fares\n'
		colWidth = max(list(map(len,['TTC','TTC_EXPRESS','GO','MIWAY', 'Boarding Fare', 'Distance Fare']))) + 2
		result += 'Agency'.ljust(colWidth) + 'Boarding Fare'.ljust(colWidth) + 'Distance Fare'.ljust(colWidth) + '\n'
		for key in self:
			result += key.ljust(colWidth) + str(self[key][0]).ljust(colWidth) + str(self[key][1]).ljust(colWidth) + '\n'
		return result

	def _validateKeyType(self, key):
		return isinstance(key, str)
			
	def _validateValueType(self, value):
		return isinstance(value, tuple) and \
				isinstance(value[0], (int, long, float)) and \
				isinstance(value[1], (int, long, float))
				
	def fillInDefaultFares(self):
		'''Based on the numbers used in DMG-Group GTAModel V4'''
		self['TTC'] = (1.98, 0)
		self['TTC_EXPRESS'] = (4.68, 0)
		self['GO'] = (4.07, 0.08)
		self['MIWAY'] = (1.98, 0)
		
class transitFareStructure(collections.MutableMapping):
	def __init__(self, numberOfIntervals, fillInDefault=False, *args):
		self._logger = logging.getLogger(__name__)
		self.elements = list()
		self._numberOfIntervals = numberOfIntervals
		# initialize the default fare with the default values
		self._defaultFare = transitFares()
		self._defaultFare.fillInDefaultFares()
		for index in range(len(args)):
			if isinstance(args[index], transitFares) and len(self) < self._numberOfIntervals:
				self.elements.append(args[index])
		for i in range(numberOfIntervals-len(self)):
			temp = transitFares()
			if fillInDefault:
				temp.fillInDefaultFares()
			self.elements.append(temp)
	
	def __iter__(self):
		return iter(self.elements)

	def __contains__(self, value):
		return value in self.elements

	def __len__(self):
		return len(self.elements)

	def __getitem__(self, key):
		return self.elements[key]
	
	def __setitem__(self, key, value):
		if not isinstance(value, transitFares):
			self._logger.error('Invalid transit fare : %s' % str(value))
			return
		self.elements[key] = value

	def __delitem__(self, key):
		del self.elements[key]

	def __str__(self):
		global fareTypeRecip
		result ='\n'.join(['# This file lists all fare values',
						'# To import these tolls to an experiment run the script "Import Toll Variables" from the experiment context menu',
						'# fares are in $ and $ per km',
						'# variable naming: <AGENCY>_<T>_<I>',
						'#	AGENCY	:	transit agency: TTC, TTCE, MIWAY, GO',
						'#	T		:	fare type: B for boarding and D for distance',
						'#	I		:	interval index (0 for the default fare to replace any missing intervals)\n\n'])
		for agency in agencies:
			result += '# ' + agency + '\n'
			for fType in range(len(fareTypeRecip)):
				param = '_'.join([agency,fareTypeRecip[fType],'0'])
				fareValue = self._defaultFare[agency][fType]
				result += ' = '.join([param, str(fareValue)])
				result += '\n'
			for i in range(self._numberOfIntervals):
				if len(self[i]) == 0:
					continue
				for fType in range(len(fareTypeRecip)):
					param = '_'.join([agency,fareTypeRecip[fType],str(i)])
					fareValue = self[i][agency][fType]
					result += ' = '.join([param, str(fareValue)])
					result += '\n'
		return result
	
	def fillInDefaultFares(self):
		for item in self:
			item.fillInDefaultFares()

	def load(self, fileName):
		global fareType
		try:
			f = open(fileName, 'r')
		except IOError:
			self._logger.error('No such file %s' %fileName)
			raise
		with f:
			content = f.readlines()
		# initialize all fares to -1
		self = [{(-1,-1) for key in singleIntFare} for singleIntFare in self]
		# remove extra whitespaces and comments
		content = [x.strip() for x in content if not x.strip().startswith('#')]
		variables = {}
		for element in content:
			keyAndValue = element.split('=')
			if len(keyAndValue) != 2 or len(keyAndValue[0]) == 0 or len(keyAndValue[1]) == 0:
				# skip this line
				continue
			fareValue = float(keyAndValue[1])
			if fareValue < 0:
				self._logger.error('Invalid negative fare value in <%s>' %element)
				continue
			attribute = keyAndValue[0].split('_')
			if len(attribute) < 3:
				self._logger.warning('Incomplete fare name <%s>' %keyAndValue[0])
				continue
			agency = '_'.join(attribute[0:-2])
			try:
				fType = fareType[attribute]
			except:
				self._logger.error('Invalid fare type in <%s>' %keyAndValue[0])
				continue
			interval = attribute[-1]
			if interval == 0:
				self._defaultFare[agency][fType] = fareValue
			elif interval > 0 and interval <= self._numberOfIntervals:
				self[interval-1][agency][fType] = fareValue
			else:
				self._logger.error('Invalid fare interval in <%s>' %keyAndValue[0])
				continue
		# replacing any ungiven fare with its defaul value
		for i in range(self._numberOfIntervals):
			for agency in self[i]:
				for j in [0,1]:
					if self[i][agency][j] == -1:
						self[i][agency][j] = self._defaultFare[agency][j]
	
	def save(self, fileName):
		try:
			f = open(fileName, 'w')
			f.write(str(self))
			f.close
		except:
			self._logger.error('Cannot save fares to %s' %str(fileName))

