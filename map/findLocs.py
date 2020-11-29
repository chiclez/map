import concurrent.futures
from console_progressbar import ProgressBar
import csv
from geopy.distance import geodesic
import itertools
import json
import numpy as np
import os 
import pandas as pd
import progressbar
import requests
from requests.adapters import HTTPAdapter
import time
from tqdm import tqdm
from urllib.parse import urlparse

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

def tsp_calc (url, combination):

    time.sleep(5)

    s = requests.Session()
    s.mount(url, HTTPAdapter(max_retries=20))
    r = s.get(url, timeout=20)
    res = r.json()

    #with open('tsp.json', 'w') as json_file: 
    #    json.dump(res, json_file, indent = 4)

    distance = round(res['trips'][0]['distance']/1000,2)
    duration = round(res['trips'][0]['duration']/60,2)
    leg1 = res['waypoints'][1]['waypoint_index']
    leg2 = res['waypoints'][2]['waypoint_index']

    timestr = time.strftime("%d%m%Y")
    csvName = f"tsp_nCr_{timestr}.csv"

    with open(csvName, 'a') as file:    
         file.write(f"{combination},{distance},{duration},0,{leg1},{leg2}\n")
         #time.sleep(2)

    return

def PopularSpotsRoutes():

    '''
    This function will read a csv file and will create a csv that Mosel can read
   with the most popular routes and stations in a certain week. 
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

def Combinations():
    '''
    This script will calculate the combinations for the Travelling salesman problem
    for Edinburgh's JustEat bike sharing service using a multithreading approach.
    It computes the nC2 combinations, where n = number of stations found in the
    input file and r is fixed to be 2 (to avoid crashing our server...)
    This script heavily relies on a Docker OSRM server as well... 

    Input:
    open_data csv: This can be found in Edinburgh's Just Eat site

    Output:
    tsp.csv: A csv file with all the required information for Mosel
            i.e. distance, duration, node visits
    '''

    header = "Travelling Salesman Problem (TSP) Combinations"
    print(header)
    print("="*len(header))
    print("Enter the full path csv file location (i.e. C:\Documents\08.csv). Press Enter when done.")
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
    nCr_stations = list(itertools.combinations(groupData['start_station_id'], 2))

    with open('nCr.csv', 'w', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerows(nCr)

    with open('nCr_stations.csv', 'w', newline='\n') as stations:
        writer = csv.writer(stations)
        writer.writerows(nCr_stations)

    tspUrls = []
    depot = "-3.157453,55.973447"

    for i in range(0, len(nCr)):
        tspUrl = "http://127.0.0.1:5000/trip/v1/driving/"
        group = f"{nCr[i][0]};{nCr[i][1]}"
        pickupUrl = f"{tspUrl}{depot};{group}?source=first"

        tspUrls.append(pickupUrl)

    print("Combinations found: {len(tspUrls)}")

    combinations = [i for i in range(0, len(tspUrls))]

    print("Computing TSP for each combination")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(tsp_calc, tspUrls, combinations), total=len(tspUrls)))    

    print("Done")
    print(f"Computing time: {time.perf_counter()}")

    return

def Dat_NetAdd(processedData):

    # Generate the appropriate dataframe form
    hourlyStart = pd.DataFrame({'startFreq': processedData.groupby(["start_station_id", 
                    "start_station_name", "hour_started_at"]).size()}).reset_index()

    hourlyEnd = pd.DataFrame({'endFreq': processedData.groupby(["end_station_id", 
                    "end_station_name", "hour_ended_at"]).size()}).reset_index()

    hourlyStart.rename(columns = {"start_station_id":"station_id", "hour_started_at":"hour"}, inplace = True)
    hourlyEnd.rename(columns = {"end_station_id":"station_id", "hour_ended_at":"hour"}, inplace = True)

    preDat = pd.merge(hourlyStart,hourlyEnd, how = 'outer', left_on=['station_id','hour'], right_on = ['station_id','hour'])
    preDat = preDat.fillna(0)

    preDat["net_add"] = preDat["endFreq"] - preDat["startFreq"]

    datFile = preDat[["station_id", "hour", "net_add"]]
    datFile = datFile.sort_values(by=["station_id", "hour"], ascending = True)

    net_add = datFile.pivot_table(index=['station_id'], columns=['hour'],
                     values='net_add', aggfunc='first', fill_value=0)

    return net_add

def Dat_BikeInit(net_add):

    init = np.zeros((net_add.shape[0],24))

    for i in range(0, init.shape[0]):
        init[i,0] = 5  

    bikeInit = pd.DataFrame(data = init)

    return bikeInit

def Dat_CityDivision(processedData):

    # Generate the appropriate dataframe form
    netStart = pd.DataFrame({'startFreq': processedData.groupby(["start_station_id", 
                    "start_station_name", "start_station_latitude", 
                    "start_station_longitude"]).size()}).reset_index()

    netEnd = pd.DataFrame({'endFreq': processedData.groupby(["end_station_id", 
                    "end_station_name", "end_station_latitude", 
                    "end_station_longitude"]).size()}).reset_index()

    netStart.rename(columns = 
                       {"start_station_id":"station_id", 
                        "start_station_latitude": "Latitude", 
                        "start_station_longitude": "Longitude"}, 
                       inplace = True)

    netEnd.rename(columns = 
                     {"end_station_id":"station_id",
                      "end_station_latitude": "Latitude", 
                      "end_station_longitude": "Longitude"}, 
                     inplace = True)

    preDat = pd.merge(netStart,netEnd, how = 'outer', 
                      left_on=['station_id', 'Latitude', 'Longitude'], 
                      right_on = ['station_id', 'Latitude', 'Longitude'])
    preDat = preDat.fillna(0)

    preDat["net_flow_in"] = ((preDat["endFreq"] - preDat["startFreq"]) > 0).astype(int)
    preDat["net_flow_out"] = ((preDat["startFreq"] - preDat["endFreq"]) > 0).astype(int)

    datFile = preDat[["station_id", "Latitude", "Longitude", "startFreq", 
                      "endFreq", "net_flow_in", "net_flow_out"]]
    datFile = datFile.sort_values(by=["startFreq", "endFreq"], ascending = True)

    latitude = datFile["Latitude"]
    longitude = datFile["Longitude"]
    net_flow_in = datFile["net_flow_in"]
    net_flow_out = datFile["net_flow_out"]
    station_id = datFile["station_id"]

    return latitude, longitude, net_flow_in, net_flow_out, station_id

def Regions(divisionFile):

    allRegions = pd.read_csv(divisionFile, dtype={"region": int})
    allRegions = allRegions.sort_values(by=["region"])

    region1 = allRegions.loc[allRegions["region"] == 1]
    region2 = allRegions.loc[allRegions["region"] == 2]
    region3 = allRegions.loc[allRegions["region"] == 3]

    return region1, region2, region3

def OutputNet_Add(netAdd, bikeInit,region):

    curDir = os.getcwd()
    
    netName = f"net_add_region{region}.dat"
    bikeName = f"bike_init_region{region}.dat"

    netAddFile = os.path.join(curDir, netName)
    bikeInitFile = os.path.join(curDir, bikeName)

    netAdd.to_csv(netAddFile, index = False, header = False, sep = " ")
    bikeInit.to_csv(bikeInitFile, index = False, header = False, sep = " ")
    
    f1 = open(bikeInitFile)

    with open(netAddFile, "r+") as f:
         old = f.read() # read everything in the file
         bike_init = f1.read()
         f.seek(0) # rewind
         f.write("net_add: [" + old + "]\n") # write the new line before
         f.write("ini_bikes: [" + bike_init + "]")

    f1.close()
    os.remove(bikeInitFile)

    print(f"Created {netName}")

    return

def DataProcessing(filePath, weekNumber, divisionFile, tsp):

    '''
    Common DataProcessing instance for all functions
    '''

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

    #Normal coordinates, for the rest of the world.
    rawData['pickupCoordinates_normal'] = rawData[['start_station_latitude', 'start_station_longitude']].apply(lambda x: ','.join(x), axis=1)
    rawData['dropCoordinates_normal'] = rawData[['end_station_latitude', 'end_station_longitude']].apply(lambda x: ','.join(x), axis=1)

    # Get coordinates in a suitable format for OSRM
    rawData['pickupCoordinates'] = rawData[['start_station_longitude', 'start_station_latitude']].apply(lambda x: ','.join(x), axis=1)
    rawData['dropCoordinates'] = rawData[['end_station_longitude', 'end_station_latitude']].apply(lambda x: ','.join(x), axis=1)

    if(tsp == 0):
    # Get the user-selected week
        processedData = rawData.loc[rawData['week_start_at'] == int(weekNumber)]
    else:
        processedData = pd.DataFrame({'count': 
                rawData.groupby(["pickupCoordinates","start_station_id", "start_station_name"]).size()}).reset_index()

    return processedData

def Tsp():
    '''
    This script will calculate the combinations for the Travelling salesman problem
    for Edinburgh's JustEat bike sharing service using a multithreading approach.
    It computes the nC2 combinations, where n = number of stations found in the
    input file and r is fixed to be 2 (to avoid crashing our server...)
    This script heavily relies on a Docker OSRM server as well... 

    Input:
    open_data csv: This can be found in Edinburgh's Just Eat site

    Output:
    tsp.csv: A csv file with all the required information for Mosel
            i.e. distance, duration, node visits
    '''

    header = "Travelling Salesman Problem (TSP) Combinations"
    print(header)
    print("-"*len(header))
    print("Enter the full path csv file location (i.e. C:\Documents\08.csv). Press Enter when done.")
    csvFile = input()
       
    curDir = os.getcwd()
    filePath = os.path.abspath(csvFile)
    fileName = os.path.basename(csvFile)

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    groupData = DataProcessing(filePath, divisionFile = 0, weekNumber= 0, tsp = 1)

    print("Hi. I'm  here!")
    print(groupData.head())

    groupData.to_csv("groupData.csv", index = False, header = True)
    coordinates = groupData["pickupCoordinates"].tolist()

    nCr = list(itertools.combinations(groupData['pickupCoordinates'], 2))
    nCr_stations = list(itertools.combinations(groupData['start_station_id'], 2))

    with open('nCr.csv', 'w', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerows(nCr)

    with open('nCr_stations.csv', 'w', newline='\n') as stations:
        writer = csv.writer(stations)
        writer.writerows(nCr_stations)

    tspUrls = []
    depot = "-3.157453,55.973447"

    for i in range(0, len(nCr)):
        tspUrl = "http://127.0.0.1:5000/trip/v1/driving/"
        group = f"{nCr[i][0]};{nCr[i][1]}"
        pickupUrl = f"{tspUrl}{depot};{group}?source=first"

        tspUrls.append(pickupUrl)

    print("Combinations found: {len(tspUrls)}")

    combinations = [i for i in range(0, len(tspUrls))]

    print("Computing TSP for each combination")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(tsp_calc, tspUrls, combinations), total=len(tspUrls)))    

    print("Done")
    print(f"Computing time: {time.perf_counter()}")

    return

def NetAdd():

    '''
    This function will read a csv file and will create a csv that Mosel can read
   with the most popular routes and stations in a certain week. 
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

   Output: None
    '''

    header = "Net_add script"
    print(header)
    print("-"*len(header))
    print("Enter the full path csv file location (i.e. C:/Documents/08.csv). Press Enter when done.")
    csvFile = input()
    print("Enter the full path txt file location containing the city division (i.e. C:/Documents/split.txt). Press Enter when done.")
    divisionFile = input()
    print("Enter the week number. Consider that there are 52 weeks in a year. Press Enter when done.")
    weekNumber = int(input())

    if(type(weekNumber) != int):
        print("The number is invalid. Try again")
        return

    curDir = os.getcwd()
    filePath = os.path.abspath(csvFile)
    fileName = os.path.basename(csvFile)

    divisionPath = os.path.abspath(divisionFile)
    divisioName = os.path.basename(divisionFile)

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    if os.path.isfile(divisionFile) != True:
        print (f"{divisionFile} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    region1, region2, region3 = Regions(divisionFile)
    latestData = DataProcessing(filePath, weekNumber, divisionFile, tsp = 0)
    
    netAdd = Dat_NetAdd(latestData)

    netAdd_region1 = pd.merge(netAdd, region1, how = "inner", on = ["station_id"])
    netAdd_region1 = netAdd_region1.drop(columns = ["station_id", "region"])
    bikeInit_region1 = Dat_BikeInit(netAdd_region1)

    netAdd_region2 = pd.merge(netAdd, region2, how = "inner", on = ["station_id"])
    netAdd_region2 = netAdd_region2.drop(columns = ["station_id", "region"])
    bikeInit_region2 = Dat_BikeInit(netAdd_region2)

    netAdd_region3 = pd.merge(netAdd, region3, how = "inner", on = ["station_id"])
    netAdd_region3 = netAdd_region3.drop(columns = ["station_id", "region"])
    bikeInit_region3 = Dat_BikeInit(netAdd_region3)

    # Generate the dat files for the required timeframe

    fileRegion1 = OutputNet_Add(netAdd_region1, bikeInit_region1, 1)
    fileRegion2 = OutputNet_Add(netAdd_region2, bikeInit_region2, 2)
    fileRegion3 = OutputNet_Add(netAdd_region3, bikeInit_region3, 3)

    ## Paths export
    #pathList = pd.DataFrame({'count': 
    #            latestData.groupby(["start_station_id", "end_station_id",
    #            "start_station_name", "end_station_name", "start_station_latitude", 
    #            "start_station_longitude", "end_station_latitude", 
    #            "end_station_longitude"]).size()}).reset_index()
    #sortedPathList = pathList.sort_values(by=['count'], ascending = False)

    #moselPath = pd.DataFrame({'count': latestData.groupby(["start_station_id", 
    #            "end_station_id"]).size()}).reset_index()
    #moselPath = moselPath.sort_values(by=['count'], ascending = False)

    ## Start Station
    #hotspotStart = pd.DataFrame({'count': latestData.groupby(["start_station_id", 
    #                "start_station_name"]).size()}).reset_index()
    #sortedHotspotStart = hotspotStart.sort_values(by=['count'], ascending = False)

    ## Destination Station
    #hotspotDestination = pd.DataFrame({'count': latestData.groupby(["end_station_id", 
    #                     "end_station_name"]).size()}).reset_index()
    #sortedHotspotDestionation = hotspotDestination.sort_values(by=['count'], 
    #                        ascending = False)

    #pathList.to_csv(os.path.join(curDir, "pathList" + suffix), index = False)
    #moselPath.to_csv(os.path.join(curDir, "moselPath" + suffix), index = False)
    #hotspotStart.to_csv(os.path.join(curDir, "hotspotStart" + suffix), index = False)
    #hotspotDestination.to_csv(os.path.join(curDir, "hotspotDestination" + suffix), index = False)

    #sortedPathList.to_csv(os.path.join(curDir, "sorted_pathList" + suffix), index = False)
    #sortedHotspotStart.to_csv(os.path.join(curDir, "sorted_hotspotStart" + suffix), index = False)
    #sortedHotspotDestionation.to_csv(os.path.join(curDir, "sorted_hotspotDestination" + suffix), index = False)

    #print(f"Created the following csv files on the {curDir} directory:")
    #print(f"pathList{suffix}")
    #print(f"moselPath{suffix}")
    #print(f"hotspotStart{suffix}")
    #print(f"hotspotDestination{suffix}")
    #print(f"sorted_pathList{suffix}")
    #print(f"sorted_hotspotStart{suffix}")
    #print(f"sorted_hotspotDestination{suffix}")

    return 

def CityDivision():

    '''
    This function will read a csv file and will create a csv that Mosel can read
   with the most popular routes and stations in a certain week. 
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

    header = "City divisions"
    print(header)
    print("-"*len(header))
    print("Enter the full path csv file location (i.e. C:/Documents/08.csv). Press Enter when done.")
    csvFile = input()
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

    if os.path.isfile(csvFile) != True:
        print (f"{fileName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    latestData = DataProcessing(filePath, weekNumber, divisionFile=0, tsp = 0)

    latitude, longitude, net_flow_in, net_flow_out, station_id = Dat_CityDivision(latestData)

    latitude = pd.DataFrame(latitude.values.reshape(1,-1))
    longitude = pd.DataFrame(longitude.values.reshape(1,-1))
    net_flow_in = pd.DataFrame(net_flow_in.values.reshape(1,-1))
    net_flow_out = pd.DataFrame(net_flow_out.values.reshape(1,-1))
    station_id = pd.DataFrame(station_id.values.reshape(1,-1))

    # Generate the dat files for the required timeframe

    latitude.to_csv(os.path.join(curDir, "city_division.dat"), index = False, header = False, sep = " ")
    longitude.to_csv(os.path.join(curDir, "longitude.dat"), index = False, header = False, sep = " ")
    net_flow_in.to_csv(os.path.join(curDir, "net_flow_in.dat"), index = False, header = False, sep = " ")
    net_flow_out.to_csv(os.path.join(curDir, "net_flow_out.dat"), index = False, header = False, sep = " ")
    station_id.to_csv(os.path.join(curDir, "station_id.dat"), index = False, header = False, sep = " ")
    
    f1 = open('longitude.dat')
    f2 = open('net_flow_in.dat')
    f3 = open('net_flow_out.dat')
    f4 = open('station_id.dat')

    with open("city_division.dat", "r+") as f:
        old = f.read() # read everything in the file
        longitude = f1.read()
        net_flow_in = f2.read()
        net_flow_out = f3.read()
        station_id = f4.read()

        f.seek(0) # rewind
        f.write("Latitude: [" + old + "]\n") # write the new line before
        f.write("Longitude: [" + longitude + "]\n")
        f.write("net_flow_in: [" + net_flow_in + "]\n")
        f.write("net_flow_out: [" + net_flow_out + "]\n")
        f.write("station_id: [" + station_id + "]")
    
    f1.close()
    f2.close()
    f3.close()
    f4.close()

    os.remove("longitude.dat")
    os.remove("net_flow_in.dat")
    os.remove("net_flow_out.dat")
    os.remove("station_id.dat")

    print("Created city_division.dat")

    return 

def Cli():

    '''
    CLI interface for exploring the different functions.
    '''

    header = "Bike sharing script"
    print(header)
    print(len(header)*"=")
    print("Script options:")
    print("1: Generate the city_division.dat initialization file for city_division.mos")
    print("2: Generate the net_add.dat initialization files per region for bike.mos")
    print("3: Calculate the travelling salesman distances for a defined number of stations using OSRM API")
    print("0: Exit")

    print("Select an option. Press enter when done")
    select = input()

    menu = True
   
    while(menu == True):

        if(select == '0'):
            print("Ciao!")
            break

        elif(select == '1'):
            edin = CityDivision()

        elif(select == '2'):
            edin = NetAdd()

        elif(select == '3'):
            tspEdin = Tsp()

        elif(select == '4'): #Easter egg
            combo = Combinations()

        else:
            print("Invalid selection. Try again using an appropriate selection.")
            select = input()

        print("Done. Need something else? Select an option from the menu. If not, enter 0")
        select = input()

    return

Cli()


## Map 
#world_map = folium.Map()
#world_map

#edinLat = 55.9533 
#edinLong = -3.1883
#edinMap = folium.Map(location=[edinLat, edinLong], zoom_start=12, tiles='Stamen Toner')
#edinMap