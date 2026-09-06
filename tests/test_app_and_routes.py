#!/usr/bin/env python3
"""Integration tests for Lumina Web App, API endpoints, and Classroom Projector"""
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import User, init_db

class TestAppAndRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            init_db()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lumina", response.data)

    def test_404_handler(self):
        response = self.client.get("/non_existent_page_12345")
        self.assertEqual(response.status_code, 404)

    def test_classroom_projector_route(self):
        response = self.client.get("/classroom/projector/CLASS_ROOM_99")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"LUMINA LIVE ARENA", response.data)
        self.assertIn(b"CLASS_ROOM_99", response.data)

    def test_talent_profile_and_submission(self):
        with self.app.app_context():
            import uuid
            rand_id = uuid.uuid4().hex[:8]
            uname = f"test_int_{rand_id}"
            uid = User.create(uname, "Integration User", f"{uname}@example.com", "pass123456")
            user = User.get_by_id(uid)

        # Login user
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        # Submit verified typing score with simulated human timings (with natural neuromuscular variance)
        import random
        random.seed(42)
        t = 0
        timings = []
        for _ in range(25):
            t += random.randint(90, 160)
            timings.append(t)
        sub_resp = self.client.post("/submit_score", json={
            "wpm": 78.5,
            "accuracy": 98.0,
            "errors": 1,
            "net_wpm": 77.5,
            "category": "code",
            "timings": timings,
            "duration_sec": 3.0,
            "passage_len": 25
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("anti_cheat", data)
        self.assertTrue(data["anti_cheat"]["verified"])

        # Fetch talent profile page
        talent_resp = self.client.get("/talent-profile")
        self.assertEqual(talent_resp.status_code, 200)
        self.assertIn(b"Lumina Talent Index", talent_resp.data)

        # Fetch printable dossier report
        dossier_resp = self.client.get(f"/talent-report/{uid}")
        self.assertEqual(dossier_resp.status_code, 200)
        self.assertIn(b"Official Cognitive Talent Dossier", dossier_resp.data)

        # Fetch JSON API
        api_resp = self.client.get(f"/api/v1/talent_profile/{uid}")
        self.assertEqual(api_resp.status_code, 200)
        api_data = api_resp.get_json()
        self.assertEqual(api_data["user_id"], uid)
        self.assertIn("lti", api_data)
        self.assertGreaterEqual(api_data["lti"], 200)

if __name__ == "__main__":
    unittest.main()
    import os; os._exit(0)
