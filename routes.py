#!/usr/bin/env python3
"""HTTP routes for Lumina v5.0 — register_routes(app) pattern"""
import csv
import io
import json
import os
import math
import hashlib
import random
import string
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, jsonify, Response, session
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash

from db import db_execute, db_fetchall, db_fetchone
from models import User, update_elo, check_badges, award_xp, check_streak, BADGES
from talent_engine import compute_cognitive_profile, compute_institutional_profile
from anti_cheat import AntiCheatEngine

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "teacher":
            flash("Teachers only.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

def register_routes(app):

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            u = request.form.get("username", "").strip()
            fn = request.form.get("fullname", "").strip()
            em = request.form.get("email", "").strip()
            pw = request.form.get("password", "")
            role = request.form.get("role", "student")
            tkey = request.form.get("teacher_key", "")
            if role == "teacher" and tkey != os.environ.get("TEACHER_KEY", "LUMINA_EDU_2026"):
                flash("Invalid teacher key.", "error")
                return redirect(url_for("register"))
            if len(pw) < 6:
                flash("Password must be at least 6 characters.", "error")
                return redirect(url_for("register"))
            try:
                uid = User.create(u, fn, em, pw, role)
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))
            except Exception:
                flash("Username or email already taken.", "error")
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            uname = request.form.get("username", "").strip()
            pw = request.form.get("password", "")
            user = User.get_by_username(uname)
            if user and user.check_password(pw):
                login_user(user)
                check_streak(user.id)
                return redirect(url_for("dashboard"))
            flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("home"))

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        check_streak(current_user.id)
        scores = db_fetchall(
            "SELECT wpm, accuracy, net_wpm, passage_category, created_at FROM scores WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (current_user.id,)
        )
        badges = db_fetchall("SELECT badge_id, awarded_at FROM user_badges WHERE user_id=?", (current_user.id,))
        badge_list = []
        for b in badges:
            d = BADGES.get(b[0], {})
            badge_list.append({"id": b[0], "name": d.get("name", b[0]), "desc": d.get("desc", ""), "date": b[1]})
        classrooms = db_fetchall("""
            SELECT c.id, c.name, c.code FROM classrooms c
            JOIN classroom_members cm ON c.id = cm.classroom_id
            WHERE cm.student_id = ?
        """, (current_user.id,))
        ratings = db_fetchall("SELECT game_type, rating FROM user_ratings WHERE user_id=?", (current_user.id,))
        homework = db_fetchall("""
            SELECT h.id, h.title, h.instructions, h.due_date, h.min_wpm_target, hs.wpm
            FROM homework h
            JOIN classroom_members cm ON h.classroom_id = cm.classroom_id
            LEFT JOIN homework_submissions hs ON hs.homework_id = h.id AND hs.user_id = ?
            WHERE cm.student_id = ? AND h.due_date >= CURRENT_DATE
            ORDER BY h.due_date
        """, (current_user.id, current_user.id))
        today = datetime.utcnow().date().isoformat()
        dc = db_fetchone("SELECT id, game_type, description, target_value, reward_xp FROM daily_challenges WHERE challenge_date=?", (today,))
        dcp = None
        if dc:
            dcp = db_fetchone("SELECT progress, completed FROM user_challenges WHERE user_id=? AND challenge_id=?", (current_user.id, dc[0]))
        my_tours = db_fetchall("""
            SELECT t.id, t.name, t.game_type, t.status FROM tournaments t
            JOIN tournament_players tp ON t.id = tp.tournament_id
            WHERE tp.user_id = ? ORDER BY t.created_at DESC LIMIT 5
        """, (current_user.id,))
        api_keys = db_fetchall("SELECT name, created_at, request_count FROM api_keys WHERE user_id=?", (current_user.id,))
        return render_template("dashboard.html", scores=scores, badges=badge_list, classrooms=classrooms,
                               ratings=ratings, homework=homework, daily_challenge=dc, daily_progress=dcp,
                               tournaments=my_tours, user=current_user, api_keys=api_keys)

    @app.route("/typing")
    @login_required
    def typing_page():
        category = request.args.get("category", "general")
        focus = request.args.get("focus", "false").lower() == "true"
        rows = db_fetchall("SELECT content, title FROM passages WHERE category=? ORDER BY RANDOM() LIMIT 1", (category,))
        if not rows:
            rows = db_fetchall("SELECT content, title FROM passages WHERE category = 'general' ORDER BY RANDOM() LIMIT 1")
        passage = rows[0][0] if rows else "The quick brown fox jumps over the lazy dog."
        title = rows[0][1] if rows else "Default"
        return render_template("typing.html", passage=passage, title=title, category=category, focus=focus)

    @app.route("/competitions")
    @login_required
    def competitions_hub():
        return render_template("competitions_hub.html")

    @app.route("/competitions/typing/<room_id>")
    @login_required
    def typing_competition(room_id):
        rows = db_fetchall("SELECT content, title FROM passages WHERE category = 'general' ORDER BY RANDOM() LIMIT 1")
        passage = rows[0][0] if rows else "The quick brown fox jumps over the lazy dog."
        return render_template("competitions.html", room_id=room_id, passage=passage, game_type="typing")

    @app.route("/chess/<room_id>")
    @login_required
    def chess_page(room_id):
        bot = request.args.get("bot", "0")
        return render_template("chess.html", room_id=room_id, bot=bot)

    @app.route("/checkers/<room_id>")
    @login_required
    def checkers_page(room_id):
        bot = request.args.get("bot", "0")
        return render_template("checkers.html", room_id=room_id, bot=bot)

    @app.route("/chat")
    @login_required
    def chat_page():
        return render_template("chat.html")

    @app.route("/leaderboard")
    def leaderboard():
        period = request.args.get("period", "all")
        classroom = request.args.get("classroom", "")
        where_clauses = []
        params = []
        if period == "weekly":
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            where_clauses.append("s.created_at >= ?")
            params.append(seven_days_ago)
        elif period == "today":
            today = datetime.utcnow().date().isoformat()
            where_clauses.append("s.created_at >= ?")
            params.append(today)
        if classroom:
            where_clauses.append("EXISTS (SELECT 1 FROM classroom_members cm WHERE cm.student_id = u.id AND cm.classroom_id = ?)")
            params.append(classroom)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"""
            SELECT * FROM (
                SELECT u.id, u.username, u.fullname, COALESCE(u.level, 1) as level, COALESCE(u.xp, 0) as xp,
                       COALESCE(s.wpm, 0) as wpm, COALESCE(s.accuracy, 0) as accuracy, COALESCE(s.net_wpm, 0) as net_wpm,
                       s.passage_category, s.created_at,
                       ROW_NUMBER() OVER (PARTITION BY u.id ORDER BY COALESCE(s.net_wpm, 0) DESC, COALESCE(s.accuracy, 0) DESC) as rn
                FROM users u
                JOIN scores s ON u.id = s.user_id
                {where_sql}
            ) t WHERE rn = 1
            ORDER BY net_wpm DESC, accuracy DESC
            LIMIT 100
        """
        rows = db_fetchall(sql, tuple(params))
        return render_template("leaderboard.html", rows=rows, period=period)

    @app.route("/analytics")
    def analytics():
        is_guest = not current_user.is_authenticated
        if is_guest:
            uid = None
            talent_profile = compute_institutional_profile()
            avg_wpm_row = db_fetchone("SELECT AVG(net_wpm), AVG(accuracy), MAX(net_wpm) FROM scores")
            best_wpm = round(float(avg_wpm_row[2]), 1) if (avg_wpm_row and avg_wpm_row[2]) else 78.5
            best_acc = round(float(avg_wpm_row[1]), 1) if (avg_wpm_row and avg_wpm_row[1]) else 96.5
            
            math_best_row = db_fetchone("SELECT MAX(score) FROM math_sprints")
            math_best = math_best_row[0] if (math_best_row and math_best_row[0]) else 54
            
            mem_best_row = db_fetchone("SELECT MAX(level_reached) FROM memory_tests")
            memory_best = mem_best_row[0] if (mem_best_row and mem_best_row[0]) else 9
            
            react_best_row = db_fetchone("SELECT MIN(best_ms) FROM reaction_tests WHERE best_ms > 50")
            reaction_best = react_best_row[0] if (react_best_row and react_best_row[0]) else 215
            
            pat_best_row = db_fetchone("SELECT MAX(puzzles_solved) FROM pattern_tests")
            pattern_best = pat_best_row[0] if (pat_best_row and pat_best_row[0]) else 14
            
            word_best_row = db_fetchone("SELECT MAX(score) FROM word_blitz_scores")
            word_best = word_best_row[0] if (word_best_row and word_best_row[0]) else 380
            
            chess_best_row = db_fetchone("SELECT MAX(rating) FROM user_ratings WHERE game_type='chess'")
            chess_best = chess_best_row[0] if (chess_best_row and chess_best_row[0]) else 1450
            
            raw_progress = db_fetchall("SELECT date(created_at) as d, AVG(net_wpm), AVG(accuracy) FROM scores GROUP BY d ORDER BY d LIMIT 30")
            has_personal_data = False
            consistency_score = 94.2
            biometric_integrity = 99.4
            tot_row = db_fetchone("SELECT COUNT(*) FROM scores")
            total_tests = tot_row[0] if tot_row else 128
            
            heat_rows = db_fetchall("SELECT error_map FROM scores WHERE error_map IS NOT NULL LIMIT 100")
            heatmap = {}
            for r in heat_rows:
                try:
                    em = json.loads(r[0])
                    for k, v in em.items():
                        heatmap[k] = heatmap.get(k, 0) + v
                except Exception:
                    pass
            if not heatmap:
                heatmap = {"p": 14, "q": 9, "b": 18, "z": 7, "x": 11, ";": 16, "-": 8, "c": 12}
        else:
            uid = current_user.id
            talent_profile = compute_cognitive_profile(uid)
            raw_progress = db_fetchall(
                "SELECT date(created_at) as d, AVG(net_wpm), AVG(accuracy) FROM scores WHERE user_id=? GROUP BY d ORDER BY d LIMIT 30",
                (uid,)
            )
            has_personal_data = len(raw_progress) > 0
            
            heat_rows = db_fetchall("SELECT error_map FROM scores WHERE user_id=? AND error_map IS NOT NULL", (uid,))
            heatmap = {}
            for r in heat_rows:
                try:
                    em = json.loads(r[0])
                    for k, v in em.items():
                        heatmap[k] = heatmap.get(k, 0) + v
                except Exception:
                    pass
                    
            math_best_row = db_fetchone("SELECT MAX(score) FROM math_sprints WHERE user_id=?", (uid,))
            memory_best_row = db_fetchone("SELECT MAX(level_reached) FROM memory_tests WHERE user_id=?", (uid,))
            reaction_best_row = db_fetchone("SELECT MIN(best_ms) FROM reaction_tests WHERE user_id=? AND best_ms > 50", (uid,))
            pattern_best_row = db_fetchone("SELECT MAX(puzzles_solved) FROM pattern_tests WHERE user_id=?", (uid,))
            word_best_row = db_fetchone("SELECT MAX(score) FROM word_blitz_scores WHERE user_id=?", (uid,))
            chess_best_row = db_fetchone("SELECT MAX(rating) FROM user_ratings WHERE user_id=? AND game_type='chess'", (uid,))
            best_wpm_row = db_fetchone("SELECT MAX(net_wpm), MAX(accuracy) FROM scores WHERE user_id=?", (uid,))
            total_tests_row = db_fetchone("SELECT COUNT(*) FROM scores WHERE user_id=?", (uid,))
            
            math_best = math_best_row[0] if (math_best_row and math_best_row[0]) else 0
            memory_best = memory_best_row[0] if (memory_best_row and memory_best_row[0]) else 0
            reaction_best = reaction_best_row[0] if (reaction_best_row and reaction_best_row[0]) else 0
            pattern_best = pattern_best_row[0] if (pattern_best_row and pattern_best_row[0]) else 0
            word_best = word_best_row[0] if (word_best_row and word_best_row[0]) else 0
            chess_best = chess_best_row[0] if (chess_best_row and chess_best_row[0]) else 1200
            best_wpm = round(best_wpm_row[0], 1) if (best_wpm_row and best_wpm_row[0]) else 0
            best_acc = round(best_wpm_row[1], 1) if (best_wpm_row and best_wpm_row[1]) else 100
            total_tests = total_tests_row[0] if total_tests_row else 0
            
            # Biometric consistency & integrity
            all_wpms = [s[0] for s in db_fetchall("SELECT net_wpm FROM scores WHERE user_id=? AND net_wpm IS NOT NULL ORDER BY created_at DESC LIMIT 30", (uid,)) if s[0] is not None]
            if len(all_wpms) >= 3:
                avg_w = sum(all_wpms) / len(all_wpms)
                var = sum((w - avg_w) ** 2 for w in all_wpms) / len(all_wpms)
                std = math.sqrt(var)
                consistency_score = round(max(50.0, min(99.0, 100.0 - (std / (avg_w or 1.0)) * 40.0)), 1)
            else:
                consistency_score = 91.0
                
            avg_int_row = db_fetchone("SELECT AVG(integrity_score) FROM scores WHERE user_id=? AND integrity_score IS NOT NULL", (uid,))
            if avg_int_row and avg_int_row[0] is not None:
                biometric_integrity = round(float(avg_int_row[0]) * 100.0, 1)
            else:
                biometric_integrity = 99.1

        # Format progress array cleanly into JSON-serializable list of [date_str, wpm_float, acc_float]
        if raw_progress:
            progress = [[str(r[0]), round(float(r[1] or 0), 1), round(float(r[2] or 0), 1)] for r in raw_progress]
        else:
            today = datetime.utcnow().date()
            progress = [
                [(today - timedelta(days=6)).strftime("%Y-%m-%d"), 58.2, 94.5],
                [(today - timedelta(days=5)).strftime("%Y-%m-%d"), 61.0, 95.2],
                [(today - timedelta(days=4)).strftime("%Y-%m-%d"), 63.5, 96.0],
                [(today - timedelta(days=3)).strftime("%Y-%m-%d"), 65.8, 96.8],
                [(today - timedelta(days=2)).strftime("%Y-%m-%d"), 67.2, 97.1],
                [(today - timedelta(days=1)).strftime("%Y-%m-%d"), 69.4, 97.4],
                [today.strftime("%Y-%m-%d"), 71.8, 98.0],
            ]

        return render_template("analytics.html", heatmap=heatmap, progress=progress,
                               math_best=math_best,
                               memory_best=memory_best,
                               reaction_best=reaction_best,
                               pattern_best=pattern_best,
                               word_best=word_best,
                               chess_best=chess_best,
                               best_wpm=best_wpm,
                               best_acc=best_acc,
                               talent_profile=talent_profile,
                               is_guest=is_guest,
                               has_personal_data=has_personal_data,
                               consistency_score=consistency_score,
                               biometric_integrity=biometric_integrity,
                               total_tests=total_tests)

    @app.route("/history")
    @login_required
    def history():
        rows = db_fetchall(
            "SELECT wpm, accuracy, net_wpm, errors, passage_category, room_id, created_at FROM scores WHERE user_id=? ORDER BY created_at DESC",
            (current_user.id,)
        )
        return render_template("history.html", rows=rows)

    @app.route("/badges")
    @login_required
    def badges_page():
        rows = db_fetchall("SELECT badge_id, awarded_at FROM user_badges WHERE user_id=?", (current_user.id,))
        earned = {r[0]: r[1] for r in rows}
        all_badges = []
        for bid, info in BADGES.items():
            all_badges.append({"id": bid, "name": info["name"], "desc": info["desc"], "xp": info["xp"], "earned": earned.get(bid)})
        return render_template("badges.html", badges=all_badges)

    @app.route("/profile/<int:user_id>")
    def profile(user_id):
        user = User.get_by_id(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("leaderboard"))
        scores = db_fetchall(
            "SELECT wpm, accuracy, net_wpm, passage_category, created_at FROM scores WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        )
        ratings = db_fetchall("SELECT game_type, rating, games_played FROM user_ratings WHERE user_id=?", (user_id,))
        talent_profile = compute_cognitive_profile(user_id)
        return render_template("profile.html", user=user, scores=scores, ratings=ratings, talent_profile=talent_profile)

    @app.route("/talent-profile")
    @login_required
    def talent_profile_page():
        profile_data = compute_cognitive_profile(current_user.id)
        return render_template("talent_profile.html", profile=profile_data)

    @app.route("/talent-profile/<int:user_id>")
    def student_talent_profile(user_id):
        user = User.get_by_id(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("leaderboard"))
        profile_data = compute_cognitive_profile(user_id)
        return render_template("talent_profile.html", profile=profile_data)

    @app.route("/talent-report")
    @login_required
    def talent_report_self():
        profile_data = compute_cognitive_profile(current_user.id)
        return render_template("talent_report.html", profile=profile_data)

    @app.route("/talent-report/<int:user_id>")
    def talent_report(user_id):
        user = User.get_by_id(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("leaderboard"))
        profile_data = compute_cognitive_profile(user_id)
        return render_template("talent_report.html", profile=profile_data)

    @app.route("/classroom/projector/<room_id>")
    def classroom_projector(room_id):
        return render_template("classroom_projector.html", room_id=room_id)

    @app.route("/api/v1/talent_profile/<int:user_id>")
    def api_talent_profile(user_id):
        profile_data = compute_cognitive_profile(user_id)
        if not profile_data:
            return jsonify({"error": "User not found"}), 404
        return jsonify(profile_data)

    @app.route("/relay")
    @login_required
    def relay_lobby():
        room_id = request.args.get("room", "RELAY_ARENA_1")
        return redirect(url_for("relay_arena", room_id=room_id))

    @app.route("/relay/<room_id>")
    @login_required
    def relay_arena(room_id):
        return render_template("team_relay.html", room_id=room_id)

    @app.route("/offline-hub")
    def offline_hub():
        import socket
        from config import PORT
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        return render_template("offline_hub.html", local_ip=local_ip, port=PORT)

    @app.route("/games")
    @login_required
    def games_hub():
        return render_template("games_hub.html")

    @app.route("/games/math")
    @login_required
    def math_sprint():
        return render_template("math_sprint.html")

    @app.route("/games/memory")
    @login_required
    def memory_palace():
        return render_template("memory_palace.html")

    @app.route("/games/reaction")
    @login_required
    def reaction_test():
        return render_template("reaction_test.html")

    @app.route("/games/pattern")
    @login_required
    def pattern_match():
        return render_template("pattern_match.html")

    @app.route("/games/word")
    @login_required
    def word_blitz():
        return render_template("word_blitz.html")

    @app.route("/teacher")
    @login_required
    @teacher_required
    def teacher_panel():
        classrooms = db_fetchall("SELECT id, name, code, created_at FROM classrooms WHERE teacher_id=?", (current_user.id,))
        custom_passages = db_fetchall("SELECT id, title, category, created_at FROM custom_passages WHERE teacher_id=?", (current_user.id,))
        homeworks = db_fetchall("SELECT id, title, due_date, classroom_id FROM homework WHERE teacher_id=? ORDER BY created_at DESC", (current_user.id,))
        return render_template("teacher.html", classrooms=classrooms, custom_passages=custom_passages, homeworks=homeworks)

    @app.route("/teacher/monitor/<classroom_code>")
    @login_required
    @teacher_required
    def teacher_monitor(classroom_code):
        cls = db_fetchone("SELECT id, name FROM classrooms WHERE code=? AND teacher_id=?", (classroom_code, current_user.id))
        if not cls:
            flash("Classroom not found.", "error")
            return redirect(url_for("teacher_panel"))
        return render_template("teacher_monitor.html", classroom=cls, code=classroom_code)

    @app.route("/teacher/export")
    @login_required
    @teacher_required
    def export_csv():
        rows = db_fetchall("""
            SELECT u.username, u.fullname, u.level, s.wpm, s.accuracy, s.net_wpm, s.passage_category, s.created_at
            FROM scores s JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
        """)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Username", "Full Name", "Level", "WPM", "Accuracy", "Net WPM", "Category", "Date"])
        for r in rows:
            writer.writerow(r)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=lumina_scores.csv"})

    @app.route("/teacher/create_classroom", methods=["POST"])
    @login_required
    @teacher_required
    def create_classroom():
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        if not name or not code:
            flash("Name and code required.", "error")
            return redirect(url_for("teacher_panel"))
        try:
            db_execute("INSERT INTO classrooms (teacher_id, name, code) VALUES (?, ?, ?)", (current_user.id, name, code))
            flash("Classroom created.", "success")
        except Exception:
            flash("Code already in use.", "error")
        return redirect(url_for("teacher_panel"))

    @app.route("/teacher/create_homework", methods=["POST"])
    @login_required
    @teacher_required
    def create_homework():
        title = request.form.get("title", "").strip()
        instructions = request.form.get("instructions", "").strip()
        passage = request.form.get("passage", "").strip()
        classroom_id = request.form.get("classroom_id")
        min_wpm = int(request.form.get("min_wpm", 0) or 0)
        due = request.form.get("due_date")
        if not title or not classroom_id:
            flash("Title and classroom required.", "error")
            return redirect(url_for("teacher_panel"))
        db_execute("INSERT INTO homework (teacher_id, classroom_id, title, instructions, passage_content, min_wpm_target, due_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (current_user.id, classroom_id, title, instructions, passage, min_wpm, due))
        flash("Homework assigned.", "success")
        return redirect(url_for("teacher_panel"))

    @app.route("/teacher/create_passage", methods=["POST"])
    @login_required
    @teacher_required
    def create_passage():
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "custom")
        classroom_id = request.form.get("classroom_id") or None
        if not title or not content:
            flash("Title and content required.", "error")
            return redirect(url_for("teacher_panel"))
        db_execute("INSERT INTO custom_passages (teacher_id, classroom_id, title, content, category) VALUES (?, ?, ?, ?, ?)",
                   (current_user.id, classroom_id, title, content, category))
        flash("Passage created.", "success")
        return redirect(url_for("teacher_panel"))

    @app.route("/join_classroom", methods=["POST"])
    @login_required
    def join_classroom():
        code = request.form.get("code", "").strip().upper()
        row = db_fetchone("SELECT id FROM classrooms WHERE code=?", (code,))
        if not row:
            flash("Invalid classroom code.", "error")
            return redirect(url_for("dashboard"))
        try:
            db_execute("INSERT INTO classroom_members (classroom_id, student_id) VALUES (?, ?)", (row[0], current_user.id))
            flash("Joined classroom!", "success")
        except Exception:
            flash("Already a member.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/submit_score", methods=["POST"])
    @login_required
    def submit_score():
        data = request.get_json() or {}
        wpm = float(data.get("wpm", 0))
        acc = float(data.get("accuracy", 0))
        errs = int(data.get("errors", 0))
        net_wpm = max(0.0, float(data.get("net_wpm", wpm - errs)))
        cat = data.get("category", "general")
        room_id = data.get("room_id")
        error_map = json.dumps(data.get("error_map", {}))
        timings = data.get("timings")
        duration_sec = data.get("duration_sec")
        passage_len = data.get("passage_len", 0)

        anti_cheat = AntiCheatEngine.verify_submission(
            wpm=wpm, accuracy=acc, duration_sec=duration_sec,
            timings=timings, passage_len=passage_len
        )
        verified = 1 if anti_cheat["verified"] else 0
        integrity = anti_cheat["integrity_score"]

        if not verified:
            reasons_str = "; ".join(anti_cheat.get("flags", []))
            try:
                db_execute(
                    "INSERT INTO anti_cheat_logs (user_id, wpm, confidence, reasons) VALUES (?, ?, ?, ?)",
                    (current_user.id, wpm, integrity, reasons_str)
                )
            except Exception:
                pass

        db_execute(
            "INSERT INTO scores (user_id, wpm, accuracy, errors, net_wpm, passage_category, room_id, error_map, verified, integrity_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (current_user.id, wpm, acc, errs, net_wpm, cat, room_id, error_map, verified, integrity)
        )
        xp = max(0, int(net_wpm / 2)) if verified else 0
        if verified:
            award_xp(current_user.id, xp)
            check_badges(current_user.id)
        return jsonify({"status": "ok", "xp_earned": xp, "anti_cheat": anti_cheat})

    @app.route("/save_replay", methods=["POST"])
    @login_required
    def save_replay():
        data = request.get_json() or {}
        db_execute("INSERT INTO typing_replays (user_id, passage, keystrokes, wpm, accuracy) VALUES (?, ?, ?, ?, ?)",
                   (current_user.id, data.get("passage"), json.dumps(data.get("keystrokes", [])), data.get("wpm", 0), data.get("accuracy", 100)))
        return jsonify({"status": "ok"})

    @app.route("/submit_homework/<int:hid>", methods=["POST"])
    @login_required
    def submit_homework(hid):
        data = request.get_json() or {}
        wpm = float(data.get("wpm", 0))
        acc = float(data.get("accuracy", 0))
        timings = data.get("timings")
        duration_sec = data.get("duration_sec")
        passage_len = data.get("passage_len", 0)
        anti_cheat = AntiCheatEngine.verify_submission(wpm=wpm, accuracy=acc, duration_sec=duration_sec, timings=timings, passage_len=passage_len)
        if not anti_cheat["verified"]:
            return jsonify({"status": "rejected", "reason": anti_cheat["reason"]}), 400
        db_execute("INSERT INTO homework_submissions (homework_id, user_id, wpm, accuracy) VALUES (?, ?, ?, ?)",
                   (hid, current_user.id, wpm, acc))
        hw = db_fetchone("SELECT min_wpm_target FROM homework WHERE id=?", (hid,))
        passed = hw and wpm >= hw[0]
        if passed:
            award_xp(current_user.id, 50)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "passed": passed, "anti_cheat": anti_cheat})

    @app.route("/submit_challenge", methods=["POST"])
    @login_required
    def submit_challenge():
        data = request.get_json() or {}
        cid = data.get("challenge_id")
        if not cid:
            today = datetime.utcnow().date().isoformat()
            ch = db_fetchone("SELECT id FROM daily_challenges WHERE challenge_date=?", (today,))
            if ch:
                cid = ch[0]
            else:
                return jsonify({"status": "error", "message": "No active challenge found"}), 400

        progress = int(data.get("progress", 0))
        completed = bool(data.get("completed", False)) or (data.get("status") == "completed")
        comp_val = 1 if completed else 0
        comp_time = datetime.utcnow().isoformat() if completed else None

        existing = db_fetchone("SELECT completed FROM user_challenges WHERE user_id=? AND challenge_id=?", (current_user.id, cid))
        xp_earned = 0
        if existing:
            was_completed = bool(existing[0])
            db_execute("UPDATE user_challenges SET progress=?, completed=MAX(completed, ?), completed_at=COALESCE(completed_at, ?) WHERE user_id=? AND challenge_id=?",
                       (progress, comp_val, comp_time, current_user.id, cid))
            if completed and not was_completed:
                ch = db_fetchone("SELECT reward_xp FROM daily_challenges WHERE id=?", (cid,))
                if ch and ch[0]:
                    award_xp(current_user.id, ch[0])
                    xp_earned = ch[0]
        else:
            db_execute("INSERT INTO user_challenges (user_id, challenge_id, progress, completed, completed_at) VALUES (?, ?, ?, ?, ?)",
                       (current_user.id, cid, progress, comp_val, comp_time))
            if completed:
                ch = db_fetchone("SELECT reward_xp FROM daily_challenges WHERE id=?", (cid,))
                if ch and ch[0]:
                    award_xp(current_user.id, ch[0])
                    xp_earned = ch[0]
        return jsonify({"status": "ok", "xp_earned": xp_earned})

    @app.route("/submit/math", methods=["POST"])
    @login_required
    def submit_math():
        d = request.get_json() or {}
        score = int(d.get("score", 0))
        db_execute("INSERT INTO math_sprints (user_id, correct, total, difficulty, time_limit, score) VALUES (?, ?, ?, ?, ?, ?)",
                   (current_user.id, d.get("correct", 0), d.get("total", 0), d.get("difficulty", "medium"), d.get("time_limit", 60), score))
        xp_earned = max(0, score // 5)
        award_xp(current_user.id, xp_earned)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "xp": xp_earned})

    @app.route("/submit/memory", methods=["POST"])
    @login_required
    def submit_memory():
        d = request.get_json() or {}
        level = int(d.get("level_reached", 0))
        db_execute("INSERT INTO memory_tests (user_id, level_reached, max_pattern_length, attempts) VALUES (?, ?, ?, ?)",
                   (current_user.id, level, d.get("max_pattern", 0), d.get("attempts", 1)))
        xp_earned = max(0, level * 10)
        award_xp(current_user.id, xp_earned)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "xp": xp_earned})

    @app.route("/submit/reaction", methods=["POST"])
    @login_required
    def submit_reaction():
        d = request.get_json() or {}
        try:
            raw_best = float(d.get("best_ms", 300))
            best = int(raw_best) if (not math.isnan(raw_best) and not math.isinf(raw_best) and raw_best > 0) else 300
        except (ValueError, OverflowError, TypeError):
            best = 300
        try:
            raw_avg = float(d.get("avg_ms", 350))
            avg = int(raw_avg) if (not math.isnan(raw_avg) and not math.isinf(raw_avg) and raw_avg > 0) else 350
        except (ValueError, OverflowError, TypeError):
            avg = 350
        attempts = int(d.get("attempts", 5))
        db_execute("INSERT INTO reaction_tests (user_id, best_ms, avg_ms, attempts) VALUES (?, ?, ?, ?)",
                   (current_user.id, best, avg, attempts))
        xp_earned = max(0, 100 - best // 5)
        award_xp(current_user.id, xp_earned)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "xp": xp_earned})

    @app.route("/submit/pattern", methods=["POST"])
    @login_required
    def submit_pattern():
        d = request.get_json()
        solved = int(d.get("puzzles_solved", 0))
        db_execute("INSERT INTO pattern_tests (user_id, puzzles_solved, difficulty, avg_time_ms) VALUES (?, ?, ?, ?)",
                   (current_user.id, solved, d.get("difficulty", "medium"), d.get("avg_time", 0)))
        award_xp(current_user.id, solved * 15)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "xp": solved * 15})

    @app.route("/submit/word", methods=["POST"])
    @login_required
    def submit_word():
        d = request.get_json()
        score = int(d.get("score", 0))
        db_execute("INSERT INTO word_blitz_scores (user_id, score, words_found, time_limit) VALUES (?, ?, ?, ?)",
                   (current_user.id, score, json.dumps(d.get("words", [])), d.get("time_limit", 60)))
        award_xp(current_user.id, score * 3)
        check_badges(current_user.id)
        return jsonify({"status": "ok", "xp": score * 3})

    @app.route("/tournaments")
    @login_required
    def tournament_list():
        open_t = db_fetchall("SELECT id, name, game_type, format, max_players, created_by, created_at FROM tournaments WHERE status='open' ORDER BY created_at DESC")
        my_t = db_fetchall("""
            SELECT t.id, t.name, t.game_type, t.status FROM tournaments t
            JOIN tournament_players tp ON t.id = tp.tournament_id
            WHERE tp.user_id = ? ORDER BY t.created_at DESC
        """, (current_user.id,))
        return render_template("tournaments.html", open_tournaments=open_t, my_tournaments=my_t)

    @app.route("/tournaments/create", methods=["POST"])
    @login_required
    def create_tournament():
        name = request.form.get("name", "").strip()
        gtype = request.form.get("game_type", "typing")
        fmt = request.form.get("format", "bracket")
        max_p = int(request.form.get("max_players", 16) or 16)
        if not name:
            flash("Name required.", "error")
            return redirect(url_for("tournament_list"))
        db_execute("INSERT INTO tournaments (name, game_type, format, max_players, created_by) VALUES (?, ?, ?, ?, ?)",
                   (name, gtype, fmt, max_p, current_user.id))
        flash("Tournament created.", "success")
        return redirect(url_for("tournament_list"))

    @app.route("/tournaments/<int:tid>/join", methods=["POST"])
    @login_required
    def join_tournament(tid):
        t = db_fetchone("SELECT status, max_players FROM tournaments WHERE id=?", (tid,))
        if not t or t[0] != "open":
            flash("Tournament not open.", "error")
            return redirect(url_for("tournament_list"))
        count = db_fetchone("SELECT COUNT(*) FROM tournament_players WHERE tournament_id=?", (tid,))[0]
        if count >= t[1]:
            flash("Tournament full.", "error")
            return redirect(url_for("tournament_list"))
        try:
            db_execute("INSERT INTO tournament_players (tournament_id, user_id, seed) VALUES (?, ?, ?)", (tid, current_user.id, count + 1))
            flash("Joined tournament!", "success")
        except Exception:
            flash("Already joined.", "info")
        return redirect(url_for("tournament_detail", tid=tid))

    @app.route("/tournaments/<int:tid>")
    @login_required
    def tournament_detail(tid):
        t = db_fetchone("SELECT * FROM tournaments WHERE id=?", (tid,))
        if not t:
            flash("Not found.", "error")
            return redirect(url_for("tournament_list"))
        players = db_fetchall("""
            SELECT u.id, u.username, u.fullname, u.level, tp.seed, tp.score, tp.eliminated
            FROM tournament_players tp
            JOIN users u ON tp.user_id = u.id
            WHERE tp.tournament_id = ?
            ORDER BY tp.eliminated ASC, tp.score DESC
        """, (tid,))
        matches = db_fetchall("""
            SELECT tm.*, u1.username as p1_name, u2.username as p2_name, w.username as w_name
            FROM tournament_matches tm
            LEFT JOIN users u1 ON tm.player1_id = u1.id
            LEFT JOIN users u2 ON tm.player2_id = u2.id
            LEFT JOIN users w ON tm.winner_id = w.id
            WHERE tm.tournament_id = ?
            ORDER BY tm.round_number, tm.id
        """, (tid,))
        is_creator = t[6] == current_user.id
        is_player = any(p[0] == current_user.id for p in players)
        return render_template("tournament_detail.html", tournament=t, players=players, matches=matches, is_creator=is_creator, is_player=is_player)

    @app.route("/tournaments/<int:tid>/start", methods=["POST"])
    @login_required
    def start_tournament(tid):
        t = db_fetchone("SELECT created_by, status, format FROM tournaments WHERE id=?", (tid,))
        if not t or t[0] != current_user.id or t[1] != "open":
            flash("Cannot start.", "error")
            return redirect(url_for("tournament_detail", tid=tid))
        db_execute("UPDATE tournaments SET status='active', started_at=? WHERE id=?", (datetime.utcnow().isoformat(), tid))
        players = db_fetchall("SELECT user_id FROM tournament_players WHERE tournament_id=? ORDER BY seed", (tid,))
        pids = [p[0] for p in players]
        n = len(pids)
        if n < 2:
            flash("Need at least 2 players.", "error")
            return redirect(url_for("tournament_detail", tid=tid))
        for i in range(0, n, 2):
            p1 = pids[i]
            p2 = pids[i+1] if i+1 < n else None
            room_id = f"tour-{tid}-r1-m{i//2}"
            if p2 is None:
                db_execute("INSERT INTO tournament_matches (tournament_id, round_number, player1_id, player2_id, room_id, status, winner_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (tid, 1, p1, None, room_id, "complete", p1))
            else:
                db_execute("INSERT INTO tournament_matches (tournament_id, round_number, player1_id, player2_id, room_id, status) VALUES (?, ?, ?, ?, ?, ?)",
                           (tid, 1, p1, p2, room_id, "pending"))
        flash("Tournament started! Round 1 matches generated.", "success")
        return redirect(url_for("tournament_bracket", tid=tid))

    @app.route("/tournaments/<int:tid>/bracket")
    @login_required
    def tournament_bracket(tid):
        t = db_fetchone("SELECT * FROM tournaments WHERE id=?", (tid,))
        if not t:
            flash("Not found.", "error")
            return redirect(url_for("tournament_list"))
        matches = db_fetchall("""
            SELECT tm.*, u1.username as p1_name, u2.username as p2_name, w.username as w_name
            FROM tournament_matches tm
            LEFT JOIN users u1 ON tm.player1_id = u1.id
            LEFT JOIN users u2 ON tm.player2_id = u2.id
            LEFT JOIN users w ON tm.winner_id = w.id
            WHERE tm.tournament_id = ?
            ORDER BY tm.round_number, tm.id
        """, (tid,))
        return render_template("tournament_bracket.html", tournament=t, matches=matches)

    @app.route("/tournaments/match/<int:mid>/submit", methods=["POST"])
    @login_required
    def submit_match(mid):
        m = db_fetchone("SELECT * FROM tournament_matches WHERE id=?", (mid,))
        if not m or m[7] != "pending":
            return jsonify({"error": "Invalid match"}), 400
        data = request.get_json()
        winner = int(data.get("winner_id"))
        p1_score = float(data.get("p1_score", 0))
        p2_score = float(data.get("p2_score", 0))
        if winner not in [m[3], m[4]]:
            return jsonify({"error": "Invalid winner"}), 400
        db_execute("UPDATE tournament_matches SET winner_id=?, p1_score=?, p2_score=?, status='complete' WHERE id=?",
                   (winner, p1_score, p2_score, mid))
        current_round = m[2]
        next_round = current_round + 1
        match_idx = db_fetchone("SELECT COUNT(*) FROM tournament_matches WHERE tournament_id=? AND round_number=? AND id <= ?", (m[1], current_round, mid))[0] - 1
        next_match_idx = match_idx // 2
        next_match = db_fetchone("SELECT id, player1_id, player2_id FROM tournament_matches WHERE tournament_id=? AND round_number=? LIMIT 1 OFFSET ?",
                                 (m[1], next_round, next_match_idx))
        if not next_match:
            winners = [r[0] for r in db_fetchall("SELECT winner_id FROM tournament_matches WHERE tournament_id=? AND round_number=? AND status='complete'", (m[1], current_round))]
            if len(winners) >= 2:
                for i in range(0, len(winners), 2):
                    w1 = winners[i]
                    w2 = winners[i+1] if i+1 < len(winners) else None
                    rid = f"tour-{m[1]}-r{next_round}-m{i//2}"
                    if w2 is None:
                        db_execute("INSERT INTO tournament_matches (tournament_id, round_number, player1_id, player2_id, room_id, status, winner_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (m[1], next_round, w1, None, rid, "complete", w1))
                    else:
                        db_execute("INSERT INTO tournament_matches (tournament_id, round_number, player1_id, player2_id, room_id, status) VALUES (?, ?, ?, ?, ?, ?)",
                                   (m[1], next_round, w1, w2, rid, "pending"))
        else:
            if next_match[1] is None:
                db_execute("UPDATE tournament_matches SET player1_id=? WHERE id=?", (winner, next_match[0]))
            elif next_match[2] is None:
                db_execute("UPDATE tournament_matches SET player2_id=? WHERE id=?", (winner, next_match[0]))
        remaining = db_fetchone("SELECT COUNT(*) FROM tournament_matches WHERE tournament_id=? AND status='pending'", (m[1],))[0]
        if remaining == 0:
            final_winner = db_fetchone("SELECT winner_id FROM tournament_matches WHERE tournament_id=? ORDER BY round_number DESC, id DESC LIMIT 1", (m[1],))
            if final_winner and final_winner[0]:
                db_execute("UPDATE tournaments SET status='complete' WHERE id=?", (m[1],))
                award_xp(final_winner[0], 300)
                check_badges(final_winner[0])
        return jsonify({"status": "ok"})

    @app.route("/parent/<code>")
    def parent_portal(code):
        student = User.get_by_parent_code(code)
        if not student:
            return render_template("parent_portal.html", error="Invalid parent code."), 404
        scores = db_fetchall(
            "SELECT wpm, accuracy, net_wpm, passage_category, created_at FROM scores WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (student.id,)
        )
        badges = db_fetchall("SELECT badge_id, awarded_at FROM user_badges WHERE user_id=?", (student.id,))
        badge_list = []
        for b in badges:
            d = BADGES.get(b[0], {})
            badge_list.append({"name": d.get("name", b[0]), "desc": d.get("desc", ""), "date": b[1]})
        ratings = db_fetchall("SELECT game_type, rating FROM user_ratings WHERE user_id=?", (student.id,))
        talent_profile = compute_cognitive_profile(student.id)
        return render_template("parent_portal.html", student=student, scores=scores, badges=badge_list, ratings=ratings, talent_profile=talent_profile)

    @app.route("/certificates")
    @login_required
    def certificates():
        certs = db_fetchall("SELECT certificate_type, milestone_value, created_at FROM certificates WHERE user_id=? ORDER BY created_at DESC", (current_user.id,))
        return render_template("certificates.html", certificates=certs)

    @app.route("/api/check_milestones")
    @login_required
    def check_milestones():
        new_certs = []
        row = db_fetchone("SELECT MAX(net_wpm) FROM scores WHERE user_id=?", (current_user.id,))
        if row and row[0] and row[0] >= 50:
            exists = db_fetchone("SELECT 1 FROM certificates WHERE user_id=? AND certificate_type=? AND milestone_value=?", (current_user.id, "typing_speed", 50))
            if not exists:
                db_execute("INSERT INTO certificates (user_id, certificate_type, milestone_value) VALUES (?, ?, ?)", (current_user.id, "typing_speed", 50))
                new_certs.append("Typing Speed: 50 WPM")
        if row and row[0] and row[0] >= 100:
            exists = db_fetchone("SELECT 1 FROM certificates WHERE user_id=? AND certificate_type=? AND milestone_value=?", (current_user.id, "typing_speed", 100))
            if not exists:
                db_execute("INSERT INTO certificates (user_id, certificate_type, milestone_value) VALUES (?, ?, ?)", (current_user.id, "typing_speed", 100))
                new_certs.append("Typing Speed: 100 WPM")
        row = db_fetchone("SELECT rating FROM user_ratings WHERE user_id=? AND game_type='chess'", (current_user.id,))
        if row and row[0] and row[0] >= 1500:
            exists = db_fetchone("SELECT 1 FROM certificates WHERE user_id=? AND certificate_type=? AND milestone_value=?", (current_user.id, "chess_elo", 1500))
            if not exists:
                db_execute("INSERT INTO certificates (user_id, certificate_type, milestone_value) VALUES (?, ?, ?)", (current_user.id, "chess_elo", 1500))
                new_certs.append("Chess ELO: 1500")
        return jsonify({"new_certificates": new_certs})

    def require_api_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = request.headers.get("X-API-Key")
            if not key:
                return jsonify({"error": "Missing API key"}), 401
            khash = hashlib.sha256(key.encode()).hexdigest()
            row = db_fetchone("SELECT user_id, rate_limit, request_count FROM api_keys WHERE key_hash=?", (khash,))
            if not row:
                return jsonify({"error": "Invalid API key"}), 401
            uid, limit, count = row
            if count >= limit:
                return jsonify({"error": "Rate limit exceeded"}), 429
            db_execute("UPDATE api_keys SET request_count=request_count+1, last_used=? WHERE key_hash=?",
                       (datetime.utcnow().isoformat(), khash))
            request.api_user_id = uid
            return f(*args, **kwargs)
        return decorated

    @app.route("/api/v1/leaderboard")
    @require_api_key
    def api_leaderboard():
        rows = db_fetchall("""
            SELECT u.username, u.fullname, u.level, MAX(s.net_wpm) as best_wpm, MAX(s.accuracy) as best_acc
            FROM users u JOIN scores s ON u.id = s.user_id
            GROUP BY u.id, u.username, u.fullname, u.level
            ORDER BY best_wpm DESC LIMIT 50
        """)
        return jsonify([{"username": r[0], "fullname": r[1], "level": r[2], "best_wpm": r[3], "best_accuracy": r[4]} for r in rows])

    @app.route("/api/v1/users/<int:user_id>/stats")
    @require_api_key
    def api_user_stats(user_id):
        total = db_fetchone("SELECT COUNT(*), AVG(net_wpm), AVG(accuracy) FROM scores WHERE user_id=?", (user_id,))
        ratings = db_fetchall("SELECT game_type, rating FROM user_ratings WHERE user_id=?", (user_id,))
        return jsonify({
            "total_tests": total[0] if total else 0,
            "avg_net_wpm": round(total[1], 2) if total and total[1] else 0,
            "avg_accuracy": round(total[2], 2) if total and total[2] else 0,
            "ratings": {r[0]: r[1] for r in ratings}
        })

    @app.route("/api/v1/classrooms/<code>/students")
    @require_api_key
    def api_classroom_students(code):
        cls = db_fetchone("SELECT id FROM classrooms WHERE code=?", (code,))
        if not cls:
            return jsonify({"error": "not found"}), 404
        rows = db_fetchall("""
            SELECT u.id, u.username, u.fullname, u.level, AVG(s.net_wpm)
            FROM users u
            JOIN classroom_members cm ON u.id = cm.student_id
            LEFT JOIN scores s ON u.id = s.user_id
            WHERE cm.classroom_id = ?
            GROUP BY u.id, u.username, u.fullname, u.level
        """, (cls[0],))
        return jsonify([{"id": r[0], "username": r[1], "fullname": r[2], "level": r[3], "avg_net_wpm": round(r[4] or 0, 2)} for r in rows])

    @app.route("/api/v1/generate_key", methods=["POST"])
    @login_required
    def generate_api_key():
        name = request.form.get("name", "default")
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        khash = hashlib.sha256(key.encode()).hexdigest()
        db_execute("INSERT INTO api_keys (user_id, key_hash, name) VALUES (?, ?, ?)", (current_user.id, khash, name))
        flash(f"API Key generated: {key}  —  Save it now, it will never be shown again.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/api/latest_replay")
    @login_required
    def latest_replay():
        row = db_fetchone("SELECT keystrokes, wpm FROM typing_replays WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (current_user.id,))
        if row:
            return jsonify({"keystrokes": json.loads(row[0]), "wpm": row[1]})
        return jsonify({"keystrokes": None})

    @app.route("/replays")
    @login_required
    def replays_page():
        rows = db_fetchall("SELECT id, passage, wpm, accuracy, created_at FROM typing_replays WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (current_user.id,))
        return render_template("replays.html", replays=rows)

    @app.route("/replay/<int:rid>")
    @login_required
    def replay_viewer(rid):
        row = db_fetchone("SELECT passage, keystrokes, wpm, accuracy FROM typing_replays WHERE id = ? AND user_id = ?", (rid, current_user.id))
        if not row:
            flash("Replay not found.", "error")
            return redirect(url_for("replays_page"))
        return render_template("replay_viewer.html", replay=row)

    @app.route("/api/replay/<int:rid>")
    @login_required
    def api_replay_detail(rid):
        row = db_fetchone("SELECT passage, keystrokes, wpm, accuracy FROM typing_replays WHERE id = ? AND user_id = ?", (rid, current_user.id))
        if row:
            return jsonify({"passage": row[0], "keystrokes": json.loads(row[1]), "wpm": row[2], "accuracy": row[3]})
        return jsonify({"error": "Not found"}), 404

    @app.route("/producer", methods=["GET", "POST"])
    @login_required
    def producer_panel():
        # Gatekeeper: must enter console key
        if not session.get("producer_unlocked"):
            if request.method == "POST":
                key = request.form.get("console_key", "").strip()
                if key == "$$manisoft11console":
                    session["producer_unlocked"] = True
                    flash("Console access granted.", "success")
                    return redirect(url_for("producer_panel"))
                else:
                    flash("Invalid console key.", "error")
                    return render_template("producer_gatekeeper.html")
            return render_template("producer_gatekeeper.html")

        users = db_fetchall("""
            SELECT u.id, u.username, u.fullname, u.email, u.role, u.level, u.xp, u.streak, u.last_active, u.created_at,
                   COUNT(DISTINCT s.id) as total_tests,
                   MAX(s.net_wpm) as best_wpm,
                   AVG(s.net_wpm) as avg_wpm
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            GROUP BY u.id, u.username, u.fullname, u.email, u.role, u.level, u.xp, u.streak, u.last_active, u.created_at
            ORDER BY u.level DESC, u.xp DESC
        """)
        totals = db_fetchone("""
            SELECT COUNT(*) as total_users,
                   COUNT(DISTINCT s.user_id) as active_users,
                   MAX(s.net_wpm) as global_best,
                   AVG(s.net_wpm) as global_avg
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
        """)
        recent = db_fetchall("""
            SELECT u.username, u.fullname, s.net_wpm, s.accuracy, s.passage_category, s.created_at
            FROM scores s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
            LIMIT 20
        """)
        agents = db_fetchall("SELECT agent_id, hostname, ip_address, platform, status, last_seen, user_id FROM client_agents WHERE status='online' ORDER BY last_seen DESC")

        # Build client agent command with current server URL
        server_url = request.host_url.rstrip('/')
        return render_template("producer_panel.html", users=users, totals=totals, recent=recent, agents=agents, server_url=server_url)

    @app.route("/producer/user/<int:user_id>")
    @login_required
    def producer_user_detail(user_id):
        if not session.get("producer_unlocked"):
            return redirect(url_for("producer_panel"))
        user = User.get_by_id(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("producer_panel"))
        scores = db_fetchall(
            "SELECT wpm, accuracy, net_wpm, errors, passage_category, room_id, created_at FROM scores WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        badges = db_fetchall("SELECT badge_id, awarded_at FROM user_badges WHERE user_id = ?", (user_id,))
        badge_list = []
        for b in badges:
            d = BADGES.get(b[0], {})
            badge_list.append({"id": b[0], "name": d.get("name", b[0]), "desc": d.get("desc", ""), "date": b[1]})
        ratings = db_fetchall("SELECT game_type, rating, games_played FROM user_ratings WHERE user_id = ?", (user_id,))
        classrooms = db_fetchall("""
            SELECT c.name, c.code FROM classrooms c
            JOIN classroom_members cm ON c.id = cm.classroom_id
            WHERE cm.student_id = ?
        """, (user_id,))
        replays = db_fetchall("SELECT passage, keystrokes, wpm, accuracy, created_at FROM typing_replays WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
        agents = db_fetchall("SELECT agent_id, hostname, platform, status, last_seen FROM client_agents WHERE user_id = ? AND status='online' ORDER BY last_seen DESC", (user_id,))
        return render_template("producer_user_detail.html", target_user=user, scores=scores, badges=badge_list, ratings=ratings, classrooms=classrooms, replays=replays, agents=agents)

    @app.route("/producer/api/users")
    @login_required
    def producer_api_users():
        users = db_fetchall("""
            SELECT u.id, u.username, u.fullname, u.role, u.level, u.xp, u.last_active,
                   COUNT(DISTINCT s.id) as tests
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            GROUP BY u.id
            ORDER BY u.xp DESC
        """)
        return jsonify([{
            "id": u[0], "username": u[1], "fullname": u[2], "role": u[3],
            "level": u[4], "xp": u[5], "last_active": u[6], "tests": u[7]
        } for u in users])

    @app.route("/producer/api/agents")
    @login_required
    def producer_api_agents():
        agents = db_fetchall("SELECT agent_id, hostname, ip_address, platform, status, last_seen FROM client_agents ORDER BY last_seen DESC")
        return jsonify([{
            "agent_id": a[0], "hostname": a[1], "ip": a[2], "platform": a[3], "status": a[4], "last_seen": a[5]
        } for a in agents])

    @app.route("/producer/api/vitals")
    @login_required
    def producer_api_vitals():
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        import shutil, resource
        from config import get_db_path

        # 1. Disk
        try:
            du = shutil.disk_usage("/")
            disk_info = {
                "total_gb": round(du.total / (1024**3), 2),
                "free_gb": round(du.free / (1024**3), 2),
                "used_gb": round(du.used / (1024**3), 2),
                "percent": round((du.used / du.total) * 100, 1)
            }
        except Exception:
            disk_info = {"total_gb": 0, "free_gb": 0, "used_gb": 0, "percent": 0}

        # 2. Memory
        mem_info = {"total_mb": 0, "avail_mb": 0, "used_mb": 0, "percent": 0}
        try:
            with open("/proc/meminfo") as f:
                raw_mem = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        raw_mem[parts[0].strip()] = parts[1].strip().split()[0]
                total = int(raw_mem.get("MemTotal", 0)) // 1024
                avail = int(raw_mem.get("MemAvailable", 0)) // 1024
                used = max(0, total - avail)
                mem_info = {
                    "total_mb": total,
                    "avail_mb": avail,
                    "used_mb": used,
                    "percent": round((used / total * 100), 1) if total > 0 else 0
                }
        except Exception:
            pass

        # 3. CPU Load
        load = [0.0, 0.0, 0.0]
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
                load = [float(parts[0]), float(parts[1]), float(parts[2])]
        except Exception:
            pass

        # 4. DB Stats
        db_path = get_db_path()
        db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0

        # 5. Counts
        users_cnt = (db_fetchone("SELECT COUNT(*) FROM users") or [0])[0]
        scores_cnt = (db_fetchone("SELECT COUNT(*) FROM scores") or [0])[0]
        replays_cnt = (db_fetchone("SELECT COUNT(*) FROM typing_replays") or [0])[0]
        online_agents = (db_fetchone("SELECT COUNT(*) FROM client_agents WHERE status='online'") or [0])[0]
        flagged_security = (db_fetchone("SELECT COUNT(*) FROM anti_cheat_logs") or [0])[0]

        return jsonify({
            "status": "healthy",
            "uptime_str": "Operational",
            "disk": disk_info,
            "memory": mem_info,
            "cpu_load": load,
            "db_size_kb": db_size_kb,
            "users_count": users_cnt,
            "scores_count": scores_cnt,
            "replays_count": replays_cnt,
            "online_agents": online_agents,
            "flagged_security": flagged_security,
            "python_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        })

    @app.route("/producer/api/security")
    @login_required
    def producer_api_security():
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        logs = db_fetchall("""
            SELECT a.id, u.username, u.fullname, a.wpm, a.confidence, a.reasons, a.created_at
            FROM anti_cheat_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 30
        """)
        return jsonify([{
            "id": l[0], "username": l[1] or "Unknown", "fullname": l[2] or "Anonymous",
            "wpm": l[3], "confidence": l[4], "reasons": l[5], "created_at": l[6]
        } for l in logs])

    @app.route("/producer/api/set_role", methods=["POST"])
    @login_required
    def producer_api_set_role():
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json() or {}
        uid = data.get("user_id")
        new_role = data.get("role")
        if not uid or new_role not in ("student", "teacher", "admin"):
            return jsonify({"error": "Invalid user_id or role"}), 400

        db_execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
        return jsonify({"status": "ok", "user_id": uid, "new_role": new_role})

    @app.route("/producer/api/broadcast", methods=["POST"])
    @login_required
    def producer_api_broadcast():
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        from extensions import socketio
        data = request.get_json() or {}
        msg = data.get("message", "").strip()
        level = data.get("level", "info")
        title = data.get("title", "⚡ SYSTEM BROADCAST")
        if not msg:
            return jsonify({"error": "Message is required"}), 400

        socketio.emit("system_broadcast", {
            "title": title,
            "message": msg,
            "level": level,
            "sender": current_user.username,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        }, broadcast=True, namespace="/")

        return jsonify({"status": "broadcast_dispatched", "message": msg})

    # === SHOWCASE FEED & PARENT PORTAL ===

    @app.route("/showcase")
    @app.route("/parents")
    def showcase_feed():
        filter_type = request.args.get("filter", "all")
        query = """
            SELECT sp.id, sp.student_id, sp.title, sp.content, sp.media_type,
                   sp.media_url, sp.achievement_type, sp.stat_highlight,
                   sp.likes_count, sp.created_at,
                   u.username, u.fullname, u.level, u.role
            FROM showcase_posts sp
            JOIN users u ON sp.student_id = u.id
        """
        params = []
        if filter_type != "all":
            query += " WHERE sp.achievement_type = ?"
            params.append(filter_type)
        query += " ORDER BY sp.created_at DESC LIMIT 50"
        posts = db_fetchall(query, tuple(params))

        unread_messages = 0
        user_stats = None
        if current_user.is_authenticated:
            unread_row = db_fetchone("SELECT COUNT(*) FROM parent_student_messages WHERE student_id=? AND read_at IS NULL", (current_user.id,))
            if unread_row:
                unread_messages = unread_row[0]
            best_wpm = db_fetchone("SELECT MAX(net_wpm) FROM scores WHERE user_id=?", (current_user.id,))
            user_stats = {
                "best_wpm": round(best_wpm[0], 1) if (best_wpm and best_wpm[0]) else 0
            }

        return render_template(
            "showcase_feed.html",
            posts=posts,
            current_filter=filter_type,
            unread_messages=unread_messages,
            user_stats=user_stats
        )

    @app.route("/showcase/post", methods=["POST"])
    @login_required
    def create_showcase_post():
        data = request.get_json(silent=True) or request.form
        title = (data.get("title") or "").strip()
        content = (data.get("content") or "").strip()
        achievement_type = data.get("achievement_type", "typing_record")
        stat_highlight = (data.get("stat_highlight") or "").strip()
        media_type = data.get("media_type", "image")
        media_url = (data.get("media_url") or "").strip()

        if not title:
            if request.is_json:
                return jsonify({"error": "Title is required"}), 400
            flash("Title is required for showcase posts.", "error")
            return redirect(url_for("showcase_feed"))

        if not media_url:
            defaults = {
                "typing_record": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80",
                "cognitive_talent": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&q=80",
                "chess_win": "https://images.unsplash.com/photo-1529699211952-734e80c4d42b?w=800&q=80",
                "certificate": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=800&q=80"
            }
            media_url = defaults.get(achievement_type, "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80")

        cur = db_execute(
            """INSERT INTO showcase_posts (student_id, title, content, media_type, media_url, achievement_type, stat_highlight, likes_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (current_user.id, title, content, media_type, media_url, achievement_type, stat_highlight)
        )
        post_id = cur.lastrowid
        if request.is_json:
            return jsonify({"success": True, "post_id": post_id, "message": "Achievement posted to showcase!"})
        flash("🎉 Milestone posted to Parent & Community Showcase!", "success")
        return redirect(url_for("showcase_feed"))

    @app.route("/showcase/like/<int:post_id>", methods=["POST"])
    def like_showcase_post(post_id):
        user_key = str(current_user.id) if current_user.is_authenticated else (request.remote_addr or "guest")
        already = db_fetchone("SELECT id FROM showcase_likes WHERE post_id=? AND user_ip_or_id=?", (post_id, user_key))
        if already:
            cur = db_fetchone("SELECT likes_count FROM showcase_posts WHERE id=?", (post_id,))
            return jsonify({"success": True, "likes_count": cur[0] if cur else 0, "already_liked": True})

        db_execute("INSERT INTO showcase_likes (post_id, user_ip_or_id) VALUES (?, ?)", (post_id, user_key))
        db_execute("UPDATE showcase_posts SET likes_count = likes_count + 1 WHERE id=?", (post_id,))
        cur = db_fetchone("SELECT likes_count FROM showcase_posts WHERE id=?", (post_id,))
        return jsonify({"success": True, "likes_count": cur[0] if cur else 1, "already_liked": False})

    @app.route("/showcase/message/<int:post_id>", methods=["POST"])
    def message_showcase_post(post_id):
        data = request.get_json(silent=True) or request.form
        msg_text = (data.get("message") or "").strip()
        if not msg_text:
            return jsonify({"error": "Message text cannot be empty."}), 400

        post = db_fetchone("SELECT student_id, title FROM showcase_posts WHERE id=?", (post_id,))
        if not post:
            return jsonify({"error": "Showcase post not found."}), 404

        student_id = post[0]
        is_anon = 1 if str(data.get("is_anonymous", "")).lower() in ("1", "true", "yes", "on") else 0
        parent_alias = (data.get("parent_alias") or "").strip()
        if not parent_alias:
            parent_alias = "Proud Parent" if is_anon else "Parent Supporter"

        parent_id = None
        if current_user.is_authenticated:
            parent_id = current_user.id
        else:
            parent_email = (data.get("email") or "").strip()
            parent_name = (data.get("fullname") or data.get("name") or "Parent Supporter").strip()
            if not parent_email:
                return jsonify({"error": "Please provide your email address or sign in so mentors can authenticate your message."}), 400

            existing = db_fetchone("SELECT id FROM users WHERE email=?", (parent_email,))
            if existing:
                parent_id = existing[0]
            else:
                uname = "parent_" + uuid.uuid4().hex[:6]
                parent_id = User.create(uname, parent_name, parent_email, uuid.uuid4().hex, role="parent")
                user_obj = User.get_by_id(parent_id)
                if user_obj:
                    login_user(user_obj)

        cur = db_execute(
            """INSERT INTO parent_student_messages (post_id, parent_id, student_id, message, is_anonymous, parent_alias)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (post_id, parent_id, student_id, msg_text, is_anon, parent_alias)
        )
        msg_id = cur.lastrowid

        return jsonify({
            "success": True,
            "message_id": msg_id,
            "message": "Your encouraging note has been sent to the student!",
            "is_anonymous": bool(is_anon)
        })

    @app.route("/parent/quick-register", methods=["POST"])
    def parent_quick_register():
        data = request.get_json(silent=True) or request.form
        fullname = (data.get("fullname") or "").strip()
        email = (data.get("email") or "").strip()
        password = data.get("password", "")
        username = (data.get("username") or "").strip()

        if not fullname or not email or not password:
            return jsonify({"error": "Full name, email, and password are required."}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters."}), 400
        if not username:
            username = "parent_" + email.split("@")[0].replace(".", "_") + "_" + uuid.uuid4().hex[:4]

        if db_fetchone("SELECT id FROM users WHERE email=?", (email,)):
            return jsonify({"error": "An account with this email already exists. Please log in."}), 400
        if db_fetchone("SELECT id FROM users WHERE username=?", (username,)):
            username = "parent_" + uuid.uuid4().hex[:8]

        uid = User.create(username, fullname, email, password, role="parent")
        user = User.get_by_id(uid)
        login_user(user)
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "fullname": user.fullname,
                "role": user.role
            },
            "message": "Parent account created and authenticated!"
        })

    @app.route("/inbox")
    @login_required
    def inbox_page():
        db_execute("UPDATE parent_student_messages SET read_at=CURRENT_TIMESTAMP WHERE student_id=? AND read_at IS NULL", (current_user.id,))
        messages = db_fetchall("""
            SELECT psm.id, psm.post_id, psm.parent_id, psm.message, psm.is_anonymous,
                   psm.parent_alias, psm.created_at, psm.read_at,
                   sp.title as post_title,
                   u.username as parent_username, u.fullname as parent_fullname
            FROM parent_student_messages psm
            LEFT JOIN showcase_posts sp ON psm.post_id = sp.id
            LEFT JOIN users u ON psm.parent_id = u.id
            WHERE psm.student_id = ?
            ORDER BY psm.created_at DESC
        """, (current_user.id,))
        return render_template("inbox.html", messages=messages)

    @app.route("/producer/api/parent_messages")
    @login_required
    def producer_api_parent_messages():
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        messages = db_fetchall("""
            SELECT psm.id, psm.post_id, psm.parent_id, psm.student_id,
                   psm.message, psm.is_anonymous, psm.parent_alias, psm.created_at,
                   parent.username, parent.fullname, parent.email,
                   student.username, student.fullname,
                   sp.title
            FROM parent_student_messages psm
            JOIN users parent ON psm.parent_id = parent.id
            JOIN users student ON psm.student_id = student.id
            LEFT JOIN showcase_posts sp ON psm.post_id = sp.id
            ORDER BY psm.created_at DESC
            LIMIT 50
        """)
        return jsonify([{
            "id": m[0],
            "post_id": m[1],
            "parent_id": m[2],
            "student_id": m[3],
            "message": m[4],
            "is_anonymous": bool(m[5]),
            "parent_alias": m[6] or "Proud Parent",
            "created_at": str(m[7]),
            "parent_username": m[8] or "Guest",
            "parent_fullname": m[9] or "Parent Supporter",
            "parent_email": m[10] or "N/A",
            "student_username": m[11] or "Student",
            "student_fullname": m[12] or "Student",
            "post_title": m[13] or "Achievement"
        } for m in messages])

    @app.route("/producer/api/delete_parent_message/<int:msg_id>", methods=["POST"])
    @login_required
    def producer_delete_parent_message(msg_id):
        if not session.get("producer_unlocked") and current_user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403
        db_execute("DELETE FROM parent_student_messages WHERE id=?", (msg_id,))
        return jsonify({"status": "ok", "deleted_id": msg_id})

    @app.route("/api_docs")
    def api_docs():
        return render_template("api_docs.html")

    @app.route("/weekly")
    def weekly():
        return render_template("weekly.html")

    @app.route("/public")
    def public():
        return render_template("public.html")

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            user = db_fetchone("SELECT id, username FROM users WHERE email=?", (email,))
            if user:
                # In production, send email. For now, flash a reset token.
                token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))
                exp = (datetime.utcnow() + timedelta(hours=1)).isoformat()
                db_execute("INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)", (user[0], token, exp))
                flash(f"Password reset link: /reset-password?token={token}", "info")
            else:
                flash("If that email exists, a reset link was sent.", "info")
            return redirect(url_for("login"))
        return render_template("forgot_password.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        token = request.args.get("token") or request.form.get("token")
        if not token:
            flash("Invalid reset link.", "error")
            return redirect(url_for("login"))
        now_iso = datetime.utcnow().isoformat()
        row = db_fetchone("SELECT user_id, expires_at FROM password_resets WHERE token=? AND expires_at > ?", (token, now_iso))
        if not row:
            flash("Reset link expired or invalid.", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            pw = request.form.get("password", "")
            if len(pw) < 6:
                flash("Password must be at least 6 characters.", "error")
                return redirect(url_for("reset_password", token=token))
            db_execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(pw), row[0]))
            db_execute("DELETE FROM password_resets WHERE token=?", (token,))
            flash("Password updated! Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("reset_password.html", token=token)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "version": "5.1", "timestamp": datetime.utcnow().isoformat()})

    @app.route("/api/status")
    def api_status():
        """Public API status endpoint for monitoring."""
        return jsonify({
            "status": "operational",
            "platform": "Lumina v5.1",
            "features": ["typing", "chess", "checkers", "math", "memory", "reaction", "pattern", "word", "tournaments"],
            "websocket": True,
            "timestamp": datetime.utcnow().isoformat()
        })

    @app.route("/principal")
    @app.route("/executive-briefing")
    def principal_briefing():
        """Executive showcase and leadership briefing for the School Principal & Academic Board."""
        student_count = (db_fetchone("SELECT COUNT(*) FROM users WHERE role='student'") or [0])[0]
        teacher_count = (db_fetchone("SELECT COUNT(*) FROM users WHERE role='teacher' OR role='producer'") or [0])[0]
        total_users = (db_fetchone("SELECT COUNT(*) FROM users") or [0])[0]
        classroom_count = (db_fetchone("SELECT COUNT(*) FROM classrooms") or [0])[0]
        score_stats = db_fetchone("SELECT COUNT(*), COALESCE(AVG(wpm), 0.0), COALESCE(AVG(accuracy), 0.0) FROM scores") or (0, 0.0, 0.0)
        badge_count = (db_fetchone("SELECT COUNT(*) FROM user_badges") or [0])[0]
        math_count = (db_fetchone("SELECT COUNT(*) FROM math_sprints") or [0])[0]
        tourney_count = (db_fetchone("SELECT COUNT(*) FROM tournaments") or [0])[0]
        replay_count = (db_fetchone("SELECT COUNT(*) FROM typing_replays") or [0])[0]

        cohort_base = max(student_count, 150)
        est_savings_annual = cohort_base * 37 + (max(classroom_count, 5) * 250)

        stats = {
            "students": student_count,
            "teachers": teacher_count,
            "classrooms": classroom_count,
            "total_users": total_users,
            "tests_taken": score_stats[0],
            "avg_wpm": round(score_stats[1], 1),
            "avg_accuracy": round(score_stats[2], 1),
            "badges_awarded": badge_count,
            "math_sprints": math_count,
            "tournaments": tourney_count,
            "replays": replay_count,
            "cohort_base": cohort_base,
            "est_savings_annual": est_savings_annual
        }
        return render_template("principal_briefing.html", stats=stats)


