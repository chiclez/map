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

def GetBestRoute (data, hours, region, fuel):

    # Get the hours schedule for the region
    hourSchedule = hours["t"].tolist()

    firstHour = hourSchedule[0]
    lastHour = hourSchedule[-1] + 1

    workingHours = len(hourSchedule)
    hourlySalary = 9.2
    pay = round(hourlySalary*workingHours,2)

    fileName = f"best_route_region{region}.csv"
    
    totalDistance = 0
    totalFuelCost = 0

    # Call OSRM per hour in the schedule and write the output file containing the OSRM results
    for i in range(firstHour, lastHour):

        tspData = data.loc[data["t"] == i]
        stations = tspData["station_id"].tolist()
        stationNames = tspData["station_name"].tolist()

        coordinates = tspData.drop(columns=["t", "station_id", "station_name"])
        coordinates = pd.DataFrame(coordinates.values.reshape(1,-1))

        coordinates.to_csv("temp_stops.csv", index = False, header = False, sep = ";")

        with open("temp_stops.csv", "r+") as f:
            tempStops = f.read()
            tempStops = tempStops.rstrip()
        
        tspUrl = "http://127.0.0.1:5000/trip/v1/driving/"
        depot = "-3.157453,55.973447"
        pickupUrl = f"{tspUrl}{depot};{tempStops}?roundtrip=false&source=first&destination=last"
        
        os.remove("temp_stops.csv")

        s = requests.Session()
        s.mount(pickupUrl, HTTPAdapter(max_retries=5))
        r = s.get(pickupUrl, timeout=5)
        res = r.json()

        #with open('distance.json', 'w') as json_file: json.dump(res, json_file, indent = 4)
        vanFuelConsumption = 7.6/100  #  L/100 km
        distance = round(res['trips'][0]['distance']/1000,1)
        duration = int(res['trips'][0]['duration']/60)
        fuelCost = round(distance*(vanFuelConsumption)*(fuel),1)  #in sterling per hour (or trip)

        totalStations = len(stations)

        totalDistance += distance
        totalFuelCost += fuelCost

        header = "time\tkm\t\t£\t\tmin\t\tstations\tstation name"

        if(i == firstHour):

            with open(fileName, 'w') as file:  
                file.write(header)
                file.write("\n")
                file.write("="*(len(header)+20))
                file.write(f"\n{i}\t\t{distance}\t{fuelCost}\t\t{duration}\t\t{totalStations}\t\t\t")

        else:
            with open(fileName, 'a') as file:  
                file.seek(0, os.SEEK_END)
                file.write(f"\n{i}\t\t{distance}\t{fuelCost}\t\t{duration}\t\t{totalStations}\t\t\t")

        for j in range(0, len(stations)):

            leg = res['waypoints'][j]['waypoint_index'] - 1
            stop = stations[leg]
            stopName = stationNames[leg]

            with open(fileName, 'a') as file:  
                if(j == len(stations)-1):
                    file.write(f"{stopName}\n")
                else:
                    file.write(f"{stopName}|")

    totalFuelCost = round(totalFuelCost, 1)
    totalDistance = round(totalDistance, 1)

    with open(fileName, 'a') as f:
        header = f"\nRegion {region} summary\n"
        f.write(header)
        f.write("="*len(header))
        f.write(f"\n\nTotal fuel cost: £{totalFuelCost}\n")
        f.write(f"Total distance: {totalDistance} km\n")
        f.write(f"Total working hours: {workingHours}h\n")
        f.write(f"Total pay: £{pay}\n")
        f.write("\nHappy ride!")

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

    # Create the region array
    region1 = region1.drop(columns = ["region"])
    region2 = region2.drop(columns = ["region"])
    region2 = region3.drop(columns = ["region"])

    return region1, region2, region3

def OutputNet_Add(netAdd, bikeInit, stations, region):

    curDir = os.getcwd()
    
    netAddFile = os.path.join(curDir, f"net_add_region{region}.dat")
    bikeInitFile = os.path.join(curDir, f"bike_init_region{region}.dat")
    stationFile = os.path.join(curDir, f"stations_region{region}.dat")

    netAdd.to_csv(netAddFile, index = False, header = False, sep = " ")
    bikeInit.to_csv(bikeInitFile, index = False, header = False, sep = " ")
    stations.to_csv(stationFile, index = False, header = False, sep = " ")
    
    f1 = open(bikeInitFile)
    f2 = open(stationFile)

    with open(netAddFile, "r+") as f:
         contents = f.read()
         ini_bikes = f1.read()
         station_id = f2.read()
         f.seek(0) # rewind
         f.write("net_add: [" + contents + "]\n") 
         f.write("ini_bikes: [" + ini_bikes + "]\n")
         f.write("station_id: [" + station_id + "]")

    f1.close()
    f2.close()
    os.remove(bikeInitFile)
    os.remove(stationFile)

    print(f"Created {netAddFile}")

    return

