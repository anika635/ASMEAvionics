# Lets the tests import the project modules (connect_gps, haversine_distance, ...)
# that live one folder up, no matter where the tests are run from.
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
