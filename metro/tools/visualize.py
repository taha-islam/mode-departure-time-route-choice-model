# -*- coding: utf-8 -*-
"""
Created on Tue May 12 11:54:13 2020

@author: islam
"""

import sys

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter, IndexLocator
from matplotlib.animation import FuncAnimation
import math
import csv
import pandas as pd

# data format -> ['eid','interval','number_of_lanes','location','time',
#                    'counts','flow','speed','occupancy']

def readData(detectorFileName, detectors=None, intervals=None):
    '''
    

    Parameters
    ----------
    detectorFileName : TYPE
        DESCRIPTION.
    detectors : TYPE, optional
        ['QEWDE0010DES','QEWDE0020DES']. The default is None.
    intervals : TYPE, optional
        range(5*4,22*4). The default is None.

    Returns
    -------
    None.

    '''
    df = pd.read_csv(detectorFileName)
    if detectors:
        df=df[df['eid'].isin(detectors)]
    if intervals:
        df=df[df['interval'].isin(intervals)]
    df.sort_values(['eid', 'interval'])
    return df
    
def equate_df_keys(df1, df2, key):
    '''
    

    Parameters
    ----------
    df1 : TYPE
        DESCRIPTION.
    df2 : TYPE
        DESCRIPTION.
    key : TYPE
        DESCRIPTION.

    Returns
    -------
    df1_new : TYPE
        DESCRIPTION.
    df2_new : TYPE
        DESCRIPTION.

    '''
    keys1 = df1.groupby(key).groups.keys()
    keys2 = df2.groupby(key).groups.keys()
    #list(set(keys1).symmetric_difference(set(keys2)))
    missing_keys1 = list(set(keys1) - set(keys2))
    if missing_keys1:
        df1_new = df1[~ df1[key].isin(missing_keys1)]
    else:
        df1_new = df1
    missing_keys2 = list(set(keys2) - set(keys1))
    if missing_keys2:
        df2_new = df2[~ df2[key].isin(missing_keys2)]
    else:
        df2_new = df2
    return df1_new, df2_new

'''
#continous heatmap for temporal video
arr = np.arange(100, dtype=float).reshape(10, 10)
arr[~(arr % 7).astype(bool)] = np.nan
current_cmap = matplotlib.cm.get_cmap()
current_cmap.set_bad(color='red')
plt.imshow(arr)
'''    
def heatmap(ax, title, df, statName, limits=None, cmap_reverse=False):
    '''
    

    Parameters
    ----------
    ax : TYPE
        DESCRIPTION.
    title : TYPE
        DESCRIPTION.
    df : TYPE
        DESCRIPTION.
    statName : TYPE
        DESCRIPTION.
    limits : TYPE, optional
        DESCRIPTION. The default is None.
    cmap_reverse : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    noIntervals = df['interval'].max() + 1
    noDetectors = df['eid'].nunique()
    g = df.groupby('interval').cumcount()
    stat = np.array(df.set_index(['interval',g]).unstack(fill_value=0).stack()
                 .groupby(level=0).apply(lambda x: x[statName].tolist()).tolist())
    locations = [x.split('-')[-1].strip() for x in 
                 df.groupby('eid').apply(lambda x:x['location'].iloc[0])]
    
    # Observed vs. Simulated Time-Space Diagrams of Speed
    def format_fn(tick_val, tick_pos):
    	if tick_val < len(locations):
    		return locations[int(tick_val)]
    	else:
    		return ''
    def format_fny(tick_val, tick_pos):
        timeIntervals = pd.unique(df['time']).tolist()
        if tick_val < len(timeIntervals):
            return timeIntervals[int(tick_val)]
        else:
            return ''
    
    if cmap_reverse:
        cmap = 'RdYlGn_r'
    else:
        cmap = 'RdYlGn'
    current_cmap = matplotlib.cm.get_cmap(cmap)
    current_cmap.set_bad(color='white')
    if limits is None:
        retVal = ax.imshow(stat, cmap=cmap)
    else:
        retVal = ax.imshow(stat, cmap=cmap, vmin=limits[0], vmax=limits[1])
    ax.set_aspect('auto')
    ax.set_title(title)
    ax.xaxis.set_major_formatter(FuncFormatter(format_fn))
    ax.xaxis.set_major_locator(IndexLocator(base=1, offset=0.5))
    for tick in ax.get_xticklabels():
    	tick.set_rotation(90)
        
    ax.yaxis.set_major_formatter(FuncFormatter(format_fny))
    ax.yaxis.set_major_locator(IndexLocator(base=4, offset=0.5))
    
    return retVal

def compare_heatmaps(suptitle, titles, dfs, statName, limits=None, cmap_reverse=False):
    '''
    

    Parameters
    ----------
    titles : TYPE
        DESCRIPTION.
    dfs : TYPE
        DESCRIPTION.
    statName : TYPE
        DESCRIPTION.
    limits : TYPE, optional
        DESCRIPTION. The default is None.
    cmap_reverse : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    None.

    '''
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10,15), sharex=True) #, subplot_kw={'yticks': range(0,noIntervals,2)})
    st = fig.suptitle(suptitle, fontsize="x-large")
    st.set_y(1)
    
    if limits is None:
        limits = (min(dfs[0][statName].min(), dfs[1][statName].min()),
                  max(dfs[0][statName].max(), dfs[1][statName].max()))
    img = heatmap(ax1, titles[0], dfs[0], statName, 
                  limits=limits, cmap_reverse=cmap_reverse)
    img = heatmap(ax2, titles[1], dfs[1], statName, 
                  limits=limits, cmap_reverse=cmap_reverse)
    plt.tight_layout(pad=3)
    fig.subplots_adjust(right=0.85, top=0.95)
    cbar_ax = fig.add_axes([0.9, 0.25, 0.03, 0.5])
    fig.colorbar(img, cax=cbar_ax)
    plt.show()
    
    return fig

def plot_series(x, y, y_titles, suptitle, 
                xaxis_title=None, yaxis_title=None, 
                plot_type='line'):
    
    # for bar chart
    x1 = np.arange(len(x))  # the label locations
    width = 0.35
    i = 1-len(y)
    
    fig, ax = plt.subplots()
    for series in y:
        if plot_type == 'line':
            ax.plot(x, series)
        elif plot_type == 'bar':
            ax.bar(x1+i*width/2, series, width)
            i += 2
    
    if plot_type == 'line':
        ax.xaxis.set_major_locator(IndexLocator(base=4, offset=0))
        ax.grid(True)
    elif plot_type == 'bar':
        ax.set_xticks(x1)
        ax.set_xticklabels(x)
        #ax.xaxis.set_major_locator(IndexLocator(base=len(y), offset=0))
        
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)
    ax.set_xlabel(xaxis_title)
    ax.set_ylabel(yaxis_title)
    plt.legend(y_titles, loc='best')
    st = fig.suptitle(suptitle, fontsize="x-large")
    st.set_y(1)
    #fig.subplots_adjust(top=0.95)
    plt.show()

#=============================================================================
# New figures
##=============================================================================
def heatmap_single(ax, df, title='', x_labels=None, y_labels=None, 
                   limits=None, cmap_reverse=False):
    '''
    

    Parameters
    ----------
    ax : TYPE
        DESCRIPTION.
    df : TYPE
        DESCRIPTION.
    title : TYPE, optional
        DESCRIPTION. The default is ''.
    x_labels : TYPE, optional
        DESCRIPTION. The default is None.
    y_labels : TYPE, optional
        DESCRIPTION. The default is None.
    limits : TYPE, optional
        DESCRIPTION. The default is None.
    cmap_reverse : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
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
    
    return img

