import pandas as pd
import numpy as np
import itertools
from geopy.distance import geodesic
from scipy.optimize import linprog
import os 
import folium
import requests
import json
import csv
import time
import progressbar
from requests.adapters import HTTPAdapter
from console_progressbar import ProgressBar
from tqdm import tqdm
from urllib.parse import urlparse
import concurrent.futures

def distance_calc (url):

    timestr = time.strftime("%d%m%Y")
    csvName = f"distances_{timestr}.csv"

    #o = urlparse(url)

    #if(o.path[18:] == o.params):
    #    with open(csvName, 'a') as file:    
    #        file.write("0.000\n")
    #else:
    time.sleep(5)
    s = requests.Session()
    s.mount(url, HTTPAdapter(max_retries=1))
    r = s.get(url, timeout=1)
    res = r.json()

    #with open('distance.json', 'w') as json_file: json.dump(res, json_file, indent = 4)

    distance = round(res['routes'][0]['distance']/1000,3)

    with open(csvName, 'a') as file:    
        file.write(f"{distance}\n")

    return

def tsp_calc (url):

    time.sleep(5)

    s = requests.Session()
    s.mount(url, HTTPAdapter(max_retries=20))
    r = s.get(url, timeout=20)
    res = r.json()

    #with open('tsp.json', 'w') as json_file: 
    #    json.dump(res, json_file, indent = 4)

    distance = round(res['trips'][0]['distance']/1000,3)
    duration = round(res['trips'][0]['duration']/60,3)
    leg1 = res['waypoints'][1]['waypoint_index']
    leg2 = res['waypoints'][2]['waypoint_index']

    timestr = time.strftime("%d%m%Y")
    csvName = f"tsp_nCr_{timestr}.csv"

    with open(csvName, 'a') as file:    
         file.write(f"{distance},{duration},0,{leg1},{leg2}\n")
         #time.sleep(2)

    return

def Combinations():
    header = "Find Combinations Python script"
    print(header)
    print("="*len(header))
    print("This script will create the combination csv files for Mosel consumption \n")
    print("Enter the full path csv file location (i.e. C:/Documents/08.csv). Press Enter when done.")
    csvFile = input()
       
    curDir = os.getcwd()
    filePath = os.path.abspath(csvFile)
    fileName = os.path.basename(csvFile)

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    rawData = pd.read_csv(filePath, parse_dates = [1,2], 
              dtype={'start_station_longitude': float, 'start_station_latitude': float, 
                     'end_station_longitude': float, 'end_station_latitude': float})

    rawData['start_station_longitude'] = (rawData['start_station_longitude'].round(5)).astype(str)
    rawData['start_station_latitude'] = (rawData['start_station_latitude'].round(5)).astype(str) 
    rawData['end_station_longitude'] = (rawData['end_station_longitude'].round(5)).astype(str)
    rawData['end_station_latitude'] = (rawData['end_station_latitude'].round(5)).astype(str)

    # Get coordinates in a suitable format for OSRM
    rawData['pickupCoordinates'] = rawData[['start_station_longitude', 'start_station_latitude']].apply(lambda x: ','.join(x), axis=1)
    rawData['dropCoordinates'] = rawData[['end_station_longitude', 'end_station_latitude']].apply(lambda x: ','.join(x), axis=1)
 
    groupData = pd.DataFrame({'count': 
                rawData.groupby(["pickupCoordinates","start_station_id", "start_station_name"]).size()}).reset_index()
    groupData.to_csv("groupData.csv", index = False, header = True)
    coordinates = groupData["pickupCoordinates"].tolist()

    nCr = list(itertools.combinations(groupData['pickupCoordinates'], 2))

#    out = csv.writer(open("nCr.csv","w"), delimiter=',',quoting=csv.QUOTE_ALL)

    with open('nCr.csv', 'w', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerows(nCr)

#    out.writerow(data)

    tspUrls = []
    depot = "-3.157453,55.973447"

    for i in range(0, len(nCr)):
        tspUrl = "http://127.0.0.1:5000/trip/v1/driving/"
        group = f"{nCr[i][0]};{nCr[i][1]}"
        pickupUrl = f"{tspUrl}{depot};{group}?source=first"
        tspUrls.append(pickupUrl)

    print(tspUrls[0])

    print("Computing TSP")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(tsp_calc, tspUrls), total=len(tspUrls)))    

    print(time.perf_counter())

    return

Combinations()


