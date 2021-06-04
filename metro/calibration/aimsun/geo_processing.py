# -*- coding: utf-8 -*-
"""
Created on Wed Jul 15 13:47:58 2020

@author: islam
"""

import geopandas as gpd
import pandas as pd
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def read_here_data(file_name, chunk_size=1000000, start_t=0, end_t=23, int_len=60, count=50, date=None):
    res = []
    epoch_col = 'EPOCH-%iMIN' %int_len
    for chunk in pd.read_csv(file_name, chunksize=chunk_size):
        chunk = chunk[(chunk[epoch_col] < end_t) & (chunk[epoch_col] >= start_t)]
        chunk = chunk[chunk['GAPFILL'] == 'N']
        chunk = chunk[['LINK-DIR', 'DATE-TIME', epoch_col, 'LENGTH', 'SPDLIMIT', 'MEAN', 'COUNT']]
        res.append(chunk)
    res = pd.concat(res)
    res['DATE-TIME'] = pd.to_datetime(res['DATE-TIME'])
    res['WEEKDAY'] = res['DATE-TIME'].dt.weekday
    res = res[res.WEEKDAY.isin(range(5))]
    res = res.groupby(['LINK-DIR', epoch_col]).mean()
    res.index = res.index.map(lambda x: (int(x[0][:-1]), x[1]))
    res = res.reset_index(level=[epoch_col])
    return res

def calculate_zone_speed(speed, sec_and_zones, int_len=60):
    epoch_col = 'EPOCH-%iMIN' % int_len
    res = speed.merge(sec_and_zones, left_on='LINK-DIR', right_on='LINK_ID')
    res = res.groupby(['GTA06', epoch_col]).mean()
    res = res.reset_index(level=[epoch_col])
    res = gtha_zones_proj.merge(res, on='GTA06')
    res['speed_percent'] = res['MEAN'] / res['SPDLIMIT']
    return res

def calculate_sec_speed(speed, sec_and_zones, int_len=60):
    epoch_col = 'EPOCH-%iMIN' % int_len
    res = speed.merge(sec_and_zones, left_on='LINK-DIR', right_on='LINK_ID')
    res = res.groupby([epoch_col]).mean()
    res = res.reset_index(level=[epoch_col])
    res = gtha_zones_proj.merge(res, on='GTA06')
    res['speed_percent'] = res['MEAN'] / res['SPDLIMIT']
    return res

def animate_zone_speeds(speed, start_t=0, end_t=23, int_len=60, save_to=None):
    def update(i):
        title = 'Average(Speed/Speed Limit) %i:00 - %i:00' %(int(i+start_t), int(i+start_t+1))
        img = speed[speed[epoch_col]==(i+6)].plot(column='speed_percent', cmap='RdYlGn', ax=axs,
                                                      vmin=speed.speed_percent.min(),
                                                      vmax=speed.speed_percent.max())
        #axs.legend(img)
        axs.set_title(title)
        return img, axs
    epoch_col = 'EPOCH-%iMIN' % int_len
    fig, axs = plt.subplots(nrows=1, ncols=1)
    fig.set_tight_layout(True)
    anim = FuncAnimation(fig, update, frames=int(end_t-start_t), interval=2000)
    if save_to is not None:
        anim.save(save_to, dpi=80, writer='pillow')
    plt.show()

# read HERE shapefiles
# <class 'geopandas.geodataframe.GeoDataFrame'>
here_maps = gpd.read_file("C:/Computer/work/HERE Data/Navstreets (181F0)/streets.shp")
print(here_maps.crs, here_maps.total_bounds); here_maps.plot()
#highways = here_maps[here_maps.ST_NAME.str.startswith('HWY')]

# read TTS2016 zones
# <class 'geopandas.geodataframe.GeoDataFrame'>
# dataframe of rows/series of int, str, polygon
zones2016 = gpd.read_file("C:/Computer/work/2016 Zone Shapefiles/2006_TTS_TRAFFIC_ZONES_shp/tts06_83_region.shp")
#zones2016_2 = gpd.read_file("C:/Computer/work/2016 Zone Shapefiles/GTAModelV4Zones/V4_Zones.shp")
print(zones2016.crs, zones2016.total_bounds); zones2016.plot(column='REGION')
# grouping centroids to GTHA and non-GTHA ones (just for plotting)
zones2016_2groups = zones2016.to_crs(here_maps.crs)
zones2016_2groups['GTHA'] = zones2016_2groups['GTA06'].apply(lambda x:'GTHA Centroids' if x < 6000 else 'External Centroids')
zones2016_2groups.plot(column='GTHA', cmap='RdYlGn', legend=True, legend_kwds={'loc': 'lower right'})

# filter out non-GTHA zones
# <class 'geopandas.geodataframe.GeoDataFrame'>
gtha_zones = zones2016[zones2016.REGION <= 6] #gtha_zones = zones2016[zones2016.GTA06 < 6000]
gtha_zones.plot()

