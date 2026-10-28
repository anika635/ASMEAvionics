
import os
import csv

def init_output_file(path="locations.txt"):
    # create file
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "latitude", "longitude", "distance_m", "bearing_deg", "north_m", "east_m"])



def save_location(entry, path="locations.txt"):
    if entry is None:
        return

    with open(path, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([entry["timestamp"], entry["latitude"], entry["longitude"], entry["distance_m"], entry["bearing_deg"], entry["north_m"], entry["east_m"]])
