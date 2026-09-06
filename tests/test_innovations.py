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

    def test_chess_bot_engine(self):
        """Verify the Chess Bot plays legal tactical moves without unpacking errors."""
        from sockets import SimpleChessBot
        import chess
        bot = SimpleChessBot(depth=2)
        board = chess.Board()
        board.push_san("e4")
        move = bot.best_move(board.fen(), False)
        self.assertIsNotNone(move)
        self.assertIn(move, board.legal_moves)

    def test_showcase_feed_public_access(self):
        """Verify the Showcase / Parents Feed is completely public (HTTP 200 without login)."""
        public_client = self.app.test_client()
        resp = public_client.get("/showcase")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Student Achievement Showcase", resp.data)
        self.assertIn(b"Public Visitor Mode", resp.data)

        resp_parents = public_client.get("/parents")
        self.assertEqual(resp_parents.status_code, 200)
        self.assertIn(b"Student Achievement Showcase", resp_parents.data)

    def test_showcase_post_creation_and_like(self):
        """Verify students can publish milestones and users can like them."""
        with self.app.app_context():
            rand_id = uuid.uuid4().hex[:8]
            uname = f"star_{rand_id}"
            uid = User.create(uname, "Star Typist", f"{uname}@example.com", "pass123")

        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        # Create post via JSON API
        post_resp = self.client.post("/showcase/post", json={
            "title": "Broke 142 WPM on C++ Algorithms! ⚡",
            "achievement_type": "typing_record",
            "stat_highlight": "142 WPM • 99.8% Acc",
            "content": "Zero backspaces in 60s drill sprint.",
            "media_url": "https://example.com/speed.jpg",
            "media_type": "image"
        })
        self.assertEqual(post_resp.status_code, 200)
        post_data = post_resp.get_json()
        self.assertTrue(post_data["success"])
        post_id = post_data["post_id"]

        # Like the post
        like_resp = self.client.post(f"/showcase/like/{post_id}")
        self.assertEqual(like_resp.status_code, 200)
        like_data = like_resp.get_json()
        self.assertTrue(like_data["success"])
        self.assertGreaterEqual(like_data["likes_count"], 1)

    def test_parent_anonymous_messaging_and_producer_audit(self):
        """Verify parent anonymous messaging: alias shown to student, real ID preserved for Producer audit."""
        with self.app.app_context():
            rand_id = uuid.uuid4().hex[:8]
            student_name = f"stud_{rand_id}"
            student_id = User.create(student_name, "Honors Student", f"{student_name}@example.com", "pass123")
            
            parent_name = f"parent_{rand_id}"
            parent_id = User.create(parent_name, "Dr. Robert Parent", f"{parent_name}@example.com", "pass123", role="parent")

            admin_name = f"admin_{rand_id}"
            admin_id = User.create(admin_name, "School Producer", f"{admin_name}@example.com", "pass123", role="admin")

        # Parent logs in and sends an anonymous message on post 1
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(parent_id)

        msg_resp = self.client.post("/showcase/message/1", json={
            "message": "Incredible focus and poise! Keep up the brilliant work.",
            "is_anonymous": 1,
            "parent_alias": "Proud Parent"
        })
        self.assertEqual(msg_resp.status_code, 200)
        msg_data = msg_resp.get_json()
        self.assertTrue(msg_data["success"])

        # Student logs in to check /inbox
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(student_id)

        inbox_resp = self.client.get("/inbox")
        self.assertEqual(inbox_resp.status_code, 200)
        self.assertIn(b"Encouragement Inbox", inbox_resp.data)

        # Producer logs in to check forensic audit stream
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(admin_id)
            sess["producer_unlocked"] = True

        audit_resp = self.client.get("/producer/api/parent_messages")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.get_json()
        self.assertIsInstance(audit_data, list)
        self.assertGreaterEqual(len(audit_data), 1)
        # Verify real parent username is in producer audit
        first_audit = audit_data[0]
        self.assertEqual(first_audit["parent_username"], parent_name)
        self.assertTrue(first_audit["is_anonymous"])
        self.assertEqual(first_audit["parent_alias"], "Proud Parent")

    def test_analytics_page_lti_summary(self):
        """Verify /analytics renders cognitive LTI index and share to showcase buttons."""
        with self.app.app_context():
            rand_id = uuid.uuid4().hex[:8]
            uname = f"analytic_{rand_id}"
            uid = User.create(uname, "Analytical Mind", f"{uname}@example.com", "pass123")

        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(uid)

        resp = self.client.get("/analytics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Performance & Cognitive Analytics", resp.data)
        self.assertIn(b"Lumina Cognitive Talent Index (LTI)", resp.data)
        self.assertIn(b"Celebrate Records on the Parent Showcase", resp.data)

if __name__ == "__main__":
    unittest.main()
    import os; os._exit(0)
