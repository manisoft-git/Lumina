#!/usr/bin/env python3
import json
import random
import string
import hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from db import get_db, db_execute, db_fetchone, db_fetchall, db_execute_returning_id

K_NEW, K_EST, K_MAST = 40, 20, 10

def get_k(games, rating):
    if games < 30: return K_NEW
    if rating >= 2200: return K_MAST
    return K_EST

def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))

def update_elo(uid, gtype, result):
    row = db_fetchone("SELECT rating, games_played FROM user_ratings WHERE user_id=? AND game_type=?", (uid, gtype))
    if not row:
        db_execute("INSERT INTO user_ratings (user_id, game_type, rating, games_played) VALUES (?, ?, 1200, 0)", (uid, gtype))
        rating, games = 1200, 0
    else:
        rating, games = row[0], row[1]
    bot_rating = 2000
    exp = expected(rating, bot_rating)
    k = get_k(games, rating)
    new_r = max(100, min(3000, int(round(rating + k * (result - exp)))))
    db_execute("UPDATE user_ratings SET rating=?, games_played=games_played+1 WHERE user_id=? AND game_type=?", (new_r, uid, gtype))
    return new_r

class User(UserMixin):
    def __init__(self, row):
        def g(idx, default=None):
            try:
                val = row[idx]
                return val if val is not None else default
            except (IndexError, KeyError):
                return default

        self.id = g(0)
        self.username = g(1, "")
        self.fullname = g(2, "")
        self.email = g(3, "")
        self.password_hash = g(4, "")
        self.role = g(5, "student")
        self.xp = g(6, 0)
        self.level = g(7, 1)
        self.streak = g(8, 0)
        self.longest_streak = g(9, 0)
        self.last_active = g(10)
        self.parent_code = g(11)
        self.created_at = g(12)
        self.is_locked = bool(g(13, 0))
        self.parent_is_anonymous = bool(g(14, 1 if self.role == 'parent' else 0))
        self.parent_alias = g(15, "Proud Parent")
        self.linked_student_id = g(16, None)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @staticmethod
    def create(username, fullname, email, password, role="student", is_anonymous=0, parent_alias="Proud Parent", linked_student_id=None):
        ph = generate_password_hash(password)
        code = None
        for _ in range(20):
            candidate = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not db_fetchone("SELECT id FROM users WHERE parent_code=?", (candidate,)):
                code = candidate
                break
        if not code:
            # Guaranteed-unique fallback using uuid4 (no DB collision possible)
            import uuid
            code = uuid.uuid4().hex.upper()[:16]
        return db_execute_returning_id(
            "INSERT INTO users (username, fullname, email, password_hash, role, parent_code, is_locked, is_anonymous, parent_alias, linked_student_id) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
            (username, fullname, email, ph, role, code, int(is_anonymous), parent_alias, linked_student_id)
        )

    @staticmethod
    def get_by_id(user_id):
        sql = "SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE id=?"
        try:
            row = db_fetchone(sql, (user_id,))
        except Exception as e:
            if "no such column" in str(e).lower() or "is_locked" in str(e).lower():
                ensure_columns()
                row = db_fetchone(sql, (user_id,))
            else:
                raise
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        sql = "SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE username=?"
        try:
            row = db_fetchone(sql, (username,))
        except Exception as e:
            if "no such column" in str(e).lower() or "is_locked" in str(e).lower():
                ensure_columns()
                row = db_fetchone(sql, (username,))
            else:
                raise
        return User(row) if row else None

    @staticmethod
    def get_by_parent_code(code):
        sql = "SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE parent_code=?"
        try:
            row = db_fetchone(sql, (code,))
        except Exception as e:
            if "no such column" in str(e).lower() or "is_locked" in str(e).lower():
                ensure_columns()
                row = db_fetchone(sql, (code,))
            else:
                raise
        return User(row) if row else None

def award_xp(user_id, amount):
    db_execute("UPDATE users SET xp = xp + ? WHERE id=?", (amount, user_id))
    row = db_fetchone("SELECT xp, level FROM users WHERE id=?", (user_id,))
    if not row: return 1
    xp, lvl = row[0] or 0, row[1] or 1
    new_lvl = max(1, int((xp / 500) ** 0.6) + 1)
    if new_lvl > lvl:
        db_execute("UPDATE users SET level=? WHERE id=?", (new_lvl, user_id))
    return new_lvl

