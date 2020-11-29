import pandas as pd
from pathlib import Path
from geopy.distance import geodesic
import os 
import folium

def FindPopularSpots(csvFile):

    '''
    This function will read a csv file from a previous week/month of 
   and will create a csv that Mosel can read with the most popular paths and 
   stations in such timeframe. The csv file will be output in the same directory
   as the 

   input:
   csvFile = the csv file path and location. i.e. "C:/Documents/example.csv"

   Output: None
    '''

    readFile = Path(csvFile)
    rawData = pd.read_csv(readFile, parse_dates = [1,2])

    # Ensure the timestamps are true timestamps
    start_date = pd.to_datetime(rawData['started_at'])
    end_date = pd.to_datetime(rawData['ended_at'])

    # Add Day of the Week and Week number as a column
    rawData['weekday_start_at'] = pd.to_datetime(rawData['started_at']).dt.dayofweek
    rawData['weekday_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.dayofweek
    rawData['week_start_at'] = pd.to_datetime(rawData['started_at']).dt.isocalendar().week
    rawData['week_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.isocalendar().week

    # Paths export
    pathList = pd.DataFrame({'count': 
                rawData.groupby(["start_station_id", "end_station_id",
                "start_station_name", "end_station_name", "start_station_latitude", 
                "start_station_longitude", "end_station_latitude", 
                "end_station_longitude"]).size()}).reset_index()
    sortedPathList = pathList.sort_values(by=['count'],
                        ascending = False, ignore_index = True)

    # From Station
    hotspotStart = pd.DataFrame({'count': rawData.groupby(["start_station_id", 
                    "start_station_name"]).size()}).reset_index()
    sortedHotspotStart = hotspotStart.sort_values(by=['count'], 
                        ascending = False, ignore_index = True)

    # To Station
    hotspotDestination = pd.DataFrame({'count': rawData.groupby(["end_station_id", 
                         "end_station_name"]).size()}).reset_index()
    sortedHotspotDestionation = hotspotDestination.sort_values(by=['count'], 
                            ascending = False, ignore_index= True)

    # Generate the csv files

    pathList.to_csv(r"D:\Solutions\experiments\map\map\raw_data\pathList.csv")
    sortedPathList.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sortedPathList.csv")

    hotspotStart.to_csv(r"D:\Solutions\experiments\map\map\raw_data\start_stations.csv")
    sortedHotspotStart.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sorted_start_stations.csv")

    hotspotDestination.to_csv(r"D:\Solutions\experiments\map\map\raw_data\destination_stations.csv")
    sortedHotspotDestionation.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sorted_destination_stations.csv")

    print("Done!")

    return 

FindPopularSpots("D:/Solutions/experiments/map/map/raw_data/2020_10.csv")

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
# Coordinates


coords_1 = (30.172705, 31.526725) #(lat, long)
coords_2 = (30.288281, 31.732326)

print(geodesic(coords_1, coords_2).kilometers)

## Import data
#workDirectory = r"D:\Solutions\experiments\map\map\raw_data"
#fileName = r"\2020_10.csv"
#readFile = workDirectory + fileName
#rawData = pd.read_csv(readFile, parse_dates = [1,2])

## Ensure the timestamps are true timestamps
#start_date = pd.to_datetime(rawData['started_at'])
#end_date = pd.to_datetime(rawData['ended_at'])

## Add Day of the Week and Week number as a column
#rawData['weekday_start_at'] = pd.to_datetime(rawData['started_at']).dt.dayofweek
#rawData['week_start_at'] = pd.to_datetime(rawData['started_at']).dt.isocalendar().week
#rawData['weekday_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.dayofweek
#rawData['week_ended_at'] = pd.to_datetime(rawData['ended_at']).dt.isocalendar().week

## Paths export
#pathList = pd.DataFrame({'count': 
#             rawData.groupby(["start_station_id", "end_station_id",
#             "start_station_name", "end_station_name", "start_station_latitude", 
#             "start_station_longitude", "end_station_latitude", 
#             "end_station_longitude"]).size()}).reset_index()
#sortedPathList = pathList.sort_values(by=['count'], ascending = False, 
#                 ignore_index = False)

#pathList.to_csv(r"D:\Solutions\experiments\map\map\raw_data\pathList.csv")
#sortedPathList.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sortedPathList.csv")

## From Station

#hotspotStart = pd.DataFrame({'count': rawData.groupby(["start_station_id", 
#                            "start_station_name"]).size()}).reset_index()
#sortedHotspotStart = hotspotStart.sort_values(by=['count'], ascending = False, 
#                     ignore_index = True)

#hotspotStart.to_csv(r"D:\Solutions\experiments\map\map\raw_data\start_stations.csv")
#sortedHotspotStart.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sorted_start_stations.csv")

## To Station

#hotspotDestination = pd.DataFrame({'count': rawData.groupby(["end_station_id", 
#                     "end_station_name"]).size()}).reset_index()
#sortedHotspotDestionation = hotspotDestination.sort_values(by=['count'], 
#                            ascending = False, ignore_index= True)

#hotspotDestination.to_csv(r"D:\Solutions\experiments\map\map\raw_data\destination_stations.csv")
#sortedHotspotDestionation.to_csv(r"D:\Solutions\experiments\map\map\raw_data\sorted_destination_stations.csv")



## Map 
#world_map = folium.Map()
#world_map

#edinLat = 55.9533 
#edinLong = -3.1883
#edinMap = folium.Map(location=[edinLat, edinLong], zoom_start=12, tiles='Stamen Toner')
#edinMap