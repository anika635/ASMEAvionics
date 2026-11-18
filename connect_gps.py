from pymavlink import mavutil


def connect_gps(port, baud=115200):
    """
    Opens the MAVLink connection to the Cube Orange+.

    Args:
        port: Serial device or connection string, such as "COM3" or
            "udp:127.0.0.1:14550".
        baud: Serial connection speed.

    Returns:
        the connection, ready to pass to get_current_location()
        None if the connection cannot be opened or no heartbeat is received
    """

    gps = None
    try:
        gps = mavutil.mavlink_connection(port, baud=baud)
        if gps.wait_heartbeat(timeout=10) is None:
            print("Failed to connect to GPS: no data received")
            _close_quietly(gps)
            return None

        return gps
    except (OSError, ValueError) as e:
        print(f"Failed to connect to GPS: {e}")
        _close_quietly(gps)
        return None


def _close_quietly(gps):
    """
    Releases the port so a retry on the same COM port doesn't fail with
    "Access is denied". Ignores errors, since the port may already be gone.
    """
    if gps is None:
        return
    try:
        gps.close()
    except (OSError, ValueError):
        pass
