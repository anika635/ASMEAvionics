import tempfile
import unittest
from unittest.mock import Mock, patch

from calculate_bearing import calculate_bearing
from connect_gps import connect_gps
from get_current_location import get_current_location
from haversine_distance import haversine_distance
from location_logger import init_output_file, save_location
from set_origin import set_origin
from should_save import should_save
from wait_for_fix import wait_for_fix


class GPSFunctionTests(unittest.TestCase):
    
    #Checking this to make sure values work
    def test_get_current_location_converts_coordinates(self):
        message = Mock(lat=337861000, lon=-842695000)
        gps = Mock()
        gps.recv_match.return_value = message
        print("Testing get_current_location with valid coordinates...")

        self.assertEqual(
            get_current_location(gps),
            (33.7861, -84.2695),
        )

    def test_get_current_location_rejects_missing_and_zero_fix(self):
        gps = Mock()
        gps.recv_match.return_value = None
        self.assertIsNone(get_current_location(gps))

        gps.recv_match.return_value = Mock(lat=0, lon=0)
        self.assertIsNone(get_current_location(gps))

    def test_bearing_cardinal_directions(self):
        self.assertEqual(calculate_bearing((0, 0), (1, 0)), 0.0)
        self.assertEqual(calculate_bearing((0, 0), (0, 1)), 90.0)

    def test_haversine_known_distance(self):
        distance = haversine_distance((0, 0), (0, 1))
        self.assertAlmostEqual(distance, 111194.92664455874, places=6)

    def test_should_save_states(self):
        point = (33.7861, -84.2695)
        self.assertFalse(should_save(None, None))
        self.assertTrue(should_save(None, point))
        self.assertFalse(should_save(point, point))

    def test_set_origin(self):
        gps = Mock()
        gps.recv_match.return_value = Mock(lat=337861000, lon=-842695000)
        self.assertEqual(set_origin(gps), (33.7861, -84.2695))
        self.assertIsNone(set_origin(None))

    @patch("connect_gps.mavutil.mavlink_connection")
    def test_connect_gps_heartbeat_success_and_failure(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = object()
        mavlink_connection.return_value = gps
        self.assertIs(connect_gps("COM3"), gps)

        gps.wait_heartbeat.return_value = None
        self.assertIsNone(connect_gps("COM3"))

    @patch("wait_for_fix.time.sleep")
    def test_wait_for_fix_accepts_gps_connection(self, sleep):
        gps = Mock()
        gps.recv_match.side_effect = [
            None,
            Mock(lat=337861000, lon=-842695000),
        ]

        self.assertEqual(wait_for_fix(gps), (33.7861, -84.2695))
        sleep.assert_called_once_with(1)

    @patch("wait_for_fix.time.sleep")
    def test_wait_for_fix_accepts_location_callback(self, sleep):
        locations = iter([None, (33.7861, -84.2695)])

        self.assertEqual(wait_for_fix(lambda: next(locations)), (33.7861, -84.2695))
        sleep.assert_called_once_with(1)

    def test_location_file_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/locations.txt"
            init_output_file(path)
            save_location(
                {
                    "timestamp": "2026-11-18",
                    "latitude": 33.7861,
                    "longitude": -84.2695,
                    "distance_m": 100,
                    "bearing_deg": 45,
                    "north_m": 70,
                    "east_m": 70,
                },
                path,
            )

            with open(path, "r", newline="") as file:
                contents = file.read()

            self.assertIn("timestamp,latitude,longitude", contents)
            self.assertIn("33.7861,-84.2695", contents)


if __name__ == "__main__":
    unittest.main()
