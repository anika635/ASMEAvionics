"""Error points for wait_for_fix(gps)."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from wait_for_fix import wait_for_fix

FIX = Mock(lat=337861000, lon=-842695000)
NO_FIX = Mock(lat=0, lon=0)


class NeverGaveUp(Exception):
    """Raised by the patched sleep to break out of an endless loop."""


def quiet(func, *args):
    with redirect_stdout(io.StringIO()):
        return func(*args)


@patch("wait_for_fix.time.sleep")
class WaitForFixErrorPoints(unittest.TestCase):

    def test_returns_immediately_when_fix_is_ready(self, sleep):
        gps = Mock()
        gps.recv_match.return_value = FIX

        self.assertEqual(quiet(wait_for_fix, gps), (33.7861, -84.2695))
        sleep.assert_not_called()

    # ERROR POINT: GPS takes several tries to lock (timeouts, then 0,0, then a fix)
    def test_retries_through_timeouts_and_zero_fixes(self, sleep):
        gps = Mock()
        gps.recv_match.side_effect = [None, NO_FIX, None, NO_FIX, FIX]

        self.assertEqual(quiet(wait_for_fix, gps), (33.7861, -84.2695))
        self.assertEqual(sleep.call_count, 4)
        sleep.assert_called_with(1)

    def test_accepts_a_location_function(self, sleep):
        readings = iter([None, None, (33.7861, -84.2695)])

        self.assertEqual(quiet(wait_for_fix, lambda: next(readings)), (33.7861, -84.2695))
        self.assertEqual(sleep.call_count, 2)

    # ERROR POINT: connect_gps() returned None. This crashes straight away
    # (good: it does not hang forever on a dead connection).
    def test_none_connection_raises_instead_of_hanging(self, sleep):
        with self.assertRaises(AttributeError):
            quiet(wait_for_fix, None)
        sleep.assert_not_called()

    # ERROR POINT: cable pulled while waiting
    def test_serial_error_while_waiting_propagates(self, sleep):
        gps = Mock()
        gps.recv_match.side_effect = [None, OSError("device disconnected")]

        with self.assertRaises(OSError):
            quiet(wait_for_fix, gps)

    # FIXED BUG: there was no timeout. If the GPS never locked (indoors,
    # antenna unplugged), wait_for_fix looped forever and the program hung.
    # This test lets it try 100 times before declaring it stuck.
    def test_gives_up_if_gps_never_locks(self, sleep):
        gps = Mock()
        gps.recv_match.return_value = None
        sleep.side_effect = [None] * 100 + [NeverGaveUp()]

        try:
            result = quiet(wait_for_fix, gps)
        except TimeoutError:
            return
        except NeverGaveUp:
            self.fail("wait_for_fix kept waiting after 100 failed readings")
        self.assertIsNone(result)

    def test_default_gives_up_after_60_attempts(self, sleep):
        gps = Mock()
        gps.recv_match.return_value = None

        self.assertIsNone(quiet(wait_for_fix, gps))
        self.assertEqual(gps.recv_match.call_count, 60)
        self.assertEqual(sleep.call_count, 59)  # no pause after the last try

    def test_custom_max_attempts(self, sleep):
        readings = iter([None] * 10)

        self.assertIsNone(quiet(wait_for_fix, lambda: next(readings), 3))
        self.assertEqual(sleep.call_count, 2)

    def test_fix_on_last_attempt_is_still_used(self, sleep):
        gps = Mock()
        gps.recv_match.side_effect = [None, None, FIX]

        self.assertEqual(quiet(wait_for_fix, gps, 3), (33.7861, -84.2695))

    def test_max_attempts_none_waits_until_fix(self, sleep):
        gps = Mock()
        gps.recv_match.side_effect = [None] * 200 + [FIX]

        self.assertEqual(quiet(wait_for_fix, gps, None), (33.7861, -84.2695))
        self.assertEqual(sleep.call_count, 200)

    def test_says_when_it_gives_up(self, sleep):
        gps = Mock()
        gps.recv_match.return_value = None
        out = io.StringIO()

        with redirect_stdout(out):
            wait_for_fix(gps, max_attempts=2)

        self.assertIn("No GPS fix after 2 attempts", out.getvalue())


if __name__ == "__main__":
    unittest.main()
