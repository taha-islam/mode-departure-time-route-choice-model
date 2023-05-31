# -*- coding: utf-8 -*-
"""
Created on Fri Nov 29 16:44:50 2019

@author: islam
"""

import numpy as np
import operator
import random
import sqlite3
import logging
from configparser import ConfigParser, ExtendedInterpolation
from base import depTimeAndModeChModel, demandCalculationMethod, losMulFactor, selectionMethod
from metro3.tools.demand import IntermODMatrices, ODMatrices


class nl(depTimeAndModeChModel):
	""" 
	A nested logit (NL) model for departure time and travel mode choice
	"""		
	def __init__(self, 
				iniFile, 
				adjFactor = None, 
				useGoogleLos = False, 
				demandStructure1 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure2 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure3 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				demandStructure4 = demandCalculationMethod.eCalculateTrafficCalculateTransit,
				mulFactor = None,
				gapFillingMethod=0):
		if mulFactor is not None and not isinstance(mulFactor, losMulFactor):
			self._logger.error('Invalid type of multiplication factor used within the '
								'discrete choice model')
			return
		super(nl, self).__init__(iniFile, useGoogleLos, demandStructure1, demandStructure2, demandStructure3, demandStructure4, gapFillingMethod)
		self._logger = logging.getLogger(__name__)
		# Nests coefficients: 5 nests (modes)
		self._nestCoef = {'D':1, 'P':1/1.228, 'T':1/1.138, 'PR':1/1.181, 'KR':1/1.212}
		# coefficients of each alternative
		# 40 alternatives (5x8)
		# In addition to the ASC of each alternative
		# for traffic modes: coefficients of [time, fuel_cost, toll], NOTE: fuel cost = distance multiplied by some constant
		# for transit modes: coefficients of [IVTT, fare, ovtt]
		self._param={('D',1) : np.array([-0.039, -0.062, -0.062]),
					('D',2) : np.array([-0.039, -0.062, -0.062]),
					('D',3) : np.array([-0.039, -0.062, -0.062]),
					('D',4) : np.array([-0.039, -0.062, -0.062]),
					('D',5) : np.array([-0.039, -0.062, -0.062]),
					('D',6) : np.array([-0.039, -0.062, -0.062]),
					('D',7) : np.array([-0.039, -0.062, -0.062]),
					('D',8) : np.array([-0.039, -0.062, -0.062]),
					('P',1) : np.array([ 0.000,  0.000,  0.000]),
					('P',2) : np.array([-0.039, -0.062, -0.062]),
					('P',3) : np.array([-0.039, -0.062, -0.062]),
					('P',4) : np.array([-0.039, -0.062, -0.062]),
					('P',5) : np.array([-0.039, -0.062, -0.062]),
					('P',6) : np.array([-0.039, -0.062, -0.062]),
					('P',7) : np.array([-0.039, -0.062, -0.062]),
					('P',8) : np.array([-0.039, -0.062, -0.062]),
					('T',1) : np.array([-0.039, -0.062,  0.000]),
					('T',2) : np.array([-0.039, -0.062, -0.046]),
					('T',3) : np.array([-0.039, -0.062, -0.046]),
					('T',4) : np.array([-0.039, -0.062, -0.046]),
					('T',5) : np.array([-0.039, -0.062, -0.046]),
					('T',6) : np.array([-0.039, -0.062, -0.046]),
					('T',7) : np.array([-0.039, -0.062, -0.046]),
					('T',8) : np.array([-0.039, -0.062, -0.046]),
					('PR',1): np.array([-0.039, -0.062, -0.046]),
					('PR',2): np.array([-0.039, -0.062, -0.046]),
					('PR',3): np.array([-0.039, -0.062, -0.046]),
					('PR',4): np.array([-0.039, -0.062, -0.046]),
					('PR',5): np.array([-0.039, -0.062, -0.046]),
					('PR',6): np.array([-0.039, -0.062, -0.046]),
					('PR',7): np.array([-0.039, -0.062, -0.046]),
					('PR',8): np.array([-0.039, -0.062, -0.046]),
					('KR',1): np.array([-0.039, -0.062, -0.046]),
					('KR',2): np.array([-0.039, -0.062, -0.046]),
					('KR',3): np.array([-0.039, -0.062, -0.046]),
					('KR',4): np.array([-0.039, -0.062, -0.046]),
					('KR',5): np.array([-0.039, -0.062, -0.046]),
					('KR',6): np.array([-0.039, -0.062, -0.046]),
					('KR',7): np.array([-0.039, -0.062, -0.046]),
					('KR',8): np.array([-0.039, -0.062, -0.046])
					}
		# regions (categories) for the ASC's
		parser = ConfigParser(interpolation=ExtendedInterpolation())
		parser.read(iniFile)
		regionsDict = {}
		for region, cenRange in parser.items('DCM Regions'):
			if region in parser.defaults():
				continue
			regionsDict[region] = tuple(map(int,cenRange.strip().split(',')))
		# sort regions and their ranges (asc) based on the start of the range
		regionsSorted = sorted(regionsDict.items(), key=lambda x: x[1][0])
		self._regions = [i[0] for i in regionsSorted]
		self._regionsCentroids = [i[1] for i in regionsSorted]
		# alternative specific constants
		self._ASC = ODMatrices(self._iniFile,
							 name='Alternative Specific Constants',
							 modes=self._intermModes,
							 numberOfIntervals=self._numberOfIntervals,
							 numberOfCentroids=len(self._regions),
							 centroidNames=self._regions)
		self._ASC[('D' ,1)].fill( 0.000)
		self._ASC[('D' ,2)].fill( 0.395)
		self._ASC[('D' ,3)].fill( 0.986)
		self._ASC[('D' ,4)].fill( 1.196)
		self._ASC[('D' ,5)].fill( 1.521)
		self._ASC[('D' ,6)].fill( 1.119)
		self._ASC[('D' ,7)].fill( 0.835)
		self._ASC[('D' ,8)].fill( 0.272)
		self._ASC[('P' ,1)].fill(-2.587)
		self._ASC[('P' ,2)].fill(-1.087)
		self._ASC[('P' ,3)].fill(-0.626)
		self._ASC[('P' ,4)].fill(-0.392)
		self._ASC[('P' ,5)].fill(-0.194)
		self._ASC[('P' ,6)].fill(-0.635)
		self._ASC[('P' ,7)].fill(-0.675)
		self._ASC[('P' ,8)].fill(-0.998)
		self._ASC[('T' ,1)].fill(-0.483)
		self._ASC[('T' ,2)].fill( 0.342)
		self._ASC[('T' ,3)].fill( 1.063)
		self._ASC[('T' ,4)].fill( 1.067)
		self._ASC[('T' ,5)].fill( 1.330)
		self._ASC[('T' ,6)].fill( 0.693)
		self._ASC[('T' ,7)].fill( 0.709)
		self._ASC[('T' ,8)].fill(-0.264)
		self._ASC[('PR',1)].fill(-1.916)
		self._ASC[('PR',2)].fill(-1.453)
		self._ASC[('PR',3)].fill(-0.932)
		self._ASC[('PR',4)].fill(-1.223)
		self._ASC[('PR',5)].fill(-1.605)
		self._ASC[('PR',6)].fill(-2.440)
		self._ASC[('PR',7)].fill(-2.648)
		self._ASC[('PR',8)].fill(-3.735)
		self._ASC[('KR',1)].fill(-2.446)
		self._ASC[('KR',2)].fill(-1.854)
		self._ASC[('KR',3)].fill(-1.262)
		self._ASC[('KR',4)].fill(-1.425)
		self._ASC[('KR',5)].fill(-1.586)
		self._ASC[('KR',6)].fill(-2.227)
		self._ASC[('KR',7)].fill(-2.669)
		self._ASC[('KR',8)].fill(-3.795)
		
		
		if mulFactor is not None:
			for mode in ['D', 'P', 'T', 'PR', 'KR']:
				for interval in range(1, self._numberOfIntervals+1):
					self._param[(mode, interval)] *= mulFactor[(mode, interval)]
		# Calibrating the ASC's
		if adjFactor is None:
			adjFactor = ODMatrices(self._iniFile,
								 name='Adjustment Factors for the Alternative Specific Constants',
								 modes=self._intermModes,
								 numberOfIntervals=self._numberOfIntervals,
								 numberOfCentroids=len(self._regions),
								 centroidNames=self._regions)
			try:
				adjFactor.load(self._adjFactorDir)
			except:
				self._logger.warning('Cannot load the calibrated ASCs. The original ones will be uesd.')
		'''adjFactor[('D' ,1)] = np.array([[-0.78,0.64,-0.05,0.99,-0.43,0.88],
										[-1.1,0.53,-0.22,1,0.15,1.23],
										[-0.93,-0.51,-0.32,0.55,-0.38,0.48],
										[-0.95,0.57,0.23,0.29,0.42,0.87],
										[-0.71,-0.37,0.08,0.65,-0.12,0.55],
										[-0.98,0.68,0.43,0.87,0.36,0.17]])
		adjFactor[('D' ,2)] = np.array([[-0.37,0.57,-0.07,0.06,-0.14,0.75],
										[-0.82,0.31,0.21,0.66,-0.21,0.65],
										[-0.73,-0.08,-0.35,0.56,0.24,0.63],
										[-0.68,0.53,0.47,0.33,0.23,0.6],
										[-1.16,0.42,0.01,0.52,-0.09,0.43],
										[-1.12,0.71,0.3,0.33,0.1,0.09]])
		adjFactor[('D' ,3)] = np.array([[-0.45,0.4,0.6,1.42,0.79,1.31],
										[-0.99,-0.12,0.39,0.48,0.39,0.79],
										[-0.85,0.33,-0.17,0.68,0.29,0.75],
										[-0.39,0.21,0.57,0.14,0.59,0.48],
										[-0.87,0.83,0.11,0.64,0,0.45],
										[-0.85,0.7,0.32,0.32,0.27,0.03]])
		adjFactor[('D' ,4)] = np.array([[0.01,0.67,0.75,1.21,1.01,1.42],
										[-0.86,0.32,0.36,0.62,0.39,0.53],
										[-0.53,0.75,0.16,0.82,0.39,0.6],
										[-0.38,0.36,0.59,0.22,0.34,0.34],
										[-0.85,0.85,0.08,0.3,0.03,0.25],
										[-1.24,0.1,0.22,0.19,0.2,0.08]])
		adjFactor[('D' ,5)] = np.array([[0.23,1.02,0.42,0.92,0.79,0.93],
										[-0.59,0.43,0.56,0.52,0.75,0.33],
										[-0.49,0.65,0.48,0.36,0.41,0.57],
										[-0.66,0.45,0.62,0.43,0.59,0.3],
										[-1.06,0.6,0.27,0.21,0.32,0.21],
										[-1.48,-0.01,0.22,-0.1,0.11,0.12]])
		adjFactor[('D' ,6)] = np.array([[0.47,1.08,1.06,0.34,0.86,0.62],
										[-0.34,0.93,0.44,0.56,0.6,0.05],
										[-0.47,0.77,0.9,0.24,0.45,0.33],
										[-0.93,0.77,0.21,0.74,0.49,0.01],
										[-1.12,0.53,0.26,0.11,0.67,0.29],
										[-2.27,0.01,-0.21,-0.15,0.07,0.16]])
		adjFactor[('D' ,7)] = np.array([[0.25,0.95,1.18,1.46,1.14,0.78],
										[-0.77,0.8,0.39,0.6,0.4,0.27],
										[-0.35,1.02,0.64,0.69,0.52,0.44],
										[-0.54,0.79,0.48,0.56,0.46,0.23],
										[-1.18,0.88,0.57,0.32,0.49,0.29],
										[-1.83,0.19,-0.01,-0.09,0.23,0.12]])
		adjFactor[('D' ,8)] = np.array([[0.51,1.29,1.65,2.51,0.78,1.4],
										[-0.84,1.09,0.68,0.51,0.56,-0.11],
										[-0.48,1.13,0.76,0.62,0.44,0.05],
										[-1.12,0.8,0.95,0.6,0.82,-0.05],
										[-1.51,0.62,0.56,0.28,0.44,0.54],
										[-1.61,-0.12,-0.15,-0.2,0.06,0.13]])
		adjFactor[('P' ,1)] = np.array([[0.0,0,0,-1.6,0,-0.96],
										[-0.65,0.08,-0.55,-0.84,0.94,1.02],
										[-0.46,-1.6,1.26,0.68,0.48,-0.25],
										[-0.79,0.53,0,0.54,-1.67,1.29],
										[-0.94,2.04,-0.1,-2.45,0.1,0.33],
										[-1.1,0.32,0.39,0.27,0.04,0.23]])
		adjFactor[('P' ,2)] = np.array([[-0.31,0,0,0,0,-2.63],
										[-0.23,0.01,0.32,0.75,-1.94,0.9],
										[-0.31,0,-0.48,0.3,-0.53,0.17],
										[-0.29,0.17,-2.31,0.21,0.26,0.78],
										[-0.11,0.41,0.02,0.43,0.19,0],
										[-0.58,0.67,0.72,-0.13,0.92,-0.01]])
		adjFactor[('P' ,3)] = np.array([[-0.29,-1.28,0,1.23,0,-0.4],
										[-0.53,0,-0.21,-0.32,-1.87,0.43],
										[-0.02,1.15,-0.2,1.46,-0.32,-0.17],
										[-0.01,0.43,1.33,0.33,0.95,0.18],
										[-0.17,1.81,-0.27,0.27,0.08,0.08],
										[-0.33,-0.06,0.44,0.51,0.02,-0.11]])
		adjFactor[('P' ,4)] = np.array([[0.72,-1.67,1.28,-0.85,0.4,1.11],
										[0.37,0.2,0.77,-1.31,-0.58,-0.33],
										[0.27,0.47,-0.13,0.43,0.27,-1.87],
										[0.32,0.55,0.87,0.24,0.2,0.26],
										[-0.35,0.61,0.31,0.7,0.03,0.52],
										[-0.4,-0.69,0.09,0.05,0.35,0.08]])
		adjFactor[('P' ,5)] = np.array([[0.6,1.04,-1.31,0.87,-0.19,-0.02],
										[0.09,0.01,-0.1,-0.24,-1.12,-0.78],
										[0.3,-0.07,0.5,-1.34,-0.57,-0.32],
										[0.41,0.27,-0.29,0.31,-0.99,-0.34],
										[-1.15,0.45,0.32,0.81,0.38,0.46],
										[-0.72,-1.04,0.03,-0.05,0.16,0.17]])
		adjFactor[('P' ,6)] = np.array([[0.88,1.49,-1.34,0.73,-1.74,0],
										[0.55,0.73,0.37,-0.55,-0.72,-0.87],
										[0.54,1.03,0.74,0.74,0.06,-0.59],
										[-1.17,1.16,0.67,0.44,1.58,-0.68],
										[-0.61,0.01,0.42,0.52,0.64,0.42],
										[-2.06,0.13,-0.06,-0.58,0.3,0.06]])
		adjFactor[('P' ,7)] = np.array([[1.36,0.9,-0.48,-1.65,1.71,-0.8],
										[-0.08,0.33,-0.32,0.26,0.39,-0.86],
										[0.17,0.33,0.43,-0.92,-0.56,0.83],
										[-0.82,0.71,-2.13,0.35,0.52,-0.14],
										[-1.24,0.8,-0.86,1.96,0.27,0.2],
										[-1.35,0.57,-0.07,-0.18,0.27,0.11]])
		adjFactor[('P' ,8)] = np.array([[0.9,0.44,-0.67,0,-2.14,0],
										[-0.59,0.52,-0.92,-0.35,-1.06,0.11],
										[-0.09,1.28,0.51,0,0.09,-1.16],
										[-0.98,0.68,1.37,0.29,0.04,-0.35],
										[-1.43,2.29,-0.25,-0.18,0.23,0.08],
										[-1.27,-0.52,-0.3,-1.15,0.17,0.05]])
		adjFactor[('T' ,1)] = np.array([[-0.65,0.49,-0.08,1.38,1.07,1.96],
										[0.57,-0.59,0.18,0.75,1.1,1.11],
										[0.48,0.45,-0.78,0.96,0.11,0.2],
										[1.06,0.8,1.05,-0.5,1.33,0.55],
										[0.66,1.91,0.14,0.9,-0.69,0.03],
										[0.39,1.07,0.76,0.7,0.12,-0.97]])
		adjFactor[('T' ,2)] = np.array([[1.04,-0.45,-0.18,1.52,0.81,1.37],
										[0.44,-0.54,0.05,0.31,0.1,0.18],
										[0.55,0.04,-0.38,0.32,-0.07,1.1],
										[0.97,0.05,0.5,-0.47,0.49,-0.06],
										[0.74,1.26,0.14,0.77,-0.42,-0.1],
										[0.67,0.39,1.08,0.64,-0.26,-1.23]])
		adjFactor[('T' ,3)] = np.array([[0.38,0.49,0.02,1.39,1.43,0.69],
										[0.52,-0.28,0.41,0.15,0.98,0.24],
										[0.61,0.51,-0.89,0.61,-0.02,-0.02],
										[0.78,0.34,0.72,-0.7,0.98,-0.09],
										[0.71,0.86,0.01,0.93,-0.65,-0.5],
										[0.31,0.86,0.6,0.11,-0.24,-0.86]])
		adjFactor[('T' ,4)] = np.array([[0.81,0.64,0.45,0.64,2.22,0.65],
										[0.47,-0.28,0.96,0.36,0.66,-0.02],
										[0.78,0.83,-0.05,0.92,-0.1,-0.19],
										[0.88,0.36,0.42,-0.39,0.77,-0.74],
										[0.82,0.9,0.44,0.29,-0.35,-0.71],
										[-0.07,-0.27,0.3,-0.02,-0.7,-0.88]])
		adjFactor[('T' ,5)] = np.array([[1.2,0.95,0.95,1.02,1.35,0.23],
										[0.75,0.04,0.77,0.18,0.29,-0.42],
										[0.71,0.54,0.07,0.19,-0.08,-0.7],
										[0.75,0.51,0.83,-0.03,0.75,-0.88],
										[0.54,0.69,-0.07,0.42,-0.12,-0.6],
										[-0.31,0.33,-0.05,0.11,-0.97,-1.08]])
		adjFactor[('T' ,6)] = np.array([[1.57,0.86,0.89,0.67,1.59,0.96],
										[1.0,0.3,0.66,-0.15,0.76,-1.72],
										[1.09,0.68,0.29,0.13,0.38,-1.08],
										[0.25,0.19,0.88,-0.36,-0.06,-0.97],
										[0.65,-0.04,0.17,0.63,-0.16,-1.32],
										[-0.69,-0.43,-1.06,0.19,-0.81,-1.25]])
		adjFactor[('T' ,7)] = np.array([[1.35,0.85,1.11,1.54,1.96,0.95],
										[0.75,-0.02,0.41,0.07,-0.25,-1.58],
										[0.94,0.66,0.04,0.46,-0.1,-2.78],
										[0.8,0.16,0.51,-0.46,0.06,-1.33],
										[0.69,1.21,-0.16,0.82,-0.27,-0.74],
										[-0.53,-0.66,-0.49,0.48,-1.03,-0.98]])
		adjFactor[('T' ,8)] = np.array([[1.83,0.95,1.61,1.41,-0.04,-0.08],
										[0.87,0.55,0.47,0.56,0.97,-1.65],
										[1.08,1,-0.05,0.1,0.88,-1.07],
										[0.78,0.55,1.08,-0.11,-1.19,0.07],
										[0.5,0.08,0.92,1.06,-0.08,-1.09],
										[-0.2,-1.62,-0.21,0.32,0.09,-0.84]])
		adjFactor[('PR',1)] = np.array([[0.0,0,0,0,0,0],
										[-4.39,0,0,0,0,0],
										[0.0,0,0,-1.12,0,0],
										[0.8,0,0,0,-0.31,0],
										[0.1,1.81,-1.93,-1.64,0,0],
										[1.58,1.45,2.48,-0.56,0.22,0]])
		adjFactor[('PR',2)] = np.array([[0.0,0,0,0,0,0],
										[-2.35,0,0,0,0,0],
										[-2.48,0,0,-0.79,0,0],
										[0.62,0,0,0,-0.34,0],
										[0.83,-1.62,-0.84,0,0,0],
										[1.5,1.26,1.88,-1.43,-0.32,-2.72]])
		adjFactor[('PR',3)] = np.array([[0.0,0,0,0,0,0],
										[-0.21,0,-1.64,0,0,0],
										[-3.91,0,0,0,-3.34,0],
										[0.8,0,-1.11,0,0,0],
										[0.09,-1.73,-2.1,0,-3.96,0],
										[1.32,1.29,1.71,-0.97,-0.68,-3.95]])
		adjFactor[('PR',4)] = np.array([[0.0,-0.53,0,0,0,0],
										[-2.13,0,0,0,0,0],
										[-0.36,0,0,0,-2.45,0],
										[1.0,0,-0.23,0,0,0],
										[0.6,0.19,-2.85,0,-4.01,0],
										[1.29,1.07,1.69,-0.19,-1.17,-3.91]])
		adjFactor[('PR',5)] = np.array([[0.0,0,0,0,0,0],
										[-0.1,0,0.33,0,0,0],
										[-0.97,0,-1.77,0,0,0],
										[0.97,-1.92,1.98,-1.25,0,0],
										[0.85,1.41,-0.28,0,0,0],
										[1.48,1.75,2.07,-0.19,-0.92,-5.38]])
		adjFactor[('PR',6)] = np.array([[0.0,0,0,0,0,0],
										[0.01,0,-0.71,0,0,0],
										[0.79,0,-2.49,0,-1.62,0],
										[1.5,-0.82,0,0,-0.4,0],
										[0.92,0,-1.71,0,0,0],
										[1.39,0.2,0.96,-0.61,0.84,-2.53]])
		adjFactor[('PR',7)] = np.array([[0.0,0,0,0,0.66,0],
										[0.16,0,-1.38,0,0,0],
										[-0.37,0,-1.13,0,0,0],
										[1.26,0,0,0,0,0],
										[0.24,0,0.9,0,-2.02,0],
										[1.44,0,1.58,0.77,-0.9,-3.33]])
		adjFactor[('PR',8)] = np.array([[0.0,0,0,0,0,0],
										[-0.01,0,0.47,0,0,0],
										[0.64,0,0,0,0,0],
										[1.82,0,-0.44,0,0,0],
										[0.17,0,0,0.07,0,0],
										[1.37,0,0,1.3,0,-2.76]])
		adjFactor[('KR',1)] = np.array([[0.0,0,0,0,0,0],
										[0.0,-2.29,0,0,0,0],
										[-1.83,0,0,0,0,-1.52],
										[0.13,0,-1.11,0,0,-2.43],
										[0.41,0,-0.68,-2.03,-4.36,-0.49],
										[1.93,1.99,2.33,1.26,1.6,-4.72]])
		adjFactor[('KR',2)] = np.array([[0.0,0,0,0,0,0.46],
										[0.84,0,0,0,0,0],
										[-0.2,0,0,0,-0.79,0],
										[0.24,0,-1.08,-1.95,0.79,-0.65],
										[0.54,-2.53,-1.74,1.36,-4.8,-1.28],
										[2.02,1.32,2.38,1.48,0.51,-2.3]])
		adjFactor[('KR',3)] = np.array([[0.0,0,-2.48,1.72,0,0],
										[-0.37,0,-2.45,-1.74,0,-2.9],
										[-1.82,0,-1.59,-1.84,-0.88,0],
										[0.23,0.13,0.54,-2.2,-2.07,-3.84],
										[0.85,1.05,-0.1,-2.13,-2.2,-1.13],
										[1.81,1.32,1.71,0.54,0.93,-2.61]])
		adjFactor[('KR',4)] = np.array([[0.0,0,0.9,0,0,2.28],
										[0.0,-0.87,-1.5,-1.77,-1.16,0],
										[-0.82,-0.56,-1.09,0.16,-0.87,-0.59],
										[0.88,-1.38,1.11,-0.34,-0.85,0],
										[0.8,0.66,0.32,0,-1.82,0],
										[1.66,0.88,2.24,0.75,0.25,-1.32]])
		adjFactor[('KR',5)] = np.array([[0.0,0,-0.47,-1.05,-1.55,0],
										[0.13,-0.55,0.91,-0.94,-0.08,0],
										[-0.2,-0.45,-0.44,-2.18,-0.87,0],
										[0.91,-1.3,0.46,-1.34,0.72,0],
										[0.83,1.87,0.64,-0.38,-1.53,-0.14],
										[1.68,1.26,1.14,1.19,0.47,-2.11]])
		adjFactor[('KR',6)] = np.array([[0.0,0,0,0,0,0],
										[0.8,-0.21,0,-1.18,0,0],
										[0.58,0,-3.04,0,-2.2,0],
										[0.41,-2.55,-0.5,0,-0.63,-2.29],
										[1.09,-2.97,-2.57,-2.22,-1.05,-2.45],
										[2.11,-0.82,-1.72,0.95,-0.09,-2.49]])
		adjFactor[('KR',7)] = np.array([[0.0,0,0,0,0,0],
										[-0.22,0,-0.02,-2.01,0,-0.02],
										[1.28,0,-4.07,0,0.12,0],
										[0.56,-0.27,-0.03,-2.93,0,0],
										[0.66,-0.75,-0.02,0.94,-1.67,-0.68],
										[1.74,0,0.84,1.76,1.16,-1]])
		adjFactor[('KR',8)] = np.array([[0.0,0,0,0,0,0],
										[0.91,0,-0.34,0,0,0],
										[-1.01,0,0,0.73,0.77,0],
										[-0.8,0,0,0,-0.39,0],
										[1.35,0,-0.86,-0.91,-2.28,0],
										[2.1,0,0,1.42,1.31,-2.01]])'''
		if adjFactor is not None:
			self._ASC += adjFactor
					
	'''def _makeaDecision(self, utility, maxUtility, nestDen, method=selectionMethod.eRouletteWheel):
		if method == selectionMethod.eRouletteWheel:
			stackedProb = 0
			randomNumber = random.random()
		elif method == selectionMethod.eMaximum:
			maxProb = 0
			maxResult = None
		for mode in self._intermModes:
			for interval in range(1, self._numberOfIntervals+1):
				if nestDen[mode] == 0:
					#self._logger.debug('zero denominator for mode %s' %mode)
					continue
				probability = np.power(utility[(mode, interval)], 1/self._nestCoef[mode]) / nestDen[mode] *\
								np.power(nestDen[mode], self._nestCoef[mode]) / maxUtility
				#self._logger.debug('Pr(%s, %i) = %f' %(mode, interval, probability))
				if method == selectionMethod.eRouletteWheel:
					stackedProb += probability
					if randomNumber < stackedProb:
						return (mode, interval)
				elif method == selectionMethod.eMaximum:
					if probability > maxProb:
						maxProb = probability
						maxResult = (mode, interval)
		if method == selectionMethod.eRouletteWheel:
			return (self._intermModes[-1], self._numberOfIntervals)
		elif method == selectionMethod.eMaximum:
			return maxResult
	'''	
	def _makeaDecision(self, utility, maxUtility, nestDen, method=selectionMethod.eRouletteWheel):
		probabilities = {}
		for mode in self._intermModes:
			for interval in range(1, self._numberOfIntervals+1):
				if nestDen[mode] == 0:
					#self._logger.debug('zero denominator for mode %s' %mode)
					continue
				probabilities[(mode,interval)] = np.power(utility[(mode, interval)], 1/self._nestCoef[mode]) / nestDen[mode] *\
								np.power(nestDen[mode], self._nestCoef[mode]) / maxUtility
				#self._logger.debug('Pr(%s, %i) = %f' %(mode, interval, probability))
		sortedProb = sorted(probabilities.items(), key=operator.itemgetter(1))
		if method == selectionMethod.eRouletteWheel:
			randomNumber = random.random()
			stackedProb = sortedProb[0][1]
			for i in range(len(sortedProb)):
				stackedProb += sortedProb[i][1]
				if randomNumber < stackedProb:
					return sortedProb[i][0]
			print(sortedProb)
			print(stackedProb)
			print(randomNumber)
			print(nestDen)
			print(utility)
		elif method == selectionMethod.eMaximum:
			return sortedProb[-1][0]
		else:
			self._logger.error('Invalid selection method %s' %str(method))
			return None

	def _evaluateCell(self, originEId, destinationEId, baseCaseMode):
		'''
		return -1, 0, or 1 to indicate if a new choice, none, or the base case choice, 
			respectively, should be to the demand
		OD matrices are composed of 4 quarters:
		1 (Toronto to Toronto)			|	2 (Toronto to outside Toronto)
		--------------------------------+-------------------------------------------
		3 (outside Toronto to Toronto)	|	4 (outside Toronto to outside Toronto)	
		Each quarter has its own "demandStructure" (defaulted to calculate both traffic and transit)
		'''
		if originEId <= self._numberOfCentroidsToronto and destinationEId <= self._numberOfCentroidsToronto:
			demandStructure = self._demandStructure1
		elif originEId <= self._numberOfCentroidsToronto and destinationEId > self._numberOfCentroidsToronto:
			demandStructure = self._demandStructure2
		elif originEId > self._numberOfCentroidsToronto and destinationEId <= self._numberOfCentroidsToronto:
			demandStructure = self._demandStructure3
		elif originEId > self._numberOfCentroidsToronto and destinationEId > self._numberOfCentroidsToronto:
			demandStructure = self._demandStructure4
			
		if baseCaseMode in ['D','P']:
			# base case mode: traffic
			if demandStructure % 10 == 0:
				return 0	# ignore (fill up with zeros)
			elif demandStructure % 10 == 1:
				return 1
			elif demandStructure % 10 == 2:
				return -1
			else:
				self._logger.error('Invalid demand structure code: %s' %str(demandStructure))
				return -1
		elif baseCaseMode in ['T','PR','KR']:
			# base case mode: transit
			if demandStructure / 10 == 0:
				return 0	# ignore (fill up with zeros)
			elif demandStructure / 10 == 1:
				return 1
			elif demandStructure / 10 == 2:
				return -1
			else:
				self._logger.error('Invalid demand structure code: %s' %str(demandStructure))
				return -1
		
	def apply(self, useExpansionFactor=True):
		# useExpansionFactor	=	1 (True)	:	calculate a decision for each individual and add each to the total demand
		#					=	0 (False)	:	calculate a decision for a single individual and add once to the total demand
		#					=	-1 			:	calculate a decision for a single individual (maximum utility) and add the <expansionFactor> to the total demand
		#					=	-2 			:	calculate a decision for a single individual (roulette wheel) and add the <expansionFactor> to the total demand
		self._logger.info('Start applying the nested logit model')
		random.seed(self._randomSeed)
		intermODMatrices = IntermODMatrices(self._iniFile)
		modes = {1:'D',2:'P',3:'T',4:'PR',5:'KR'}
		# connect to demand DB
		conn = sqlite3.connect(self._inputDB)
		cur = conn.cursor()
		# loop over all individuals in demand database
		# apply the DCM for each individual with fixed origin, destination, and expansion factor
		cur.execute('SELECT origin, destination, expansion_factor, basecase_interval, basecase_mode, '
			'fixed_utility_D, fixed_utility_P, fixed_utility_T, fixed_utility_PR, fixed_utility_KR, '
			'availability_D, availability_P, availability_T, availability_PR, availability_KR '
			'FROM demand')
		counter = 0
		for (originGTA06, destinationGTA06, expansionFactor, baseCaseInterval, baseCaseMode\
				, fixed_utility_D, fixed_utility_P, fixed_utility_T, fixed_utility_PR, fixed_utility_KR\
				, availability_D, availability_P, availability_T, availability_PR, availability_KR) in cur:
			# ignore (don't consider) intrazonal demand
			if originGTA06 == destinationGTA06:
				continue
			originEId = self._centroidIdToEidDict.GTA06ToEId(originGTA06)
			destinationEId = self._centroidIdToEidDict.GTA06ToEId(destinationGTA06)
			# skip, maintain base case choice, or calculate a new one based on the given demand structures
			# and origin-destination-baseCaseMode combination
			cellValue = self._evaluateCell(originEId, destinationEId, modes[baseCaseMode])
			if cellValue != -1:
				intermODMatrices[(modes[baseCaseMode],baseCaseInterval)][originEId-1][destinationEId-1] += expansionFactor*cellValue
				continue
			
			for index in range(len(self._regionsCentroids)):
				if originEId >= self._regionsCentroids[index][0] and originEId <= self._regionsCentroids[index][1]:
					originRegion = index
				if destinationEId >= self._regionsCentroids[index][0] and destinationEId <= self._regionsCentroids[index][1]:
					destinationRegion = index
			# get route LOS for between origin and destination 
			# time, distance, toll
			trafficLOS = self._getODTrafficLOS(originEId, destinationEId)
			# ivtt, fare, accT, egrT
			transitLOS = self._getODTransitLOS(originEId, destinationEId)
			'''for interval in range(1, self._numberOfIntervals+1):
				for mode in ['D', 'P']:
					trafficLOS[(mode, interval)] *= mulFactor.factors['traffic'] * mulFactor.temporalDist[interval-1]
				for mode in ['T', 'PR', 'KR']:
					transitLOS[(mode, interval)] *= mulFactor.factors['transit'] * mulFactor.temporalDist[interval-1]
			'''
			#self._logger.debug('OD: %i,%i' %(originEId, destinationEId))
			#self._logger.debug(trafficLOS)
			#self._logger.debug(transitLOS)
			# initialize empty utility and zero denominator
			utility = {}		# for each alternative, keys are (intermediateMode, interval) tuples
			nestDen = {'D':0, 'P':0, 'T':0, 'PR':0, 'KR':0}
			fixedUtility = {'D':fixed_utility_D, 'P':fixed_utility_P, 'T':fixed_utility_T, 
							'PR':fixed_utility_PR, 'KR':fixed_utility_KR}
			availability = {'D':availability_D, 'P':availability_P, 'T':availability_T, 
							'PR':availability_PR, 'KR':availability_KR}
			maxUtility = 0
			# calculate utility of each alternative
			# traffic modes nests
			for mode in ['D', 'P']:
				# individual alternatives
				for interval in range(1, self._numberOfIntervals+1):
					if availability[mode] == 0:
						# in case of unavailability of this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.debug('Mode %s is not available for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					elif  trafficLOS[(mode, interval)][0] == 0:
						# in case of no information about this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.error('Mode %s has no LOS for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					else:
						#self._logger.debug('ASC(%s, %i) = %f' %(mode, interval, ASC[(mode, interval)]))
						utility[(mode, interval)] = np.exp(fixedUtility[mode] + \
							self._ASC[(mode, interval)][originRegion][destinationRegion] + \
							self._param[(mode, interval)][0] * trafficLOS[(mode, interval)][0]+ \
							self._param[(mode, interval)][1] * trafficLOS[(mode, interval)][1] * self._fuelCostPer100km /100000 + \
							self._param[(mode, interval)][2] * trafficLOS[(mode, interval)][2] / (trafficLOS[(mode, interval)][1]/1000))
					nestDen[mode] += np.power(utility[(mode, interval)], 1/self._nestCoef[mode])
				maxUtility += np.power(nestDen[mode], self._nestCoef[mode])
			# transit modes nests
			for mode in ['T', 'PR', 'KR']:
				# individual alternatives
				for interval in range(1, self._numberOfIntervals+1):
					if availability[mode] == 0:
						# in case of unavailability of this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.debug('Mode %s is not available for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					elif  transitLOS[(mode, interval)][0] == 0:
						# in case of no information about this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.error('Mode %s has no LOS for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					else:
						utility[(mode, interval)] = np.exp(fixedUtility[mode] + \
							self._ASC[(mode, interval)][originRegion][destinationRegion] + \
							self._param[(mode, interval)][0] * transitLOS[(mode, interval)][0]+ \
							self._param[(mode, interval)][1] * transitLOS[(mode, interval)][1]+ \
							self._param[(mode, interval)][2] * transitLOS[(mode, interval)][2])
					nestDen[mode] += np.power(utility[(mode, interval)], 1/self._nestCoef[mode])
				maxUtility += np.power(nestDen[mode], self._nestCoef[mode])
			#self._logger.debug(utility)
			# making decisions for each individual having this fixed utility and OD & updating interm demand
			if useExpansionFactor == 1:
				for individualIndex in range(int(expansionFactor)):
					# Decision making based on calculated utilities and denominators
					(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
					# Update the corresponding OD matrices
					intermODMatrices[(mode,interval)][originEId-1][destinationEId-1] += 1
				# dealing with fractions in the expansion factor
				lastInd = expansionFactor - int(expansionFactor)
				if lastInd != 0:
					# Decision making based on calculated utilities and denominators
					(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
					# Update the corresponding OD matrices
					intermODMatrices[(mode,interval)][originEId-1][destinationEId-1] += lastInd
			elif useExpansionFactor == 0:
				# Don't use the expansion factor
				# Decision making based on calculated utilities and denominators
				(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
				# Update the corresponding OD matrices
				intermODMatrices[(mode,interval)][originEId-1][destinationEId-1] += 1
			elif useExpansionFactor == -1:
				# Use the expansion factor and the highest probability
				# Decision making based on calculated utilities and denominators
				(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen, method=selectionMethod.eMaximum)
				# Update the corresponding OD matrices
				intermODMatrices[(mode,interval)][originEId-1][destinationEId-1] += expansionFactor
			elif useExpansionFactor == -2:
				# Select a decision with the roulette wheel and multiply by the expansion factor
				# Decision making based on calculated utilities and denominators
				(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
				# Update the corresponding OD matrices
				intermODMatrices[(mode,interval)][originEId-1][destinationEId-1] += expansionFactor
			counter += 1
			if counter % 10000 == 0:
				self._logger.debug(counter)
				#break	# just for debugging a few records
		# close the connection to demand DB
		conn.close()
		self._logger.debug('printing AIMSUN LOS matrices after filling all the gaps with Google LOS')
		trafficLOSFull, transitLOSFull = self.getTravelLOS()
		for key in trafficLOSFull:
			self._logger.debug(trafficLOSFull[key].nonzeromean().str(np.mean))
		for key in transitLOSFull:
			self._logger.debug(transitLOSFull[key].nonzeromean().str(np.mean))
		return intermODMatrices

	def applyReturnDisaggregate(self, useExpansionFactor=True):
		self._logger.info('Start applying the nested logit model')
		disaggregateDecisions = []
		modes = {1:'D',2:'P',3:'T',4:'PR',5:'KR'}
		# connect to demand DB
		conn = sqlite3.connect(self._inputDB)
		cur = conn.cursor()
		# loop over all individuals in demand database
		# apply the DCM for each individual with fixed origin, destination, and expansion factor
		cur.execute('SELECT origin, destination, expansion_factor, basecase_interval, basecase_mode, '
			'fixed_utility_D, fixed_utility_P, fixed_utility_T, fixed_utility_PR, fixed_utility_KR, '
			'availability_D, availability_P, availability_T, availability_PR, availability_KR '
			'FROM demand')
		counter = 0
		for (originGTA06, destinationGTA06, expansionFactor, baseCaseInterval, baseCaseMode\
				, fixed_utility_D, fixed_utility_P, fixed_utility_T, fixed_utility_PR, fixed_utility_KR\
				, availability_D, availability_P, availability_T, availability_PR, availability_KR) in cur:
			# ignore (don't consider) intrazonal demand
			if originGTA06 == destinationGTA06:
				continue
			originEId = self._centroidIdToEidDict.GTA06ToEId(originGTA06)
			destinationEId = self._centroidIdToEidDict.GTA06ToEId(destinationGTA06)
			resultHeader = [originEId, destinationEId, modes[baseCaseMode], baseCaseInterval]
			# skip, maintain base case choice, or calculate a new one based on the given demand structures
			# and origin-destination-baseCaseMode combination
			cellValue = self._evaluateCell(originEId, destinationEId, modes[baseCaseMode])
			if cellValue == 0:
				continue
			elif cellValue == 1:
				result = resultHeader + [modes[baseCaseMode], baseCaseInterval, expansionFactor]
				disaggregateDecisions.append(result)
				continue
			
			for index in range(len(self._regionsCentroids)):
				if originEId >= self._regionsCentroids[index][0] and originEId <= self._regionsCentroids[index][1]:
					originRegion = index
				if destinationEId >= self._regionsCentroids[index][0] and destinationEId <= self._regionsCentroids[index][1]:
					destinationRegion = index
			# get route LOS for between origin and destination 
			# time, distance, toll
			trafficLOS = self._getODTrafficLOS(originEId, destinationEId)
			# ivtt, fare, accT, egrT
			transitLOS = self._getODTransitLOS(originEId, destinationEId)
			#self._logger.debug('OD: %i,%i' %(originEId, destinationEId))
			#self._logger.debug(trafficLOS)
			#self._logger.debug(transitLOS)
			# initialize empty utility and zero denominator
			utility = {}		# for each alternative, keys are (intermediateMode, interval) tuples
			nestDen = {'D':0, 'P':0, 'T':0, 'PR':0, 'KR':0}
			fixedUtility = {'D':fixed_utility_D, 'P':fixed_utility_P, 'T':fixed_utility_T, 
							'PR':fixed_utility_PR, 'KR':fixed_utility_KR}
			availability = {'D':availability_D, 'P':availability_P, 'T':availability_T, 
							'PR':availability_PR, 'KR':availability_KR}
			maxUtility = 0
			# calculate utility of each alternative
			# traffic modes nests
			for mode in ['D', 'P']:
				# individual alternatives
				for interval in range(1, self._numberOfIntervals+1):
					if availability[mode] == 0:
						# in case of unavailability of this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.debug('Mode %s is not available for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					elif  trafficLOS[(mode, interval)][0] == 0:
						# in case of no information about this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.error('Mode %s has no LOS for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					else:
						#self._logger.debug('ASC(%s, %i) = %f' %(mode, interval, ASC[(mode, interval)]))
						utility[(mode, interval)] = np.exp(fixedUtility[mode] + \
							self._ASC[(mode, interval)][originRegion][destinationRegion] + \
							self._param[(mode, interval)][0] * trafficLOS[(mode, interval)][0]+ \
							self._param[(mode, interval)][1] * trafficLOS[(mode, interval)][1] * self._fuelCostPer100km /100000 + \
							self._param[(mode, interval)][2] * trafficLOS[(mode, interval)][2] / (trafficLOS[(mode, interval)][1]/1000))
					nestDen[mode] += np.power(utility[(mode, interval)], 1/self._nestCoef[mode])
				maxUtility += np.power(nestDen[mode], self._nestCoef[mode])
			# transit modes nests
			for mode in ['T', 'PR', 'KR']:
				# individual alternatives
				for interval in range(1, self._numberOfIntervals+1):
					if availability[mode] == 0:
						# in case of unavailability of this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.debug('Mode %s is not available for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					elif  transitLOS[(mode, interval)][0] == 0:
						# in case of no information about this alternative
						# its probability should be zero
						utility[(mode, interval)] = 0
						#self._logger.error('Mode %s has no LOS for OD pair '
						#					'%i,%i' %(mode, originEId, destinationEId))
					else:
						utility[(mode, interval)] = np.exp(fixedUtility[mode] + \
							self._ASC[(mode, interval)][originRegion][destinationRegion] + \
							self._param[(mode, interval)][0] * transitLOS[(mode, interval)][0]+ \
							self._param[(mode, interval)][1] * transitLOS[(mode, interval)][1]+ \
							self._param[(mode, interval)][2] * transitLOS[(mode, interval)][2])
					nestDen[mode] += np.power(utility[(mode, interval)], 1/self._nestCoef[mode])
				maxUtility += np.power(nestDen[mode], self._nestCoef[mode])
			#self._logger.debug(utility)
			# making decisions for each individual having this fixed utility and OD & updating interm demand
			if useExpansionFactor:
				for individualIndex in range(int(expansionFactor)):
					# Decision making based on calculated utilities and denominators
					(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
					# Update the corresponding OD matrices
					result = resultHeader + [mode, interval, 1]
					disaggregateDecisions.append(result)
				# dealing with fractions in the expansion factor
				lastInd = expansionFactor - int(expansionFactor)
				if lastInd != 0:
					# Decision making based on calculated utilities and denominators
					(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
					# Update the corresponding OD matrices
					result = resultHeader + [mode, interval, lastInd]
					disaggregateDecisions.append(result)
			else:
				# Don't use the expansion factor
				# Decision making based on calculated utilities and denominators
				(mode, interval) = self._makeaDecision(utility, maxUtility, nestDen)
				# Update the corresponding OD matrices
				result = resultHeader + [mode, interval, 1]
				disaggregateDecisions.append(result)
			counter += 1
			if counter % 10000 == 0:
				self._logger.debug(counter)
				#break	# just for debugging a few records
		# close the connection to demand DB
		conn.close()
		return disaggregateDecisions
