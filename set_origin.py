from get_current_location import get_current_location


def set_origin(gps):
    """
    Sets the starting GPS location as the origin.

    The origin is returned rather than stored in a global, so the caller
    keeps it and passes it to the distance/bearing functions:

        origin = set_origin(gps)

    Returns:
        (latitude, longitude) of the origin
        None if a valid GPS position is not available
    """

    return get_current_location(gps)
