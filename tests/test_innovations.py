#!/usr/bin/env python3
"""Tests for Lumina Global Innovations: Team Relay, Neurodiversity, and Offline Hub"""
import unittest
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import User, init_db

class TestGlobalInnovations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            init_db()

    def test_offline_hub_route(self):
        """Verify the Zero-Cloud Global Offline Hub renders successfully with local IP."""
        response = self.client.get("/offline-hub")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Global Offline Classroom Hub", response.data)
        self.assertIn(b"Local Classroom Server Address", response.data)

    def test_team_relay_routes(self):
        """Verify the Team Cognitive Relay routes load properly for authenticated users."""
        with self.app.app_context():
            rand_id = uuid.uuid4().hex[:8]
            uname = f"relay_{rand_id}"
            uid = User.create(uname, "Relay Runner", f"{uname}@example.com", "secret123")

        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        # Test lobby redirect
        lobby_resp = self.client.get("/relay")
        self.assertEqual(lobby_resp.status_code, 302)

        # Test live relay arena
        arena_resp = self.client.get("/relay/TEST_RELAY_ROOM")
        self.assertEqual(arena_resp.status_code, 200)
        self.assertIn(b"Team Cognitive Relay", arena_resp.data)
        self.assertIn(b"Team Alpha", arena_resp.data)
        self.assertIn(b"Team Beta", arena_resp.data)

    def test_neurodiversity_and_bionic_markup_in_typing(self):
        """Verify the typing test includes Bionic Reading, Dyslexia Font, and 432Hz Soundscape controls."""
        with self.app.app_context():
            rand_id = uuid.uuid4().hex[:8]
            uname = f"neuro_{rand_id}"
            uid = User.create(uname, "Neuro User", f"{uname}@example.com", "secret123")

        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        resp = self.client.get("/typing")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Bionic Reading", resp.data)
        self.assertIn(b"Dyslexia Font", resp.data)
        self.assertIn(b"432Hz Soundscape", resp.data)
        self.assertIn(b"Attentional Stamina Ratio", resp.data)

if __name__ == "__main__":
    unittest.main()
    import os; os._exit(0)
