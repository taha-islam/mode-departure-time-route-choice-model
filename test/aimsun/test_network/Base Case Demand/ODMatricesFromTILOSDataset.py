import sys
import time
import argparse
import logging
from configparser import ConfigParser, ExtendedInterpolation

sys.path.append("..")
from metro.dcm import nl
from metro.dcm.base import demandCalculationMethod
from metro.tools import demand, setup_logging

argParser = argparse.ArgumentParser(
	description = 'Validate and test the joint model of departure time and mode choice '
					'by applying it to the whole population usign GOOGLE LOS data'
					' and comparing the result demand with the base case demand')
argParser.add_argument('iniFile', help="Initialization file used to initialize most modules in METRO")
argParser.add_argument('-l', "--log_level", type = str.upper, 
					choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					help="Set the logging level")
args = argParser.parse_args()

setup_logging.setup_logging(args.log_level)
# create logger
logger = logging.getLogger(__name__)

parser = ConfigParser(interpolation=ExtendedInterpolation())
parser.read(args.iniFile)
skimMatricesDir = parser['Paths']['SKIM_MATRICES_DIR']
baseDemandDir = parser['Paths']['BASE_DEMAND_DIR']

start_time = time.time()
dcm = nl.nl(args.iniFile, useGoogleLos=True,
			demandStructure1=demandCalculationMethod.eMaintainTrafficMaintainTransit,
			demandStructure2=demandCalculationMethod.eMaintainTrafficMaintainTransit,
			demandStructure3=demandCalculationMethod.eMaintainTrafficMaintainTransit,
			demandStructure4=demandCalculationMethod.eMaintainTrafficMaintainTransit,)
dcmDemand = dcm.apply()
logger.info('--- NL calculations finished in %s seconds ---' % (time.time() - start_time))
dcmDemand.rename('NL Demand')
dcmDemandSum = dcmDemand.sum()
logger.info(dcmDemandSum)
logger.info(dcmDemandSum.sum())
dcmDemand.save('F:/PhD/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/Base Case Demand/')

demandCalculations = demand.demandEval(args.iniFile)
finalDemand = demandCalculations.calculateAimsunDemand(dcmDemand)
finalDemand.rename('AIMSUN Demand')
finalDemandSum = finalDemand.sum()
logger.info(finalDemandSum)
logger.info(finalDemandSum.sum())
finalDemand.save('F:/PhD/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/Base Case Demand/')