def Run():

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
    print("Do you want to calculate the TSP? 0: No. 1: Yes")
    tsp = int(input())

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

    if(tsp == 1):
        print("What time? Use 24 h format. For 4 pm use 16")
        hour = int(input())
        
    curDir = os.getcwd()
    filePath = os.path.abspath(csvFile)
    fileName = os.path.basename(csvFile)

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    rawData = pd.read_csv(filePath, parse_dates = [1,2], 
              dtype={'start_station_longitude': float, 'start_station_latitude': float, 
                     'end_station_longitude': float, 'end_station_latitude': float})

    rawData['start_station_longitude'] = (rawData['start_station_longitude'].round(5)).astype(str)
    rawData['start_station_latitude'] = (rawData['start_station_latitude'].round(5)).astype(str) 
    rawData['end_station_longitude'] = (rawData['end_station_longitude'].round(5)).astype(str)
    rawData['end_station_latitude'] = (rawData['end_station_latitude'].round(5)).astype(str)

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
    rawData['hour_started_at'] = pd.to_datetime(rawData['started_at']).dt.hour
    rawData['hour_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.hour

    # Get coordinates in a suitable format for OSRM
    rawData['pickupCoordinates'] = rawData[['start_station_longitude', 'start_station_latitude']].apply(lambda x: ','.join(x), axis=1)
    rawData['dropCoordinates'] = rawData[['end_station_longitude', 'end_station_latitude']].apply(lambda x: ','.join(x), axis=1)

    if(selector ==0):
        #Get the previous day data
        latestData = rawData.loc[rawData['monthday_start_at'] == int(monthDay)]
        print(f"Calculating paths for day {monthDay}")
    elif(selector == 1):
        # Get the latest week
        latestData = rawData.loc[rawData['week_start_at'] == int(weekNumber)]
        print(f"Calculating paths for week {weekNumber}")

    if(tsp == 1):
        pickupData = rawData.loc[rawData['hour_started_at'] == int(hour)]
        dropData = rawData.loc[rawData['hour_ended_at'] == int(hour)]

        groupPickup = pd.DataFrame({'count': pickupData.groupby(["start_station_id", 
                    "start_station_name", 'pickupCoordinates']).size()}).reset_index()
        groupDrop = pd.DataFrame({'count': dropData.groupby(["end_station_id", 
                    "end_station_name", 'dropCoordinates']).size()}).reset_index()

        topPickup = groupPickup.nlargest(10,'count')
        topDrop = groupDrop.nlargest(10,'count')

        pick = f"{topPickup['pickupCoordinates'].values[1]};{topPickup['pickupCoordinates'].values[2]};{topPickup['pickupCoordinates'].values[3]};{topPickup['pickupCoordinates'].values[4]};{topPickup['pickupCoordinates'].values[5]};{topPickup['pickupCoordinates'].values[6]};{topPickup['pickupCoordinates'].values[7]};{topPickup['pickupCoordinates'].values[8]};{topPickup['pickupCoordinates'].values[9]}"
        drop = f"{topDrop['dropCoordinates'].values[1]};{topDrop['dropCoordinates'].values[2]};{topDrop['dropCoordinates'].values[3]};{topDrop['dropCoordinates'].values[4]};{topDrop['dropCoordinates'].values[5]};{topDrop['dropCoordinates'].values[6]};{topDrop['dropCoordinates'].values[7]};{topDrop['dropCoordinates'].values[8]};{topDrop['dropCoordinates'].values[9]}"

        depot = "-3.157453,55.973447"

        tspUrl = "http://127.0.0.1:5000/trip/v1/driving/"
        pickupUrl = f"{tspUrl}{depot};{pick}?source=first"
        dropUrl = f"{tspUrl}{depot};{drop}?source=first"

        tspUrls = [pickupUrl,dropUrl]

        print("Computing TSP")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(tqdm(executor.map(tsp_calc, tspUrls), total=len(tspUrls)))    

        print(time.perf_counter())

    elif(tsp ==0):

        #Calculate the trips
        tripList = pd.DataFrame({'count': 
                latestData.groupby(["start_station_id", "end_station_id",
                "start_station_name", "end_station_name", "start_station_latitude", 
                "start_station_longitude", "end_station_latitude", 
                "end_station_longitude"]).size()}).reset_index()

        # Add distance and duration
        pickupCoordinates = tripList[["start_station_longitude","start_station_latitude"]].to_numpy()
        dropCoordinates = tripList[["end_station_longitude","end_station_latitude"]].to_numpy()
    
        datapoints = tripList.shape[0]
        urls = []

        bar = progressbar.ProgressBar(maxval=int(datapoints), \
        widgets=[progressbar.Bar('#', '|', '|'), ' ', progressbar.Percentage()])
        bar.start()
    
        for i in range(datapoints):

            #baseUrl = "http://router.project-osrm.org/route/v1/driving/" #demo server
            distanceUrl = "http://127.0.0.1:5000/route/v1/driving/" #local server

            pickup = f"{pickupCoordinates[i,0]},{pickupCoordinates[i,1]}"
            drop = f"{dropCoordinates[i,0]},{dropCoordinates[i,1]}"

            url = f"{distanceUrl}{pickup};{drop}?overview=false"
            urls.append(url)
            bar.update(i+1)

        bar.finish()

        print("Computing the distances")

        with concurrent.futures.ThreadPoolExecutor() as executor:
        #executor.map(distance_calc, urls)
            results = list(tqdm(executor.map(distance_calc, urls), total=len(urls)))

        print(time.perf_counter())

        distances = pd.read_csv("distances.csv")
        #latestData.join(pd.DataFrame(distances))

    # Paths export
    pathList = pd.DataFrame({'count': 
                latestData.groupby(["start_station_id", "end_station_id",
                "start_station_name", "end_station_name", "start_station_latitude", 
                "start_station_longitude", "end_station_latitude", 
                "end_station_longitude"]).size()}).reset_index()
    sortedPathList = pathList.sort_values(by=['count'], ascending = False)

    moselPath = pd.DataFrame({'count': latestData.groupby(["start_station_id", 
                "end_station_id"]).size()}).reset_index()
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

    # Generate the csv files for the required timeframe

    if(selector == 0):
        suffix = f"_day{monthDay}.csv"
    elif(selector ==1):
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



Run()

## Map 
#world_map = folium.Map()
#world_map

#edinLat = 55.9533 
#edinLong = -3.1883
#edinMap = folium.Map(location=[edinLat, edinLong], zoom_start=12, tiles='Stamen Toner')
#edinMap