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

    try:
        gps = mavutil.mavlink_connection(port, baud=baud)
        if gps.wait_heartbeat(timeout=10) is None:
            print("Failed to connect to GPS: no heartbeat received")
            return None

        return gps
    except (OSError, ValueError) as e:
        print(f"Failed to connect to GPS: {e}")
        return None