def DataProcessing(filePath, weekNumber, tsp):

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
    for Edinburgh's JustEat bike sharing service using a Docker OSRM server per hour

    Input:
    open_data csv: This can be found in Edinburgh's Just Eat site

    Output:
    best_route_region.csv: A csv file with all the required information for Mosel
            i.e. distance, duration, node visits
    '''

    header = "Travelling Salesman Problem (TSP) Combinations"
    print(header)
    print("-"*len(header))

    print("Enter the full path csv file location for the unbalanced stations (i.e. C:/Documents/unbalanced.csv)")
    unbalanced = input()

    print("Can I get today's fuel price? Please enter it in pounds per liter")
    fuel = float(input())

    print("What region is this for? Valid values are 1, 2 and 3")
    region = input()
       
    curDir = os.getcwd()
    unbalancedPath = os.path.abspath(unbalanced)
    unbalancedName = os.path.basename(unbalanced)

    dictPath = os.path.join(curDir, "raw_data\stationsDic.csv")

    if os.path.isfile(unbalanced) != True:
        print (f"{unbalancedName} does not exist. Try again")
        return

    print("All good. Processing the file... \n")

    stationsDic = pd.read_csv(dictPath)
    stationsDic = stationsDic.drop(columns = ["count"])

    unbalancedStations = pd.read_csv(unbalancedPath)

    tspData = pd.merge(unbalancedStations,stationsDic, how = "inner", on="station_id")
    tspData = tspData.sort_values(by = ["t"])

    hours = pd.DataFrame({'stations': tspData.groupby(["t"]).size()}).reset_index()

    tsp = GetBestRoute(tspData, hours, region, fuel)

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

    #Process the csv files
    region1, region2, region3 = Regions(divisionFile)
    latestData = DataProcessing(filePath, weekNumber, tsp = 0)
    netAdd = Dat_NetAdd(latestData)

    # Split the data per region
    netAddR1 = pd.merge(netAdd, region1, how = "inner", on = ["station_id"])
    netAddR1 = netAddR1.drop(columns = ["station_id"])

    netAddR2 = pd.merge(netAdd, region2, how = "inner", on = ["station_id"])
    netAddR2 = netAddR2.drop(columns = ["station_id"])

    netAddR3 = pd.merge(netAdd, region3, how = "inner", on = ["station_id"])
    netAddR3 = netAddR3.drop(columns = ["station_id"])

    # Create the init_bikes arrays
    bikeInitR1 = Dat_BikeInit(netAddR1)
    bikeInitR2 = Dat_BikeInit(netAddR2)
    bikeInitR3 = Dat_BikeInit(netAddR3)

    stationR1 = pd.DataFrame(region1.values.reshape(1,-1))
    stationR2 = pd.DataFrame(region2.values.reshape(1,-1))
    stationR3 = pd.DataFrame(region3.values.reshape(1,-1))

    # Generate the net_add.dat files for the required timeframe per region
    fileRegion1 = OutputNet_Add(netAddR1, bikeInitR1, stationR1, 1)
    fileRegion2 = OutputNet_Add(netAddR2, bikeInitR2, stationR2, 2)
    fileRegion3 = OutputNet_Add(netAddR3, bikeInitR3, stationR3, 3)

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

    latestData = DataProcessing(filePath, weekNumber, tsp = 0)

    latitude, longitude, net_flow_in, net_flow_out, station_id = Dat_CityDivision(latestData)

    latitude = pd.DataFrame(latitude.values.reshape(1,-1))
    longitude = pd.DataFrame(longitude.values.reshape(1,-1))
    net_flow_in = pd.DataFrame(net_flow_in.values.reshape(1,-1))
    net_flow_out = pd.DataFrame(net_flow_out.values.reshape(1,-1))
    station_id = pd.DataFrame(station_id.values.reshape(1,-1))

    numberStations = station_id.shape[1]

    # Generate the dat files for the required timeframe

    cityDivisionFile = f"city_division_week{weekNumber}.dat"

    latitude.to_csv(os.path.join(curDir, cityDivisionFile), index = False, header = False, sep = " ")
    longitude.to_csv(os.path.join(curDir, "longitude.dat"), index = False, header = False, sep = " ")
    net_flow_in.to_csv(os.path.join(curDir, "net_flow_in.dat"), index = False, header = False, sep = " ")
    net_flow_out.to_csv(os.path.join(curDir, "net_flow_out.dat"), index = False, header = False, sep = " ")
    station_id.to_csv(os.path.join(curDir, "station_id.dat"), index = False, header = False, sep = " ")
    
    f1 = open('longitude.dat')
    f2 = open('net_flow_in.dat')
    f3 = open('net_flow_out.dat')
    f4 = open('station_id.dat')

    with open(cityDivisionFile, "r+") as f:
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

    print(f"Created {cityDivisionFile}")
    print(f"The number of stations are: {numberStations}")

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