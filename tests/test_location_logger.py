"""Error points for init_output_file(path) and save_location(entry, path)."""
import csv
import os
import tempfile
import unittest

from location_logger import init_output_file, save_launch_position, save_location

HEADER = ["timestamp", "latitude", "longitude", "distance_m", "bearing_deg", "north_m", "east_m"]


def make_entry(**overrides):
    entry = {
        "timestamp": "2026-11-18T12:00:00",
        "latitude": 33.7861,
        "longitude": -84.2695,
        "distance_m": 804.7,
        "bearing_deg": 45.0,
        "north_m": 569.0,
        "east_m": 569.0,
    }
    entry.update(overrides)
    return entry


class LocationLoggerErrorPoints(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "locations.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def read_rows(self):
        with open(self.path, newline="") as file:
            return list(csv.reader(file))

    def test_init_creates_file_with_header(self):
        init_output_file(self.path)
        self.assertEqual(self.read_rows(), [HEADER])

    # ERROR POINT: program restarts mid-flight. Must NOT wipe earlier rows
    # or write a second header.
    def test_init_does_not_overwrite_existing_log(self):
        init_output_file(self.path)
        save_location(make_entry(), self.path)

        init_output_file(self.path)

        rows = self.read_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], HEADER)

    # ERROR POINT: file exists but is empty (crash right after it was created)
    def test_init_writes_header_into_empty_file(self):
        open(self.path, "w").close()
        init_output_file(self.path)
        self.assertEqual(self.read_rows(), [HEADER])

    def test_save_appends_rows_in_order(self):
        init_output_file(self.path)
        save_location(make_entry(timestamp="t1"), self.path)
        save_location(make_entry(timestamp="t2"), self.path)

        rows = self.read_rows()
        self.assertEqual([r[0] for r in rows[1:]], ["t1", "t2"])

    def test_saved_values_round_trip(self):
        init_output_file(self.path)
        save_location(make_entry(), self.path)

        row = dict(zip(HEADER, self.read_rows()[1]))
        self.assertEqual(float(row["latitude"]), 33.7861)
        self.assertEqual(float(row["longitude"]), -84.2695)

    # ERROR POINT: build_entry returned None (no fix). Nothing should be written.
    def test_save_none_writes_nothing(self):
        init_output_file(self.path)
        save_location(None, self.path)
        self.assertEqual(self.read_rows(), [HEADER])

    # ERROR POINT: entry is missing a field. Raises KeyError, but does not
    # leave a half-written row in the file.
    def test_missing_field_raises_and_writes_nothing(self):
        init_output_file(self.path)
        entry = make_entry()
        del entry["bearing_deg"]

        with self.assertRaises(KeyError):
            save_location(entry, self.path)
        self.assertEqual(self.read_rows(), [HEADER])

    # ERROR POINT: a value containing a comma must not split into extra columns
    def test_comma_in_value_stays_one_column(self):
        init_output_file(self.path)
        save_location(make_entry(timestamp="Nov 18, 2026"), self.path)

        row = self.read_rows()[1]
        self.assertEqual(len(row), len(HEADER))
        self.assertEqual(row[0], "Nov 18, 2026")

    # ERROR POINT: save_location used without init_output_file first. It
    # works, but the file has no header row. main() must call init first.
    def test_save_without_init_has_no_header(self):
        save_location(make_entry(), self.path)
        self.assertNotEqual(self.read_rows()[0], HEADER)

    # ERROR POINT: output folder does not exist (e.g. a missing SD card path)
    def test_missing_folder_raises(self):
        bad_path = os.path.join(self.tmp.name, "no_such_folder", "locations.txt")
        with self.assertRaises(FileNotFoundError):
            init_output_file(bad_path)
        with self.assertRaises(FileNotFoundError):
            save_location(make_entry(), bad_path)


class LaunchPositionErrorPoints(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "launch_position.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def read_rows(self):
        with open(self.path, newline="") as file:
            return list(csv.reader(file))

    def test_writes_header_and_launch_point(self):
        self.assertTrue(save_launch_position((33.7861, -84.2695), self.path, "t0"))
        self.assertEqual(
            self.read_rows(),
            [["timestamp", "latitude", "longitude"], ["t0", "33.7861", "-84.2695"]],
        )

    def test_fills_in_timestamp_when_not_given(self):
        save_launch_position((33.7861, -84.2695), self.path)
        timestamp = self.read_rows()[1][0]
        self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    # ERROR POINT: second launch (battery swap, restart). Must keep the first
    # launch and add the new one, with only one header.
    def test_second_launch_is_added_not_overwritten(self):
        save_launch_position((33.7861, -84.2695), self.path, "t0")
        save_launch_position((33.8000, -84.3000), self.path, "t1")

        rows = self.read_rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ["timestamp", "latitude", "longitude"])
        self.assertEqual(rows[2], ["t1", "33.8", "-84.3"])

    # ERROR POINT: set_origin() returned None (no GPS fix)
    def test_no_fix_writes_nothing(self):
        self.assertFalse(save_launch_position(None, self.path))
        self.assertFalse(os.path.exists(self.path))

    def test_empty_file_gets_header(self):
        open(self.path, "w").close()
        save_launch_position((1.0, 2.0), self.path, "t0")
        self.assertEqual(self.read_rows()[0], ["timestamp", "latitude", "longitude"])

    # ERROR POINT: output folder missing
    def test_missing_folder_raises(self):
        bad = os.path.join(self.tmp.name, "nope", "launch_position.txt")
        with self.assertRaises(FileNotFoundError):
            save_launch_position((1.0, 2.0), bad)


if __name__ == "__main__":
    unittest.main()
