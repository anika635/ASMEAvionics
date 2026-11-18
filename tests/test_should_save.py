"""Error points for should_save(last_saved, current, threshold)."""
import math
import unittest

from haversine_distance import haversine_distance
from should_save import HALF_MILE_METERS, should_save

EARTH_RADIUS_M = 6371000
START = (33.7861, -84.2695)


def north_of(point, meters):
    return (point[0] + math.degrees(meters / EARTH_RADIUS_M), point[1])


class ShouldSaveErrorPoints(unittest.TestCase):

    def test_half_mile_constant(self):
        self.assertAlmostEqual(HALF_MILE_METERS, 0.5 * 1609.344)

    # ERROR POINT: no GPS fix this loop
    def test_no_fix_never_saves(self):
        self.assertFalse(should_save(START, None))

    def test_no_fix_and_nothing_saved_yet(self):
        self.assertFalse(should_save(None, None))

    # ERROR POINT: first valid reading. Must save even though there is
    # nothing to measure from (and must not crash calling haversine on None).
    def test_first_point_is_always_saved(self):
        self.assertTrue(should_save(None, START))

    def test_not_moved(self):
        self.assertFalse(should_save(START, START))

    # ERROR POINT: GPS jitter. Small wobbles must not trigger saves.
    def test_gps_jitter_does_not_save(self):
        self.assertFalse(should_save(START, north_of(START, 5)))

    # ERROR POINT: off-by-one at the boundary
    def test_just_under_half_mile_does_not_save(self):
        self.assertFalse(should_save(START, north_of(START, HALF_MILE_METERS - 0.01)))

    def test_exactly_threshold_saves(self):
        current = north_of(START, HALF_MILE_METERS)
        exact = haversine_distance(START, current)
        self.assertTrue(should_save(START, current, threshold=exact))

    def test_over_half_mile_saves(self):
        self.assertTrue(should_save(START, north_of(START, HALF_MILE_METERS + 1)))

    # ERROR POINT: threshold units. It is METERS, not miles. Passing 0.5
    # thinking "half a mile" saves on almost every reading.
    def test_threshold_is_meters_not_miles(self):
        self.assertTrue(should_save(START, north_of(START, 1), threshold=0.5))

    def test_custom_threshold(self):
        self.assertFalse(should_save(START, north_of(START, 50), threshold=100))
        self.assertTrue(should_save(START, north_of(START, 150), threshold=100))


if __name__ == "__main__":
    unittest.main()
