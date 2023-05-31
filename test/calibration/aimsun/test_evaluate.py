# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 16:11:47 2020

@author: islam
"""

'''
TO RUN:
py .\test\calibration\aimsun\test_evaluate.py 0
py -m metro3.test.calibration.aimsun.test_evaluate 0
'''
import unittest
import os
import numpy as np
import pandas as pd
import argparse
import logging
import logging.config
import sys
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                              '../../../../')))
from metro3.metro.tools import setup_logging
#from configparser import ConfigParser, ExtendedInterpolation

from metro3.metro.calibration.aimsun.evaluate import evaluate, geh, rmse


class TestEvaluate(unittest.TestCase):
	
    def setUp(self):
        self.iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                     '../../aimsun/test_network/network1/network1.ini'))
        self.id = 890
        self.datasetDir = os.path.normpath(os.path.dirname(__file__))
        self.objectsFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                         '../../aimsun/test_network/network1/network1_detectors.csv'))
        observed_data = pd.read_csv(os.path.join(os.path.dirname(__file__),
                                                 '../../aimsun/test_network/network1/x0.csv'))
        self.obs_flow = observed_data.flow_per_lane.to_numpy()
        self.obs_speed = observed_data.speed.to_numpy()
        self.sim_params = pd.read_csv(os.path.join(os.path.dirname(__file__),
                                                   '../../aimsun/test_network/network1/y0.csv'),
                                      header=None)[0].to_numpy()
	
    def test_geh(self):
        pred = np.array([10000,40000])
        target = np.array([10500,41000])
        self.assertEqual(geh(pred, pred), 0)
        self.assertEqual(np.round(geh(pred, target), 2), 4.95)
        
    def test_rmse(self):
        pred = np.array([34, 37, 44, 47, 48, 48, 46, 43, 32, 27, 26, 24])
        target = np.array([37, 40, 46, 44, 46, 50, 45, 44, 34, 30, 22, 23])
        self.assertEqual(rmse(pred, pred), 0)
        self.assertEqual(np.round(rmse(pred, target), 2), 2.43)
    
    def test_evaluate(self):
        sim_error = evaluate(self.obs_flow, self.obs_speed,
                             iniFile=self.iniFile,
                             id=self.id,
                             index=0,
                             datasetDir=self.datasetDir,
                             objectsFile=self.objectsFile,
                             w_flow=0.5,
                             w_speed=0.5,
                             simStep = self.sim_params[0],
                             CFAggressivenessMean = self.sim_params[1],
                             maxAccelMean = self.sim_params[2],
                             normalDecelMean = self.sim_params[3],
                             aggressiveness = self.sim_params[4],
                             cooperation = self.sim_params[5],
                             onRampMergingDistance = self.sim_params[6],
                             distanceZone1 = self.sim_params[7],
                             distanceZone2 = self.sim_params[8],
                             clearance = self.sim_params[9])
        self.assertEqual(sim_error, 0.0)
        
        sim_error = evaluate(self.obs_flow, self.obs_speed,
                             iniFile=self.iniFile,
                             id=self.id,
                             index=0,
                             datasetDir=self.datasetDir,
                             objectsFile=self.objectsFile,
                             w_flow=0.5,
                             w_speed=0.5,
                             simStep = self.sim_params[0]*1.1,
                             CFAggressivenessMean = self.sim_params[1]*1.1,
                             maxAccelMean = self.sim_params[2]*1.1,
                             normalDecelMean = self.sim_params[3]*1.1,
                             aggressiveness = self.sim_params[4]*1.1,
                             cooperation = self.sim_params[5]*1.1,
                             onRampMergingDistance = self.sim_params[6]*1.1,
                             distanceZone1 = self.sim_params[7]*1.1,
                             distanceZone2 = self.sim_params[8]*1.1,
                             clearance = self.sim_params[9]*1.1)
        self.assertNotEqual(sim_error, 0.0)
        
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

    test_model = TestEvaluate()
    test_model.setUp()
    if args.testNumber in [0,1]:
        test_model.test_geh()
    if args.testNumber in [0,2]:
        test_model.test_rmse()
    if args.testNumber in [0,3]:
        test_model.test_evaluate()
    print("Done...")