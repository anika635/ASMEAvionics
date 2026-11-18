# Keeps calling get_current_location() until it gets a valid reading. Useful at startup, since GPS takes a bit to lock on
import time

from get_current_location import get_current_location


def wait_for_fix(gps, max_attempts=60):
    """
    Waits for a valid GPS reading.

    gps:          the connection from connect_gps(), or a function that
                  returns (latitude, longitude) or None
    max_attempts: how many readings to try before giving up. Each try takes
                  up to ~3 seconds (2 s read timeout + 1 s pause), so the
                  default of 60 gives up after roughly 1-3 minutes.
                  Pass None to wait forever.

    Returns:
        (latitude, longitude) once the GPS has a fix
        None if there was still no fix after max_attempts tries
    """
    print("Waiting for GPS fix...")
    attempt = 0
    while max_attempts is None or attempt < max_attempts:
        attempt += 1

        recv_match = getattr(gps, "recv_match", None)
        if callable(recv_match):
            location = get_current_location(gps)
        elif callable(gps):
            location = gps()
        else:
            location = get_current_location(gps)

        if location is not None:
            return location

        # Don't pause after the last try; we're about to give up anyway
        if max_attempts is None or attempt < max_attempts:
            time.sleep(1)

    print(f"No GPS fix after {max_attempts} attempts, giving up")
    return None