def heatmap_grid(dfs, suptitle='', titles=[''], x_labels=None, y_labels=None, 
                 limits=None, cmap_reverse=False,
                 nrows=1, ncols=1):
    '''
    

    Parameters
    ----------
    dfs : TYPE
        DESCRIPTION.
    suptitle : TYPE, optional
        DESCRIPTION. The default is ''.
    titles : TYPE, optional
        DESCRIPTION. The default is [''].
    x_labels : TYPE, optional
        DESCRIPTION. The default is None.
    y_labels : TYPE, optional
        DESCRIPTION. The default is None.
    limits : TYPE, optional
        DESCRIPTION. The default is None.
    cmap_reverse : TYPE, optional
        DESCRIPTION. The default is False.
    nrows : TYPE, optional
        DESCRIPTION. The default is 1.
    ncols : TYPE, optional
        DESCRIPTION. The default is 1.

    Returns
    -------
    fig : TYPE
        DESCRIPTION.

    '''
    if nrows == 1 and ncols==1:
        fig, axs = plt.subplots(nrows=1, ncols=1)
        if suptitle == '':
            title = titles[0]
        else:
            title = suptitle
        img = heatmap_single(ax=axs, df=dfs[0], title=title, 
                             x_labels=x_labels, y_labels=y_labels, 
                             limits=limits, cmap_reverse=cmap_reverse)
    else:
        fig, axs = plt.subplots(nrows=nrows, ncols=ncols,
                                 sharex=True,figsize=(10,15))
        # subplot_kw={'yticks': range(0,noIntervals,2)})
        for ax, df, title in zip(axs.ravel(), dfs, titles):
            img = heatmap_single(ax=ax, df=df, title=title, 
                                 x_labels=x_labels, y_labels=y_labels, 
                                 limits=limits, cmap_reverse=cmap_reverse)
        st = fig.suptitle(suptitle, fontsize="x-large")
        st.set_y(1)
    
    plt.tight_layout(pad=3)
    fig.subplots_adjust(right=0.85, top=0.95)
    cbar_ax = fig.add_axes([0.9, 0.25, 0.03, 0.5])
    fig.colorbar(img, cax=cbar_ax)
    plt.show()
    return fig

