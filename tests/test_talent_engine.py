#!/usr/bin/env python3
"""Tests for Lumina Cognitive Talent Discovery Engine"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import User, init_db
from db import db_execute
from talent_engine import compute_cognitive_profile, COGNITIVE_ARCHETYPES

class TestTalentEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        init_db()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def test_new_user_profile(self):
        """A new user with minimal history still receives a valid profile baseline."""
        import uuid
        rand_id = uuid.uuid4().hex[:8]
        uname = f"student_{rand_id}"
        uid = User.create(uname, "Test Student", f"{uname}@example.com", "password123")
        self.assertIsNotNone(uid)

        profile = compute_cognitive_profile(uid)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["username"], uname)
        self.assertEqual(profile["fullname"], "Test Student")
        self.assertGreaterEqual(profile["lti"], 200)
        self.assertLessEqual(profile["lti"], 1000)
        self.assertEqual(len(profile["domains"]), 7)
        self.assertIn("title", profile["archetype"])
        self.assertGreater(len(profile["archetype"]["careers"]), 0)
        self.assertGreater(len(profile["adaptive_drills"]), 0)
        self.assertTrue(len(profile["dossier_hash"]) >= 12)

    def test_high_performer_archetype(self):
        """A student with high math and pattern scores should be recognized as an Algorithmic Architect."""
        import uuid
        rand_id = uuid.uuid4().hex[:8]
        uname = f"algo_{rand_id}"
        uid = User.create(uname, "Ada Lovelace", f"{uname}@example.com", "password123")

        # Inject high scores in Math Sprint and Pattern Tests
        db_execute("INSERT INTO math_sprints (user_id, score, correct, total) VALUES (?, 140, 35, 36)", (uid,))
        db_execute("INSERT INTO pattern_tests (user_id, puzzles_solved, avg_time_ms) VALUES (?, 15, 800)", (uid,))
        db_execute("INSERT INTO scores (user_id, wpm, accuracy, net_wpm, errors) VALUES (?, 95.0, 99.0, 94.0, 1)", (uid,))

        profile = compute_cognitive_profile(uid)
        self.assertIsNotNone(profile)
        self.assertGreaterEqual(profile["lti"], 500)
        self.assertIn(profile["archetype"]["title"], ["Algorithmic Architect", "Computational Polymath"])

if __name__ == "__main__":
    unittest.main()
