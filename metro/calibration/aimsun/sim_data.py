# -*- coding: utf-8 -*-
"""
Created on Fri May 29 12:42:42 2020

@author: islam
"""
import os
import sys
if __name__ == "__main__":
    package_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                "../../../.."))
    #package_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    #                                            "../../../.."))
    sys.path.append(package_path)

import metro3.metro.tools.site_packages
from metro3.metro.aimsun.base import aimsunModel, aimsunModelType
from metro3.metro.tools.setup_logging import setup_logging as setup_logging
from metro3.metro.aimsun.sim_outputs import simOutputs, objectIdsType
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyQt5.QtCore import *
from configparser import ConfigParser, ExtendedInterpolation
import argparse
import logging
import time
import sqlite3
import pandas as pd


class CalibrationDataModel(aimsunModel):
    ''' 
    A class for a microscopic Aimsun model to generate data required for 
    deep-learning-based calibration
    '''
    def __init__(self,
                 iniFile,
                 replicationId,
                 modelType,
                 console=None,
                 model=None):
        super(CalibrationDataModel, self).__init__(iniFile, replicationId,
                                                   modelType, console, model, 
                                                   calculateLOS=False, 
                                                   baseCaseModel=False)
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(iniFile)
        trafficAssignmentParam = parser['Traffic Assignment']
        self._noOfIter = int(trafficAssignmentParam['NUMBER_OF_ITERATIONS'])
        self._noOfThreads = int(trafficAssignmentParam['NUMBER_OF_THREADS'])
        self._logger = logging.getLogger(__name__)
		
    def run(self):
        '''
        This function runs the dynamic result whose id is self._id
        '''
        def print_sim_info():
            conn = sqlite3.connect(self._database)
            cur = conn.cursor()
            if self._type == aimsunModelType.eMicro:
                vOut, vIn, vWait = cur.execute('SELECT vOut, vIn, vWait '
                                               'FROM MISYS WHERE '
                                               'ent = 0 AND sid = 0 AND did = ?',
                                               (self._id,)).fetchone()
            if self._type == aimsunModelType.eMeso:
                vOut, vIn, vWait = cur.execute('SELECT vOut, vIn, vWait '
                                               'FROM MESYS WHERE '
                                               'ent = 0 AND sid = 0 AND did = ?',
                                               (self._id,)).fetchone()
            return vOut, vIn, vWait

        super(CalibrationDataModel, self).run()
        if self._model is not None:
            replication = self._model.getCatalog().find(self._id)
            if replication is None or not replication.isA("GKReplication"):
                self._console.getLog().addError("Cannot find replication")
                self._logger.error("Cannot find replication %i" % self._id)
                return -1
            else:
                self.removeDatabase()
                experiment = self._getExperiment()
                scenario = self._getScenario()
                # initialize the scenario's parameters
                scenario.getDemand().setFactor(str(self._demandMulFactor))
                # initialize the experiment's parameters
                #if experiment.getEngineMode() == GKExperiment.eIterative:
                #    experiment.setStoppingCriteriaIterations(self._noOfIter)
                #experiment.setNbThreadsPaths(self._noOfThreads)
                # run the simulation
                selection = []
                self._logger.debug('Starting simulation %i' % self._id)
                GKSystem.getSystem().executeAction("execute", replication,
                                                   selection,
                                                   time.strftime("%Y%m%d-%H%M%S"))
                self._outputsInMemory = scenario.getInputData().getKeepHistoryStat()
                # load the results
                #plugin.readResult(replication, False, False)
                self._logger.debug('Simulation (result) %i is completed' % self._id)
                vOut, vIn, vWait = print_sim_info()
                self._logger.debug('Number of vehicles reached their '
                                   'destination = %f\n'
                                   'Number of vehicles still in the network '
                                   '= %f\n'
                                   'Number of vehicles waiting to enter the '
                                   'network = %f' %(vOut, vIn, vWait))
            return 0
        else:
            self._logger.error('cannot load network')
            return -1

    def _setAttributes(self, object, attributes):
        # attributes --> {att : val}
        objType = object.getType()
        for key in attributes:
            att = objType.getColumn(key, GKType.eSearchOnlyThisType)
            object.setDataValue(att, QVariant(attributes[key]))

    def _getAttributes(self, object, attributes):
        # attributes --> [att]
        # result --> {att : val}
        result = {}
        objType = object.getType()
        for key in attributes:
            att = objType.getColumn(key, GKType.eSearchOnlyThisType)
            if object.getDataValue(att)[1]:
                result[key] = object.getDataValue(att)[0]
        return result

    def setParams(self,
                  simStep=None,
                  CFAggressivenessMean=None,
                  maxAccelMean=None,
                  normalDecelMean=None, # named in Aimsun as normalAccelMean
                  aggressiveness=None,
                  cooperation=None,
                  onRampMergingDistance=None,
                  distanceZone1=None,
                  distanceZone2=None,
                  clearance=None):
        # experiment's parameters
        experiment = self._getExperiment()
        self._setAttributes(experiment, {"GKExperiment::simStepAtt":simStep})
        # vehicle's parameters
        for vehicle in self._getTrafficDemand().getUsedVehicles():
            if CFAggressivenessMean is not None:
                self._setAttributes(vehicle, 
						{"GKVehicle::CFAggressivenessMean":CFAggressivenessMean,
						"GKVehicle::CFAggressivenessMin":CFAggressivenessMean,
						"GKVehicle::CFAggressivenessMax":CFAggressivenessMean,
						"GKVehicle::CFAggressivenessDev":0})
            if maxAccelMean is not None:
                self._setAttributes(vehicle, 
						{"GKVehicle::maxAccelMean":maxAccelMean,
						"GKVehicle::maxAccelMin":maxAccelMean,
						"GKVehicle::maxAccelMax":maxAccelMean,
						"GKVehicle::maxAccelDev":0})
            if normalDecelMean is not None:
                self._setAttributes(vehicle, 
						{"GKVehicle::normalAccelMean":normalDecelMean,
						"GKVehicle::normalAccelMin":normalDecelMean,
						"GKVehicle::normalAccelMax":normalDecelMean,
						"GKVehicle::normalAccelDev":0})
            if clearance is not None:
                self._setAttributes(vehicle, 
						{"GKVehicle::minDistMean":clearance,
						"GKVehicle::minDistMin":clearance,
						"GKVehicle::minDistMax":clearance,
						"GKVehicle::minDistDev":0})
        # road's parameters
        roadType = self._model.getType("GKRoadType")
        roadTypes = self._model.getCatalog( ).getObjectsByType(roadType)
        if roadTypes != None:
            for roadType in roadTypes.values():
                if aggressiveness is not None:
                    self._setAttributes(roadType, {"GKRoadType::aggressivenessAtt":aggressiveness})
                if cooperation is not None:
                    self._setAttributes(roadType, {"GKRoadType::cooperationAtt":cooperation})
                if onRampMergingDistance is not None:
                    self._setAttributes(roadType, {"GKRoadType::onRampMergingDistanceAtt":onRampMergingDistance})
                if distanceZone1 is not None:
                    self._setAttributes(roadType, {"GKRoadType::distanceZone1Att":distanceZone1})
                if distanceZone2 is not None:
                    self._setAttributes(roadType, {"GKRoadType::distanceZone2Att":distanceZone2})

    def getParams(self,
                  simStep=None,
                  CFAggressivenessMean=None,
                  maxAccelMean=None,
                  normalDecelMean=None, # named in Aimsun as normalAccelMean
                  aggressiveness=None,
                  cooperation=None,
                  onRampMergingDistance=None,
                  distanceZone1=None,
                  distanceZone2=None,
                  clearance=None):
        # experiment's parameters
        experiment = self._getExperiment()
        result = {}
        result.update(self._getAttributes(experiment,
                                          ["GKExperiment::simStepAtt"]))
        # vehicle's parameters
        for vehicle in self._getTrafficDemand().getUsedVehicles():
            result.update(self._getAttributes(vehicle,
                                          ["GKVehicle::CFAggressivenessMean",
                                           "GKVehicle::CFAggressivenessMin",
                                           "GKVehicle::CFAggressivenessMax",
                                           "GKVehicle::CFAggressivenessDev",
                                           "GKVehicle::maxAccelMean",
                                           "GKVehicle::maxAccelMin",
                                           "GKVehicle::maxAccelMax",
                                           "GKVehicle::maxAccelDev",
                                           "GKVehicle::normalAccelMean",
                                           "GKVehicle::normalAccelMin",
                                           "GKVehicle::normalAccelMax",
                                           "GKVehicle::normalAccelDev",
                                           "GKVehicle::minDistMean",
                                           "GKVehicle::minDistMin",
                                           "GKVehicle::minDistMax",
                                           "GKVehicle::minDistDev"]))
        # road's parameters
        roadType = self._model.getType("GKRoadType")
        roadTypes = self._model.getCatalog( ).getObjectsByType(roadType)
        if roadTypes != None:
            for roadType in roadTypes.values():
                result.update(self._getAttributes(roadType, 
                                      ["GKRoadType::aggressivenessAtt",
                                       "GKRoadType::cooperationAtt",
                                       "GKRoadType::onRampMergingDistanceAtt",
                                       "GKRoadType::distanceZone1Att",
                                       "GKRoadType::distanceZone2Att"]))
        return result

