# -*- coding: utf-8 -*-
"""
.. Created on Fri May  8 12:36:23 2020

.. @author: islam
"""

'''
	This script processes ITSoS detector's data and converts it into compatible files with Aimsun.
	Paths to "speed" and "counts" files of all detectors should be given as <speedPath> and <countsPath>
	and the output file full name is <outputFileName>
	
	id	|	time	|	counts	|	flow	|	speed
'''
import csv
import os
import warnings
import numpy as np
import pandas as pd
import datetime
from .progress_bar import printProgressBar as printProgressBar

def stringToFloat(x):
	'''
	return NaN in case of any failure
	'''
	try:
		return float(x)
	except:
		return np.nan
		
def movingAvgFilter(m, deg):
    '''
    create a new numpy matrix containing the moving average of numpy matrix <m> with degree <deg>
    '''
    ret = np.empty_like(m)
    nrow, ncol = np.shape(m)
    noOfElem = int(deg) // 2
    for i in range(ncol):
        for j in range(nrow):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                ret[j,i] = np.nanmean(m[max(0,j-noOfElem):min(nrow,j+noOfElem+1),i])
    return ret

def readFile(fileName, filterDeg=5, skipLines=4, skipMissingLoc=True):
    '''
    read a file into a numpy matrix and replace the empty cells with the average of their neighbours 
    '''
    try:
        file = open(fileName, 'r')
    except IOError:
        print('No such file %s' %fileName)
        return None
    else:
        with file:
            reader = csv.reader(file)
            # skip metadata
            #for i in range(skipLines):
            #	next(reader)
            loc = ''
            coordinates = None
            i = 0
            for row in reader:
                i += 1
                if row[0] == 'Location':
                    loc = row[1]
                if row[0] == 'Coordinates (X':
                    coordinates = row[2]
                if row[0] == 'Time':
                    days = list(filter(None, map(str.strip, row[1:])))
                    break
            if skipMissingLoc and coordinates is None:
                # skip detectors with no location/coordinates
                return None
            # matrix containing all-month day-by-day 20-second data
            matrix = np.empty((24*60*3, len(days)))
            matrix[:] = np.nan	# initialize <matrix> with NaN to replace empty cells
            # a vector of time: it should be time in 20-second steps
            time = []
            rowInd = 0
            for row in reader:
                time.append(row[0])
                matrix[rowInd] = list(map(stringToFloat, row[1:len(days)+1]))
                rowInd += 1
    # replacing nan cells in matrix with the average of their neighbour cells, if possible
    matrix[np.isnan(matrix)] = movingAvgFilter(matrix, filterDeg)[np.isnan(matrix)]
    return time, matrix, loc
	
def checkFileNameAffixes(fileName, prefixes, suffixes):
	'''
	return True, if the detector name (filename without the .csv extension) starts with one of the given prefixes
		and ends with one of the given suffixes
	'''
	if prefixes and not fileName.split('.')[0].startswith(tuple(prefixes)):
		return False
	if suffixes and not fileName.split('.')[0].endswith(tuple(suffixes)):
		return False
	return True

def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

def split_det_name(df):
    '''
    Split each detector's id (existing in the first column of the dataframe) 
    into freeway, direction, etc. Then add new attributes to the dataframe 
    at the second column (after 'eid' column)

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing detectors data.

    Returns
    -------
    df : pandas.DataFrame
        Updated dataframe.

    '''
    df1 = df.copy()
    df1.insert(loc=1, column='rd_type', 
              value=df1.apply(lambda row: row['eid'][-1], axis=1))
    df1.insert(loc=1, column='dir', 
              value=df1.apply(lambda row: row['eid'][-2], axis=1))
    df1.insert(loc=1, column='dev_type', 
              value=df1.apply(lambda row: row['eid'][-3], axis=1))
    df1.insert(loc=1, column='station_num_2', 
              value=df1.apply(lambda row: row['eid'][-4], axis=1))
    df1.insert(loc=1, column='station_num', 
              value=df1.apply(lambda row: row['eid'][-7:-4], axis=1))
    df1.insert(loc=1, column='dir_ctrl', 
              value=df1.apply(lambda row: row['eid'][-8], axis=1))
    df1.insert(loc=1, column='eq_type', 
              value=df1.apply(lambda row: row['eid'][-9], axis=1))
    df1.insert(loc=1, column='fwy_id', 
              value=df1.apply(lambda row: row['eid'][:-9], axis=1))
    return df1

def hour_to_period(hour):
    if hour < 6:
        return "Off-peak"
    elif hour < 9:
        return "Morning peak"
    elif hour < 16:
        return "Mid-day"
    elif hour < 19:
        return "Afternoon peak"
    else:
        return "Off-peak"
    
