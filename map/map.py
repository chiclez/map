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