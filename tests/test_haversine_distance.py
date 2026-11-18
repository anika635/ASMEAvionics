"""Error points for haversine_distance(point_a, point_b)."""
import math
import unittest

from haversine_distance import haversine_distance

EARTH_RADIUS_M = 6371000
HALF_MILE_M = 804.672


class HaversineErrorPoints(unittest.TestCase):

    def test_same_point_is_zero(self):
        self.assertEqual(haversine_distance((33.7861, -84.2695), (33.7861, -84.2695)), 0.0)

    def test_one_degree_of_longitude_at_equator(self):
        self.assertAlmostEqual(haversine_distance((0, 0), (0, 1)), 111194.93, places=2)

    def test_order_does_not_matter(self):
        a, b = (33.7861, -84.2695), (34.0, -84.0)
        self.assertAlmostEqual(haversine_distance(a, b), haversine_distance(b, a), places=6)

    # The distance the logger actually cares about: half a mile due north
    def test_half_mile_north(self):
        start = (33.7861, -84.2695)
        dlat = math.degrees(HALF_MILE_M / EARTH_RADIUS_M)
        end = (start[0] + dlat, start[1])

        self.assertAlmostEqual(haversine_distance(start, end), HALF_MILE_M, places=3)

    # ERROR POINT: crossing the 180 degree line. Two points 0.2 degrees apart
    # must NOT come out as ~40,000 km.
    def test_crossing_the_antimeridian(self):
        distance = haversine_distance((0, 179.9), (0, -179.9))
        self.assertAlmostEqual(distance, 22238.99, places=2)

    def test_pole_to_pole(self):
        self.assertAlmostEqual(
            haversine_distance((90, 0), (-90, 0)), math.pi * EARTH_RADIUS_M, places=3
        )

    # ERROR POINT: missing reading passed in (get_current_location returned None)
    def test_none_point_raises(self):
        with self.assertRaises(TypeError):
            haversine_distance(None, (33.7861, -84.2695))

    # ERROR POINT: coordinates read from a file as text
    def test_string_coordinates_raise(self):
        with self.assertRaises(TypeError):
            haversine_distance(("33.7861", "-84.2695"), (34.0, -84.0))

    # FIXED BUG: for some points on opposite sides of the Earth, rounding made
    # the intermediate value `a` slightly bigger than 1, so math.sqrt(1 - a)
    # crashed with "ValueError: math domain error".
    def test_opposite_side_of_earth_does_not_crash(self):
        distance = haversine_distance((45, 45), (-45, -135))
        self.assertAlmostEqual(distance, math.pi * EARTH_RADIUS_M, places=0)

    def test_many_antipodal_pairs_do_not_crash(self):
        for lat in range(-85, 86, 5):
            for lon in range(-180, 1, 15):
                distance = haversine_distance((lat, lon), (-lat, lon + 180))
                self.assertAlmostEqual(distance, math.pi * EARTH_RADIUS_M, delta=1)


if __name__ == "__main__":
    unittest.main()
