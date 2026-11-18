"""Error points for connect_gps(port, baud)."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from connect_gps import connect_gps


@patch("connect_gps.mavutil.mavlink_connection")
class ConnectGPSErrorPoints(unittest.TestCase):

    def call_quietly(self, *args, **kwargs):
        """Runs connect_gps and captures what it prints."""
        out = io.StringIO()
        with redirect_stdout(out):
            result = connect_gps(*args, **kwargs)
        return result, out.getvalue()

    def test_success_returns_connection(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = object()
        mavlink_connection.return_value = gps

        result, _ = self.call_quietly("COM3")

        self.assertIs(result, gps)

    def test_passes_port_baud_and_heartbeat_timeout(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = object()
        mavlink_connection.return_value = gps

        self.call_quietly("COM7", baud=57600)

        mavlink_connection.assert_called_once_with("COM7", baud=57600)
        gps.wait_heartbeat.assert_called_once_with(timeout=10)

    # ERROR POINT: wrong COM port / cable unplugged / port in use by Mission Planner
    def test_port_cannot_be_opened_returns_none(self, mavlink_connection):
        mavlink_connection.side_effect = OSError("could not open port COM3")

        result, printed = self.call_quietly("COM3")

        self.assertIsNone(result)
        self.assertIn("Failed to connect to GPS", printed)

    # ERROR POINT: malformed connection string
    def test_bad_connection_string_returns_none(self, mavlink_connection):
        mavlink_connection.side_effect = ValueError("bad connection string")

        result, printed = self.call_quietly("not-a-port")

        self.assertIsNone(result)
        self.assertIn("Failed to connect to GPS", printed)

    # ERROR POINT: port opens but the Cube never sends a heartbeat
    # (wrong baud rate, Cube not powered, wrong TELEM port)
    def test_no_heartbeat_returns_none(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = None
        mavlink_connection.return_value = gps

        result, printed = self.call_quietly("COM3")

        self.assertIsNone(result)
        self.assertIn("no data received", printed)

    # ERROR POINT: cable pulled while waiting for the heartbeat
    def test_disconnect_during_heartbeat_returns_none(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.side_effect = OSError("device disconnected")
        mavlink_connection.return_value = gps

        result, _ = self.call_quietly("COM3")

        self.assertIsNone(result)

    # FIXED BUG: when the heartbeat never arrived, the serial port was left
    # open, so a retry on the same COM port failed with "Access is denied".
    def test_no_heartbeat_closes_the_port(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = None
        mavlink_connection.return_value = gps

        self.call_quietly("COM3")

        gps.close.assert_called_once()

    def test_disconnect_during_heartbeat_closes_the_port(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.side_effect = OSError("device disconnected")
        mavlink_connection.return_value = gps

        self.call_quietly("COM3")

        gps.close.assert_called_once()

    def test_close_failing_still_returns_none(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = None
        gps.close.side_effect = OSError("already gone")
        mavlink_connection.return_value = gps

        result, _ = self.call_quietly("COM3")

        self.assertIsNone(result)

    def test_success_does_not_close_the_port(self, mavlink_connection):
        gps = Mock()
        gps.wait_heartbeat.return_value = object()
        mavlink_connection.return_value = gps

        self.call_quietly("COM3")

        gps.close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
