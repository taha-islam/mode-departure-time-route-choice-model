# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 12:00:38 2020

@author: islam
"""
#py .\metro3\metro\calibration\aimsun\datasets_parallel.py . \QEW_20.ini 10299761 0 4 .\dataset5\ .\QEW_20_detectors5.csv -l debug -t 4
#py .\metro3\metro\calibration\aimsun\datasets_parallel.py .\metro3\metro\calibration\aimsun\networks\network1.ini 890 0 8 .\metro3\metro\calibration\aimsun\datasets\ .\metro3\metro\calibration\aimsun\networks\network1_detectors.csv -l debug -t 4
'''
py .\metro3\metro\calibration\aimsun\datasets_parallel.py .\metro3\metro\calibration\aimsun\networks\network1.ini 890 0 1000 .\metro3\metro\calibration\aimsun\datasets\ .\metro3\metro\calibration\aimsun\networks\network1_detectors.csv -l debug -t 4
'''
import os
import sys
if __name__ == "__main__":
    package_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                "../../../.."))
    #package_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    #                                            "../../../.."))
    sys.path.append(package_path)

from metro3.metro.tools.setup_logging import setup_logging as setup_logging
from metro3.metro.tools.progress_bar import printProgressBar as printProgressBar
import argparse
import logging
import os
import random
import numpy as np
from configparser import ConfigParser, ExtendedInterpolation
from shutil import copyfile
from multiprocessing.pool import ThreadPool
import subprocess
from collections import deque


# defining parameters ranges
simStepArray = np.arange(0.1, 1.6, 0.1)
CFAggressivenessMeanArray = np.arange(-1, 1.1, 0.1)
maxAccelMeanArray = np.arange(1, 4.1, 0.1)
normalDecelMeanArray = np.arange(1, 5.1, 0.1)
aggressivenessArray = np.arange(0, 101, 1)
cooperationArray = np.arange(0, 101, 1)
onRampMergingDistanceArray = np.arange(0, 301, 5)
distanceZone1Array = np.arange(200, 1001, 10)
distanceZone2Array = np.arange(100, 501, 10)
clearanceArray = np.arange(0.1, 2.1, 0.1)
paramEnabled = {'simStep': True,
				'CFAggressivenessMean': True,
				'maxAccelMean': True,
				'normalDecelMean': True,
				'aggressiveness': True,
				'cooperation': True,
				'onRampMergingDistance': False,
				'distanceZone1': False,
				'distanceZone2': False,
				'clearance':True}
temp_files = []
ini_files = None

def append_id(filename, id):
  return "{0}_{2}{1}".format(*os.path.splitext(filename) + (id,))

def sim_init(ini_file, no_threads):
    global temp_files
    global ini_files
    ini_files.append(ini_file)
    for i in range(1, no_threads):
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(ini_file)
        
        aimsun_file = parser['Paths']['ANGFile']
        aimsun_file_new = append_id(aimsun_file, i)
        copyfile(aimsun_file, aimsun_file_new)
        parser['Paths']['ANGFile'] = aimsun_file_new
        
        output_db = parser['Paths']['SQLITE_DB_OUTPUT_TRAFFIC']
        output_db_new = append_id(output_db, i)
        parser['Paths']['SQLITE_DB_OUTPUT_TRAFFIC'] = output_db_new
        
        ini_file_new = append_id(ini_file, i)
        ini_files.append(ini_file_new)
        with open(ini_file_new, 'w') as configfile:
            parser.write(configfile)
            
        temp_files += [aimsun_file_new, output_db_new, ini_file_new]
        
def sim_end():
    global temp_files
    for i in temp_files:
        try:
            os.remove(i)
        except OSError as e:
            print ("Error: %s - %s." % (e.filename, e.strerror))

def sim_run(cmd, index):
    global ini_files
    simStep = None
    CFAggressivenessMean = None
    maxAccelMean = None
    normalDecelMean = None
    aggressiveness = None
    cooperation = None
    onRampMergingDistance = None
    distanceZone1 = None
    distanceZone2 = None
    clearance = None
    
    cmd_ = cmd.copy()
    cmd_[5] = ini_files.pop()
    cmd_.append('--index')
    cmd_.append(str(index))
    if paramEnabled['simStep']:
        simStep = round(random.sample(list(simStepArray), 1)[0].item(), 2)
        cmd_.append('--simStep')
        cmd_.append(str(simStep))
    if paramEnabled['CFAggressivenessMean']:
        CFAggressivenessMean = round(random.sample(list(CFAggressivenessMeanArray), 1)[0].item(), 2)
        cmd_.append('--CFAggressivenessMean')
        cmd_.append(str(CFAggressivenessMean))
    if paramEnabled['maxAccelMean']:
        maxAccelMean = round(random.sample(list(maxAccelMeanArray), 1)[0].item(), 2)
        cmd_.append('--maxAccelMean')
        cmd_.append(str(maxAccelMean))
    if paramEnabled['normalDecelMean']:
        normalDecelMean = round(random.sample(list(normalDecelMeanArray), 1)[0].item(), 2)
        cmd_.append('--normalDecelMean')
        cmd_.append(str(normalDecelMean))
    if paramEnabled['aggressiveness']:
        aggressiveness = round(random.sample(list(aggressivenessArray), 1)[0].item(), 2)
        cmd_.append('--aggressiveness')
        cmd_.append(str(aggressiveness))
    if paramEnabled['cooperation']:
        cooperation = round(random.sample(list(cooperationArray), 1)[0].item(), 2)
        cmd_.append('--cooperation')
        cmd_.append(str(cooperation))
    if paramEnabled['onRampMergingDistance']:
        onRampMergingDistance = round(random.sample(list(onRampMergingDistanceArray), 1)[0].item(), 2)
        cmd_.append('--onRampMergingDistance')
        cmd_.append(str(onRampMergingDistance))
    if paramEnabled['distanceZone1']:
        distanceZone1 = round(random.sample(list(distanceZone1Array), 1)[0].item(), 2)
        cmd_.append('--distanceZone1')
        cmd_.append(str(distanceZone1))
    if paramEnabled['distanceZone2']:
        distanceZone2 = round(min(random.sample(list(distanceZone2Array), 1), distanceZone1), 2)
        cmd_.append('--distanceZone2')
        cmd_.append(str(distanceZone2))
    if paramEnabled['clearance']:
        clearance = round(random.sample(list(clearanceArray), 1)[0].item(), 2)
        cmd_.append('--clearance')
        cmd_.append(str(clearance))
    #logger.debug('Running command: %s' %' '.join(cmd_))
    #print('Running command: %s' %' '.join(cmd_))
    ps = subprocess.Popen(cmd_,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    stdout, stderr = ps.communicate()
    print(cmd_[5])
    #print(stdout)
    #ps.wait()
    ini_files.appendleft(cmd_[5])
    return 1
    '''if stdout[-1] == 1:
        return True
    else:
        return False'''

def main():
    '''
    Run simulation within AIMSUN running using original python.exe
    example:
    py -m metro3.metro.calibration.aimsun.datasets .\metro3\metro\calibration\aimsun\networks\network1.ini 890 0 5 .\metro3\metro\calibration\aimsun\datasets\ .\metro3\metro\calibration\aimsun\networks\network1_detectors.csv -l info
    '''
    global simStepArray, CFAggressivenessMeanArray, maxAccelMeanArray
    global normalDecelMeanArray, aggressivenessArray, cooperationArray
    global onRampMergingDistanceArray, distanceZone1Array, distanceZone2Array
    global clearanceArray, paramEnabled
    global ini_files
    argParser = argparse.ArgumentParser(description = 'Run DUE traffic assignment model')
    argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
    argParser.add_argument('id', type=int,
    						help='Aimsun replication Id')
    argParser.add_argument('index', type=int,
    						help='Index of the first generated sample')
    argParser.add_argument('datasetSize', type=int,
    						help='Size of the generated calibration dataset')
    argParser.add_argument('datasetDir', help='Path to where the output dataset will be stored')
    # 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv'
    argParser.add_argument('objectsFile', help='File of objects whose stats would be collected')
    argParser.add_argument('-l', "--log_level", type = str.upper,
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                           help="Set the logging level")
    argParser.add_argument('-t', "--threads", type = int, 
                           help="Number of threads (parallel simulations)")
    argParser.add_argument('-s', "--seed", type = float, default=-1,
                           help="Number of threads (parallel simulations)")
    args = argParser.parse_args()
    
    if args.seed != -1:
        print("setting the seed to %i" %args.seed)
        random.seed(args.seed)
    pool = ThreadPool(args.threads)
    ini_files = deque(maxlen=args.threads)
    sim_init(args.iniFile, args.threads)
    
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(args.iniFile)
    aimsunExe = os.path.join(parser['Paths']['AIMSUN_DIR'],'aconsole.exe')
    setup_logging(args.log_level)#, path=os.path.join(baseDir, 'logging.yaml'))
    logger = logging.getLogger(__name__)
    logger.info(' '.join(sys.argv))
    
    # print system info
    cmd = [aimsunExe, '-log_file', 'aimsun.log', '-script']
    cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),'../../tools/system_info.py')))
    logger.debug('Running command: %s' %' '.join(cmd))
    ps = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    logLevel = logging.getLevelName(logger.getEffectiveLevel())
    ps.wait()
    
    cmd = [aimsunExe, '-log_file', 'aimsun.log', '-script']
    cmd.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                             'sim_data.py')))
    cmd.append(args.iniFile)
    cmd.append(str(args.id))
    cmd.append(args.datasetDir)
    cmd.append(args.objectsFile)
    cmd.append('-l')
    cmd.append(logLevel)
    
    # run the tasks 
    result = pool.map(lambda idx: sim_run(cmd, idx),
                      range(args.index, args.datasetSize + args.index))
    '''printProgressBar(0, args.datasetSize, prefix = 'Progress:', 
                     suffix = 'Complete', length = 50)	
    for i, _ in enumerate(pool.map(lambda idx: sim_run(cmd, idx),
                                   range(args.index, args.datasetSize + args.index)),
                          1):
        printProgressBar(i, args.datasetSize, prefix = 'Progress:', 
                         suffix = 'Complete', length = 50)'''
    sim_end()
    print(result)

if __name__ == "__main__":
    sys.exit(main())
    '''
    # allow up to 5 concurrent threads
    pool = ThreadPool(5)
    
    parameters = [ 10, 20, 50]
    
    def parallel_test(thread_index):
        time.sleep(random.random() * 100)
        print(thread_index)
        return thread_index + 1
    
    # run the tasks 
    pool.map(lambda idx: parallel_test(idx), parameters)
    ini_file = './metro/calibration/aimsun/networks/network1.ini'
    prepare_parallel_sim(ini_file, 4)
    end_parallel_sim()'''