# project zones shp files to here shp files coordinates
# <class 'geopandas.geodataframe.GeoDataFrame'>
gtha_zones_proj = gtha_zones.to_crs(here_maps.crs)
# plot sections and zones (same coord sys)
fig, ax = plt.subplots(figsize = (20,16))
here_maps.plot(ax=ax, edgecolor='k')
gtha_zones_proj.plot(ax=ax, edgecolor='r')

# find sections within each zone
# <class 'geopandas.geodataframe.GeoDataFrame'>
sec_and_zones = gpd.sjoin(here_maps, gtha_zones_proj, how="inner", op="within") #sec_and_zones[sec_and_zones.GTA06==10]

# read HERE speed data
int_len = 60
start_t = 6 * 60 / int_len
end_t = 10 * 60 / int_len
here_stats_path = "C:\Computer\work\HERE Data"

# Toronto 60-min speeds
# <class 'geopandas.geodataframe.GeoDataFrame'>
sec_and_zones_tor = sec_and_zones[sec_and_zones.REGION == 1]
sec_and_zones_tor['FUNC_CLASS'] = sec_and_zones_tor['FUNC_CLASS'].apply(pd.to_numeric)
sec_and_zones_tor = sec_and_zones_tor[sec_and_zones_tor['FUNC_CLASS'] <= 5]
# <class 'pandas.core.frame.DataFrame'>
speed_60_toronto = read_here_data(os.path.join(here_stats_path, 'Toronto/HERE_DA_117855_00000.csv'),
                                  start_t=start_t, end_t=end_t, int_len=int_len)
# <class 'geopandas.geodataframe.GeoDataFrame'>
speed_60_toronto_zones = calculate_zone_speed(speed_60_toronto, sec_and_zones_tor, int_len=int_len)
speed_60_toronto_zones.plot(column='speed_percent', legend=True, cmap='RdYlGn', vmin=speed_60_toronto_zones.speed_percent.min(),
                             vmax=speed_60_toronto_zones.speed_percent.max())

animate_zone_speeds(speed = speed_60_toronto_zones, start_t=6, end_t=10,
                    save_to='C:/Computer/work/SOW4/y1_presentation/here_speed_by_zone_toronto2.gif')
# York 60-min speeds
sec_and_zones_york = sec_and_zones[sec_and_zones.REGION == 3]
sec_and_zones_york['FUNC_CLASS'] = sec_and_zones_york['FUNC_CLASS'].apply(pd.to_numeric)
sec_and_zones_york = sec_and_zones_york[sec_and_zones_york['FUNC_CLASS'] <= 5]

speed_60_york = read_here_data(os.path.join(here_stats_path, 'York/HERE_DA_117860_00000.csv'),
                                  start_t=start_t, end_t=end_t, int_len=int_len)

speed_60_york_zones = calculate_zone_speed(speed_60_york, sec_and_zones_york, int_len=int_len)
speed_60_york_zones.plot(column='speed_percent', legend=True, cmap='RdYlGn', vmin=speed_60_york_zones.speed_percent.min(),
                             vmax=speed_60_york_zones.speed_percent.max())

speed_60_york_secs = calculate_sec_speed(speed_60_york, sec_and_zones_york, int_len=int_len)
speed_60_york_secs.plot(column='speed_percent', legend=True, cmap='RdYlGn', vmin=speed_60_york_secs.speed_percent.min(),
                             vmax=speed_60_york_secs.speed_percent.max())
# Toronto & York Region
toronto_and_york = pd.concat([speed_60_toronto_zones, speed_60_york_zones])
toronto_and_york.plot(column='speed_percent', legend=True, cmap='RdYlGn', vmin=toronto_and_york.speed_percent.min(),
                             vmax=toronto_and_york.speed_percent.max())
animate_zone_speeds(speed = toronto_and_york, start_t=6, end_t=10,
                    save_to='C:/Computer/work/SOW4/y1_presentation/here_speed_by_zone_toronto_and_york.gif')
#======================================================================

speed_60_toronto = pd.read_csv(os.path.join(here_stats_path, 'Toronto/HERE_DA_117855_00000.csv'))
speed_60_toronto = speed_60_toronto[speed_60_toronto. >= start_t & speed_60_toronto. < end]
speed_60_durham = pd.read_csv(os.path.join(here_stats_path, 'Durham/HERE_DA_117977_00000.csv'))
speed_60_york = pd.read_csv(os.path.join(here_stats_path, 'York/HERE_DA_117860_00000.csv'))
speed_60_peel = pd.read_csv(os.path.join(here_stats_path, 'Peel/HERE_DA_117849_00000.csv'))
speed_60_halton = pd.read_csv(os.path.join(here_stats_path, 'Halton/HERE_DA_117838_00000.csv'))
#speed_60_hamilton = pd.read_csv(os.path.join(here_stats_path, 'Hamilton/HERE_DA_117845_00000.csv'))

speed_60 = pd.concat([speed_60_toronto, speed_60_durham, speed_60_york, speed_60_peel, speed_60_halton])#, speed_60_hamilton])
print(speed_60.head)

geo_speed = pd.join(speed_60, sec_and_zones, on="LINK")
