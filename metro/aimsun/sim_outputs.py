# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 12:31:31 2020

@author: islam
"""

import metro3.metro.tools.site_packages
import sys
import os
import csv
import logging
import pandas as pd
from configparser import ConfigParser, ExtendedInterpolation
from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *
from PyQt5.QtCore import *


class objectIdsType:
	eId = 0
	eExternalId = 1
	eName = 2
	
class simOutputs(object):
    '''
    
    '''
    def __init__(self, 
                 iniFile, 
                 simModel=None, 
                 replId=None):
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(iniFile)
        self._iniFile = iniFile
        self._simModel = simModel	# aimsunModel instance
        self._replId = replId
        self._objectIds = []
        self._objectIdsType = None
        self._logger = logging.getLogger(__name__)
		
    @property
    def simModel(self):
        return self._simModel
    		
    @simModel.setter
    def simModel(self, value):
        self._simModel = value
    
    @simModel.deleter
    def simModel(self):
        del self._simModel
    
    @property
    def replId(self):
        return self._replId
    
    @replId.setter
    def replId(self, value):
        self._replId = value
    
    @replId.deleter
    def replId(self):
        del self._replId

    def _getReplicationTS(self, statName, replId, vehicleId=0):
        output = []
        replication = model.getCatalog().find(replId)
        attName = 'DYNAMIC::GKExperimentResult_%s_%i_%i' % (statName, replId, vehicleId)
        replAtt = replication.getType().getColumn(attName, GKType.eSearchOnlyThisType)
        for i in range(0, replication.getDataValueTS(replAtt).size()):
            output.append(replication.getDataValueInTS(replAtt, GKTimeSerieIndex(i))[0])
        return output

    def _getDetectorTS(self, detector, statName, replId, vehicleId=0):
        output = []
        attName = 'DYNAMIC::GKDetector_%s_%i_%i' % (statName, replId, vehicleId)
        detAtt = self._objectsType.getColumn(attName, GKType.eSearchOnlyThisType)
        if detector.getDataValueTS(detAtt) is None:
            return None
        print(detector.getDataValueTS(detAtt).size())
        for i in range(0, detector.getDataValueTS(detAtt).size()):
            output.append(detector.getDataValueInTS(detAtt, GKTimeSerieIndex(i))[0])
        print(output)
        return output

    def _getDetectorFundDiag(self, detector, replId, vehicleId=0):
        speed = self._getDetectorTS(detector, 'speed', replId, vehicleId)
        flow = self._getDetectorTS(detector, 'flow', replId, vehicleId)
        density = self._getDetectorTS(detector, 'density', replId, vehicleId)
        nbOfLanes = detector.getToLane() - detector.getFromLane() + 1
        flowPerLane = [x / nbOfLanes for x in flow]
        densityPerLane = [x / nbOfLanes for x in density]
        return zip(speed, flow, density, flowPerLane, densityPerLane)

    def _getDetectorStat(self, replId, detector, statName, interval, vehicleId=0):
        attName = 'DYNAMIC::GKDetector_%s_%i_%i' % (statName, replId, vehicleId)
        detAtt = self._objectsType.getColumn(attName, GKType.eSearchOnlyThisType)
        if detector.getDataValueTS(detAtt) is None:
            return None
        return detector.getDataValueInTS(detAtt, GKTimeSerieIndex(interval))[0]

    def _getDetectorNoOfLanes(self, detector):
        return detector.getToLane() - detector.getFromLane() + 1

    def setObjects(self, objType, idType, objList=None, inputFileName=None):
        # set objects/detectors Ids to objList or import it from inputFileName
        #detectors = ['QEWDE0020DES','QEWDE0030DES','QEWDE0040DES','QEWDE0050DES','QEWDE0060DES','QEWDE0080DES','QEWDE0090DES','QEWDE0100DES','QEWDE0110DES','QEWDE0120DES','QEWDE0140DES','QEWDE0150DES','QEWDE0180DES','QEWDE0190DES','QEWDE0200DES','QEWDE0210DES','QEWDE0220DES','QEWDE0230DES','QEWDE0240DES','QEWDE0250DES','QEWDE0260DES','QEWDE0270DES','QEWDE0280DES','QEWDE0290DES','QEWDE0330DES','QEWDE0340DES','QEWDE0370DES','QEWDE0380DES','QEWDE0390DES','QEWDE0400DES','QEWDE0410DES','QEWDE0430DES','QEWDE0440DES','QEWDE0450DES','QEWDE0460DES','QEWDE0470DES','QEWDE0480DES','QEWDE0490DES','QEWDE0510DES','QEWDE0520DES','QEWDE0530DES','QEWDE0540DES','QEWDE0550DES']
        self._objectsTypeName = objType
        self._objectIdsType = idType
        # set from list
        if objList is not None:
            self._objectIds = objList
            return
        # read from external file
        #inputFileName = 'C:/Aimsun Projects/CATTS/Calibration Final Results/list_detectors.csv'
        with open(inputFileName, 'r') as fin:
            reader = csv.reader(fin)
            next(reader)	# skip header
            objectIdPrev = None
            for row in reader:
                objectId = row[0]
                if objectId != objectIdPrev:
                    self._objectIds.append(objectId)
        # TO DO: Check the casting to int
        if self._objectIdsType == objectIdsType.eId:
            self._objectIds = map(int, self._objectIds)

    def calculate(self, numberOfIntervals=0):
        # calculate the stats
        assert self._simModel is not None
        assert self._replId is not None
		
        self._objectsType = self._simModel.getType(self._objectsTypeName)
		
        self.stats = pd.DataFrame(columns=['id', 'interval', 'number_of_lanes',
                                           'speed','flow','density',
                                           'flow_per_lane','density_per_lane'])
        i = 0
        for id in self._objectIds:
            if self._objectIdsType == objectIdsType.eId:
                object = self._simModel.getCatalog().find(id)
            elif self._objectIdsType == objectIdsType.eExternalId:
                object = self._simModel.getCatalog().findObjectByExternalId(id,
                                self._simModel.getType(self._objectsTypeName))
            elif self._objectIdsType == objectIdsType.eName:
                object = self._simModel.getCatalog().findByName(id, 
                                self._simModel.getType(self._objectsTypeName))
            else:
                self._logger.warning("Invalid object Id type: cannot collect "
                                     "statistics for Id type {}".format(
                                         self._objectIdsType))
                return
            for interval in range(numberOfIntervals):
                flow = self._getDetectorStat(self._replId, object, 'flow', 
                                             interval, vehicleId=0)
                speed = self._getDetectorStat(self._replId, object, 'speed', 
                                              interval, vehicleId=0)
                density = self._getDetectorStat(self._replId, object, 'density', 
                                                interval, vehicleId=0)
                self.stats.loc[i] = [id, interval, 
                                     self._getDetectorNoOfLanes(object), 
                                     speed, flow, density,
                                     (flow / self._getDetectorNoOfLanes(object)), 
                                     (density / self._getDetectorNoOfLanes(object))]
                i += 1
	
    def save(self, outputFileName):
        # export stats
        #outputFileName = 'C:/Aimsun Projects/CATTS/Calibration Final Results/repl%i_detectors.csv' % replId
        self.stats.to_csv(outputFileName, index=False)

'''
	def average(lst):
		return reduce(lambda a,b:a+b, lst) / len(lst)
	workingDir = 'C:/Aimsun Projects/CATTS'
	replicationFileName = os.path.join(workingDir, 'replication_stats_%i.csv' % replId)
	with open(replicationFileName, 'wb') as fp:
		writer = csv.writer(fp, delimiter=',')
		statNames = ['delayTime','totalTravelTime','vehiclesOut','flow','speed','density']
		writer.writerow([statNames[0], str(average(self._getReplicationTS(statNames[0], replId)))])
		writer.writerow([statNames[1], str(sum(self._getReplicationTS(statNames[1], replId)))])
		writer.writerow([statNames[2], str(sum(self._getReplicationTS(statNames[2], replId)))])
		writer.writerow([statNames[3], str(average(self._getReplicationTS(statNames[3], replId)))])
		writer.writerow([statNames[4], str(average(self._getReplicationTS(statNames[4], replId)))])
		writer.writerow([statNames[5], str(average(self._getReplicationTS(statNames[5], replId)))])
'''
