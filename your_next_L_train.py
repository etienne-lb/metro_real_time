from google.transit import gtfs_realtime_pb2
from urllib.request import urlopen
import urllib.error
import pandas as pd
from tkinter import *
import pytz
from datetime import datetime

def next_train_date(feed, direction, station):
    # We are getting the information for the Next L train
    trains = pd.DataFrame(columns=["trip_id", "stop_id", "arrival"])
    # This is the L line of the New York metro
    with urlopen(
            "http://datamine.mta.info/mta_esi.php?key=[KEY]&feed_id=2") as response:
        feed.ParseFromString(response.read())
        for entity in feed.entity:
            # Because the feed also includes "alerts"
            if entity.HasField('trip_update'):
                # For each train, getting the trip ID
                trip_id_current = entity.trip_update.trip.trip_id
                for stop in entity.trip_update.stop_time_update:
                    # For each stop of the train, getting the time and the time at which it will arrive at this stop
                    stop_id_current = stop.stop_id
                    arrival_current = stop.departure.time
                    trains = trains.append(
                        {'trip_id': trip_id_current, 'stop_id': stop_id_current, 'arrival': arrival_current},
                        ignore_index=True)

    # setting the date to the right format
    trains["arrival"] = trains["arrival"].apply(
        lambda t: pd.to_datetime(t, unit='s', utc=True).tz_convert("America/New_York"))
    # N = North = Manhattan bound, S = South = Brooklyn bound
    if direction == 'Manhattan':
        current_stop = station + 'N'
    else:
        current_stop = station + 'S'
    trains = trains[trains["stop_id"] == current_stop]
    # Taking the lowest arrival time (or next the lowest is before now)
    try:
        if min(trains["arrival"]) >= datetime.now(pytz.timezone("America/New_York")):
            date_next_train = min(trains["arrival"])
        else:
            old_min = min(trains["arrival"])
            trains = trains[trains["arrival"] != old_min]
            date_next_train = min(trains["arrival"])
    except ValueError:
        date_next_train = 0
    return date_next_train


def refresh(direction, station, station_name):
    # Getting the new destination
    if (station == "L29" and direction == "Brooklyn") or (station == "L01" and direction == "Manhattan"):
        # Iif it is the last stop (no train to display)
        text_var.set("This is the last stop, there is no train in that direction.")
    else:
        try:
            # Getting info for the next train
            train_time = next_train_date(feed=my_feed, direction=direction, station=station)
            try:
                time = str(train_time.strftime("%H:%M"))
                # Updating the text we display
                text_var.set("The next L train for {0} leaves at {1} from {2}.".format(direction, time, station_name))
            except AttributeError:
                # in case we don't have a date, 0 is returned and a AttributeError is raised
                text_var.set("Oops, we couldn't find any incoming train!")
            # Refreshing every minute by calling the function (time in milliseconds)
            new_station = data_stations[data_stations["Stop Name"] == station_var.get()].iloc[0]['GTFS Stop ID']
            new_station_name = station_var.get()
            fenetre.after(60000, refresh, destination_var.get(), new_station, new_station_name)
        except urllib.error.URLError:
            text_var.set("Error: Couldn't connect to the MTA data! ")


def change_menu(*args):
    # When the destination or station is changed, we refresh
    new_destination = destination_var.get()
    new_station_name = station_var.get()
    # We send the "GTFS Stop ID" to the function, not the "Stop Name"
    the_station = data_stations[data_stations["Stop Name"] == new_station_name]
    new_station = the_station.iloc[0]['GTFS Stop ID']
    refresh(new_destination, new_station, new_station_name)


# Reading the csv file to get the list of stations
data_stations = pd.read_csv("Stations-MTA.csv")
data_stations = data_stations[["GTFS Stop ID", "Stop Name"]]
# Only the stations on the L line
data_stations = data_stations[data_stations["GTFS Stop ID"].str.startswith('L')]
list_stations = list(data_stations["Stop Name"])
# Creating the window
fenetre = Tk()
fenetre.title("Your next L train")
fenetre.geometry("450x120")
fenetre.configure(background='white')
fenetre.iconbitmap(r'MTA.ico')
# The station text
text_station = Label(fenetre, text="Select your station: ", background='white')
text_station.grid(row=1, column=1, sticky=W, padx=5, pady=5)
# The menu for station
station_var = StringVar(fenetre)
station_var.set(list_stations[5])
menu_station = OptionMenu(*(fenetre, station_var) + tuple(list_stations))
menu_station.grid(row=1, column=2, sticky=W+E+N+S, padx=5, pady=5)
# The direction text
text_direction = Label(fenetre, text="Select direction: ", background='white')
text_direction.grid(row=2, column=1, sticky=W, padx=5, pady=5)
# The menu for direction
destination_var = StringVar(fenetre)
destination_var.set("Manhattan")
menu_direction = OptionMenu(fenetre, destination_var, "Manhattan", "Brooklyn")
menu_direction.grid(row=2, column=2, sticky=W+E+N+S, padx=5, pady=5)
# The text for the hour
text_var = StringVar(fenetre)
text_var.set("Loading data... please wait.")
text_label = Label(fenetre, textvariable=text_var, background='white')
text_label.grid(row=3, column=1, columnspan=2, sticky=W+E+N+S, padx=5, pady=5)
# Launching the feed of MTA info
my_feed = gtfs_realtime_pb2.FeedMessage()
# Getting first value of station and direction selected
train_direction = destination_var.get()
train_station_name = station_var.get()
train_station = data_stations[data_stations["Stop Name"] == station_var.get()].iloc[0]['GTFS Stop ID']

# Calling change_menu_direction when the direction is changed
destination_var.trace('w', change_menu)
# Calling change_menu_station when the station is changed
station_var.trace('w', change_menu)
# Keeping it refreshed
refresh(train_direction, train_station, train_station_name)
# The mainloop
fenetre.mainloop()