# -*- coding: utf-8 -*-
"""
Created on Wed May 13 09:28:19 2020

@author: islam
"""

import unittest
import pandas as pd
import matplotlib.pyplot as plt

import metro.tools.visualize as visualize


class TestTolls(unittest.TestCase):
	
    def setUp(self):
        pass
	
    def test_equate_df_keys(self):
        df1 = pd.DataFrame(data={'col1': [1, 2, 3, 5], 'col2': [3, 4, 5, 6]})
        df2 = pd.DataFrame(data={'col1': [4, 5, 2, 7], 'col2': [1, 2, 3, 4]})
        key = 'col1'
        df1_filtered, df2_filtered = visualize.equate_df_keys(df1, df2, key)
        keys1 = list(df1_filtered.groupby(key).groups.keys())
        keys2 = list(df2_filtered.groupby(key).groups.keys())
        self.assertCountEqual(keys1, 
                              keys2,
                              "Failed to equate dataframes")
        self.assertListEqual(keys1, 
                             keys2,
                             "Failed to equate dataframes")

    def test_read_data(self):
        pass

    '''def test_(self):
        intervals = range(5*4,22*4)
        detectors = ['QEWDE0010DES','QEWDE0020DES','QEWDE0030DES','QEWDE0040DES','QEWDE0050DES','QEWDE0060DES','QEWDE0070DES','QEWDE0090DES','QEWDE0100DES','QEWDE0110DES','QEWDE0120DES','QEWDE0130DES','QEWDE0140DES','QEWDE0150DES','QEWDE0170DES','QEWDE0180DES','QEWDE0190DES','QEWDE0200DES','QEWDE0210DES','QEWDE0220DES','QEWDE0230DES','QEWDE0240DES','QEWDE0250DES','QEWDE0260DES','QEWDE0270DES','QEWDE0280DES','QEWDE0290DES','QEWDE0300DES','QEWDE0310DES','QEWDE0340DES','QEWDE0350DES','QEWDE0360DES','QEWDE0370DES','QEWDE0380DES','QEWDE0390DES','QEWDE0400DES','QEWDE0410DES','QEWDE0420DES','QEWDE0430DES','QEWDE0440DES','QEWDE0450DES','QEWDE0460DES','QEWDE0470DES','QEWDE0480DES']
        df2019 = visualize.readData('C:\\Computer\\work\\detector_data\\observed_data_2019_3.csv',
                          detectors=detectors, intervals=intervals)
        df2020 = visualize.readData('C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv',
                          detectors=detectors, intervals=intervals)
        # find common detectors
        df2019_filtered, df2020_filtered = visualize.equate_df_keys(df2019, df2020, 'eid')
        #noIntervals = len(intervals)
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10,20), sharex=True) #, subplot_kw={'yticks': range(0,noIntervals,2)})
        img = visualize.heatmap(ax1, '2019', df2019_filtered, 'speed', limits=(0,120))
        #plt.colorbar(img)
        img = visualize.heatmap(ax2, '2020', df2020_filtered, 'speed', limits=(0,120))
        #plt.colorbar(img)
        plt.tight_layout(pad=3)
        #plt.tight_layout(rect=(0,0,0,3))
        fig.subplots_adjust(right=0.85)
        cbar_ax = fig.add_axes([0.9, 0.25, 0.03, 0.5])
        fig.colorbar(img, cax=cbar_ax)
        plt.show()
    '''    
    def test_compare_heatmaps(self):
        intervals = range(5*4,22*4)
        detectors = ['QEWDE0010DES','QEWDE0020DES','QEWDE0030DES','QEWDE0040DES','QEWDE0050DES','QEWDE0060DES','QEWDE0070DES','QEWDE0090DES','QEWDE0100DES','QEWDE0110DES','QEWDE0120DES','QEWDE0130DES','QEWDE0140DES','QEWDE0150DES','QEWDE0170DES','QEWDE0180DES','QEWDE0190DES','QEWDE0200DES','QEWDE0210DES','QEWDE0220DES','QEWDE0230DES','QEWDE0240DES','QEWDE0250DES','QEWDE0260DES','QEWDE0270DES','QEWDE0280DES','QEWDE0290DES','QEWDE0300DES','QEWDE0310DES','QEWDE0340DES','QEWDE0350DES','QEWDE0360DES','QEWDE0370DES','QEWDE0380DES','QEWDE0390DES','QEWDE0400DES','QEWDE0410DES','QEWDE0420DES','QEWDE0430DES','QEWDE0440DES','QEWDE0450DES','QEWDE0460DES','QEWDE0470DES','QEWDE0480DES']
        df2019 = visualize.readData('C:\\Computer\\work\\detector_data\\observed_data_2019_3.csv',
                          detectors=detectors, intervals=intervals)
        df2020 = visualize.readData('C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv',
                          detectors=detectors, intervals=intervals)
        # find common detectors
        df2019_filtered, df2020_filtered = visualize.equate_df_keys(df2019, df2020, 'eid')
        visualize.compare_heatmaps(['2019','2020'], [df2019_filtered, df2020_filtered], 'speed')

		
if __name__ == '__main__':
	unittest.main()