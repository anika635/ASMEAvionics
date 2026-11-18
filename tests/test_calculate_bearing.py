"""Error points for calculate_bearing(point_a, point_b)."""
import unittest

from calculate_bearing import calculate_bearing

ORIGIN = (0, 0)


class CalculateBearingErrorPoints(unittest.TestCase):

    def test_north(self):
        self.assertAlmostEqual(calculate_bearing(ORIGIN, (1, 0)), 0.0)

    def test_east(self):
        self.assertAlmostEqual(calculate_bearing(ORIGIN, (0, 1)), 90.0)

    def test_south(self):
        self.assertAlmostEqual(calculate_bearing(ORIGIN, (-1, 0)), 180.0)

    # ERROR POINT: atan2 returns -90 for west; it must be shifted to 270
    def test_west_is_270_not_negative(self):
        self.assertAlmostEqual(calculate_bearing(ORIGIN, (0, -1)), 270.0)

    def test_northwest_is_in_fourth_quadrant(self):
        bearing = calculate_bearing(ORIGIN, (1, -1))
        self.assertTrue(270 < bearing < 360, bearing)

    # ERROR POINT: haven't moved yet (first reading == origin). Docstring says 0.0.
    def test_same_point_returns_zero(self):
        self.assertEqual(calculate_bearing((33.7861, -84.2695), (33.7861, -84.2695)), 0.0)

    # ERROR POINT: result must always be in [0, 360), never negative and never 360
    def test_result_always_between_0_and_360(self):
        points = [(lat, lon) for lat in range(-80, 81, 20) for lon in range(-180, 181, 45)]
        for a in points:
            for b in points:
                bearing = calculate_bearing(a, b)
                self.assertGreaterEqual(bearing, 0.0, (a, b))
                self.assertLess(bearing, 360.0, (a, b))

    # ERROR POINT: crossing the 180 degree line. Going from 179.9 E to 179.9 W
    # is a short hop EAST, not a trip west around the planet.
    def test_crossing_the_antimeridian_eastward(self):
        self.assertAlmostEqual(calculate_bearing((0, 179.9), (0, -179.9)), 90.0)

    def test_crossing_the_antimeridian_westward(self):
        self.assertAlmostEqual(calculate_bearing((0, -179.9), (0, 179.9)), 270.0)

    # ERROR POINT: at the poles, every direction is south (or north)
    def test_from_north_pole_everything_is_south(self):
        self.assertAlmostEqual(calculate_bearing((90, 0), (0, 0)), 180.0)

    def test_from_south_pole_everything_is_north(self):
        self.assertAlmostEqual(calculate_bearing((-90, 0), (0, 0)) % 360, 0.0)

    # ERROR POINT: argument order. Swapping origin and current flips the
    # direction by 180 degrees.
    def test_argument_order_matters(self):
        self.assertAlmostEqual(calculate_bearing((0, 0), (0, 1)), 90.0)
        self.assertAlmostEqual(calculate_bearing((0, 1), (0, 0)), 270.0)

    # ERROR POINT: missing reading passed in
    def test_none_point_raises(self):
        with self.assertRaises(TypeError):
            calculate_bearing(ORIGIN, None)


if __name__ == "__main__":
    unittest.main()
