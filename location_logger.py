import os
import csv
from datetime import datetime


def save_launch_position(origin, path="launch_position.txt", timestamp=None):
    """
    Records where the drone launched from.

    Each launch adds one row (the header is written the first time), so
    earlier launches are never overwritten. The last row is the current
    flight's launch point.

    origin:    (latitude, longitude) from set_origin(), or None
    timestamp: optional time string; defaults to now

    Returns:
        True if the launch position was written
        False if origin is None (no GPS fix, so nothing to record)
    """
    if origin is None:
        return False

    if timestamp is None:
        timestamp = datetime.now().isoformat(timespec="seconds")

    needs_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as file:
        writer = csv.writer(file)
        if needs_header:
            writer.writerow(["timestamp", "latitude", "longitude"])
        writer.writerow([timestamp, origin[0], origin[1]])
    return True


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
