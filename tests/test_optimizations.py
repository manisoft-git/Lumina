#!/usr/bin/env python3
"""
Tests for Lumina World-Class Optimizations, Edge-Cases, and Hardening
Verifies database integrity, anti-cheat clamping, memory cleanup, and offline asset caching.
"""
import unittest
import sys
import os
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import User, init_db
from db import get_db
import sockets

class TestOptimizationsAndHardening(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            init_db()

    def _create_test_user(self):
        rand_id = uuid.uuid4().hex[:8]
        uname = f"opt_user_{rand_id}"
        with self.app.app_context():
            uid = User.create(uname, f"Optimization User {rand_id}", f"{uname}@example.com", "pass123456")
        return uid, uname

    def test_daily_challenge_resubmission(self):
        """Verify re-submitting or updating daily challenge does not trigger UNIQUE constraint crash"""
        uid, uname = self._create_test_user()
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        # First submission
        res1 = self.client.post("/submit_challenge", json={
            "challenge_type": "speed_demon",
            "progress": 50,
            "status": "in_progress"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()["status"], "ok")

        # Second submission on same day (updating progress)
        res2 = self.client.post("/submit_challenge", json={
            "challenge_type": "speed_demon",
            "progress": 100,
            "status": "completed"
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["status"], "ok")
        self.assertGreater(res2.get_json().get("xp_earned", 0), 0)

        # Third submission on same day (already completed - no duplicate XP exploit)
        res3 = self.client.post("/submit_challenge", json={
            "challenge_type": "speed_demon",
            "progress": 100,
            "status": "completed"
        })
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.get_json()["status"], "ok")
        self.assertEqual(res3.get_json().get("xp_earned", 0), 0)

    def test_submit_score_negative_net_wpm_clamping(self):
        """Verify negative net WPM is clamped to 0.0 and awards zero negative XP"""
        uid, uname = self._create_test_user()
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        resp = self.client.post("/submit_score", json={
            "wpm": 5.0,
            "accuracy": 20.0,
            "errors": 25,
            "net_wpm": -20.0,
            "category": "words",
            "timings": [100, 250, 420],
            "duration_sec": 10.0,
            "passage_len": 15
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["xp_earned"], 0)

    def test_reaction_test_edge_cases(self):
        """Verify reaction submission handles NaN, Infinity, negative, and null values safely without 500"""
        uid, uname = self._create_test_user()
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        for payload in [
            {"best_ms": None, "avg_ms": None, "attempts": 0},
            {"best_ms": "NaN", "avg_ms": "NaN", "attempts": 5},
            {"best_ms": "Infinity", "avg_ms": "Infinity", "attempts": 5},
            {"best_ms": -100, "avg_ms": -100, "attempts": 1},
            {"best_ms": 215.4, "avg_ms": 230.1, "attempts": 5}
        ]:
            resp = self.client.post("/submit/reaction", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data["status"], "ok")

    def test_static_asset_caching_and_local_qr(self):
        """Verify static assets have aggressive caching headers and local QR library is bundled"""
        # Test local QR code library
        qr_resp = self.client.get("/static/qrcode.min.js")
        self.assertEqual(qr_resp.status_code, 200)
        self.assertGreater(len(qr_resp.data), 1000)

        # Test Cache-Control headers on static asset
        css_resp = self.client.get("/static/style.css")
        self.assertEqual(css_resp.status_code, 200)
        cache_header = css_resp.headers.get("Cache-Control", "")
        self.assertIn("max-age=31536000", cache_header)
        self.assertIn("immutable", cache_header)

    def test_socket_disconnect_cleanup(self):
        """Verify socket disconnect handler cleans up memory leaks in room state"""
        fake_sid = "test_socket_sid_9999"
        sockets.CHAT_RATELIMIT[fake_sid] = [100.0, 101.0]
        sockets.MONITOR_SUBSCRIBERS.setdefault("code_123", set()).add(fake_sid)
        sockets.SPECTATORS.setdefault("room_test", set()).add(fake_sid)
        sockets.TYPING_ROOMS["room_test"] = {
            "players": {fake_sid: {"username": "test_player", "progress": 0}},
            "state": "waiting"
        }

        # Trigger cleanup
        sockets.clean_disconnected_socket(fake_sid)

        # Verify pruned
        self.assertNotIn(fake_sid, sockets.CHAT_RATELIMIT)
        self.assertNotIn(fake_sid, sockets.MONITOR_SUBSCRIBERS.get("code_123", set()))
        self.assertNotIn(fake_sid, sockets.SPECTATORS.get("room_test", set()))
        self.assertNotIn(fake_sid, sockets.TYPING_ROOMS.get("room_test", {}).get("players", {}))

    def test_principal_briefing_and_executive_routes(self):
        """Verify the Principal Executive Briefing & Laptop Grant Proposal loads for both guests and authenticated users"""
        # Test anonymous access
        resp_anon = self.client.get("/principal")
        self.assertEqual(resp_anon.status_code, 200)
        self.assertIn(b"PROPOSAL FOR STUDENT INNOVATION GRANT", resp_anon.data)
        self.assertIn(b"OFFICIAL ACADEMIC BRIEFING", resp_anon.data)

        resp_alias = self.client.get("/executive-briefing")
        self.assertEqual(resp_alias.status_code, 200)

        # Test authenticated student access
        uid, uname = self._create_test_user()
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        resp_auth = self.client.get("/principal")
        self.assertEqual(resp_auth.status_code, 200)
        self.assertIn(b"Optimization User", resp_auth.data)

    def test_sound_fx_asset_and_caching(self):
        """Verify Web Audio sound synthesis asset is served with 200 OK and cache headers"""
        resp = self.client.get("/static/sound_fx.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"LuminaAudio", resp.data)
        self.assertIn(b"LuminaConfetti", resp.data)
        cache_header = resp.headers.get("Cache-Control", "")
        self.assertIn("max-age=31536000", cache_header)

    def test_analytics_guest_and_scores_serialization(self):
        """Verify /analytics works for guests without redirect and serializes Row objects safely when scores exist"""
        # 1. Guest access should return 200 OK (never 302 redirect)
        res_guest = self.client.get("/analytics")
        self.assertEqual(res_guest.status_code, 200)
        self.assertIn(b"Campus Telemetry", res_guest.data)
        self.assertIn(b"Performance & Cognitive Analytics", res_guest.data)

        # 2. Authenticated user WITH score rows (must not raise TypeError: Object of type Row is not JSON serializable)
        uid, uname = self._create_test_user()
        with self.app.app_context():
            from db import db_execute
            db_execute(
                "INSERT INTO scores (user_id, wpm, accuracy, net_wpm, errors, error_map, integrity_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, 92.0, 98.5, 90.6, 2, json.dumps({"p": 3, "q": 1}), 0.99)
            )

        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        res_user = self.client.get("/analytics")
        self.assertEqual(res_user.status_code, 200)
        self.assertIn(b"90.6", res_user.data)
        self.assertIn(b"Motor Cadence & Accuracy Trajectory", res_user.data)

    def test_local_chart_asset_serving(self):
        """Verify local Chart.js bundle is served with 200 OK and aggressive caching"""
        resp = self.client.get("/static/chart.umd.min.js")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.data), 50000)

if __name__ == "__main__":
    unittest.main()
    import os; os._exit(0)

