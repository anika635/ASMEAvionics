from haversine_distance import haversine_distance


HUNDRED_FEET_METERS = 30.48  # 100 ft * 0.3048 m/ft


def should_save(last_saved, current, threshold=HUNDRED_FEET_METERS):
    """
    Decides whether a new location entry should be written.

    last_saved: (latitude, longitude) of the last saved point, or None if
                nothing has been saved yet
    current:    (latitude, longitude) from get_current_location(), or None
                if there was no valid GPS fix
    threshold:  minimum distance in METERS since the last saved point
                (default 30.48 m = 100 feet)

    Returns:
        True if current is at least `threshold` meters from last_saved
        True if nothing has been saved yet (and current is valid)
        False otherwise, including when current is None
    """

    # No valid GPS fix, so there's nothing to save
    if current is None:
        return False

    # Nothing saved yet, so save this first point
    if last_saved is None:
        return True

    distance = haversine_distance(last_saved, current)

    return distance >= threshold
