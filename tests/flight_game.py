"""
Drone flight simulator: fly with W/A/S/D in the terminal.

This drives the REAL project code end to end:

    simulated drone --(MAVLink over UDP)--> connect_gps()
                                            wait_for_fix()
                                            set_origin()  -> save_launch_position()
                                            get_current_location()
                                            should_save() -> save_location()

The only fake part is the drone. It sends HEARTBEAT and GLOBAL_POSITION_INT
messages exactly like the Cube Orange+ does, over a local UDP port instead of
a USB cable.

Run from the project folder:
    python tests/flight_game.py              # you fly
    python tests/flight_game.py --autopilot  # watch it fly a preset route

Controls:
    W / A / S / D (or arrow keys)   fly north / west / south / east
    1 / 2 / 3                       speed: 1 / 3 / 10 meters per step
    G                               toggle GPS signal loss
    Q                               land and quit

The game saves an entry every 10 m (SAVE_EVERY_M) so you can see saves
happen quickly. The real program still uses should_save()'s default of
0.5 mile. Change it with --save-every, e.g. --save-every 804.672.

Output (overwritten each run):
    tests/sim_output/launch_position.txt
    tests/sim_output/locations.txt
"""
import argparse
import math
import os
import sys
import threading
import time
from datetime import datetime

# Allow `python tests/flight_game.py` to find the project modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pymavlink import mavutil  # noqa: E402

from calculate_bearing import calculate_bearing  # noqa: E402
from connect_gps import connect_gps  # noqa: E402
from get_current_location import get_current_location  # noqa: E402
from haversine_distance import haversine_distance  # noqa: E402
from location_logger import init_output_file, save_launch_position, save_location  # noqa: E402
from set_origin import set_origin  # noqa: E402
from should_save import should_save  # noqa: E402
from wait_for_fix import wait_for_fix  # noqa: E402

EARTH_RADIUS_M = 6371000
DEFAULT_HOME = (33.7861, -84.2695)
DEFAULT_PORT = 14560  # not 14550, so it won't clash with Mission Planner
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "tests", "sim_output")
SAVE_EVERY_M = 10  # game save distance; the real program uses 0.5 mile
SPEEDS = {"1": 1, "2": 3, "3": 10}
MOVES = {"w": (1, 0), "s": (-1, 0), "d": (0, 1), "a": (0, -1)}
HEADING_ICON = {"w": "^", "s": "v", "d": ">", "a": "<"}

# 120 m north, 90 m east, lose GPS for 36 m, 120 m south, 90 m west home
AUTOPILOT_ROUTE = "2" + "w" * 40 + "d" * 30 + "g" + "s" * 12 + "g" + "s" * 28 + "a" * 30


# --------------------------------------------------------------------------
# The simulated drone (stands in for the Cube Orange+ and Here GPS)
# --------------------------------------------------------------------------

class SimDrone:
    """Sends MAVLink to the logger like a real flight controller would."""

    def __init__(self, port, home=DEFAULT_HOME, no_lock_reads=3):
        self.home = home
        self.north_m = 0.0
        self.east_m = 0.0
        self.gps_lost = False
        self.no_lock_reads = no_lock_reads  # GPS readings sent before it locks
        self.reads_sent = 0
        self.started = time.monotonic()
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._heartbeat_thread = None
        self.link = mavutil.mavlink_connection(
            f"udpout:127.0.0.1:{port}", source_system=1, source_component=1
        )

    def move(self, direction, meters):
        dn, de = MOVES[direction]
        self.north_m += dn * meters
        self.east_m += de * meters

    def true_position(self):
        """Where the drone really is (flat-earth offset from home)."""
        lat0, lon0 = self.home
        lat = lat0 + math.degrees(self.north_m / EARTH_RADIUS_M)
        lon = lon0 + math.degrees(self.east_m / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
        return lat, lon

    def has_lock(self):
        return self.reads_sent > self.no_lock_reads and not self.gps_lost

    def transmit_position(self):
        """Sends one GLOBAL_POSITION_INT. Reports 0,0 when there's no GPS lock,
        which is what ArduPilot does before the GPS has a fix."""
        self.reads_sent += 1
        if self.has_lock():
            lat, lon = self.true_position()
            lat_e7, lon_e7 = int(round(lat * 1e7)), int(round(lon * 1e7))
        else:
            lat_e7 = lon_e7 = 0
        boot_ms = int((time.monotonic() - self.started) * 1000) & 0xFFFFFFFF
        with self._send_lock:
            self.link.mav.global_position_int_send(
                boot_ms, lat_e7, lon_e7, 300000, 50000, 0, 0, 0, 65535
            )

    def _heartbeat_loop(self):
        while not self._stop.is_set():
            with self._send_lock:
                self.link.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_QUADROTOR,
                    mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                    0, 0, mavutil.mavlink.MAV_STATE_ACTIVE,
                )
            self._stop.wait(0.25)

    def power_on(self):
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def power_off(self):
        self._stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1)
        self.link.close()


