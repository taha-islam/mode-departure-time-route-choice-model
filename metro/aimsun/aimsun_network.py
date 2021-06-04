# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 18:36:04 2019

@author: islam
"""

import sys
SITEPACKAGES = 'C:\\Python27\\Lib\\site-packages'
if SITEPACKAGES not in sys.path:
	sys.path.append(SITEPACKAGES)

import sqlite3
import logging
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyQt5.QtCore import *
from configparser import ConfigParser, ExtendedInterpolation


class aimsunNetwork(object):
	''' 
	A base class for Aimsun networks that does not require specific experiment
	initialized with .ini file + optional(console and model)
	loadNetwork			:	to load the model given in the ini file
	unloadNetwork		:	to unload Aimsun model
	'''
	def __init__(self, 
				iniFile, 
				console=None, 
				model=None, 
				angFile=None):
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		self._iniFile = iniFile
		self._console = console
		self._model = model
		self._baseDir = parser['Paths']['BASE_DIR']
		if angFile is None:
			self._angFile = parser['Paths']['ANGFile']
		else:
			self._angFile = angFile
		self._centConfigId = int(parser['Trip Assignment']['CENTROID_CONFIGURATION_ID'])
		self._logger = logging.getLogger(__name__)
		self.loadNetwork()
		self._centDict = self.centroidIdToEidDict(iniFile, self._model, self._centConfigId)
		
	def loadNetwork(self):
		# start console
		self._logger.debug('Loading %s' %self._angFile)
		if self._console is not None and self._model is not None:
			self._logger.debug('AIMSUN is already loaded')
		else:
			if self._console is None:
				self._console = ANGConsole()
			# load a network
			if self._console.open(self._angFile):
				self._logger.debug('Loading Aimsun Model')
				self._model = self._console.getModel()
			else:
				self._logger.error('cannot load network')
				self._console = None
				self._model = None
		return (self._console, self._model)
		
	def unloadNetwork(self):
		# close Aimsun
		if self._console is not None:
			try:
				self._logger.debug('Closing Aimsun')
				self._console.close()
				self._model = self._console.getModel()
			except:
				self._logger.error('Cannot close AIMSUN')
		else:
			self._logger.error('No Aimsun instance is running')
		return (self._console, self._model)
	
	def saveNetwork(self, fileName=None):
		'''save (overwrite) the model
			if fileName is not None, a copy will be saved with that name
		'''
		if self._console is not None:
			if fileName is None:
				fileName = self._angFile
			if self._console.save(fileName):
				self._logger.info('AIMSUN model was saved to %s' %fileName)
				return 0
			else:
				self._logger.error('Cannot save AIMSUN model to %s' %fileName)
		else:
			self._logger.error('No Aimsun instance is running')
			return -1
	
	class centroidIdToEidDict(dict):
		""" A dictionary of centroids' id-->eid 
		A centroid with id <row[0]> has eid <row[1]>
		There's another hidden dict, GTA06-->eid, accessed using GTA06ToEId
		"""
		def __init__(self, iniFile, model=None, centConfigId=-1):
			self._GTA06ToEId = {}
			parser = ConfigParser(interpolation=ExtendedInterpolation())
			parser.read(iniFile)
			try:
				inputDB = parser['Paths']['SQLITE_DB_INPUT']
				conn = sqlite3.connect(inputDB)
				cur = conn.cursor()
				cur.execute('SELECT Id, ExtId, GTA06 FROM CENTROID_ID_TO_EID_DICT')
				for (id, extId, GTA06) in cur:
					self[int(id)] = int(extId)
					self._GTA06ToEId[int(GTA06)] = int(extId)
			except:
				# if CENTROID_ID_TO_EID_DICT does not exist, set extId as a 
				# unique id based on each centroid's id
				centConfig = model.getCatalog().find(centConfigId)
				for centroid in centConfig.getCentroids():
					self[centroid.getId()] = 0
				sortedIds = sorted(self.keys())
				i = 1
				for id in sortedIds:
					self[id] = i
					i += 1
				for centroid in centConfig.getCentroids():
					if centroid.getName() != '':
						self._GTA06ToEId[centroid.getName()] = self[centroid.getId()]
			
			
			
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
	
