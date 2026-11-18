# ASMEAvionics

# Relative Location Logger

Saves your current location relative to where you started.

When the program starts, it records your initial GPS coordinates as the origin. As you move, it tracks your current position, and each time you travel 100 feet from the last saved point, it writes an entry to a file containing:

- Your exact current coordinates (latitude, longitude)
- Your distance from the starting point
- Your direction (bearing) from the starting point

You can also check your exact current coordinates at any time.

Saved locations are written to a file that will be called locations.txt 


Functions Outlined:

connect_gps(port, baud=115200): Opens the MAVLink connection to your GPS device,
waits for a heartbeat, and returns the connection. Returns nothing if the
connection cannot be opened or no heartbeat is received.

get_current_location(gps): Reads the latest GPS fix and returns your latitude and longitude, or nothing if the signal isn't good enough yet.

wait_for_fix(gps): Keeps calling get_current_location() until it gets a valid reading. Useful at startup, since GPS takes a bit to lock on.

set_origin(gps): Grabs your location when the program starts and stores it as the reference point everything else is measured from.

haversine_distance(point_a, point_b): Calculates the real distance in meters between two coordinates, accounting for the Earth's curve.

calculate_bearing(point_a, point_b): Figures out which direction point B is from point A, in degrees (0 is north, 90 is east). - Isha

relative_offset(origin, current): Breaks your position down into how many meters north and east you are from the start. Easier to picture than a distance plus angle.

should_save(last_saved, current, threshold): Checks if you've moved at least 100 feet (30.48 m) since the last saved point. Returns true or false. - Isha

build_entry(origin, current): Packages everything for one save: timestamp, current coordinates, distance and bearing from the start, and the north/east offsets.

init_output_file(path): Creates the file and writes the column headers if it doesn't already exist.

save_location(entry, path): Adds one row to the file.

save_launch_position(origin, path): Records the launch (origin) coordinates in launch_position.txt. Each launch adds a row, so earlier launches are kept.

main(): Ties it together. Connects to the GPS, sets the origin, then loops forever reading your location, checking should_save(), and saving when you've moved far enough.


Testing:

Run all checks from the project folder:

    python -m unittest discover tests

Fly a simulated drone in the terminal with W/A/S/D (uses the real functions above over a simulated MAVLink link):

    python tests/flight_game.py

Or watch it fly a preset route by itself:

    python tests/flight_game.py --autopilot

The game saves an entry every 10 m so saves show up quickly; the real program saves every 100 feet. Use --save-every 30.48 to fly the game with the real distance, or --port 14570 if the default port is busy.


