# -*- coding: utf-8 -*-

import unittest
from metro.tools.progress_bar import printProgressBar as printProgressBar
import time

class TestDetectors(unittest.TestCase):
	
    def setUp(self):
        pass
        
    def test_detectors(self):
        # A List of Items
        items = list(range(0, 100))
        l = len(items)
        
        # Initial call to print 0% progress
        printProgressBar(0, l, prefix = 'Progress:', suffix = 'Complete', length = 50)
        for i, item in enumerate(items):
            # Do stuff...
            time.sleep(0.1)
            # Update Progress Bar
            printProgressBar(i + 1, l, prefix = 'Progress:', suffix = 'Complete', length = 50)
		
if __name__ == '__main__':
    unittest.main()