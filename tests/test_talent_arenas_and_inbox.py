#!/usr/bin/env python3
"""Tests for the 12 Talent Arenas and WhatsApp Unread Badge Clearing Mechanics"""
import unittest
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from models import User, init_db, db_execute, db_fetchone, db_fetchall

class TestTalentArenasAndInbox(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            init_db()

    def setUp(self):
        # Create unique student user for testing
        with self.app.app_context():
            rand = uuid.uuid4().hex[:6]
            uname = f'arena_user_{rand}'
            self.uid = User.create(uname, f'Student {rand}', f'{uname}@school.edu', 'pass123', role='student')
            
            p_uname = f'parent_{rand}'
            self.pid = User.create(p_uname, f'Parent {rand}', f'{p_uname}@school.edu', 'pass123', role='parent')

    def test_briefing_navbar_button(self):
        """Verify navbar has 'Briefing' instead of 'Principal Briefing'."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('🎓 Briefing', html)
        self.assertNotIn('🎓 Principal Briefing', html)

    def test_games_hub_fourteen_domains(self):
        """Verify Games Hub displays all 14 domains including Cowbellpedia Olympiad, Code Debugger, Spelling Bee, Sudoku, GeoQuest, and Grammar Scalpel."""
        resp = self.client.get('/games')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('14 standardized cognitive & academic domains', html)
        self.assertIn('/olympiad', html)
        self.assertIn('/code_sprint', html)
        self.assertIn('/spelling_bee', html)
        self.assertIn('/sudoku', html)
        self.assertIn('/geo_quest', html)
        self.assertIn('/grammar_scalpel', html)

    def test_olympiad_arena_and_submit(self):
        """Verify Cowbellpedia STEM Olympiad arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/olympiad')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'STEM Olympiad', resp.data)

        # Submit
        sub_resp = self.client.post('/api/olympiad/submit', json={
            'score': 8,
            'total': 10
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('score'), 8)
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_code_sprint_arena_and_submit(self):
        """Verify Algorithmic Logic & Code Debugger arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/code_sprint')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Code Debugger', resp.data)

        # Submit
        sub_resp = self.client.post('/api/code_sprint/submit', json={
            'score': 6
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('score'), 6)
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_spelling_bee_arena_and_submit(self):
        """Verify Oratory Spelling Bee arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/spelling_bee')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Spelling Bee', resp.data)

        # Submit
        sub_resp = self.client.post('/api/spelling_bee/submit', json={
            'score': 7
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('score'), 7)
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_sudoku_arena_and_submit(self):
        """Verify Deductive Sudoku Grid arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/sudoku')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Sudoku Grid', resp.data)

        # Submit
        sub_resp = self.client.post('/api/sudoku/submit', json={
            'grid_size': 4,
            'time_sec': 30
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_geo_quest_arena_and_submit(self):
        """Verify African & Global GeoQuest arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/geo_quest')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'GeoQuest', resp.data)

        # Submit GeoQuest score
        sub_resp = self.client.post('/api/geo_quest/submit', json={
            'score': 12,
            'total': 15
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('score'), 12)
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_grammar_scalpel_arena_and_submit(self):
        """Verify English Grammar & Syntax Scalpel arena loads and records score/XP."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/grammar_scalpel')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Grammar', resp.data)

        # Submit Grammar Scalpel score
        sub_resp = self.client.post('/api/grammar_scalpel/submit', json={
            'score': 14,
            'total': 15
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('score'), 14)
        self.assertGreater(data.get('xp_earned', 0), 0)

    def test_whatsapp_unread_cleared_on_reply(self):
        """Verify that answering a WhatsApp message clears unread signs completely."""
        cid = f'direct_{min(self.uid, self.pid)}_{max(self.uid, self.pid)}'
        
        # Parent sends a message to student
        with self.app.app_context():
            db_execute(
                'INSERT INTO direct_messages (conversation_id, sender_id, receiver_id, sender_alias, is_anonymous, message) VALUES (?, ?, ?, ?, ?, ?)',
                (cid, self.pid, self.uid, 'Parent', 0, 'Are you prepared for the Olympiad?')
            )

        # Student logs in
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        # 1. Thread list must report 1 unread message
        threads = self.client.get('/api/messages/conversations').get_json()
        thread = next((t for t in threads if t['id'] == cid), None)
        self.assertIsNotNone(thread)
        self.assertEqual(thread['unread_count'], 1)

        # 2. Student replies / answers the message
        reply_resp = self.client.post('/api/messages/send', json={
            'conversation_id': cid,
            'receiver_id': self.pid,
            'message': 'Yes! I scored 8/10 in the Cowbellpedia Olympiad!'
        })
        self.assertEqual(reply_resp.status_code, 200)

        # 3. Thread list unread count must now be 0 since student answered
        threads_after = self.client.get('/api/messages/conversations').get_json()
        thread_after = next((t for t in threads_after if t['id'] == cid), None)
        self.assertIsNotNone(thread_after)
        self.assertEqual(thread_after['unread_count'], 0, 'Unread count should be 0 after replying')

        # 4. In database, incoming message must have read_at set
        with self.app.app_context():
            row = db_fetchone('SELECT read_at FROM direct_messages WHERE conversation_id=? AND receiver_id=?', (cid, self.uid))
            self.assertIsNotNone(row[0], 'Incoming message read_at must be populated after answer')

    def test_whatsapp_mark_read_endpoint(self):
        """Verify explicit /api/messages/mark_read clears unread count."""
        cid = f'direct_{min(self.uid, self.pid)}_{max(self.uid, self.pid)}'
        with self.app.app_context():
            db_execute(
                'INSERT INTO direct_messages (conversation_id, sender_id, receiver_id, sender_alias, is_anonymous, message) VALUES (?, ?, ?, ?, ?, ?)',
                (cid, self.pid, self.uid, 'Parent', 0, 'Great job!')
            )

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        # Call mark_read
        resp = self.client.post('/api/messages/mark_read', json={'conversation_id': cid})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json().get('unread_count'), 0)

    def test_inter_house_standings_aggregation(self):
        """Verify get_inter_house_standings aggregates all 4 Good Shepherd houses."""
        from models import get_inter_house_standings
        with self.app.app_context():
            standings = get_inter_house_standings()
            self.assertEqual(len(standings), 4)
            names = [h['name'] for h in standings]
            self.assertIn('St. Michael House', names)
            self.assertIn('St. Gabriel House', names)
            self.assertIn('St. Raphael House', names)
            self.assertIn('St. Joseph House', names)
            for h in standings:
                self.assertIn('points', h)
                self.assertIn('members', h)
                self.assertIn('color', h)

    def test_certificates_distinction_page(self):
        """Verify certificates page loads with Good Shepherd distinction diploma."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.uid)

        resp = self.client.get('/certificates')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Good Shepherd Catholic College', html)
        self.assertIn('Certificate of Academic Distinction', html)
        self.assertIn('GeoQuest', html)
        self.assertIn('Grammar Scalpel', html)

    def test_principal_briefing_inter_house_and_fourteen_arenas(self):
        """Verify Principal Briefing presents 14 arenas and Good Shepherd House Championship."""
        with self.client.session_transaction() as sess:
            sess['principal_unlocked'] = True

        resp = self.client.get('/principal')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('14 Arenas', html)
        self.assertIn('Inter-House Cognitive & Academic Championship', html)
        self.assertIn('St. Michael House', html)

