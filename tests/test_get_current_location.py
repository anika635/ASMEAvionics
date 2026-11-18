"""Error points for get_current_location(gps)."""
import unittest
from unittest.mock import Mock

from get_current_location import get_current_location


def fake_gps(lat=None, lon=None):
    """A gps connection whose next GLOBAL_POSITION_INT has these raw values.
    Pass nothing to simulate recv_match timing out."""
    gps = Mock()
    gps.recv_match.return_value = None if lat is None else Mock(lat=lat, lon=lon)
    return gps


class GetCurrentLocationErrorPoints(unittest.TestCase):

    def test_converts_raw_degE7_to_decimal_degrees(self):
        self.assertEqual(
            get_current_location(fake_gps(337861000, -842695000)),
            (33.7861, -84.2695),
        )

    def test_asks_for_the_right_message_with_a_timeout(self):
        gps = fake_gps(337861000, -842695000)

        get_current_location(gps)

        gps.recv_match.assert_called_once_with(
            type="GLOBAL_POSITION_INT", blocking=True, timeout=2
        )

    # ERROR POINT: no message within 2 seconds (Cube stopped streaming, link dropped)
    def test_timeout_returns_none(self):
        self.assertIsNone(get_current_location(fake_gps()))

    # ERROR POINT: Cube is streaming but has no GPS lock yet; it reports 0, 0
    def test_zero_zero_means_no_fix(self):
        self.assertIsNone(get_current_location(fake_gps(0, 0)))

    # ERROR POINT: the 0,0 check must not throw away real points on the
    # equator or the prime meridian
    def test_equator_is_still_valid(self):
        self.assertEqual(get_current_location(fake_gps(0, 123456789)), (0.0, 12.3456789))

    def test_prime_meridian_is_still_valid(self):
        self.assertEqual(get_current_location(fake_gps(515000000, 0)), (51.5, 0.0))

    def test_southern_and_western_hemispheres(self):
        self.assertEqual(
            get_current_location(fake_gps(-338688000, -1512093000)),
            (-33.8688, -151.2093),
        )

    # ERROR POINT: connect_gps() failed and returned None, and the caller
    # passed it straight in. This crashes; callers must check for None first.
    def test_none_connection_raises(self):
        with self.assertRaises(AttributeError):
            get_current_location(None)

    # ERROR POINT: USB cable pulled mid-read. The error is not caught here,
    # so main() has to handle it.
    def test_serial_error_during_read_propagates(self):
        gps = Mock()
        gps.recv_match.side_effect = OSError("device disconnected")

        with self.assertRaises(OSError):
            get_current_location(gps)


if __name__ == "__main__":
    unittest.main()
