# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 14:15:51 2020

@author: islam
"""

'''
py .\metro3\test\calibration\aimsun\test_datasets.py
'''
import sys
import os
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                              '../../../../')))
from metro3.metro.tools import setup_logging
#import metro3.metro.calibration.aimsun.datasets as ds
import argparse
import time


if __name__=='__main__':
    '''parser = argparse.ArgumentParser(description='something')
    parser.add_argument('--my_env', help='my environment')
    args,rest = parser.parse_known_args()
    rest_arg = ['datasets_parallel.py']
    rest_arg.extend(rest)'''
    import metro3.metro.calibration.aimsun.datasets_parallel as ds_pl
    
    t1 = time.time()
    sys.argv = ['datasets_parallel.py', 
                '.\\metro3\\metro\\calibration\\aimsun\\networks\\network1.ini', 
                '890', '10', '4', 
                '.\\metro3\\metro\\calibration\\aimsun\\datasets\\', 
                '.\\metro3\\metro\\calibration\\aimsun\\networks\\network1_detectors.csv', 
                '-l', 'debug', '-t', '4', '-s', '10']
    #sys.argv = rest_arg
    #print(sys.argv)
    ds_pl.main()
    t2 = time.time()
    
    sys.argv = ['datasets_parallel.py', 
                '.\\metro3\\metro\\calibration\\aimsun\\networks\\network1.ini', 
                '890', '30', '4', 
                '.\\metro3\\metro\\calibration\\aimsun\\datasets\\', 
                '.\\metro3\\metro\\calibration\\aimsun\\networks\\network1_detectors.csv', 
                '-l', 'debug', '-t', '4', '-s', '10']
    #sys.argv = rest_arg
    #print(sys.argv)
    ds_pl.main()
    t3 = time.time()
    print(t2-t1)
    print(t3-t2)