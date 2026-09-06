#!/usr/bin/env python3
"""Tests for Lumina Anti-Cheat Engine"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from anti_cheat import AntiCheatEngine

class TestAntiCheat(unittest.TestCase):

    def test_normal_human_typing(self):
        """Simulate realistic human typing with natural flight-time variance."""
        import random
        random.seed(42)
        # 40 characters typed over ~5 seconds (~95 WPM) with natural timing variance
        t = 0
        timings = []
        for _ in range(40):
            t += random.randint(80, 180) # 80ms - 180ms per key
            timings.append(t)

        result = AntiCheatEngine.verify_submission(
            wpm=85.0,
            accuracy=97.5,
            duration_sec=5.0,
            timings=timings,
            passage_len=40
        )
        self.assertTrue(result["verified"])
        self.assertGreaterEqual(result["integrity_score"], 0.70)
        self.assertEqual(len(result["flags"]), 0)

    def test_bulk_paste_injection(self):
        """Simulate a paste or script injection where characters dump at 0-2ms intervals."""
        timings = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 7, 7, 8, 8, 9, 9, 10, 10]
        result = AntiCheatEngine.verify_submission(
            wpm=220.0,
            accuracy=100.0,
            duration_sec=0.1,
            timings=timings,
            passage_len=20
        )
        self.assertFalse(result["verified"])
        self.assertTrue(any("burst" in f.lower() or "mismatch" in f.lower() for f in result["flags"]))

    def test_synthetic_interval_uniformity(self):
        """Simulate a setInterval bot with exactly identical intervals (0ms variance)."""
        timings = [i * 50 for i in range(30)] # Exactly 50ms every key
        result = AntiCheatEngine.verify_submission(
            wpm=120.0,
            accuracy=100.0,
            duration_sec=1.5,
            timings=timings,
            passage_len=30
        )
        self.assertFalse(result["verified"])
        self.assertTrue(any("uniformity" in f.lower() for f in result["flags"]))

    def test_superhuman_speed(self):
        """WPM > 260 exceeds physical biological limits."""
        result = AntiCheatEngine.verify_submission(
            wpm=320.0,
            accuracy=100.0,
            duration_sec=2.0,
            passage_len=100
        )
        self.assertFalse(result["verified"])
        self.assertTrue(any("improbable wpm" in f.lower() for f in result["flags"]))

if __name__ == "__main__":
    unittest.main()
