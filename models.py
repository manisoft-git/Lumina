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
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return db_execute_returning_id(
            "INSERT INTO users (username, fullname, email, password_hash, role, parent_code, is_locked, is_anonymous, parent_alias, linked_student_id) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
            (username, fullname, email, ph, role, code, int(is_anonymous), parent_alias, linked_student_id)
        )

    @staticmethod
    def get_by_id(user_id):
        row = db_fetchone("SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE id=?", (user_id,))
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = db_fetchone("SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE username=?", (username,))
        return User(row) if row else None

    @staticmethod
    def get_by_parent_code(code):
        row = db_fetchone("SELECT id, username, fullname, email, password_hash, role, xp, level, streak, longest_streak, last_active, parent_code, created_at, is_locked, is_anonymous, parent_alias, linked_student_id FROM users WHERE parent_code=?", (code,))
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
    if not cnt or cnt[0] == 0:
        passages = [
            ("general", "The Quick Brown Fox", "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. How vexingly quick daft zebras jump!"),
            ("code", "Python Hello World", "def hello_world():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    hello_world()"),
            ("quotes", "Einstein", "Imagination is more important than knowledge. For knowledge is limited, whereas imagination embraces the entire world."),
            ("numbers", "Pi Digits", "3.1415926535 8979323846 2643383279 5028841971 6939937510 5820974944 5923078164"),
            ("science", "DNA", "Deoxyribonucleic acid is a molecule composed of two polynucleotide chains that coil around each other to form a double helix."),
            ("code", "JavaScript Function", "const greet = (name) => {\n  return `Hello, ${name}!`;\n};\nconsole.log(greet('Lumina'));"),
            ("quotes", "Turing", "We can only see a short distance ahead, but we can see plenty there that needs to be done."),
        ]
        for cat, title, content in passages:
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

    cnt_showcase = db_fetchone("SELECT COUNT(*) FROM showcase_posts")
    if not cnt_showcase or cnt_showcase[0] == 0:
        first_user = db_fetchone("SELECT id FROM users LIMIT 1")
        uid = first_user[0] if first_user else 1
        initial_posts = [
            (uid, "Broke 125 WPM on Advanced Python Syntax! ⚡", "Practiced late last night with Bionic Reading enabled. The saccade fixations made code reading so much faster! Dedicated to our upcoming school competition.", "image", "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80", "typing_record", "125 WPM • 99.4% Acc", 14),
            (uid, "Certified: Algorithmic Architect (MIT Pathway Matched) 🏛️", "My 7-axis cognitive radar just qualified for the MIT EECS pathway after yesterday's tournament win and math sprint record!", "image", "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&q=80", "cognitive_talent", "LTI: 940 • Top 1%", 28),
            (uid, "Checkmated Grandmaster Bot in 34 Moves! ♟️", "Double knight sacrifice in the endgame against Manisoft_Chess[GM]. ELO jumped by +45 points!", "image", "https://images.unsplash.com/photo-1529699211952-734e80c4d42b?w=800&q=80", "chess_win", "ELO: 1520 • Victory", 19)
        ]
        for p in initial_posts:
            try:
                db_execute(
                    "INSERT INTO showcase_posts (student_id, title, content, media_type, media_url, achievement_type, stat_highlight, likes_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    p
                )
            except Exception:
                pass

def record_activity(user_id, arena_type, title, description, metric_value, metric_unit="", score_points=0, tier="bronze"):
    """Records a verified achievement into the student's activity history."""
    try:
        return db_execute_returning_id(
            """INSERT INTO student_activity_history 
               (user_id, arena_type, title, description, metric_value, metric_unit, score_points, tier, is_posted)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (user_id, arena_type, title, description, str(metric_value), metric_unit, int(score_points), tier)
        )
    except Exception:
        return None

def sync_all_student_history(user_id):
    """Backfills activity history for a student from verified scores, math sprints, chess, ratings, and badges."""
    existing_count = (db_fetchone("SELECT COUNT(*) FROM student_activity_history WHERE user_id=?", (user_id,)) or [0])[0]
    if existing_count > 0:
        return
    # 1. Best verified typing scores
    top_scores = db_fetchall("SELECT wpm, accuracy, net_wpm, created_at FROM scores WHERE user_id=? AND (verified=1 OR verified IS NULL) AND wpm <= 260 ORDER BY net_wpm DESC LIMIT 5", (user_id,))
    for s in top_scores:
        wpm = round(s[0], 1)
        acc = round(s[1], 1)
        tier = "legendary" if wpm >= 80 else ("gold" if wpm >= 60 else "silver")
        points = int(wpm * 10)
        record_activity(
            user_id=user_id,
            arena_type="typing",
            title=f"Typing Velocity Milestone: {wpm} WPM",
            description=f"Achieved {wpm} Net WPM with {acc}% biometric precision in Speed Typing Arena.",
            metric_value=f"{wpm} WPM",
            metric_unit="WPM",
            score_points=points,
            tier=tier
        )

    # 2. Chess & Checkers ratings
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
            tier=tier
        )

    # 3. Badges
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
            tier="gold"
        )


