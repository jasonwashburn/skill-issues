#!/usr/bin/env python3
"""Run renderer tests without creating bytecode caches."""

import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
