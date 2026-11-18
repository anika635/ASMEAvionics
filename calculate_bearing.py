def calculate_bearing(point_a, point_b):
    """
    Calculates the direction from point_a to point_b.

    point_a: (latitude, longitude) in decimal degrees (the starting point)
    point_b: (latitude, longitude) in decimal degrees (the target point)

    Returns:
        Initial bearing in degrees from 0 up to (but not including) 360,
        measured clockwise from true north.
        0 = north, 90 = east, 180 = south, 270 = west.
        Returns 0.0 if both points are the same.
    """

    lat1, lon1 = point_a
    lat2, lon2 = point_b

    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    # atan2 gives -180 to 180, so shift it into 0 to 360
    bearing = math.degrees(math.atan2(x, y))

    return (bearing + 360) % 360
