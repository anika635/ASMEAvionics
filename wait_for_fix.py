# Keeps calling get_current_location() until it gets a valid reading. Useful at startup, since GPS takes a bit to lock on

import time


def wait_for_fix(get_current_location):
    while True:
        location = get_current_location()
        if location is not None:
            return location
        time.sleep(1)  # Wait for 1 second before trying again