# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 17:04:39 2020

@author: islam
"""

import sys
import os
executableName = os.path.basename(sys.executable)
print(executableName)
if executableName == 'aconsole.exe':
	print('Running using aconsole.exe')
	mode = 0
elif executableName == 'python.exe':
	print('Running using python.exe')
	mode = 1
else:
	print('Unrecognizable executable %s' %executableName)
	mode = -1
