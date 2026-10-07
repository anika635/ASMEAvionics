def get_current_location(gps):
    """
    Gets the current GPS location from the Cube Orange+.

    gps is the pymavlink connection returned by connect_gps(). The Cube
    reads the Here GPS and publishes its navigation position over MAVLink
    as GLOBAL_POSITION_INT (latitude/longitude in degrees * 1e7).

    Returns:
        (latitude, longitude) in decimal degrees
        None if a valid GPS position is not available
    """

    message = gps.recv_match(
        type="GLOBAL_POSITION_INT",
        blocking=True,
        timeout=2
    )

    if message is None:
        return None

    if message.lat == 0 and message.lon == 0:
        return None

    latitude = message.lat / 1e7
    longitude = message.lon / 1e7

    return latitude, longitude
