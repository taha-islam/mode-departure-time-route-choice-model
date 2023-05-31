# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 15:08:04 2020

@author: islam
"""

'''
TO RUN:
py -m unittest -v test.calibration.aimsun.test_sim_data
py -m unittest -v test.calibration.aimsun.test_sim_data.TestTolls.<testmethod>

"C:/Program Files/Aimsun/Aimsun Next 20/aconsole.exe" --script .\test\calibration\aimsun\test_base.py <test_num>
'''

from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *

import os
import sys
sys.path.append("..")
import metro3.metro.tools.site_packages
import argparse
import logging
import logging.config
from metro3.metro.aimsun.base import aimsunModel, aimsunModelType
from metro3.metro.tools import setup_logging


#from metro3.metro.trip_assignment.trip_assignment import tripAssignmentModel, simulationMode
#from trip_assignment.transit_fares import transitFares
#from trip_assignment.tolls import roadTolls

class TestBaseModel(object):

    def setUp(self):
        #self.iniFile = os.path.normpath(os.path.join(os.path.dirname(__file__),
        #                                 'test_network/network1/network1.ini'))
        self.iniFile = './test/aimsun/test_network/network1/network1.ini'
        self.id = 890
        # initialize an Aimsun model
        self.aimsun_model = aimsunModel(self.iniFile, self.id, aimsunModelType.eMicro)
        # load the network
        _, self.model = self.aimsun_model.loadNetwork()

    def test_setDatabase(self):
        self.aimsun_model.setDatabase("testDB1.sqlite")
        test_db1 = self.aimsun_model._getScenario().getDB(False).getDatabaseName(self.model)
        print(test_db1)
        self.aimsun_model.setDatabase("testDB2.sqlite")
        test_db2 = self.aimsun_model._getScenario().getDB(False).getDatabaseName(self.model)
        print(test_db2)
        assert test_db1 != test_db2
        self.aimsun_model.unloadNetwork()
        
    def test_setDemandDir(self):
        self.aimsun_model.setDemandDir("demand_dir1")
        test_dir1 = self.aimsun_model._getScenario().getDemand().getSchedule()[0].getTrafficDemandItem().getLocation()
        print(test_dir1)
        self.aimsun_model.setDemandDir("demand_dir2")
        test_dir2 = self.aimsun_model._getScenario().getDemand().getSchedule()[0].getTrafficDemandItem().getLocation()
        print(test_dir2)
        assert test_dir1 != test_dir2
        self.aimsun_model.unloadNetwork()
        
    def test_setExperimentVars(self):
        self.aimsun_model.setExperimentVars(key1='val1')
        assert self.aimsun_model._getExperiment().getVariables()['key1'] == 'val1'
        
    def test_retrieveOutput(self):
        self.aimsun_model.retrieveOutput()
        assert self.aimsun_model._outputsInMemory
		
if __name__ == '__main__':
    #unittest.main()
    argParser = argparse.ArgumentParser()
    argParser.add_argument('testNumber', type=int, choices=range(0, 5))
    argParser.add_argument('-l', "--log_level", type = str.upper,
                            choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'],
                            help="Set the logging level")
    args = argParser.parse_args()
    	
    setup_logging.setup_logging(args.log_level)
    # create logger
    logger = logging.getLogger(__name__)

    test_model = TestBaseModel()
    test_model.setUp()
    if args.testNumber in [0,4]:
        test_model.test_retrieveOutput()
    if args.testNumber in [0,1]:
        test_model.test_setDatabase()
    if args.testNumber in [0,2]:
        test_model.test_setDemandDir()
    if args.testNumber in [0,3]:
        test_model.test_setExperimentVars()
    print("Done...")
		