def process_det_data(inputPath, outputFileName,
                     weekday, firstDay=1, daysInWeek=3, weeks=4, 
                     startTime=0, endTime=86400, intervalLen=900,
                     files=None, prefixes=None, suffixes=None,
                     skipMissingLoc=True, dropna_key=None):
    '''
    Reads second-by-second speed, count, and occupancy files and aggregate into 
    a single Dataframe. The aggregated Dataframe could be saved to the disk as 
    well.

    Parameters
    ----------
    inputPath : str
        Path to detector data. Counts, speed, and occupancy are stored in 
        "Full_details", "speed", and "occ", respectively.
    outputFileName : str
        Path to store the output file.
    weekday : datetime.date
        Reference day in a month.
    firstDay : int, optional
        Day index in the week. The default is 1 for Tuesday.
    daysInWeek : int, optional
        Number of days per week to be included in the calculations. The default 
        is 3.
    weeks : int, optional
        Number of weeks to be included in the calculations. The default is 4.
    startTime : int, optional
        Start of the aggregation interval in seconds. The default is 0 
        representing midnight (start of the day).
    endTime : int, optional
         of the aggregation interval in seconds. The default is 86400 
         representing midnight (end of the day).
    intervalLen : int, optional
        Aggregation interval width in seconds. The default is 900 representing 
        15 minutes.
    files : a list of detector files/names to process, optional
        To specify some files/detectors to process. The default is None to 
        process all files in the *inputPath* directory.
    prefixes : list of str, optional
        List of freeway encoded-names to filter the files to be processed. The 
        default is None to process all files in the *inputPath* directory.
    suffixes : list of str, optional
        List of detector suffixes to filter the files to be processed. The 
        default is None to process all files in the *inputPath* directory.
    skipMissingLoc : bool, optional
        Skip detector files that do not have location information. The default 
        is True.
    dropna_key: str, optional
        Drop records/rows that has no data in column 'dropna_key'. The default 
        is None, i.e. keeps all records

    Returns
    -------
    pandas.DataFrame
        A dataframe of aggregated and filtered detector data. A record/row for 
        each detector and interval. The Output may contain information about: 
        eid, fwy_id, eq_type, dir_ctrl, station_num, station_num_2, dev_type, 
        dir, rd_type, interval, number_of_lanes, location, time, hour, period, 
        counts, flow, speed, occupancy, flow_per_lane, density_per_lane

    '''
    countsPath = os.path.join(inputPath, 'Full_Details')
    speedPath = os.path.join(inputPath, 'speed')
    occupancyPath = os.path.join(inputPath, 'occ')
    stats = ['counts','flow','speed','occupancy', 'flow_per_lane', 'density_per_lane']
    metadata = ['eid','interval','number_of_lanes','location','time']
    outputHeader = metadata + stats
    skipLines = 4
    recordLen = 20 # in seconds
    
    # process all files in the input directories, if "files" is not specified
    if files is None:
        countsFiles = [f for f in os.listdir(countsPath) if os.path.isfile(os.path.join(countsPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        #countsFiles = [f for f in os.listdir(countsPath) if os.path.isfile(os.path.join(countsPath, f)) and (f.split('.')[0].endswith('DES') or f.split('.')[0].endswith('DWS'))]
        speedFiles = [f for f in os.listdir(speedPath) if os.path.isfile(os.path.join(speedPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        #speedFiles = [f for f in os.listdir(speedPath) if os.path.isfile(os.path.join(speedPath, f)) and (f.split('.')[0].endswith('DES') or f.split('.')[0].endswith('DWS'))]
        occFiles = [f for f in os.listdir(occupancyPath) if os.path.isfile(os.path.join(occupancyPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        files = list(set().union(countsFiles, speedFiles, occFiles))

    d = next_weekday(weekday, firstDay)
    days = []
    for i in range(weeks):
        for j in range(daysInWeek):
            days.append(d)
            d += datetime.timedelta(1)
            if d.month != weekday.month:
                break
        d += datetime.timedelta(7-daysInWeek)
        if d.month != weekday.month:
            break
    colIndices = [i.day - 1 for i in days]
    
    noOfIntervals = int((endTime - startTime) / intervalLen)
    recordsPerInterval = int(intervalLen / recordLen)
    
    # list of lists: each list represents data for one detector and one interval
    # 'eid','time','counts','flow','speed','occupancy'
    #outputs = [[] for i in range(len(files) * noOfIntervals)]
    outputs = []
    printProgressBar(0, len(files), prefix = 'Progress:', suffix = 'Complete', length = 50)
    for fileName, fileInd in zip(files, range(len(files))):
        detName = fileName.split('.')[0]
        # read counts
        retVal = readFile(os.path.join(countsPath, fileName), skipLines=skipLines,
                          skipMissingLoc=skipMissingLoc)
        if retVal is None:
            continue
        else:
            time, countsMatrix, loc = retVal
        # read speed
        retVal = readFile(os.path.join(speedPath, fileName), skipLines=skipLines,
                          skipMissingLoc=skipMissingLoc)
        if retVal is None:
            continue
        else:
            time, speedMatrix, loc = retVal
        # read occupancy
        retVal = readFile(os.path.join(occupancyPath, fileName), skipLines=skipLines,
                          skipMissingLoc=skipMissingLoc)
        if retVal is None:
            continue
        else:
            time, occMatrix, loc = retVal

        # calculate each period's average/sum
        #df_counts = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        #df_flow = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        #df_speed = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        #df_occupancy = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        
        for intInd in range(noOfIntervals):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                # sum(counts) and avg(flows)
                perDayAvg = np.sum(countsMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                counts = np.nanmean(perDayAvg)
                flow = counts / float(intervalLen) * (60*60)
                # avg(speed)
                perDayAvg = np.mean(speedMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                speed = np.nanmean(perDayAvg)
                # avg(occupancy)
                perDayAvg = np.mean(occMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                occupancy = np.nanmean(perDayAvg)
            #outputs[fileInd * noOfIntervals + intInd] = [detName, intInd, '', loc, time[(startTime//recordLen + intInd*recordsPerInterval)], counts, flow, speed, occupancy]
            outputs.append([detName, intInd, '', loc, 
                            time[(startTime//recordLen + intInd*recordsPerInterval)], 
                            counts, flow, speed, occupancy, '', ''])
        printProgressBar(fileInd + 1, len(files), prefix = 'Progress:', suffix = 'Complete', length = 50)
    
    # sort the outputs by name and interval
    outputs.sort(key=lambda x: (x[outputHeader.index('eid')], 
                                x[outputHeader.index('time')]))
    # writing the outputs in "outputFileName" if given, otherwise print to the console
    '''if outputFileName is not None:
        with open(outputFileName, 'w', newline='') as fp:
            writer = csv.writer(fp, delimiter=',')
            writer.writerow(outputHeader)	# writing the header
            for i in range(len(outputs)):
                if len(outputs[i]) == 0 or np.isnan(outputs[i][-1]) or outputs[i][-1] == 0:
                    # don't write nan or zero-speed entries
                    continue
                writer.writerow(outputs[i])'''
    
    df = pd.DataFrame(columns=outputHeader, data=outputs)
    #dropna_key = 'speed'
    if dropna_key is not None:
        df.dropna(subset=[dropna_key], inplace=True)
    df.insert(loc=df.columns.get_loc('time')+1, column='hour',
          value=pd.to_datetime(df.time, format='%H:%M:%S').dt.hour)
    df.insert(loc=df.columns.get_loc('hour')+1, column='period', 
          value=df.apply(lambda row: hour_to_period(row['hour']), axis=1))
    result = split_det_name(df)
    if outputFileName is not None:
        result.to_csv(outputFileName)
    return result

    
def process_det_data2(inputPath, outputFileName,
                     firstDay, startTime=0, endTime=86400, intervalLen=900,
                     files=None, prefixes=None, suffixes=None,
                     skipMissingLoc=True):	
    '''
    

    Parameters
    ----------
    inputPath : str
        Path to detector data. Counts, speed, and occupancy are stored in 
        "Full_details", "speed", and "occ", respectively.
    outputFileName : str
        Path to store the output file.
    firstDay : int
        Index of first Tuesday in the month. 0 is for day 1 of the month.
    startTime : int, optional
        Start of the aggregation interval in seconds. The default is 0 
        representing midnight (start of the day).
    endTime : int, optional
         of the aggregation interval in seconds. The default is 86400 
         representing midnight (end of the day).
    intervalLen : int, optional
        Aggregation interval width in seconds. The default is 900 representing 
        15 minutes.
    files : a list of detector files/names to process, optional
        To specify some files/detectors to process. The default is None to 
        process all files in the *inputPath* directory.
    prefixes : list of str, optional
        List of freeway encoded-names to filter the files to be processed. The 
        default is None to process all files in the *inputPath* directory.
    suffixes : list of str, optional
        List of detector suffixes to filter the files to be processed. The 
        default is None to process all files in the *inputPath* directory.

    Returns
    -------
    None.

    '''
    countsPath = os.path.join(inputPath, 'Full_Details')
    speedPath = os.path.join(inputPath, 'speed')
    occupancyPath = os.path.join(inputPath, 'occ')
    stats = ['counts','flow','speed','occupancy']
    metadata = ['eid','interval','number_of_lanes','location','time']
    outputHeader = metadata + stats
    skipLines = 4
    recordLen = 20 # in seconds
    
    # process all files in the input directories, if "files" is not specified
    if files is None:
        countsFiles = [f for f in os.listdir(countsPath) if os.path.isfile(os.path.join(countsPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        #countsFiles = [f for f in os.listdir(countsPath) if os.path.isfile(os.path.join(countsPath, f)) and (f.split('.')[0].endswith('DES') or f.split('.')[0].endswith('DWS'))]
        speedFiles = [f for f in os.listdir(speedPath) if os.path.isfile(os.path.join(speedPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        #speedFiles = [f for f in os.listdir(speedPath) if os.path.isfile(os.path.join(speedPath, f)) and (f.split('.')[0].endswith('DES') or f.split('.')[0].endswith('DWS'))]
        occFiles = [f for f in os.listdir(occupancyPath) if os.path.isfile(os.path.join(occupancyPath, f)) and checkFileNameAffixes(f, prefixes, suffixes)]
        files = list(set().union(countsFiles, speedFiles, occFiles))

    colIndices = np.array([firstDay, firstDay+1, firstDay+2,
    				firstDay+7 , firstDay+8 , firstDay+9 ,
    				firstDay+14, firstDay+15, firstDay+16,
    				firstDay+21, firstDay+22, firstDay+23])
    
    noOfIntervals = int((endTime - startTime) / intervalLen)
    recordsPerInterval = int(intervalLen / recordLen)
    
    # list of lists: each list represents data for one detector and one interval
    # 'eid','time','counts','flow','speed','occupancy'
    #outputs = [[] for i in range(len(files) * noOfIntervals)]
    outputs = []
    printProgressBar(0, len(files), prefix = 'Progress:', suffix = 'Complete', length = 50)
    for fileName, fileInd in zip(files, range(len(files))):
        detName = fileName.split('.')[0]
        # read counts
        retVal = readFile(os.path.join(countsPath, fileName), skipLines=skipLines,
                          skipMissingLoc=skipMissingLoc)
        if retVal is None:
            continue
        else:
            time, countsMatrix, loc = retVal
        # read speed
        retVal = readFile(os.path.join(speedPath, fileName), skipLines=skipLines)
        if retVal is None:
            continue
        else:
            time, speedMatrix, loc = retVal
        # read occupancy
        retVal = readFile(os.path.join(occupancyPath, fileName), skipLines=skipLines)
        if retVal is None:
            continue
        else:
            time, occMatrix, loc = retVal

        # calculate each period's average/sum
        df_counts = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        df_flow = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        df_speed = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        df_occupancy = pd.DataFrame(columns=metadata+list(map(lambda x:'day'+str(x),colIndices+1)))
        
        for intInd in range(noOfIntervals):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                # sum(counts) and avg(flows)
                perDayAvg = np.sum(countsMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                counts = np.nanmean(perDayAvg)
                flow = counts / float(intervalLen) * (60*60)
                # avg(speed)
                perDayAvg = np.mean(speedMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                speed = np.nanmean(perDayAvg)
                # avg(occupancy)
                perDayAvg = np.mean(occMatrix[(startTime//recordLen + intInd*recordsPerInterval):(startTime//recordLen + recordsPerInterval + intInd*recordsPerInterval), colIndices],0)
                occupancy = np.nanmean(perDayAvg)
            #outputs[fileInd * noOfIntervals + intInd] = [detName, intInd, '', loc, time[(startTime//recordLen + intInd*recordsPerInterval)], counts, flow, speed, occupancy]
            outputs.append([detName, intInd, '', loc, time[(startTime//recordLen + intInd*recordsPerInterval)], counts, flow, speed, occupancy])
        printProgressBar(fileInd + 1, len(files), prefix = 'Progress:', suffix = 'Complete', length = 50)
    
    # sort the outputs by name and interval
    outputs.sort(key=lambda x: (x[outputHeader.index('eid')], 
                                x[outputHeader.index('time')]))
    # writing the outputs in "outputFileName" if given, otherwise print to the console
    '''if outputFileName is None:
        print(outputHeader)	# writing the header
        for i in range(len(outputs)):
            if np.isnan(outputs[i][-1]) or outputs[i][-1] == 0:
                # don't write nan or zero-speed entries
                continue
            print(outputs[i])
    else:'''
    if outputFileName is not None:
        with open(outputFileName, 'w', newline='') as fp:
            writer = csv.writer(fp, delimiter=',')
            writer.writerow(outputHeader)	# writing the header
            for i in range(len(outputs)):
                if len(outputs[i]) == 0 or np.isnan(outputs[i][-1]) or outputs[i][-1] == 0:
                    # don't write nan or zero-speed entries
                    continue
                writer.writerow(outputs[i])
                
    return pd.DataFrame(columns=outputHeader, data=outputs)