def check_streak(user_id):
    today = datetime.utcnow().date().isoformat()
    row = db_fetchone("SELECT last_active, streak, longest_streak FROM users WHERE id=?", (user_id,))
    if not row: return 0
    last, streak, longest = row[0], row[1] or 0, row[2] or 0
    if last == today:
        return streak
    yesterday = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    if last == yesterday:
        streak += 1
    else:
        streak = 1
    longest = max(longest, streak)
    db_execute("UPDATE users SET streak=?, longest_streak=?, last_active=? WHERE id=?", (streak, longest, today, user_id))
    return streak

BADGES = {
    "first_typing_test": {"name": "First Steps", "desc": "Completed your first typing test.", "xp": 50},
    "speed_demon_50": {"name": "Speed Demon", "desc": "Reached 50 WPM.", "xp": 100},
    "speed_demon_80": {"name": "Lightning", "desc": "Reached 80 WPM.", "xp": 200},
    "accuracy_king": {"name": "Precision", "desc": "99%+ accuracy.", "xp": 150},
    "competition_winner": {"name": "Champion", "desc": "Won a multiplayer race.", "xp": 100},
    "chess_novice": {"name": "Pawn Star", "desc": "First chess game.", "xp": 50},
    "checkers_novice": {"name": "Checker Champ", "desc": "First checkers game.", "xp": 50},
    "math_whiz": {"name": "Math Whiz", "desc": "Scored 100+ in Math Sprint.", "xp": 100},
    "memory_master": {"name": "Memory Master", "desc": "Reached level 10 in Memory Palace.", "xp": 150},
    "react_ninja": {"name": "Ninja Reflex", "desc": "Reaction time under 200ms.", "xp": 100},
    "pattern_solver": {"name": "Pattern Solver", "desc": "Solved 5 pattern puzzles.", "xp": 100},
    "word_blitzer": {"name": "Word Blitzer", "desc": "Found 20 words in one round.", "xp": 100},
    "tournament_winner": {"name": "Tournament King", "desc": "Won a tournament.", "xp": 300},
    "homework_hero": {"name": "Homework Hero", "desc": "Completed 5 homework assignments.", "xp": 100},
    "seven_streak": {"name": "Dedicated", "desc": "7-day login streak.", "xp": 200},
}

def check_badges(user_id):
    existing = {r[0] for r in db_fetchall("SELECT badge_id FROM user_badges WHERE user_id=?", (user_id,))}
    to_award = []
    row = db_fetchone("SELECT MAX(wpm), MAX(accuracy) FROM scores WHERE user_id=?", (user_id,))
    if row:
        max_wpm, max_acc = row[0], row[1]
        if max_wpm is not None and max_wpm >= 10: to_award.append("first_typing_test")
        if max_wpm is not None and max_wpm >= 50: to_award.append("speed_demon_50")
        if max_wpm is not None and max_wpm >= 80: to_award.append("speed_demon_80")
        if max_acc is not None and max_acc >= 99: to_award.append("accuracy_king")
    row = db_fetchone("SELECT COUNT(*) FROM scores WHERE user_id=? AND room_id IS NOT NULL", (user_id,))
    if row and row[0] and row[0] > 0: to_award.append("competition_winner")
    for gtype in ["chess", "checkers"]:
        row = db_fetchone(f"SELECT COUNT(*) FROM {gtype}_games WHERE white_id=? OR black_id=?", (user_id, user_id)) if gtype == "chess" else db_fetchone("SELECT COUNT(*) FROM checkers_games WHERE red_id=? OR black_id=?", (user_id, user_id))
        if row and row[0] and row[0] > 0: to_award.append(f"{gtype}_novice")
    row = db_fetchone("SELECT MAX(score) FROM math_sprints WHERE user_id=?", (user_id,))
    if row and row[0] is not None and row[0] >= 100: to_award.append("math_whiz")
    row = db_fetchone("SELECT MAX(level_reached) FROM memory_tests WHERE user_id=?", (user_id,))
    if row and row[0] is not None and row[0] >= 10: to_award.append("memory_master")
    row = db_fetchone("SELECT MIN(best_ms) FROM reaction_tests WHERE user_id=?", (user_id,))
    if row and row[0] is not None and row[0] <= 200: to_award.append("react_ninja")
    row = db_fetchone("SELECT SUM(puzzles_solved) FROM pattern_tests WHERE user_id=?", (user_id,))
    if row and row[0] is not None and row[0] >= 5: to_award.append("pattern_solver")
    row = db_fetchone("SELECT MAX(score) FROM word_blitz_scores WHERE user_id=?", (user_id,))
    if row and row[0] is not None and row[0] >= 20: to_award.append("word_blitzer")
    row = db_fetchone("SELECT COUNT(*) FROM tournament_matches WHERE winner_id=?", (user_id,))
    if row and row[0] and row[0] > 0: to_award.append("tournament_winner")
    row = db_fetchone("SELECT COUNT(*) FROM homework_submissions WHERE user_id=?", (user_id,))
    if row and row[0] and row[0] >= 5: to_award.append("homework_hero")
    row = db_fetchone("SELECT streak FROM users WHERE id=?", (user_id,))
    if row and row[0] is not None and row[0] >= 7: to_award.append("seven_streak")

    new_badges = []
    for bid in to_award:
        if bid not in existing:
            try:
                db_execute("INSERT INTO user_badges (user_id, badge_id, awarded_at) VALUES (?, ?, ?)", (user_id, bid, datetime.utcnow().isoformat()))
                award_xp(user_id, BADGES[bid]["xp"])
                new_badges.append(bid)
            except Exception:
                pass
    return new_badges