if __name__ == "__main__":
	argParser = argparse.ArgumentParser(description = 'Run a dynamic model to generate data for automatic calibration')
	argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
	argParser.add_argument('id', type=int,
							help='Aimsun replication Id')
	argParser.add_argument('datasetDir', help='Path to where the output dataset will be stored')
	argParser.add_argument('objectsFile', help='File of objects whose stats would be collected')
	argParser.add_argument('--index', type=int, default=None,
							help='Index of the first generated sample')
	argParser.add_argument('--simStep', type=float, default=None,
							help='Simulation step (reaction time)')
	argParser.add_argument('--CFAggressivenessMean', type=float, default=None,
							help="Mean of car-followinf vehicle's aggressiveness")
	argParser.add_argument('--maxAccelMean', type=float, default=None,
							help="Mean of vehicle's maximum acceleration")
	argParser.add_argument('--normalDecelMean', type=float, default=None,
							help="Mean of vehicle's normal deceleration")
	argParser.add_argument('--aggressiveness', type=float, default=None,
							help="Section's aggressiveness")
	argParser.add_argument('--cooperation', type=float, default=None,
							help="Section's cooperation")
	argParser.add_argument('--onRampMergingDistance', type=float, default=None,
							help="Section's side-lane's merging distance")
	argParser.add_argument('--distanceZone1', type=float, default=None,
							help="End of zone 1 in changing-lane model")
	argParser.add_argument('--distanceZone2', type=float, default=None,
							help="End of zone 2 in changing-lane model")
	argParser.add_argument('--clearance', type=float, default=None,
							help="Jam distance")
	argParser.add_argument('-l', "--log_level", type = str.upper,
						choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
						help="Set the logging level")
	args = argParser.parse_args()
	parser = ConfigParser(interpolation=ExtendedInterpolation())
	parser.read(args.iniFile)
	numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
	baseDir = parser['Paths']['BASE_DIR']
	setup_logging(args.log_level, path=os.path.join(baseDir, 'logging.yaml'))
	logger = logging.getLogger(__name__)
	logger.info(' '.join(sys.argv))
	
	# initialize an Aimsun model
	trafficModel = CalibrationDataModel(args.iniFile, args.id, aimsunModelType.eMicro)
	# read data of objects used to collect stats
	statObjects = pd.read_csv(args.objectsFile, index_col=False)
	statObjects.rename(columns = {statObjects.columns.values[0]:'id'})
	# load the network
	_, model = trafficModel.loadNetwork()
	# set calibration parameters
	trafficModel.setParams( args.simStep,
							args.CFAggressivenessMean,
							args.maxAccelMean,
							args.normalDecelMean,
							args.aggressiveness,
							args.cooperation,
							args.onRampMergingDistance,
							args.distanceZone1,
							args.distanceZone2,
							args.clearance)
	# run the simulation
	trafficModel.run()
	logger.debug('finish running')
	#trafficModel.retrieveOutput()
	# extract detectors' data
	outputs = simOutputs(args.iniFile, model, args.id)
	#outputs.setObjects("GKDetector", objectIdsType.eName, objList=[])
	outputs.setObjects("GKDetector", objectIdsType.eId, inputFileName = args.objectsFile)
	outputs.calculate(numberOfIntervals=numberOfIntervals)
	# save x & y of this sample
	logger.debug('Printing x')
	logger.debug(outputs.stats)
	logger.debug(statObjects)
	x = pd.merge(outputs.stats, statObjects, how='inner', on='id')
	x.to_csv(os.path.join(args.datasetDir, 'x'+str(args.index)+'.csv'), index=False)
    #x.to_pickle(file_name)
    #pd.read_pickle(file_name)
	y = pd.DataFrame( [ args.simStep,
						args.CFAggressivenessMean,
						args.maxAccelMean,
						args.normalDecelMean,
						args.aggressiveness,
						args.cooperation,
						args.onRampMergingDistance,
						args.distanceZone1,
						args.distanceZone2,
						args.clearance])
	y.to_csv(os.path.join(args.datasetDir, 'y'+str(args.index)+'.csv'), index=False, header=False)
	# unload the network
	trafficModel.unloadNetwork()
	#print(1)