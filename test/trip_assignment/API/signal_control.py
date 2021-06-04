from AAPI import *

def AAPILoad(): 
	return 0

def AAPIInit(): 
	return 0

def AAPIManage(time, timeSta, timeTrans, acycle):   
	return 0

def AAPIPostManage(time, timeSta, timeTrans, acycle):
	global previousPhaseIndex
	global previousPhaseTime

	busPhase = 5
	intersection = 2062
	busCallDetector = 2700
	busExitDetector = 2699
	busTypeId = 58
	#get bus internal position
	busVehiclePosition = AKIVehGetVehTypeInternalPosition( 58 )
	currentPhase = ECIGetCurrentPhase( intersection )
	
	#check bus presence over busCallDetector 
	if AKIDetGetCounterCyclebyId( busCallDetector, busVehiclePosition ) > 0 and \
		currentPhase != busPhase and \
		previousPhaseIndex == -1:
		print "bus detected"                    
		#change the control to bus phase
		previousPhaseIndex = currentPhase
		previousPhaseTime  = time - ECIGetStartingTimePhase( intersection )
		ECIChangeDirectPhase( intersection, busPhase, timeSta, time, acycle, 0 )
		
	#check bus presence over busExitDetector
	if AKIDetGetCounterCyclebyId( busExitDetector, busVehiclePosition ) > 0:        
		#go back to previous phase
		if previousPhaseIndex > 0:
			print "go back to previous state"				   
			ECIChangeDirectPhase( intersection, previousPhaseIndex, timeSta, time, acycle,  previousPhaseTime)
			previousPhaseIndex = -1
			previousPhaseTime = -1  
        
    
	return 0

def AAPIFinish():   
	return 0

def AAPIUnLoad():   
	return 0

previousPhaseIndex = -1
previousPhaseTime = -1   