def ensure_columns():
    cols_to_add = [
        ("users", "email", "TEXT"),
        ("users", "xp", "INTEGER DEFAULT 0"),
        ("users", "level", "INTEGER DEFAULT 1"),
        ("users", "streak", "INTEGER DEFAULT 0"),
        ("users", "longest_streak", "INTEGER DEFAULT 0"),
        ("users", "last_active", "DATE"),
        ("users", "parent_code", "TEXT"),
        ("users", "is_locked", "INTEGER DEFAULT 0"),
        ("users", "is_anonymous", "INTEGER DEFAULT 0"),
        ("users", "parent_alias", "TEXT DEFAULT 'Proud Parent'"),
        ("users", "linked_student_id", "INTEGER"),
        ("scores", "net_wpm", "REAL"),
        ("scores", "passage_category", "TEXT"),
        ("scores", "room_id", "TEXT"),
        ("scores", "error_map", "TEXT"),
        ("scores", "verified", "INTEGER DEFAULT 1"),
        ("scores", "integrity_score", "REAL DEFAULT 1.0"),
        ("showcase_posts", "achievement_rank_score", "INTEGER DEFAULT 0"),
        ("showcase_posts", "verified_history_id", "INTEGER"),
        ("student_activity_history", "source_ref", "TEXT"),
    ]
    is_pg = bool(__import__("config").DATABASE_URL)
    db = get_db()
    for table, col, col_type in cols_to_add:
        try:
            if not is_pg:
                cur = db.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in cur.fetchall()]
                if col in cols:
                    continue
            db_execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

