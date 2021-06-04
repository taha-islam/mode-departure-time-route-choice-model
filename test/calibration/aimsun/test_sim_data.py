# -*- coding: utf-8 -*-

'''
TO RUN:
py .\test\calibration\aimsun\test_sim_data.py 0
py -m unittest -v test.calibration.aimsun.test_sim_data
py -m unittest -v test.calibration.aimsun.test_sim_data.TestTolls.<testmethod>
'''            
            
import os
import sys
sys.path.append("..")
import metro3.metro.tools.site_packages
from metro3.metro.calibration.aimsun.sim_data import CalibrationDataModel
from metro3.metro.aimsun.sim_outputs import simOutputs, objectIdsType
from metro3.metro.aimsun.base import aimsunModelType
from metro3.metro.tools import setup_logging
from configparser import ConfigParser, ExtendedInterpolation
import argparse
import logging
import logging.config
import pandas as pd


#from metro3.metro.trip_assignment.trip_assignment import tripAssignmentModel, simulationMode
#from trip_assignment.transit_fares import transitFares
#from trip_assignment.tolls import roadTolls

class TestCalibrationDataModel(object):

    def setUp(self):
        self.iniFile = './test/aimsun/test_network/network1/network1.ini'
        self.objectsFile = './test/aimsun/test_network/network1/network1_detectors.csv'
        self.id = 890
        # initialize an Aimsun model
        self.aimsun_model = CalibrationDataModel(self.iniFile, self.id,
                                                 aimsunModelType.eMicro)
        # load the network
        _, self.model = self.aimsun_model.loadNetwork()
        
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(self.iniFile)
        self.numberOfIntervals = int(parser['Demand']['numberOfIntervals'])
        self.baseDir = parser['Paths']['BASE_DIR']

    def test_setParams(self):
        # set calibration parameters
        simStep = 1
        CFAggressivenessMean = 0
        maxAccelMean = 2
        normalDecelMean = 3
        aggressiveness = 50
        cooperation = 50
        onRampMergingDistance = 200
        distanceZone1 = 200
        distanceZone2 = 500
        clearance = 1
        self.aimsun_model.setParams(simStep,
                               CFAggressivenessMean,
                               maxAccelMean,
                               normalDecelMean,
                               aggressiveness,
                               cooperation,
                               onRampMergingDistance,
                               distanceZone1,
                               distanceZone2,
                               clearance)
        params1 = self.aimsun_model.getParams()
        params2 = self.aimsun_model.getParams()
        simStep += 1
        CFAggressivenessMean += 1
        maxAccelMean += 1
        normalDecelMean += 1
        aggressiveness += 1
        cooperation += 1
        onRampMergingDistance += 1
        distanceZone1 += 1
        distanceZone2 += 1
        clearance += 1
        self.aimsun_model.setParams(simStep,
                               CFAggressivenessMean,
                               maxAccelMean,
                               normalDecelMean,
                               aggressiveness,
                               cooperation,
                               onRampMergingDistance,
                               distanceZone1,
                               distanceZone2,
                               clearance)
        params3 = self.aimsun_model.getParams()
        assert params1 == params2
        assert params1 != params3
        # unload the network
        self.aimsun_model.unloadNetwork()
    
    def test_run(self):
        datasetDir = 'C:/Aimsun Projects/Departure-Time Travel-Mode and Route '\
                     'Choice Model/metro3/metro/calibration/aimsun/datasets'
        
        # read data of objects used to collect stats
        statObjects = pd.read_csv(self.objectsFile, index_col=False)
        statObjects.rename(columns = {statObjects.columns.values[0]:'id'})
        # run simulation and collect the resulting outputs
        simStep = 1
        CFAggressivenessMean = 0
        maxAccelMean = 2
        normalDecelMean = 3
        aggressiveness = 50
        cooperation = 50
        onRampMergingDistance = 200
        distanceZone1 = 200
        distanceZone2 = 500
        clearance = 1
        # set calibration parameters
        self.aimsun_model.setParams(simStep,
                               CFAggressivenessMean,
                               maxAccelMean,
                               normalDecelMean,
                               aggressiveness,
                               cooperation,
                               onRampMergingDistance,
                               distanceZone1,
                               distanceZone2,
                               clearance)
        # run the simulation
        self.aimsun_model.run()
        #trafficModel.retrieveOutput()
        # extract detectors' data
        outputs = simOutputs(self.iniFile, self.model, self.id)
        #outputs.setObjects("GKDetector", objectIdsType.eName, objList=[])
        outputs.setObjects("GKDetector", objectIdsType.eId, 
                           inputFileName = self.objectsFile)
        outputs.calculate(numberOfIntervals=self.numberOfIntervals)
        # save x & y of this sample
        x = pd.merge(outputs.stats, statObjects, how='inner', on='id')
        #x.to_csv(os.path.join(datasetDir, 'x.csv'), index=False)
        print('Printing x',x)
        y = pd.DataFrame([simStep,
                          CFAggressivenessMean,
                          maxAccelMean,
                          normalDecelMean,
                          aggressiveness,
                          cooperation,
                          onRampMergingDistance,
                          distanceZone1,
                          distanceZone2,
                          clearance])
        #y.to_csv(os.path.join(datasetDir, 'y.csv'), index=False, header=False)
        print('Printing y',y)
        # unload the network
        self.aimsun_model.unloadNetwork()
	
    def test_main(self):
        pass
        '''iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
        										'trip_assignment/meso.ini'))
        tripAssignment = tripAssignmentModel(iniFile, baseCaseModel=True)
        			
        los = tripAssignment.run(calculateLOS = True, mode = simulationMode.eDynamicTrafficAssignmentOnly)
        los.saveTrafficOnly(os.path.normpath(os.path.join(os.path.dirname(__file__),
        										'trip_assignment/traffic_los_meso')))
        '''
		
if __name__ == '__main__':
    #unittest.main()
    argParser = argparse.ArgumentParser()
    argParser.add_argument('testNumber', type=int, choices=range(0, 4))
    argParser.add_argument('-l', "--log_level", type = str.upper,
                            choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'],
                            help="Set the logging level")
    args = argParser.parse_args()
    	
    setup_logging.setup_logging(args.log_level)
    # create logger
    logger = logging.getLogger(__name__)

    test_model = TestCalibrationDataModel()
    test_model.setUp()
    if args.testNumber in [0,1]:
        test_model.test_setParams()
    if args.testNumber in [0,2]:
        test_model.test_run()
    if args.testNumber in [0,3]:
        test_model.test_main()
    print("Done...")
		