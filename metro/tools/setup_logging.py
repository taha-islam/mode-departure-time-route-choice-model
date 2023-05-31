# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 08:25:40 2019

@author: islam
"""

import os
import logging
import logging.config
import yaml

def setup_logging(
	level,
	path=os.path.join(os.path.dirname(__file__), 'logging.yaml'),
):
	'''
	Setup logging configuration
	'''
	if os.path.exists(path):
		with open(path, 'rt') as f:
			config = yaml.safe_load(f.read())
		logging.config.dictConfig(config)
		if level is not None:
			logging.root.setLevel(getattr(logging, level))
	else:
		if level is None:
			logging.basicConfig(logging.INFO)
		else:
			logging.basicConfig(level=getattr(logging, level))
		
class LoggingErrorFilter(logging.Filter):
	def filter(self, record):
		return record.levelno == logging.ERROR
		
class LoggingWarningFilter(logging.Filter):
	def filter(self, record):
		return record.levelno == logging.WARNING
