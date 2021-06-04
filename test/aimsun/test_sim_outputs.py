# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 12:38:05 2020

@author: islam
"""

# -*- coding: utf-8 -*-

'''
TO RUN:
"C:/Program Files/Aimsun/Aimsun Next 20/aconsole.exe" --script .\test\calibration\aimsun\test_sim_data.py <test_num>
'''            
            
import os
import sys
sys.path.append("..")
import metro3.metro.tools.site_packages
from metro3.metro.aimsun.sim_outputs import simOutputs, objectIdsType
from metro3.metro.aimsun.base import aimsunModel, aimsunModelType
from metro3.metro.aimsun.traffic_assignment import DUEModel
from configparser import ConfigParser, ExtendedInterpolation
import argparse
import logging
import logging.config


#from metro3.metro.trip_assignment.trip_assignment import tripAssignmentModel, simulationMode
#from trip_assignment.transit_fares import transitFares
#from trip_assignment.tolls import roadTolls

class TestSimOutputs(object):

    def setUp(self):
        self.iniFile = './test/aimsun/test_network/network1/network1.ini'
        self.id = 890
        # initialize an Aimsun model
        self.aimsun_model = DUEModel(self.iniFile, self.id)
        # load the network
        _, self.model = self.aimsun_model.loadNetwork()
        
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(self.iniFile)
        self.numberOfIntervals = int(parser['Demand']['numberOfIntervals'])

    def test_detOutputs(self):
        self.objectsFile = './test/aimsun/test_network/network1/network1_detectors.csv'
        # extract detectors' data
        self.aimsun_model.run()
        self.aimsun_model.retrieveOutput()
        outputs = simOutputs(self.iniFile, self.model, self.id)
        outputs.setObjects("GKDetector", objectIdsType.eId, inputFileName = self.objectsFile)
        outputs.calculate(numberOfIntervals=self.numberOfIntervals)
        # save x & y of this sample
        print('Printing simulation outputs')
        print(outputs.stats)
		
if __name__ == '__main__':
    #unittest.main()
    print("Starting...")
    outputs = TestSimOutputs()
    outputs.setUp()
    outputs.test_detOutputs()
    print("Done...")
		