def init_db():
    is_pg = bool(__import__("config").DATABASE_URL)
    pk = "id SERIAL PRIMARY KEY" if is_pg else "id INTEGER PRIMARY KEY AUTOINCREMENT"

    tables = [
        f"""CREATE TABLE IF NOT EXISTS users (
            {pk}, username TEXT UNIQUE NOT NULL, fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'student', xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
            streak INTEGER DEFAULT 0, longest_streak INTEGER DEFAULT 0,
            last_active DATE, parent_code TEXT UNIQUE,
            is_locked INTEGER DEFAULT 0, is_anonymous INTEGER DEFAULT 0,
            parent_alias TEXT DEFAULT 'Proud Parent', linked_student_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS classrooms (
            {pk}, teacher_id INTEGER NOT NULL, name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS classroom_members (
            classroom_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (classroom_id, student_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS passages (
            {pk}, category TEXT DEFAULT 'general', title TEXT,
            content TEXT NOT NULL, difficulty TEXT DEFAULT 'medium'
        )""",
        f"""CREATE TABLE IF NOT EXISTS custom_passages (
            {pk}, teacher_id INTEGER NOT NULL, classroom_id INTEGER,
            title TEXT NOT NULL, content TEXT NOT NULL, category TEXT DEFAULT 'custom',
            difficulty TEXT DEFAULT 'medium', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS scores (
            {pk}, user_id INTEGER NOT NULL, wpm REAL NOT NULL, accuracy REAL NOT NULL,
            errors INTEGER DEFAULT 0, net_wpm REAL, passage_category TEXT,
            room_id TEXT, error_map TEXT, verified INTEGER DEFAULT 1, integrity_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS user_badges (
            user_id INTEGER NOT NULL, badge_id TEXT NOT NULL,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, badge_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS chat_messages (
            {pk}, room TEXT DEFAULT 'global', user_id INTEGER NOT NULL,
            username TEXT NOT NULL, message TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS chess_games (
            {pk}, room_id TEXT UNIQUE NOT NULL, white_id INTEGER, black_id INTEGER,
            pgn TEXT, result TEXT, status TEXT DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS checkers_games (
            {pk}, room_id TEXT UNIQUE NOT NULL, red_id INTEGER, black_id INTEGER,
            board_state TEXT, result TEXT, status TEXT DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS user_ratings (
            user_id INTEGER NOT NULL, game_type TEXT NOT NULL,
            rating INTEGER DEFAULT 1200, games_played INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, game_type)
        )""",
        f"""CREATE TABLE IF NOT EXISTS typing_replays (
            {pk}, user_id INTEGER NOT NULL, passage TEXT NOT NULL,
            keystrokes TEXT NOT NULL, wpm REAL, accuracy REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS daily_challenges (
            {pk}, challenge_date DATE UNIQUE NOT NULL, game_type TEXT NOT NULL,
            description TEXT NOT NULL, target_value INTEGER NOT NULL, reward_xp INTEGER DEFAULT 50
        )""",
        """CREATE TABLE IF NOT EXISTS user_challenges (
            user_id INTEGER NOT NULL, challenge_id INTEGER NOT NULL,
            progress INTEGER DEFAULT 0, completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP, PRIMARY KEY (user_id, challenge_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS homework (
            {pk}, teacher_id INTEGER NOT NULL, classroom_id INTEGER,
            title TEXT NOT NULL, instructions TEXT, passage_content TEXT,
            min_wpm_target INTEGER DEFAULT 0, due_date DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS homework_submissions (
            {pk}, homework_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            wpm REAL, accuracy REAL, completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS tournaments (
            {pk}, name TEXT NOT NULL, game_type TEXT NOT NULL,
            format TEXT DEFAULT 'bracket', status TEXT DEFAULT 'open',
            max_players INTEGER DEFAULT 16, created_by INTEGER NOT NULL,
            started_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS tournament_players (
            tournament_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            seed INTEGER, score REAL DEFAULT 0, eliminated INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (tournament_id, user_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS tournament_matches (
            {pk}, tournament_id INTEGER NOT NULL, round_number INTEGER NOT NULL,
            player1_id INTEGER, player2_id INTEGER, p1_score REAL, p2_score REAL,
            winner_id INTEGER, status TEXT DEFAULT 'pending', room_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS certificates (
            {pk}, user_id INTEGER NOT NULL, certificate_type TEXT NOT NULL,
            milestone_value INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS reaction_tests (
            {pk}, user_id INTEGER NOT NULL, best_ms INTEGER, avg_ms INTEGER,
            attempts INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS math_sprints (
            {pk}, user_id INTEGER NOT NULL, correct INTEGER, total INTEGER,
            difficulty TEXT, time_limit INTEGER, score INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS memory_tests (
            {pk}, user_id INTEGER NOT NULL, level_reached INTEGER,
            max_pattern_length INTEGER, attempts INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS pattern_tests (
            {pk}, user_id INTEGER NOT NULL, puzzles_solved INTEGER,
            difficulty TEXT, avg_time_ms INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS word_blitz_scores (
            {pk}, user_id INTEGER NOT NULL, score INTEGER, words_found TEXT,
            time_limit INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS api_keys (
            {pk}, user_id INTEGER NOT NULL, key_hash TEXT UNIQUE NOT NULL,
            name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP, request_count INTEGER DEFAULT 0, rate_limit INTEGER DEFAULT 100
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_agents (
            {pk}, agent_id TEXT UNIQUE NOT NULL, user_id INTEGER,
            hostname TEXT, ip_address TEXT, platform TEXT,
            status TEXT DEFAULT 'online', last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS agent_commands (
            {pk}, agent_id TEXT NOT NULL, command TEXT NOT NULL,
            output TEXT, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS anti_cheat_logs (
            {pk}, user_id INTEGER, wpm REAL, confidence REAL,
            reasons TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS showcase_posts (
            {pk}, student_id INTEGER NOT NULL, title TEXT NOT NULL,
            content TEXT, media_type TEXT DEFAULT 'card',
            media_url TEXT, achievement_type TEXT DEFAULT 'typing_record',
            stat_highlight TEXT, likes_count INTEGER DEFAULT 0,
            achievement_rank_score INTEGER DEFAULT 0, verified_history_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS parent_student_messages (
            {pk}, post_id INTEGER, parent_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL, message TEXT NOT NULL,
            is_anonymous INTEGER DEFAULT 0, parent_alias TEXT DEFAULT 'Proud Parent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, read_at TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS showcase_likes (
            {pk}, post_id INTEGER NOT NULL, user_ip_or_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS blocked_emails (
            {pk}, email TEXT UNIQUE NOT NULL, username TEXT,
            reason TEXT, is_blocked INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS direct_messages (
            {pk}, conversation_id TEXT NOT NULL,
            sender_id INTEGER NOT NULL, receiver_id INTEGER,
            sender_alias TEXT, is_anonymous INTEGER DEFAULT 0,
            message TEXT NOT NULL, read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS student_activity_history (
            {pk}, user_id INTEGER NOT NULL,
            arena_type TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT, metric_value TEXT NOT NULL,
            metric_unit TEXT, score_points INTEGER DEFAULT 0,
            tier TEXT DEFAULT 'bronze', is_posted INTEGER DEFAULT 0,
            source_ref TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS parent_students (
            {pk}, parent_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            is_confirmed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    for sql in tables:
        db_execute(sql)

    ensure_columns()

    cnt = db_fetchone("SELECT COUNT(*) FROM passages")
    if not cnt or cnt[0] < 30:
        passages = [
            ("general", "The Quick Brown Fox", "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. How vexingly quick daft zebras jump!"),
            ("general", "The Art of Focus", "Focus is not merely about saying yes to the thing you have to focus on. It means saying no to the hundred other good ideas that are there. You have to pick carefully."),
            ("general", "African Renaissance", "Education is the most powerful weapon which you can use to change the world. When an African youth grasps science, technology, and literature, whole communities rise."),
            ("general", "The Open Mind", "The mind that opens to a new idea never returns to its original size. Cultivating boundless curiosity unlocks realms of innovation that conventional schooling overlooks."),
            ("general", "The Digital Frontier", "A sovereign digital future belongs to nations that build their own computational infrastructure, train their own artificial intelligence, and cherish indigenous talent."),
            ("general", "Rivers and Persistence", "A river cuts through rock not because of its sheer power, but because of its relentless persistence. Great works are performed not by brute strength, but by endurance."),
            ("general", "Architecture of Discipline", "Discipline is the bridge between cognitive aspirations and tangible scholastic accomplishment. Every keystroke mastered builds mental acuity and resilience."),
            ("general", "The Midnight Lamp", "In the silence of late night study, when the rest of the world rests, visionaries trace the outlines of discoveries that will transform humanity tomorrow."),
            ("general", "Courage in Learning", "Success is not final, failure is not fatal: it is the courage to continue and refine one's craft that truly counts across every academic trial."),
            ("general", "The Echo of Wisdom", "Those who read widely and think deeply become architects of their own destiny, immune to transient illusions and anchored in fundamental truths."),
            ("general", "The Path to Mastery", "Mastery is not an accident of birth; it is the deliberate compounding of rigorous practice, patient reflection, and unyielding intellectual curiosity."),
            ("general", "The Sovereign Vision", "Building self-reliant educational platforms empowers young minds to compete globally while remaining firmly rooted in communal purpose and excellence."),
            ("science", "DNA Double Helix", "Deoxyribonucleic acid is a molecule composed of two polynucleotide chains that coil around each other to form a double helix carrying genetic instructions."),
            ("science", "Quantum Superposition", "In quantum mechanics, particles can exist in a superposition of states until measured, defying macroscopic intuition and enabling quantum computing."),
            ("science", "Cosmic Expansion", "The universe is expanding at an accelerating rate driven by dark energy, carrying distant galaxies beyond our cosmic horizon into eternal obscurity."),
            ("science", "Neural Plasticity", "Neuroplasticity allows the human brain to reorganize itself by forming new neural connections throughout life in response to learning and experience."),
            ("science", "Thermodynamics", "The second law of thermodynamics states that total entropy in an isolated system can never decrease over time, establishing the arrow of time."),
            ("science", "Photosynthesis", "Photosynthesis converts radiant solar photons into stable chemical energy, fixing atmospheric carbon dioxide into glucose to sustain terrestrial life."),
            ("science", "Plate Tectonics", "The rigid lithosphere floats upon the ductile asthenosphere, continuously sculpting mountain ranges, oceanic trenches, and volcanic island arcs."),
            ("science", "Black Hole Physics", "At the event horizon of a black hole, spacetime curvature becomes so acute that not even light can escape gravitational confinement."),
            ("code", "Python Hello World", "def hello_world():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    hello_world()"),
            ("code", "JavaScript Async Fetch", "const fetchData = async (endpoint) => {\n  const res = await fetch(endpoint);\n  return await res.json();\n};"),
            ("code", "Binary Search Algorithm", "def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: low = mid + 1\n        else: high = mid - 1\n    return -1"),
            ("code", "Fibonacci Generator", "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b"),
            ("code", "SQL Aggregation", "SELECT u.username, COUNT(s.id) as tests, AVG(s.wpm) as avg_speed FROM users u JOIN scores s ON u.id = s.user_id GROUP BY u.id ORDER BY avg_speed DESC LIMIT 10;"),
            ("code", "Recursive Factorial", "const factorial = (n) => (n <= 1 ? 1 : n * factorial(n - 1));"),
            ("code", "Neural Layer Class", "class NeuralLayer {\n  constructor(inputs, outputs) {\n    this.weights = new Float32Array(inputs * outputs);\n    this.biases = new Float32Array(outputs);\n  }\n}"),
            ("quotes", "Albert Einstein", "Imagination is more important than knowledge. For knowledge is limited, whereas imagination embraces the entire world, stimulating progress, giving birth to evolution."),
            ("quotes", "Alan Turing", "We can only see a short distance ahead, but we can see plenty there that needs to be done. A computer would deserve to be called intelligent if it could deceive a human."),
            ("quotes", "Nelson Mandela", "It always seems impossible until it is done. Education is the most powerful weapon which you can use to change the world."),
            ("quotes", "Ada Lovelace", "The Analytical Engine weaves algebraic patterns just as the Jacquard loom weaves flowers and leaves."),
            ("quotes", "Chinua Achebe", "Until the lions have their own historians, the history of the hunt will always glorify the hunter."),
            ("quotes", "Steve Jobs", "Stay hungry. Stay foolish. Never satisfy yourself that you know enough. The people who are crazy enough to think they can change the world usually do."),
            ("quotes", "Marie Curie", "Nothing in life is to be feared, it is only to be understood. Now is the time to understand more, so that we may fear less."),
            ("quotes", "Kwame Nkrumah", "Revolutions are brought about by men, by men who think as men of action and act as men of thought."),
            ("numbers", "Pi Digits", "3.1415926535 8979323846 2643383279 5028841971 6939937510 5820974944 5923078164"),
            ("numbers", "Mathematical Constants", "1.6180339887 4989484820 2.7182818284 5904523536 0.5772156649 0153286060"),
            ("numbers", "Prime Numbers Sequence", "2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97")
        ]
        for cat, title, content in passages:
            exists = db_fetchone("SELECT 1 FROM passages WHERE title=?", (title,))
            if not exists:
                db_execute("INSERT INTO passages (category, title, content) VALUES (?, ?, ?)", (cat, title, content))

    today = datetime.utcnow().date().isoformat()
    exists = db_fetchone("SELECT 1 FROM daily_challenges WHERE challenge_date=?", (today,))
    if not exists:
        db_execute("INSERT INTO daily_challenges (challenge_date, game_type, description, target_value, reward_xp) VALUES (?, ?, ?, ?, ?)",
                   (today, "typing", "Type at 40 WPM with 95% accuracy", 40, 50))

    db_execute("CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(user_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_scores_created ON scores(created_at)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_scores_user_created ON scores(user_id, created_at)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_chat_room ON chat_messages(room)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_classroom_code ON classrooms(code)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_tournament_status ON tournaments(status)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_api_key ON api_keys(key_hash)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON client_agents(agent_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_user_badges_uid ON user_badges(user_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_user_ratings_uid ON user_ratings(user_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_showcase_created ON showcase_posts(created_at)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_showcase_type ON showcase_posts(achievement_type)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_parent_msg_student ON parent_student_messages(student_id, read_at)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_replays_user ON typing_replays(user_id, created_at)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_hw_classroom ON homework(classroom_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_hw_sub_user ON homework_submissions(user_id)")
    db_execute("CREATE INDEX IF NOT EXISTS idx_classroom_members_stu ON classroom_members(student_id)")

    # Per-key typing statistics table
    db_execute("""
        CREATE TABLE IF NOT EXISTS key_stats (
            user_id INTEGER NOT NULL,
            key_char TEXT NOT NULL,
            total_hits INTEGER DEFAULT 0,
            correct_hits INTEGER DEFAULT 0,
            avg_time_ms REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, key_char)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def record_activity(user_id, arena_type, title, description, metric_value, metric_unit="", score_points=0, tier="bronze", source_ref=None):
    """Records a verified achievement into the student's activity history without duplicates."""
    try:
        if source_ref:
            existing = db_fetchone("SELECT id FROM student_activity_history WHERE user_id=? AND source_ref=?", (user_id, source_ref))
            if existing:
                return existing[0]
        # Also prevent duplicate milestones with identical user, arena_type, title, and metric_value
        existing = db_fetchone(
            "SELECT id FROM student_activity_history WHERE user_id=? AND arena_type=? AND title=? AND metric_value=?",
            (user_id, arena_type, title, str(metric_value))
        )
        if existing:
            return existing[0]

        return db_execute_returning_id(
            """INSERT INTO student_activity_history 
               (user_id, arena_type, title, description, metric_value, metric_unit, score_points, tier, is_posted, source_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (user_id, arena_type, title, description, str(metric_value), metric_unit, int(score_points), tier, source_ref)
        )
    except Exception:
        return None

def sync_all_student_history(user_id):
    """Backfills activity history for a student across all standardized arenas, ratings, and badges."""
    # 1. Best verified typing scores
    top_scores = db_fetchall(
        "SELECT id, wpm, accuracy, net_wpm, created_at, passage_category FROM scores WHERE user_id=? AND (verified=1 OR verified IS NULL) AND wpm <= 260 ORDER BY net_wpm DESC LIMIT 5",
        (user_id,)
    )
    for s in top_scores:
        sid = s[0]
        wpm = round(s[1], 1)
        acc = round(s[2], 1)
        net_wpm = round(s[3], 1)
        cat = (s[5] or "General").capitalize()
        tier = "legendary" if net_wpm >= 80 else ("gold" if net_wpm >= 60 else "silver")
        points = int(net_wpm * 10)
        record_activity(
            user_id=user_id,
            arena_type="typing",
            title=f"Typing Velocity Milestone: {net_wpm} WPM",
            description=f"Achieved {net_wpm} Net WPM with {acc}% biometric precision in {cat} Speed Typing Arena.",
            metric_value=f"{net_wpm} WPM",
            metric_unit="WPM",
            score_points=points,
            tier=tier,
            source_ref=f"score:{sid}"
        )

    # 2. Math Sprints
    math_rows = db_fetchall(
        "SELECT id, score, correct, total, difficulty, time_limit FROM math_sprints WHERE user_id=? ORDER BY score DESC LIMIT 5",
        (user_id,)
    )
    for m in math_rows:
        mid, sc, corr, tot = m[0], m[1], m[2], m[3]
        diff = (m[4] or "medium").capitalize()
        tlim = m[5] or 60
        tier = "legendary" if sc >= 200 else ("gold" if sc >= 120 else ("silver" if sc >= 60 else "bronze"))
        record_activity(
            user_id=user_id,
            arena_type="math",
            title=f"Math Sprint Velocity: {sc} Pts",
            description=f"Rapid mental arithmetic across {tot} problems ({corr} correct) in {tlim}s ({diff} difficulty).",
            metric_value=f"{sc} Pts ({corr}/{tot})",
            metric_unit="Math",
            score_points=int(sc),
            tier=tier,
            source_ref=f"math:{mid}"
        )

    # 3. Reaction Tests
    reaction_rows = db_fetchall(
        "SELECT id, best_ms, avg_ms, attempts FROM reaction_tests WHERE user_id=? ORDER BY best_ms ASC LIMIT 5",
        (user_id,)
    )
    for r in reaction_rows:
        rid, best, avg, att = r[0], r[1], r[2], r[3]
        tier = "legendary" if best <= 200 else ("gold" if best <= 250 else ("silver" if best <= 350 else "bronze"))
        record_activity(
            user_id=user_id,
            arena_type="reaction",
            title=f"Neuromuscular Reflex: {best}ms Latency",
            description=f"Visual stimulus response across {att} rounds with {avg}ms average latency.",
            metric_value=f"{best}ms Reflex",
            metric_unit="ms",
            score_points=max(10, 500 - best),
            tier=tier,
            source_ref=f"reaction:{rid}"
        )

    # 4. Pattern Tests
    pattern_rows = db_fetchall(
        "SELECT id, puzzles_solved, difficulty, avg_time_ms FROM pattern_tests WHERE user_id=? ORDER BY puzzles_solved DESC LIMIT 5",
        (user_id,)
    )
    for p in pattern_rows:
        pid, solved = p[0], p[1]
        diff = (p[2] or "medium").capitalize()
        tier = "legendary" if solved >= 10 else ("gold" if solved >= 6 else ("silver" if solved >= 3 else "bronze"))
        record_activity(
            user_id=user_id,
            arena_type="pattern",
            title=f"Pattern Induction: {solved} Puzzles Solved",
            description=f"Completed inductive visual sequence puzzles ({diff} difficulty).",
            metric_value=f"{solved} Patterns",
            metric_unit="Patterns",
            score_points=solved * 40,
            tier=tier,
            source_ref=f"pattern:{pid}"
        )

    # 5. Memory Tests
    memory_rows = db_fetchall(
        "SELECT id, level_reached, max_pattern_length, attempts FROM memory_tests WHERE user_id=? ORDER BY level_reached DESC LIMIT 5",
        (user_id,)
    )
    for mem in memory_rows:
        mem_id, lvl, max_pat, att = mem[0], mem[1], mem[2], mem[3]
        tier = "legendary" if lvl >= 10 else ("gold" if lvl >= 7 else ("silver" if lvl >= 4 else "bronze"))
        record_activity(
            user_id=user_id,
            arena_type="memory",
            title=f"Memory Palace: Level {lvl} Reached",
            description=f"Working memory sequence retention up to {max_pat} nodes across {att} attempts.",
            metric_value=f"Level {lvl} ({max_pat} Nodes)",
            metric_unit="Memory",
            score_points=lvl * 50,
            tier=tier,
            source_ref=f"memory:{mem_id}"
        )

    # 6. Word Blitz
    word_rows = db_fetchall(
        "SELECT id, score, time_limit FROM word_blitz_scores WHERE user_id=? ORDER BY score DESC LIMIT 5",
        (user_id,)
    )
    for w in word_rows:
        wid, sc, tlim = w[0], w[1], w[2] or 60
        tier = "legendary" if sc >= 80 else ("gold" if sc >= 50 else ("silver" if sc >= 25 else "bronze"))
        record_activity(
            user_id=user_id,
            arena_type="word",
            title=f"Word Blitz Fluency: {sc} Pts",
            description=f"Rapid lexical vocabulary fluency in {tlim} seconds.",
            metric_value=f"{sc} Pts",
            metric_unit="Words",
            score_points=sc,
            tier=tier,
            source_ref=f"word:{wid}"
        )

    # 7. Chess & Checkers ratings
    ratings = db_fetchall("SELECT game_type, rating, games_played FROM user_ratings WHERE user_id=? AND games_played > 0", (user_id,))
    for r in ratings:
        gtype = r[0]
        elo = r[1]
        tier = "legendary" if elo >= 1600 else ("gold" if elo >= 1400 else "silver")
        record_activity(
            user_id=user_id,
            arena_type=gtype,
            title=f"{gtype.capitalize()} Strategic Rating: {elo} ELO",
            description=f"Ranked competitive rating in tactical {gtype} arena across {r[2]} matches.",
            metric_value=f"{elo} ELO",
            metric_unit="ELO",
            score_points=int(elo / 2),
            tier=tier,
            source_ref=f"rating:{gtype}"
        )

    # 8. Badges
    badges = db_fetchall("SELECT badge_id, awarded_at FROM user_badges WHERE user_id=?", (user_id,))
    for b in badges:
        bid = b[0]
        meta = BADGES.get(bid, {})
        record_activity(
            user_id=user_id,
            arena_type="badge",
            title=f"Badge Unlocked: {meta.get('name', bid)}",
            description=meta.get('desc', 'Earned merit badge in Lumina Talent Ecosystem.'),
            metric_value=meta.get('name', 'Badge'),
            metric_unit="Badge",
            score_points=meta.get('xp', 50),
            tier="gold",
            source_ref=f"badge:{bid}"
        )

def get_inter_house_standings():
    """Aggregates cognitive & academic points for Good Shepherd Catholic College Houses:
       - St. Michael House (Red)
       - St. Gabriel House (Blue)
       - St. Raphael House (Green)
       - St. Joseph House (Gold)
    """
    houses = [
        {"name": "St. Michael House", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.15)", "motto": "Strength & Valor", "icon": "🛡️", "points": 0, "members": 0, "top_student": None},
        {"name": "St. Gabriel House", "color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.15)", "motto": "Truth & Eloquence", "icon": "🕊️", "points": 0, "members": 0, "top_student": None},
        {"name": "St. Raphael House", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.15)", "motto": "Healing & Wisdom", "icon": "🌿", "points": 0, "members": 0, "top_student": None},
        {"name": "St. Joseph House", "color": "#fbbf24", "bg": "rgba(251, 191, 36, 0.15)", "motto": "Diligence & Honor", "icon": "⭐", "points": 0, "members": 0, "top_student": None},
    ]

    try:
        users = db_fetchall("SELECT id, username, fullname, xp FROM users WHERE role='student' OR role='user'")
        for u in users:
            uid, uname, fname, xp = u[0], u[1], u[2] or u[1], u[3] or 0
            h_idx = uid % 4
            houses[h_idx]["members"] += 1
            houses[h_idx]["points"] += xp
            if not houses[h_idx]["top_student"] or xp > houses[h_idx]["top_student"]["xp"]:
                houses[h_idx]["top_student"] = {"username": uname, "fullname": fname, "xp": xp}
    except Exception:
        pass

    houses.sort(key=lambda x: x["points"], reverse=True)
    return houses



