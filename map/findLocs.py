import pandas as pd
import numpy as np
from geopy.distance import geodesic
from scipy.optimize import linprog
import os 
import folium
import requests
import json
import time
import progressbar
from requests.adapters import HTTPAdapter
from console_progressbar import ProgressBar
from tqdm import tqdm
from urllib.parse import urlparse
import concurrent.futures

def distance_calc (url):

    o = urlparse(url)

    if(o.path[18:] == o.params):
        with open("distances.csv", 'a') as file:    
            file.write("0.000\n")
    else:
        s = requests.Session()
        s.mount(url, HTTPAdapter(max_retries=10))
        r = s.get(url, timeout=10)
        res = r.json()
        distance = round(res['routes'][0]['distance']/1000,3)

        with open("distances.csv", 'a') as file:    
            file.write(f"{distance}\n")
            #time.sleep(2)
    #with open('distance.json', 'w') as json_file: json.dump(res, json_file, indent = 4)

    return

def FindPopularSpots():

    '''
    This function will read a csv file and will create a csv that Mosel can read
   with the most popular paths and stations in a certain week. 
   The csv files will be output in the same directory as the working directory of
   this Python script

   input:
   csvFile = the csv file path containing the accumulated monthly data 
               i.e. "C:\Documents\08.csv"
   Day/Month selector = a flag that will indicate the function to calculate the
                demandas and routes using either previous day or previous week data.
                0 for day, and 1 for month.
   weekNumber = required week number for calculating the demands and routes using
                the OSRM API
   weekDay = Previous day for calculating the demands and routes using the OSRM API

   Output: None
    '''

    header = "Find Locations Python script"
    print(header)
    print("="*len(header))
    print("This script will create the appropriate csv files for Mosel consumption \n")
    print("Enter the full path csv file location (i.e. C:/Documents/08.csv). Press Enter when done.")
    csvFile = input()
    print("How do you want to calculate the demands and paths? Previous day: 0. Previous week: 1")
    selector = int(input())

    if(type(selector) != int):
        print("Invalid value for the selection")
        return

    elif(selector == 0):
        print("Enter the day (i.e. for the 2nd of a month, type 02). Press Enter when done.")
        monthDay = int(input())

        if(type(monthDay) != int):
            print("The number is invalid. Try again")
            return

    elif(selector == 1):
        print("Enter the week number. Consider that there are 52 weeks in a year. Press Enter when done.")
        weekNumber = int(input())

        if(type(weekNumber) != int):
            print("The number is invalid. Try again")
            return

    curDir = os.getcwd()
    filePath = os.path.abspath(csvFile)
    fileName = os.path.basename(csvFile)

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    rawData = pd.read_csv(filePath, parse_dates = [1,2])

    # Ensure the timestamps are true timestamps
    start_date = pd.to_datetime(rawData['started_at'])
    end_date = pd.to_datetime(rawData['ended_at'])

    # Add Day of the Month, Day of the Week and Week number as columns
    rawData['weekday_start_at'] = pd.to_datetime(rawData['started_at']).dt.dayofweek
    rawData['weekday_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.dayofweek
    rawData['week_start_at'] = pd.to_datetime(rawData['started_at']).dt.isocalendar().week
    rawData['week_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.isocalendar().week
    rawData['monthday_start_at'] = pd.to_datetime(rawData['started_at']).dt.day
    rawData['monthday_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.day

    if(selector ==0):
        #Get the previous day data
        latestData = rawData.loc[rawData['monthday_start_at'] == int(monthDay)]
        print(f"Calculating paths for day {monthDay}")
    elif(selector == 1):
        # Get the latest week
        latestData = rawData.loc[rawData['week_start_at'] == int(weekNumber)]
        print(f"Calculating paths for week {weekNumber}")

    # Add distance and duration
    startCoordinates = latestData[['start_station_longitude', 'start_station_latitude']].to_numpy()
    endCoordinates = latestData[['end_station_longitude', 'end_station_latitude']].to_numpy()
    
    datapoints = startCoordinates.shape[0]
    urls = []

    bar = progressbar.ProgressBar(maxval=int(datapoints), \
    widgets=[progressbar.Bar('#', '|', '|'), ' ', progressbar.Percentage()])
    bar.start()
    
    for i in range(datapoints):

        baseUrl = "http://router.project-osrm.org/route/v1/driving/"

        start = f"{round(startCoordinates[i,0], 6)},{round(startCoordinates[i,1], 6)}"
        end = f"{round(endCoordinates[i,0], 6)},{round(endCoordinates[i,1], 6)}"
        url = f"{baseUrl}{start};{end}?overview=false"

        urls.append(url)
        bar.update(i+1)

    bar.finish()

    print("Computing the distances")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        #executor.map(distance_calc, urls)
        results = list(tqdm(executor.map(distance_calc, urls), total=len(urls)))

    print(time.perf_counter())
    print(results)

    #weeklyData.loc(['distance'] = distance
    latestData = latestData.assign(distance=1)
    latestData = latestData.assign(duration=1)

    # Paths export
    pathList = pd.DataFrame({'count': 
                latestData.groupby(["start_station_id", "end_station_id", "distance",
                "start_station_name", "end_station_name", "start_station_latitude", 
                "start_station_longitude", "end_station_latitude", 
                "end_station_longitude"]).size()}).reset_index()
    sortedPathList = pathList.sort_values(by=['count'], ascending = False)

    moselPath = pd.DataFrame({'count': latestData.groupby(["start_station_id", 
                "end_station_id", "distance"]).size()}).reset_index()
    moselPath = moselPath.sort_values(by=['count'], ascending = False)

    # Start Station
    hotspotStart = pd.DataFrame({'count': latestData.groupby(["start_station_id", 
                    "start_station_name"]).size()}).reset_index()
    sortedHotspotStart = hotspotStart.sort_values(by=['count'], ascending = False)

    # Destination Station
    hotspotDestination = pd.DataFrame({'count': latestData.groupby(["end_station_id", 
                         "end_station_name"]).size()}).reset_index()
    sortedHotspotDestionation = hotspotDestination.sort_values(by=['count'], 
                            ascending = False)

    # Generate the csv files for the required week
    suffix = f"_week{weekNumber}.csv"

    pathList.to_csv(os.path.join(curDir, "pathList" + suffix), index = False)
    moselPath.to_csv(os.path.join(curDir, "moselPath" + suffix), index = False)
    hotspotStart.to_csv(os.path.join(curDir, "hotspotStart" + suffix), index = False)
    hotspotDestination.to_csv(os.path.join(curDir, "hotspotDestination" + suffix), index = False)

    sortedPathList.to_csv(os.path.join(curDir, "sorted_pathList" + suffix), index = False)
    sortedHotspotStart.to_csv(os.path.join(curDir, "sorted_hotspotStart" + suffix), index = False)
    sortedHotspotDestionation.to_csv(os.path.join(curDir, "sorted_hotspotDestination" + suffix), index = False)

    print(f"Created the following csv files on the {curDir} directory:")
    print(f"pathList{suffix}")
    print(f"moselPath{suffix}")
    print(f"hotspotStart{suffix}")
    print(f"hotspotDestination{suffix}")
    print(f"sorted_pathList{suffix}")
    print(f"sorted_hotspotStart{suffix}")
    print(f"sorted_hotspotDestination{suffix}")

    return 

FindPopularSpots()

## Map 
#world_map = folium.Map()
#world_map

#edinLat = 55.9533 
#edinLong = -3.1883
#edinMap = folium.Map(location=[edinLat, edinLong], zoom_start=12, tiles='Stamen Toner')
#edinMap