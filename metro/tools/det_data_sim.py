# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 13:00:11 2020

@author: islam
"""

import os
import sys
if __name__ == "__main__":
    package_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                "../../../.."))
    #package_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    #                                            "../../../.."))
    sys.path.append(package_path)
import metro.tools.visualize as visualize
    
import math
import csv
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter, IndexLocator
from matplotlib.animation import FuncAnimation
import pandas as pd

        
def process_all_lanes(df, locations=None, intervals=None):
    detectors = list(df.groupby('eid').groups)
    if locations is None:
        locations = [x.split('-')[-1].strip() for x in 
                     df.groupby('eid').apply(lambda x:x['Location'].iloc[0])]
    if intervals is None:
        intervals = [x for x in 
                     df.groupby('interval').apply(lambda x:x['time'].iloc[0])]
    
    speed = df.pivot(index='interval',
                     columns='eid',
                     values='Speed')
    speed = speed.reindex(sorted(speed.columns), axis=1)
    
    flow = df.pivot(index='interval',
                    columns='eid',
                    values='Flow per lane')
    flow = flow.reindex(sorted(flow.columns), axis=1)
    
    density = df.pivot(index='interval',
                       columns='eid',
                       values='Density per lane')
    density = density.reindex(sorted(density.columns), axis=1)
    
    return detectors, intervals, locations, speed, flow, density

def process_stats(df, locations=None, intervals=None):
    detectors = list(df.groupby('eid').groups)
    if locations is None:
        locations = [x.split('-')[-1].strip() if not pd.isna(x) else '' for x in 
                     df.groupby('eid').apply(lambda x:x['location'].iloc[0])]
    if intervals is None:
        intervals = [x for x in 
                     df.groupby('interval').apply(lambda x:x['time'].iloc[0])]
    
    speed = df.pivot(index='interval',
                     columns='eid',
                     values='speed')
    speed = speed.reindex(sorted(speed.columns), axis=1)
    
    flow = df.pivot(index='interval',
                    columns='eid',
                    values='flow_per_lane')
    flow = flow.reindex(sorted(flow.columns), axis=1)
    
    density = df.pivot(index='interval',
                       columns='eid',
                       values='density_per_lane')
    density = density.reindex(sorted(density.columns), axis=1)
    
    return detectors, intervals, locations, speed, flow, density

def update_number_of_lanes(df, number_of_lanes_df, hov=True, dropna=True,
                           update_stats=True):
    '''
    Updates number of lanes of each detector in df based on number_of_lanes_df

    Parameters
    ----------
    df : pandas.DataFrame
        DESCRIPTION.
    number_of_lanes_df : pandas.DataFrame
        DESCRIPTION.
    hov : bool, optional
        DESCRIPTION. The default is True.
    dropna : bool, optional
        DESCRIPTION. The default is True.
    update_stats : bool, optional
        DESCRIPTION. The default is True.

    Returns
    -------
    result : TYPE
        DESCRIPTION.

    '''
    number_of_lanes_df.drop_duplicates(['eid'], keep='first', inplace=True)
    result = df.merge(number_of_lanes_df, 'left', on='eid', suffixes=('','_y'))
    result['number_of_lanes'] = result.apply(lambda x:x['number_of_lanes_y'], 
                                             axis=1)
    result = result.drop(columns=['number_of_lanes_y'])
    if hov:
        result['number_of_lanes'] = result.apply(lambda x:1 if x['station_num_2']==1 \
                                                 else x['number_of_lanes'], axis=1)
    if dropna:
        result.dropna(subset=['number_of_lanes'], inplace=True)
    if update_stats:
        result['flow_per_lane'] = result.apply(
            lambda x:x['flow']/x['number_of_lanes'] \
                if x['number_of_lanes']!=0 else None, 
                axis=1)
        result['density_per_lane'] = result.apply(
            lambda x:x['flow_per_lane']/x['speed'] \
                if x['number_of_lanes']!=0 else None, 
                axis=1)
    return result
    
def update_hov_locations(df):
    locations = df[df.station_num_2==0].groupby('station_num').\
                    apply(lambda x:x['location'].iloc[0])
    locations = df[df.station_num_2==0][['station_num','location']]
    locations.drop_duplicates(['station_num'], keep='first', inplace=True)
    result = df.merge(locations, 'left', on='station_num', suffixes=('','_y'))
    result['location'] = result.apply(lambda x:x['location_y'], axis=1)
    result = result.drop(columns=['location_y'])
    return result
    
# Observed Data
#==============
# observed data 2016
#___________________
df_obs = pd.read_csv('C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/ITSoS_detectors.csv')
detectors, intervals, locations, speed_obs, flow_obs, density_obs = \
    process_all_lanes(df_obs)
#df_heatmap(df=speed, title='Observed Speed', y_labels=intervals, x_labels=locations)
df_obs = pd.read_csv('C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/ITSoS_detectors2.csv')
detectors, intervals, locations, speed_obs, flow_obs, density_obs = \
    process_stats(df_obs)
visualize.heatmap_grid(dfs=[speed_obs], suptitle='Observed Speed', 
             x_labels=locations, y_labels=intervals)
# Observed Data 2019
#___________________
inputPath = 'C:\\Computer\\work\\detector_data\\2019_03'
outputFileName = None #'C:\\Computer\\work\\detector_data\\observed_data_2019_3.csv'	# output file's absolute path
#inputPath = 'C:\\Computer\\work\\detector_data\\2020_03'
#outputFileName = 'C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv'	# output file's absolute path
startTime=21600
endTime=36000
intervalLen=900
files=None
prefixes = ['QEW']
suffixes = ['DES']
data = det_data.process_det_data(inputPath, outputFileName,
                                 datetime.date(2019, 3, 1), 1, 3, 4,
                                 startTime, endTime, intervalLen,
                                 files, prefixes, suffixes, 
                                 skipMissingLoc=False)
data.to_csv('C:\\Users\\islam\\Desktop\\qew_2019_10.csv')
data = pd.read_csv('C:\\Users\\islam\\Desktop\\qew_2019_10.csv')
data.insert(loc=len(data.columns), column='flow_per_lane', value=np.nan)
data.insert(loc=len(data.columns), column='density_per_lane', value=np.nan)
data.dropna(subset=['speed'], inplace=True)
number_of_lanes_df = df_obs[['eid','number_of_lanes']]
data = update_number_of_lanes(data, number_of_lanes_df)
data = update_hov_locations(data)
obs2019 = process_stats(data)
len(data.columns)
# Simulated Data
#==============
file_sim = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/repl10297720_detectors.csv'
df_sim = pd.read_csv(file_sim)
df_sim.insert(loc=2, column='lane',
              value=df_sim.apply(lambda row: int(row['name'].split('_')[-1]) \
                                 if len(row['name'].split('_'))>1 else -1,
                                 axis=1))
df_sim.insert(loc=2, column='eid',
              value=df_sim.apply(lambda row: row['name'].split('_')[0], axis=1))
df_by_lane = df_sim[df_sim.lane != -1]
df_all_lanes = df_sim[df_sim.lane == -1]
# all lanes
#__________
# reuse intervals from "observed data" section
# check this
_, _, _, speed_sim, flow_sim, density_sim = process_all_lanes(df_all_lanes, 
                                                              locations,
                                                              intervals)
df_heatmap(df=speed_sim, title='Simulated Speed', 
           y_labels=intervals, x_labels=locations)
heatmap_grid(dfs=[speed_sim], suptitle='Simulated Speed', 
             x_labels=locations, y_labels=intervals)

# lane by lane
#_____________
speed = df_by_lane.pivot_table(index=['interval','lane'],
                         columns=['eid'],
                         values='speed')

# heatmap of specific lane speed for all intervals
#-------------------------------------------------
lane_index = 1
lane_speed = speed.loc[[x for x in list(speed.index) if x[1]==lane_index]]
#df_heatmap(df=lane_speed, title='Lane %i Speed (km/hr)' % lane_index, 
#           y_labels=intervals, x_labels=locations)
visualize.heatmap_grid(dfs=[lane_speed], suptitle='Lane %i Speed (km/hr)' % lane_index, 
             x_labels=locations, y_labels=intervals)

lane_speeds = []
titles = []
no_intervals = max([x[0] for x in speed.index.values]) + 1
#intervals = range(no_intervals)
no_lanes = max([x[1] for x in speed.index.values]) + 1
for lane_index in range(no_lanes):
    lane_speeds.append(speed.loc[[x for x in list(speed.index) if x[1]==lane_index]])
    titles.append('Lane %i' % lane_index)
visualize.heatmap_grid(dfs=lane_speeds, suptitle='Speed', titles=titles, 
             x_labels=locations, y_labels=intervals, nrows=no_lanes, ncols=1)
visualize.heatmap_animated(dfs=lane_speeds, suptitle='Speed', titles=titles, 
             x_labels=locations, y_labels=intervals,
             save_to='C:/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/metro3/metro/line.gif')

# heatmap of lane speed for specific interval
#--------------------------------------------
interval_index = 4
interval_speed = speed.loc[interval_index]
#df_heatmap(df=interval_speed, title='Interval %i Speed (km/hr)' % interval_index, 
#           y_labels=list(interval_speed.index), x_labels=locations)
visualize.heatmap_grid(dfs=[interval_speed], 
             suptitle='Interval %i Speed (km/hr)' % interval_index, 
             x_labels=locations, y_labels=list(interval_speed.index))

interval_speeds = []
titles = []
no_intervals = max([x[0] for x in speed.index.values]) + 1
#intervals = range(no_intervals)
no_lanes = max([x[1] for x in speed.index.values]) + 1
for interval_index in range(no_intervals):
    interval_speeds.append(speed.loc[interval_index])
    titles.append('Interval %i' % interval_index)
visualize.heatmap_grid(dfs=interval_speeds, suptitle='Speed', titles=titles, 
             x_labels=locations, y_labels=range(no_lanes), nrows=4, ncols=4)
visualize.heatmap_animated(dfs=interval_speeds, suptitle='Speed', titles=intervals, 
             x_labels=locations, y_labels=range(no_lanes),
             save_to='C:/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/metro3/metro/line.gif')

#=============================================================================
# obselete functions
#=============================================================================
def heatmap_animated2(save=False):
    def update(i):
        label = 'timestep {0}'.format(i)
        print(label)
        # Update the line and the axes (with a new xlabel). Return a tuple of
        # "artists" that have to be redrawn for this frame.
        line.set_ydata(x - 5 + i)
        ax.set_xlabel(label)
        return line, ax
    
    fig, ax = plt.subplots()
    fig.set_tight_layout(True)
    # Query the figure's on-screen size and DPI. Note that when saving the figure to
    # a file, we need to provide a DPI for that separately.
    print('fig size: {0} DPI, size in inches {1}'.format(
        fig.get_dpi(), fig.get_size_inches()))
    
    # Plot a scatter that persists (isn't redrawn) and the initial line.
    x = np.arange(0, 20, 0.1)
    ax.scatter(x, x + np.random.normal(0, 3.0, len(x)))
    line, = ax.plot(x, x - 5, 'r-', linewidth=2)
    
    # FuncAnimation will call the 'update' function for each frame; here
    # animating over 10 frames, with an interval of 200ms between frames.
    anim = FuncAnimation(fig, update, frames=np.arange(0, 10), interval=200)
    if save:
        anim.save('C:/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/metro3/metro/line.gif', 
                  dpi=80, writer='imagemagick')
    else:
        # plt.show() will just loop the animation forever.
        plt.show()

def df_heatmap(df, title='', x_labels=None, y_labels=None, limits=None, cmap_reverse=False):
    # Observed vs. Simulated Time-Space Diagrams of Speed
    def format_fnx(tick_val, tick_pos):
    	if tick_val < len(x_labels):
    		return x_labels[int(tick_val)]
    	else:
    		return ''
    def format_fny(tick_val, tick_pos):
    	if tick_val < len(y_labels):
    		return y_labels[int(tick_val)]
    	else:
    		return ''
    # default args
    if y_labels is None:
        y_labels = list(df.columns)
    if x_labels is None:
        x_labels = list(df.index)
    if cmap_reverse:
        cmap = 'RdYlGn_r'
    else:
        cmap = 'RdYlGn'
    current_cmap = matplotlib.cm.get_cmap(cmap)
    current_cmap.set_bad(color='white')
    
    fig, ax = plt.subplots(nrows=1, ncols=1)
    
    if limits is None:
        img = ax.imshow(df, cmap=cmap, aspect='auto')
    else:
        img = ax.imshow(df, cmap=cmap, aspect='auto', 
                        vmin=limits[0], vmax=limits[1])
    ax.set_title(title)
    ax.xaxis.set_major_formatter(FuncFormatter(format_fnx))
    ax.xaxis.set_major_locator(IndexLocator(base=2, offset=0.5))
    for tick in ax.get_xticklabels():
    	tick.set_rotation(90)
    ax.yaxis.set_major_formatter(FuncFormatter(format_fny))
    ax.yaxis.set_major_locator(IndexLocator(base=1, offset=0.5))
    
    plt.tight_layout(pad=3)
    fig.subplots_adjust(right=0.85, top=0.95)
    cbar_ax = fig.add_axes([0.9, 0.25, 0.03, 0.5])
    fig.colorbar(img, cax=cbar_ax)
    plt.show()
    return img

#=============================================================================
# old figures
#=============================================================================

maxNoLanes = 6
noIntervals = 16
noDetectors = 42
# Observed Data
#==============
#detectorFileName = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/ITSoS_detectors.csv'
#detectorFileName = 'C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv'
detectorFileName = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/' \
                    'ITSoS_detectors.csv'

with open(detectorFileName, 'r') as fin:
	reader = csv.reader(fin)
	data = list(reader)
header = data[0]
observedData = {} # {<det>_<interval> : {'u': , 'q': , 'k': }}
# heatmaps: speed, flow, density
# heatmaps: time on vertical axis and space (detectors) on horizontal axis
obsSpeed = np.zeros((noIntervals, noDetectors))
obsFlow = np.zeros((noIntervals, noDetectors))
obsDensity = np.zeros((noIntervals, noDetectors))
detectorLocation = {}
for row in data[1:]:
	# skip the first detector
	if row[0].startswith("QEWDE0020DES"):
		continue
	detectorLocation[row[0]] = row[3]
	observedData['_'.join([row[0], str(row[1])])] = {'u':float(row[7]), 'q':float(row[8]), 'k':float(row[9])}
	obsSpeed[int(row[1]), len(detectorLocation)-1] = float(row[7])
	obsFlow[int(row[1]), len(detectorLocation)-1] = float(row[8])
	obsDensity[int(row[1]), len(detectorLocation)-1] = float(row[9])

detectors = list(detectorLocation.keys())
detectors.sort()
locations = [detectorLocation[x] for x in detectors]

# Observed vs. Simulated Time-Space Diagrams of Speed
def format_fn(tick_val, tick_pos):
	if tick_val < len(locations):
		return locations[int(tick_val)]
	else:
		return ''
fig1, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10,9),
                       subplot_kw={'yticks': range(0,noIntervals,2)})
ax1.imshow(obsSpeed, cmap='RdYlGn')
ax1.set_title('Observed Speed')
ax1.xaxis.set_major_formatter(FuncFormatter(format_fn))
ax1.xaxis.set_major_locator(IndexLocator(base=1, offset=0.5))
for tick in ax1.get_xticklabels():
	tick.set_rotation(90)

# Simulated Data
#===============
inputFileName = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/repl10297720_detectors.csv'
with open(inputFileName, 'r') as fin:
	reader = csv.reader(fin)
	data = list(reader)

laneDet = {} # {<det>_<interval> : {'u': , 'q': , 'k': }}
wideDet = {} # {<det>_<interval> : {'u': , 'q': , 'k': }}
laneSpeed = {}
laneFlow = {}
laneDensity = {}
simSpeed = np.zeros((noIntervals, noDetectors))
simFlow = np.zeros((noIntervals, noDetectors))
simDensity = np.zeros((noIntervals, noDetectors))
header = data[0]
for row in data[1:]:
	if row[0].startswith("QEWDE0020DES"):
		continue
	if '_' in row[0]:
		laneDet['_'.join([row[0], str(row[1])])] = {'u':row[3], 'q':row[6], 'k':row[7]}
	else:
		wideDet['_'.join([row[0], str(row[1])])] = {'u':row[3], 'q':row[6], 'k':row[7]}
		simSpeed[int(row[1]), detectors.index(row[0])] = float(row[3])
		simFlow[int(row[1]), detectors.index(row[0])] = float(row[6])
		simDensity[int(row[1]), detectors.index(row[0])] = float(row[7])
	
		laneSpeed[row[0]] = np.zeros((int(row[2]), noIntervals))
		laneFlow[row[0]] = np.zeros((int(row[2]), noIntervals))
		laneDensity[row[0]] = np.zeros((int(row[2]), noIntervals))

ax2.imshow(simSpeed, cmap='RdYlGn')
#ax2.set_anchor('W')
ax2.set_title('Simulated Speed')
ax2.xaxis.set_major_formatter(FuncFormatter(format_fn))
ax2.xaxis.set_major_locator(IndexLocator(base=1, offset=0.5))
for tick in ax2.get_xticklabels():
	tick.set_rotation(90)
plt.tight_layout(pad=3)
#plt.tight_layout(rect=(0,0,0,3))
plt.show()


detectors = list(laneSpeed.keys())
detectors.sort()	
for i in laneDet:
	detector, lane, interval = i.split('_')
	laneSpeed[detector][int(lane), int(interval)] = laneDet[i]['u']
	laneFlow[detector][int(lane), int(interval)] = laneDet[i]['q']
	laneDensity[detector][int(lane), int(interval)] = laneDet[i]['k']

maxSpeed = max(map(np.max, laneSpeed.values()))
maxFlow = max(map(np.max, laneFlow.values()))
maxDensity = max(map(np.max, laneDensity.values()))
maxSpeed = math.ceil(maxSpeed/10)*10
maxFlow = math.ceil(maxFlow/100)*100
maxDensity = math.ceil(maxDensity/10)*10

methods = [None, 'none', 'nearest', 'bilinear', 'bicubic', 'spline16',
           'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric',
           'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos']
interp_method = None

fig, axs = plt.subplots(nrows=6, ncols=7, figsize=(noIntervals, maxNoLanes),
                       subplot_kw={'xticks': [], 'yticks': range(0,maxNoLanes,2)})
images = []
for ax, detector in zip(axs.flat, detectors):
	images.append(ax.imshow(laneSpeed[detector], interpolation=interp_method, cmap='RdYlGn')) #aspect="auto"
	if detector <= "QEWDE0260DES":
		ax.set_title(detector, color='green')
	else:
		ax.set_title(detector, color='black')
	ax.set_anchor('N')
	#plt.legend(loc="upper left")
plt.suptitle('Time-Space Diagrams', color='blue')
plt.tight_layout(pad=3)
plt.show()

fig, axs = plt.subplots(nrows=6, ncols=7, figsize=(18, 9),
                       subplot_kw={'xticks': [0, maxDensity], 'yticks': [0, maxFlow]})
colors = ['green', 'red', 'blue', 'yellow', 'gray', 'brown']
for ax, detector in zip(axs.flat, detectors):
	for i in range(laneDensity[detector].shape[0]):
		ax.scatter(laneDensity[detector][i], laneFlow[detector][i], color=colors[i], s=10)
	if detector <= "QEWDE0260DES":
		ax.set_title(detectorLocation[detector], color='green')
	else:
		ax.set_title(detectorLocation[detector], color='black')
	#plt.legend(loc="upper left")
	ax.set_xlim(0, maxDensity)
	ax.set_ylim(0, maxFlow)
	
#handles, labels = ax.get_legend_handles_labels()
#fig.legend(handles, labels, loc='upper center')

patches = []
for i in range(len(colors)):
	patches.append(mpatches.Patch(color=colors[i], label='lane ' + str(i)))
fig.legend(handles=patches, loc='lower center', ncol=len(patches))
plt.suptitle('Flow-Density Diagrams', color='blue')
plt.tight_layout(pad=3)
plt.show()

print("Done")