def heatmap_animated(dfs, suptitle='', titles=[''], 
                     x_labels=None, y_labels=None,
                     limits=None, cmap_reverse=False,
                     nrows=1, ncols=1, save_to=None):
    '''
    

    Parameters
    ----------
    dfs : TYPE
        DESCRIPTION.
    suptitle : TYPE, optional
        DESCRIPTION. The default is ''.
    titles : TYPE, optional
        DESCRIPTION. The default is [''].
    x_labels : TYPE, optional
        DESCRIPTION. The default is None.
    y_labels : TYPE, optional
        DESCRIPTION. The default is None.
    limits : TYPE, optional
        DESCRIPTION. The default is None.
    cmap_reverse : TYPE, optional
        DESCRIPTION. The default is False.
    nrows : TYPE, optional
        DESCRIPTION. The default is 1.
    ncols : TYPE, optional
        DESCRIPTION. The default is 1.
    save_to : TYPE, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    img : TYPE
        DESCRIPTION.
    axs : TYPE
        DESCRIPTION.

    '''
    # TO DO: support two heatmaps above each other
    def update(i):
        label = 'timestep {0}'.format(i)
        print(label)
        # Update the line and the axes (with a new xlabel). Return a tuple of
        # "artists" that have to be redrawn for this frame.
        img = heatmap_single(ax=axs, df=dfs[i], title=titles[i],
                             x_labels=x_labels, y_labels=y_labels,
                             limits=limits, cmap_reverse=cmap_reverse)
        #ax.set_xlabel(label)
        return img, axs
    
    fig, axs = plt.subplots(nrows=1, ncols=1)
    if suptitle == '':
        title = titles[0]
    else:
        title = suptitle
    fig.set_tight_layout(True)
    # Query the figure's on-screen size and DPI. Note that when saving the figure to
    # a file, we need to provide a DPI for that separately.
    print('fig size: {0} DPI, size in inches {1}'.format(
        fig.get_dpi(), fig.get_size_inches()))
    
    # Plot a scatter that persists (isn't redrawn) and the initial line.
    '''img = heatmap_single(ax=axs, df=dfs[0], title=title, 
                         x_labels=x_labels, y_labels=y_labels, 
                         limits=limits, cmap_reverse=cmap_reverse)'''
    
    
    # FuncAnimation will call the 'update' function for each frame; here
    # animating over 10 frames, with an interval of 200ms between frames.
    anim = FuncAnimation(fig, update, frames=len(dfs), interval=2000)
    if save_to is not None:
        anim.save(save_to, dpi=80, writer='imagemagick')
    else:
        # plt.show() will just loop the animation forever.
        plt.show()
    
#detectorFileName = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/ITSoS_detectors.csv'
#detectorFileName = 'C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv'
"""
intervals = range(5*4,22*4)
detectors = ['QEWDE0010DES','QEWDE0020DES','QEWDE0030DES','QEWDE0040DES','QEWDE0050DES','QEWDE0060DES','QEWDE0070DES','QEWDE0090DES','QEWDE0100DES','QEWDE0110DES','QEWDE0120DES','QEWDE0130DES','QEWDE0140DES','QEWDE0150DES','QEWDE0170DES','QEWDE0180DES','QEWDE0190DES','QEWDE0200DES','QEWDE0210DES','QEWDE0220DES','QEWDE0230DES','QEWDE0240DES','QEWDE0250DES','QEWDE0260DES','QEWDE0270DES','QEWDE0280DES','QEWDE0290DES','QEWDE0300DES','QEWDE0310DES','QEWDE0340DES','QEWDE0350DES','QEWDE0360DES','QEWDE0370DES','QEWDE0380DES','QEWDE0390DES','QEWDE0400DES','QEWDE0410DES','QEWDE0420DES','QEWDE0430DES','QEWDE0440DES','QEWDE0450DES','QEWDE0460DES','QEWDE0470DES','QEWDE0480DES']
df2019 = readData('C:\\Computer\\work\\detector_data\\observed_data_2019_3.csv',
                  detectors=detectors, intervals=intervals)
df2020 = readData('C:\\Computer\\work\\detector_data\\observed_data_2020_3.csv',
                  detectors=detectors, intervals=intervals)
# find common detectors
df2019_filtered, df2020_filtered = equate_df_keys(df2019, df2020, 'eid')
#noIntervals = len(intervals)
fig1, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10,20), sharex=True) #, subplot_kw={'yticks': range(0,noIntervals,2)})
heatmap(ax1, '2019', df2019_filtered, 'speed')
heatmap(ax2, '2020', df2020_filtered, 'speed')
plt.tight_layout(pad=3)
#plt.tight_layout(rect=(0,0,0,3))
plt.show()

#=============================================================================


maxNoLanes = 6
noIntervals = 16
noDetectors = 42
# Observed Data
#==============
detectorFileName = 'C:/Aimsun Projects/CATTS8.4/calibration R1.0Cl2.0/ITSoS_detectors.csv'
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

detectors = detectorLocation.keys()
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


detectors = laneSpeed.keys()
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
"""