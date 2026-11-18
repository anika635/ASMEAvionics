"""Error points for set_origin(gps)."""
import unittest
from unittest.mock import Mock

from set_origin import set_origin


class SetOriginErrorPoints(unittest.TestCase):

    def test_returns_current_location(self):
        gps = Mock()
        gps.recv_match.return_value = Mock(lat=337861000, lon=-842695000)

        self.assertEqual(set_origin(gps), (33.7861, -84.2695))

    # ERROR POINT: connect_gps() failed
    def test_none_connection_returns_none(self):
        self.assertIsNone(set_origin(None))

    # ERROR POINT: called before the GPS has locked. set_origin takes ONE
    # reading and does not wait, so the origin comes back as None.
    # main() should call wait_for_fix() first, or retry until it is not None.
    def test_no_fix_yet_returns_none_without_waiting(self):
        gps = Mock()
        gps.recv_match.return_value = Mock(lat=0, lon=0)

        self.assertIsNone(set_origin(gps))
        gps.recv_match.assert_called_once()

    def test_timeout_returns_none(self):
        gps = Mock()
        gps.recv_match.return_value = None

        self.assertIsNone(set_origin(gps))


if __name__ == "__main__":
    unittest.main()