# --------------------------------------------------------------------------
# Logger side (what main() will do on the real drone)
# --------------------------------------------------------------------------

def build_entry(origin, current):
    """Stand-in for the planned build_entry(); not written in the project yet."""
    distance = haversine_distance(origin, current)
    bearing = calculate_bearing(origin, current)
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "latitude": round(current[0], 7),
        "longitude": round(current[1], 7),
        "distance_m": round(distance, 1),
        "bearing_deg": round(bearing, 1),
        "north_m": round(distance * math.cos(math.radians(bearing)), 1),
        "east_m": round(distance * math.sin(math.radians(bearing)), 1),
    }


class FlightGame:
    def __init__(self, port=DEFAULT_PORT, home=DEFAULT_HOME, output_dir=OUTPUT_DIR,
                 no_lock_reads=3, fix_attempts=10, render=True,
                 save_every_m=SAVE_EVERY_M):
        self.port = port
        self.save_every_m = save_every_m
        self.render_enabled = render
        self.fix_attempts = fix_attempts
        self.launch_path = os.path.join(output_dir, "launch_position.txt")
        self.locations_path = os.path.join(output_dir, "locations.txt")
        os.makedirs(output_dir, exist_ok=True)

        self.drone = SimDrone(port, home, no_lock_reads)
        self.gps = None
        self.origin = None
        self.current = None
        self.last_saved = None
        self.saves = []
        self.trail = []
        self.step_m = SPEEDS["2"]
        self.heading = "^"
        self.flown_m = 0.0
        self.event = "Powering on"
        self.running = False

    # ---- startup ---------------------------------------------------------

    def read_gps(self):
        """The drone sends one position, and the logger reads it with the
        real get_current_location()."""
        self.drone.transmit_position()
        return get_current_location(self.gps)

    def start(self):
        """Connect, wait for GPS lock, record launch position.
        Returns True if ready to fly."""
        for path in (self.launch_path, self.locations_path):
            if os.path.exists(path):
                os.remove(path)

        self.drone.power_on()
        self.gps = connect_gps(f"udpin:127.0.0.1:{self.port}")
        if self.gps is None:
            self.event = "Could not connect to the drone"
            return False

        if wait_for_fix(self.read_gps, max_attempts=self.fix_attempts) is None:
            self.event = "No GPS lock, launch aborted"
            return False

        self.drone.transmit_position()
        self.origin = set_origin(self.gps)
        if self.origin is None:
            self.event = "Lost GPS while setting origin, launch aborted"
            return False

        save_launch_position(self.origin, self.launch_path)
        init_output_file(self.locations_path)
        self.current = self.origin
        self.running = True
        self.event = "Launched. Launch position logged."
        self.tick()  # first point gets saved straight away
        return True

    def stop(self):
        self.running = False
        if self.gps is not None:
            self.gps.close()
        self.drone.power_off()

    # ---- game loop -------------------------------------------------------

    def handle_key(self, key):
        key = key.lower()
        if key in MOVES:
            self.drone.move(key, self.step_m)
            self.flown_m += self.step_m
            self.heading = HEADING_ICON[key]
        elif key in SPEEDS:
            self.step_m = SPEEDS[key]
            self.event = f"Speed set to {self.step_m} m per step"
        elif key == "g":
            self.drone.gps_lost = not self.drone.gps_lost
            self.event = "GPS SIGNAL LOST" if self.drone.gps_lost else "GPS signal back"
        elif key in ("q", "\x03", "\x1b"):
            self.running = False
            self.event = "Landing"

    def tick(self):
        """One GPS read + save check, like one pass of main()'s loop."""
        reading = self.read_gps()
        if reading is not None:
            self.current = reading
            self.trail.append(reading)
        if should_save(self.last_saved, reading, threshold=self.save_every_m):
            entry = build_entry(self.origin, reading)
            save_location(entry, self.locations_path)
            self.last_saved = reading
            self.saves.append(entry)
            self.event = f"SAVED entry #{len(self.saves)} ({entry['distance_m']:.0f} m from launch)"

    def run_scripted(self, keys, delay=0.0):
        """Flies a string of key presses (used by the tests and --autopilot)."""
        for key in keys:
            if not self.running:
                break
            self.handle_key(key)
            self.tick()
            if self.render_enabled:
                self.render()
                time.sleep(delay)

    def run_interactive(self):
        with KeyReader() as keys:
            while self.running:
                for key in keys.pending():
                    self.handle_key(key)
                self.tick()
                self.render()
                time.sleep(0.08)

    # ---- drawing ---------------------------------------------------------

    def offset_m(self, point):
        """(north, east) meters of point from the launch position."""
        d = haversine_distance(self.origin, point)
        b = math.radians(calculate_bearing(self.origin, point))
        return d * math.cos(b), d * math.sin(b)

    def draw_map(self, cols=31, rows=15):
        pts = [(0.0, 0.0)] + [self.offset_m(p) for p in self.trail[-400:]]
        extent = max([4 * self.save_every_m] + [max(abs(n), abs(e)) for n, e in pts]) * 1.15
        per_cell = max(extent / (cols // 2), extent / (rows // 2))
        grid = [[" "] * cols for _ in range(rows)]

        def plot(n, e, ch):
            c = cols // 2 + int(round(e / per_cell))
            r = rows // 2 - int(round(n / per_cell))
            if 0 <= r < rows and 0 <= c < cols:
                grid[r][c] = ch

        for n, e in pts[1:]:
            plot(n, e, ".")
        for s in self.saves:
            plot(s["north_m"], s["east_m"], "*")
        plot(0, 0, "H")
        plot(*self.offset_m(self.current), "X" if self.drone.gps_lost else self.heading)

        border = "+" + "-" * (cols * 2) + "+"
        lines = [border] + ["|" + "".join(ch + " " for ch in row) + "|" for row in grid] + [border]
        lines.append(f"  1 cell = {per_cell:.1f} m    H launch   * saved   . path   N is up")
        return lines

    def render(self):
        here = self.current
        dist = haversine_distance(self.origin, here)
        bearing = calculate_bearing(self.origin, here)
        n, e = self.offset_m(here)
        since = haversine_distance(self.last_saved, here) if self.last_saved else 0.0
        filled = min(20, int(20 * since / self.save_every_m))
        gps = "LOST (no fix)" if self.drone.gps_lost else "LOCKED"

        lines = [
            "  ASME AVIONICS  //  DRONE FLIGHT SIM" + " " * 18 + f"GPS: {gps}",
            *self.draw_map(),
            f"  Position    {here[0]:.6f}, {here[1]:.6f}",
            f"  From launch {dist:8.1f} m   bearing {bearing:05.1f} deg   (N {n:+.0f} m, E {e:+.0f} m)",
            f"  Next save   [{'#' * filled}{'-' * (20 - filled)}] {since:6.1f} / {self.save_every_m:g} m",
            f"  Saved       {len(self.saves)} entries    flown {self.flown_m:.0f} m    speed {self.step_m} m/step",
            f"  Launch      {self.origin[0]:.6f}, {self.origin[1]:.6f}  (logged)",
            f"  >> {self.event}",
            "  W/A/S/D fly   1/2/3 speed   G toggle GPS loss   Q land",
        ]
        sys.stdout.write("\033[H" + "\n".join(line + "\033[K" for line in lines) + "\n\033[J")
        sys.stdout.flush()


# --------------------------------------------------------------------------
# Checking the logs after a flight
# --------------------------------------------------------------------------

def check_flight_logs(launch_path, locations_path, threshold=SAVE_EVERY_M):
    """Reads the two log files back and returns a list of problems (empty = all good)."""
    import csv

    problems = []
    if not os.path.exists(launch_path):
        return ["launch_position.txt was not written"]
    with open(launch_path, newline="") as f:
        launch_rows = list(csv.DictReader(f))
    if not launch_rows:
        return ["launch_position.txt has no launch row"]
    launch = (float(launch_rows[-1]["latitude"]), float(launch_rows[-1]["longitude"]))

    with open(locations_path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return ["locations.txt has no entries"]

    points = [(float(r["latitude"]), float(r["longitude"])) for r in rows]
    if any(p == (0.0, 0.0) for p in points):
        problems.append("a 0,0 (no fix) point was saved")
    if haversine_distance(launch, points[0]) > 1:
        problems.append("first entry is not at the launch position")
    for i in range(1, len(points)):
        gap = haversine_distance(points[i - 1], points[i])
        if gap < threshold:
            problems.append(f"entries {i} and {i + 1} are only {gap:.0f} m apart")
    for r, p in zip(rows, points):
        if abs(float(r["distance_m"]) - haversine_distance(launch, p)) > 0.5:
            problems.append(f"distance_m wrong in row at {r['timestamp']}")
    return problems


# --------------------------------------------------------------------------
# Keyboard input without pressing Enter (Windows + Mac/Linux)
# --------------------------------------------------------------------------

class KeyReader:
    ARROWS = {"H": "w", "P": "s", "K": "a", "M": "d", "A": "w", "B": "s", "D": "a", "C": "d"}

    def __enter__(self):
        if os.name == "nt":
            import msvcrt
            self._msvcrt = msvcrt
        else:
            import termios
            import tty
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, *exc):
        if os.name != "nt":
            import termios
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def pending(self):
        keys = []
        if os.name == "nt":
            while self._msvcrt.kbhit():
                ch = self._msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # arrow keys come as two characters
                    ch = self.ARROWS.get(self._msvcrt.getwch(), "")
                keys.append(ch)
        else:
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x1b" and select.select([sys.stdin], [], [], 0.01)[0]:
                    sys.stdin.read(1)
                    ch = self.ARROWS.get(sys.stdin.read(1), "")
                keys.append(ch)
        return [k for k in keys if k]


# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fly a simulated drone with W/A/S/D.")
    parser.add_argument("--autopilot", action="store_true", help="fly a preset route by itself")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="local UDP port for the sim link")
    parser.add_argument("--save-every", type=float, default=SAVE_EVERY_M,
                        help="meters between saved entries (default 10)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="folder for launch_position.txt and locations.txt")
    args = parser.parse_args()

    if os.name == "nt":
        os.system("")  # turns on ANSI screen codes in the Windows console

    try:
        game = FlightGame(port=args.port, save_every_m=args.save_every,
                          output_dir=args.output_dir)
    except OSError:
        print(f"UDP port {args.port} is already in use. Is another flight game or a")
        print("ground station (Mission Planner, QGroundControl) using it?")
        print(f"Close it, or pick another port:  python tests/flight_game.py --port {args.port + 10}")
        return 1
    print("Powering on drone and connecting over MAVLink...")
    try:
        if not game.start():
            print(game.event)
            return 1
        sys.stdout.write("\033[2J")
        if args.autopilot:
            game.run_scripted(AUTOPILOT_ROUTE, delay=0.06)
        else:
            game.run_interactive()
    except KeyboardInterrupt:
        pass
    finally:
        game.stop()

    print("\nLanded.")
    print(f"  Flew {game.flown_m:.0f} m, saved {len(game.saves)} entries")
    print(f"  Launch position: {game.launch_path}")
    print(f"  Location log:    {game.locations_path}")
    problems = check_flight_logs(game.launch_path, game.locations_path, game.save_every_m)
    if problems:
        print("  LOG CHECK FAILED:")
        for p in problems:
            print("   -", p)
        return 1
    print(f"  Log check passed: launch logged, every entry at least {game.save_every_m:g} m apart")
    return 0


if __name__ == "__main__":
    sys.exit(main())
