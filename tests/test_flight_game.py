"""
Simulated drone flights, run automatically.

Each test flies tests/flight_game.py with a scripted set of W/A/S/D presses
over a real local MAVLink (UDP) link, then checks the log files it wrote.
"""
import csv
import io
import math
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stdout

from haversine_distance import haversine_distance
from should_save import HUNDRED_FEET_METERS
from tests.flight_game import (
    AUTOPILOT_ROUTE, SAVE_EVERY_M, SPEEDS, FlightGame, check_flight_logs,
)

HOME = (33.7861, -84.2695)
STEP = SPEEDS["2"]  # default speed, meters per key press
# key presses that stay just under / just over the save distance
PRESSES_UNDER = math.ceil(SAVE_EVERY_M / STEP) - 1
PRESSES_OVER = PRESSES_UNDER + 1


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class SimulatedFlightTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.stop()
        self.tmp.cleanup()

    def launch(self, no_lock_reads=0, fix_attempts=10, save_every_m=SAVE_EVERY_M):
        game = FlightGame(
            port=free_udp_port(), home=HOME, output_dir=self.tmp.name,
            no_lock_reads=no_lock_reads, fix_attempts=fix_attempts, render=False,
            save_every_m=save_every_m,
        )
        self.games.append(game)
        with redirect_stdout(io.StringIO()):
            started = game.start()
        return game, started

    # ---- launch ----------------------------------------------------------

    def test_launch_position_is_logged(self):
        game, started = self.launch()
        self.assertTrue(started, game.event)

        rows = read_rows(game.launch_path)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(float(rows[0]["latitude"]), HOME[0], places=6)
        self.assertAlmostEqual(float(rows[0]["longitude"]), HOME[1], places=6)

    def test_launch_point_is_first_saved_entry(self):
        game, _ = self.launch()

        rows = read_rows(game.locations_path)
        self.assertEqual(len(rows), 1)
        self.assertLess(float(rows[0]["distance_m"]), 1)

    # ERROR POINT: GPS takes a few readings to lock before takeoff
    def test_waits_through_no_lock_then_launches(self):
        game, started = self.launch(no_lock_reads=2)

        self.assertTrue(started, game.event)
        self.assertAlmostEqual(game.origin[0], HOME[0], places=6)

    # ERROR POINT: GPS never locks. Launch is aborted (no hang), and no
    # launch position is written.
    def test_no_gps_lock_aborts_launch(self):
        game, started = self.launch(no_lock_reads=1000, fix_attempts=2)

        self.assertFalse(started)
        self.assertIn("No GPS lock", game.event)
        self.assertFalse(os.path.exists(game.launch_path))

    # ---- controls ---------------------------------------------------------

    def test_wasd_moves_the_drone(self):
        game, _ = self.launch()

        s = STEP
        for key, expected in [("w", (s, 0)), ("d", (s, s)), ("s", (0, s)), ("a", (0, 0))]:
            game.handle_key(key)
            self.assertEqual((game.drone.north_m, game.drone.east_m), expected)

    def test_speed_keys(self):
        game, _ = self.launch()

        game.handle_key("3")
        game.handle_key("w")
        self.assertEqual(game.drone.north_m, SPEEDS["3"])
        game.handle_key("1")
        game.handle_key("w")
        self.assertEqual(game.drone.north_m, SPEEDS["3"] + SPEEDS["1"])

    def test_uppercase_keys_work(self):
        game, _ = self.launch()
        game.handle_key("W")
        self.assertEqual(game.drone.north_m, STEP)

    def test_q_lands(self):
        game, _ = self.launch()
        game.run_scripted("wwq" + "w" * 20)
        self.assertFalse(game.running)
        self.assertEqual(game.drone.north_m, 2 * STEP)

    # ---- flying and logging -----------------------------------------------

    def test_reported_position_matches_where_drone_flew(self):
        game, _ = self.launch()

        game.run_scripted("3" + "w" * 5 + "d" * 5)  # 50 m N, 50 m E

        leg = 5 * SPEEDS["3"]
        self.assertLess(haversine_distance(game.current, game.drone.true_position()), 0.1)
        self.assertAlmostEqual(
            haversine_distance(game.origin, game.current), leg * math.sqrt(2), delta=0.1
        )

    def test_short_hops_do_not_save(self):
        game, _ = self.launch()

        game.run_scripted("w" * PRESSES_UNDER)  # just under 10 m

        self.assertEqual(len(game.saves), 1)

    def test_saves_once_past_10_m(self):
        game, _ = self.launch()

        game.run_scripted("w" * PRESSES_OVER)  # just over 10 m

        self.assertEqual(len(game.saves), 2)
        self.assertGreaterEqual(game.saves[1]["distance_m"], SAVE_EVERY_M)
        self.assertAlmostEqual(game.saves[1]["bearing_deg"], 0.0, places=0)

    def test_saves_every_10_m_in_a_straight_line(self):
        game, _ = self.launch()

        game.handle_key("1")  # 1 m steps
        game.run_scripted("w" * 100)

        # GPS reports position to ~1 cm (degrees x 1e7), so a save lands on
        # the 10 m step or, if rounding leaves it at 9.99 m, the 11 m step
        gaps = [b["distance_m"] - a["distance_m"] for a, b in zip(game.saves, game.saves[1:])]
        for gap in gaps:
            self.assertGreaterEqual(gap, 10 - 0.1)  # 0.1 = rounding in the log
            self.assertLessEqual(gap, 11 + 0.1)
        self.assertGreaterEqual(len(game.saves), 1 + 100 // 11)
        self.assertLessEqual(len(game.saves), 1 + 100 // 10)

    def test_real_100_feet_mode(self):
        game, _ = self.launch(save_every_m=HUNDRED_FEET_METERS)

        game.run_scripted("3" + "w" * 3)  # 30 m, just under 100 ft
        self.assertEqual(len(game.saves), 1)
        game.run_scripted("w")  # 40 m
        self.assertEqual(len(game.saves), 2)

    # ERROR POINT: GPS drops out mid-flight. Nothing is saved while lost,
    # and the next good reading is saved as soon as it comes back.
    def test_gps_loss_mid_flight(self):
        game, _ = self.launch()

        game.run_scripted("g" + "w" * 40)  # 120 m with no GPS
        self.assertEqual(len(game.saves), 1)

        game.run_scripted("g")  # signal back
        self.assertEqual(len(game.saves), 2)
        self.assertAlmostEqual(game.saves[1]["distance_m"], 40 * STEP, delta=0.1)

    def test_full_autopilot_route(self):
        game, _ = self.launch()

        game.run_scripted(AUTOPILOT_ROUTE)
        game.stop()
        self.games.remove(game)

        problems = check_flight_logs(game.launch_path, game.locations_path)
        self.assertEqual(problems, [])
        # Launch point + one save about every 10 m (a bit more, since a save
        # happens on the first step that reaches 10 m)
        route_m = game.flown_m
        self.assertEqual(route_m, 140 * STEP)
        self.assertGreaterEqual(len(game.saves), int(route_m // (SAVE_EVERY_M + STEP)))
        self.assertLessEqual(len(game.saves), 1 + int(route_m // SAVE_EVERY_M))
        self.assertEqual(len(read_rows(game.launch_path)), 1)

    def test_log_checker_catches_bad_logs(self):
        launch = os.path.join(self.tmp.name, "launch.txt")
        locations = os.path.join(self.tmp.name, "loc.txt")
        with open(launch, "w", newline="") as f:
            f.write("timestamp,latitude,longitude\nt,33.7861,-84.2695\n")
        with open(locations, "w", newline="") as f:
            f.write("timestamp,latitude,longitude,distance_m,bearing_deg,north_m,east_m\n")
            f.write("t1,33.7861,-84.2695,0,0,0,0\n")
            f.write("t2,33.78614,-84.2695,4.4,0,4.4,0\n")  # only ~4 m later

        problems = check_flight_logs(launch, locations)
        self.assertTrue(any("apart" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
