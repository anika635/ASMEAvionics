# ASMEAvionics

# Relative Location Logger

Saves your current location relative to where you started.

When the program starts, it records your initial GPS coordinates as the origin. As you move, it tracks your current position, and each time you travel 0.5 mile from the last saved point, it writes an entry to a file containing:

- Your exact current coordinates (latitude, longitude)
- Your distance from the starting point
- Your direction (bearing) from the starting point

You can also check your exact current coordinates at any time.

Saved locations are written to a file that will be called locations.txt 


Functions Outlined:

connect_gps(port, baud): Opens the connection to your GPS device so you can read from it.

get_current_location(gps): Reads the latest GPS fix and returns your latitude and longitude, or nothing if the signal isn't good enough yet.

wait_for_fix(gps): Keeps calling get_current_location() until it gets a valid reading. Useful at startup, since GPS takes a bit to lock on.

set_origin(gps): Grabs your location when the program starts and stores it as the reference point everything else is measured from.

haversine_distance(point_a, point_b): Calculates the real distance in meters between two coordinates, accounting for the Earth's curve.

calculate_bearing(point_a, point_b): Figures out which direction point B is from point A, in degrees (0 is north, 90 is east).

relative_offset(origin, current): Breaks your position down into how many meters north and east you are from the start. Easier to picture than a distance plus angle.

should_save(last_saved, current, threshold): Checks if you've moved at least 0.5 mile since the last saved point. Returns true or false.

build_entry(origin, current): Packages everything for one save: timestamp, current coordinates, distance and bearing from the start, and the north/east offsets.

init_output_file(path): Creates the file and writes the column headers if it doesn't already exist.

save_location(entry, path): Adds one row to the file.

main(): Ties it together. Connects to the GPS, sets the origin, then loops forever reading your location, checking should_save(), and saving when you've moved far enough.


