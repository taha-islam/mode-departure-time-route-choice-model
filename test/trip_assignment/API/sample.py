from AAPI import *

def AAPILoad():
	AKIPrintString( "AAPILoad" )
	return 0

def AAPIInit():
	AKIPrintString( "AAPIInit" )
	return 0

def AAPIManage(time, timeSta, timeTrans, acycle):
	AKIPrintString( "AAPIManage" )
	return 0

def AAPIPostManage(time, timeSta, timeTrans, acycle):
	AKIPrintString( "AAPIPostManage" )
	return 0

def AAPIFinish():
	AKIPrintString( "AAPIFinish" )
	return 0

def AAPIUnLoad():
	AKIPrintString( "AAPIUnLoad" )
	return 0
	
def AAPIPreRouteChoiceCalculation(time, timeSta):
	AKIPrintString( "AAPIPreRouteChoiceCalculation" )
	return 0

def AAPIEnterVehicle(idveh, idsection):
	return 0

def AAPIExitVehicle(idveh, idsection):
	return 0

def AAPIEnterPedestrian(idPedestrian, originCentroid):
	return 0

def AAPIExitPedestrian(idPedestrian, destinationCentroid):
	return 0

def AAPIEnterVehicleSection(idveh, idsection, atime):
	return 0

def AAPIExitVehicleSection(idveh, idsection, atime):
	return 0
