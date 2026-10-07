# ASMEAvionics

# Relative Location Logger

Saves your current location relative to where you started.

When the program starts, it records your initial GPS coordinates as the origin. As you move, it tracks your current position, and each time you travel 0.5 mile from the last saved point, it writes an entry to a file containing:

- Your exact current coordinates (latitude, longitude)
- Your distance from the starting point
- Your direction (bearing) from the starting point

You can also check your exact current coordinates at any time.

Saved locations are written to a file that will be called locations.txt 
