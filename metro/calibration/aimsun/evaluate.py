# -*- coding: utf-8 -*-
"""
Created on Fri May 29 13:01:18 2020

@author: islam
"""

#import metro3.metro.tools.site_packages
import os
from configparser import ConfigParser, ExtendedInterpolation
import subprocess
import numpy as np
import pandas as pd
import logging
logger = logging.getLogger(__name__)

def read_sim_data(data_file):
    df = pd.read_csv(data_file)
    return df.flow_per_lane.to_numpy(), df.speed.to_numpy()

def geh(predictions, targets):
    return np.sqrt((2 * (predictions - targets) ** 2) / (predictions + targets)).mean()

def rmse(predictions, targets):
    return np.sqrt(((predictions - targets) ** 2).mean())

def evaluate(obs_flow, obs_speed,
             ini_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/generate_calibration_data.ini',
             id = 890,
             index = 0,
             dataset_dir = os.path.normpath(os.path.dirname(__file__)),
             objects_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv',
             w_flow=0.5,
             w_speed=0.5,
             simStep = None,
             CFAggressivenessMean = None,
             maxAccelMean = None,
             normalDecelMean = None,
             aggressiveness = None,
             cooperation = None,
             onRampMergingDistance = None,
             distanceZone1 = None,
             distanceZone2 = None,
             clearance = None):
    '''
    Run the simulation with the given parameters and compare simulated flows 
    and speeds against their observed counterparts.

    Parameters
    ----------
    obs_flow : numpy.ndarray
        Observed flow
    obs_speed : numpy.ndarray
        Observed speed
    w_flow : Int, optional
        The weight of flows in the weighted-sum evaluation function. The 
        default is 0.5.
    w_speed : Int, optional
        The weight of flows in the weighted-sum evaluation function. The 
        default is 0.5.
    simStep : Double, optional
        Simulation step. The default is None.
    CFAggressivenessMean : Double, optional
        DESCRIPTION. The default is None.
    maxAccelMean : TYPE, optional
        DESCRIPTION. The default is None.
    normalDecelMean : TYPE, optional
        DESCRIPTION. The default is None.
    aggressiveness : TYPE, optional
        DESCRIPTION. The default is None.
    cooperation : TYPE, optional
        DESCRIPTION. The default is None.
    onRampMergingDistance : TYPE, optional
        DESCRIPTION. The default is None.
    distanceZone1 : TYPE, optional
        DESCRIPTION. The default is None.
    distanceZone2 : TYPE, optional
        DESCRIPTION. The default is None.
    clearance : TYPE, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    global logger
    
	
    #ini_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/generate_calibration_data.ini'
    #id = 890
    #index = 0
    #dataset_dir = os.path.normpath(os.path.dirname(__file__))
    #'C:/Aimsun Projects/Calibration Using Neural Networks/dataset/'
    #objects_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv'
	
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(ini_file)
    aimsunExe = os.path.join(parser['Paths']['AIMSUN_DIR'],'aconsole.exe')
	
    cmd = [aimsunExe, '-log_file', 'aimsun.log', '-script']
    cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                             'sim_data.py')))
    cmd.append(ini_file)
    cmd.append(str(id))
    cmd.append(dataset_dir)
    cmd.append(objects_file)
    cmd.append('--index')
    cmd.append(str(index))
    cmd.append('-l')
    cmd.append('info')
    if simStep is not None and not np.isnan(simStep):
        cmd.append('--simStep')
        cmd.append(str(simStep))
    if CFAggressivenessMean is not None and not np.isnan(CFAggressivenessMean):
        cmd.append('--CFAggressivenessMean')
        cmd.append(str(CFAggressivenessMean))
    if maxAccelMean is not None and not np.isnan(maxAccelMean):
        cmd.append('--maxAccelMean')
        cmd.append(str(maxAccelMean))
    if normalDecelMean is not None and not np.isnan(normalDecelMean):
        cmd.append('--normalDecelMean')
        cmd.append(str(normalDecelMean))
    if aggressiveness is not None and not np.isnan(aggressiveness):
        cmd.append('--aggressiveness')
        cmd.append(str(aggressiveness))
    if cooperation is not None and not np.isnan(cooperation):
        cmd.append('--cooperation')
        cmd.append(str(cooperation))
    if onRampMergingDistance is not None and not np.isnan(onRampMergingDistance):
        cmd.append('--onRampMergingDistance')
        cmd.append(str(onRampMergingDistance))
    if distanceZone1 is not None and not np.isnan(distanceZone1):
        cmd.append('--distanceZone1')
        cmd.append(str(distanceZone1))
    if distanceZone2 is not None and not np.isnan(distanceZone2):
        cmd.append('--distanceZone2')
        cmd.append(str(distanceZone2))
    if clearance is not None and not np.isnan(clearance):
        cmd.append('--clearance')
        cmd.append(str(clearance))
    logger.debug('Running command: %s' %' '.join(cmd))
    ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    stdout, stderr = ps.communicate()
    
    sim_flow, sim_speed = read_sim_data(os.path.join(dataset_dir,
                                                     'x'+str(index)+'.csv'))
    GEH = geh(sim_flow, obs_flow) # flow/lane
    speed_rms = rmse(sim_speed, obs_speed) # speed
    
    return (w_flow * GEH + w_speed * speed_rms) / ( w_flow * w_speed)
	