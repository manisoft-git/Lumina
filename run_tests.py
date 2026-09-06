#!/usr/bin/env python3
"""
Lumina Automated Test Runner
Runs all unit and integration tests across cognitive engines, anti-cheat, and web endpoints.
"""
import unittest
import sys
import os

if __name__ == "__main__":
    test_dir = os.path.join(os.path.dirname(__file__), "tests")
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    os._exit(0 if result.wasSuccessful() else 1)
