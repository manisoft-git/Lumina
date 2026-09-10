#!/usr/bin/env python3
"""SocketIO events for Lumina v5.0 — register_sockets(socketio) pattern"""
import json
import random
import time
from datetime import datetime
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from extensions import socketio
from db import db_execute, db_fetchall, db_fetchone
from models import update_elo

TYPING_ROOMS = {}
CHESS_ROOMS = {}
CHECKERS_ROOMS = {}
MONITOR_SUBSCRIBERS = {}
SPECTATORS = {}
AGENTS = {}  # agent_id -> {sid, user_id, hostname, platform, last_seen}
PRODUCER_ROOMS = {}  # agent_id -> producer_sid
RELAY_ROOMS = {}  # room_id -> {state, teams, winner}
BR_ROOMS = {}  # room_code -> {host_sid, players: {sid: {name, lives, answered, chosen}}, state, round}

# Safe command whitelist for remote diagnostics (Windows, macOS, Linux, Chromebooks)
SAFE_COMMANDS = {
    'ipconfig', 'ifconfig', 'ping', 'hostname', 'whoami', 'systeminfo',
    'netstat', 'tasklist', 'ver', 'date', 'time', 'dir', 'ls', 'pwd',
    'echo', 'cls', 'clear', 'path', 'vol', 'driverquery', 'getmac',
    'nslookup', 'tracert', 'traceroute', 'route', 'arp', 'net', 'wmic',
    'uname', 'uptime', 'ps', 'df', 'free'
}

try:
    import chess as chess_lib
    CHESS_AVAILABLE = True
except Exception:
    CHESS_AVAILABLE = False

class SimpleChessBot:
    def __init__(self, depth=2):
        self.depth = depth

    def best_move(self, board_fen, maximizing=False):
        if not CHESS_AVAILABLE:
            return None
        try:
            b = chess_lib.Board(board_fen)
            if b.is_game_over() or not list(b.legal_moves):
                return None
            _, move = self._minimax(b, self.depth, -99999, 99999, maximizing)
            if not move and list(b.legal_moves):
                move = random.choice(list(b.legal_moves))
            return move
        except Exception as e:
            print(f"[./] Chess bot error: {e}")
            return None

    def _minimax(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_game_over():
            return self._eval(board), None
        legal = list(board.legal_moves)
        if not legal:
            return self._eval(board), None

        legal.sort(key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)
        best_move = legal[0]

        if maximizing:
            max_eval = -99999
            for move in legal:
                board.push(move)
                ev, _ = self._minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                if ev > max_eval:
                    max_eval = ev
                    best_move = move
                alpha = max(alpha, ev)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = 99999
            for move in legal:
                board.push(move)
                ev, _ = self._minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                if ev < min_eval:
                    min_eval = ev
                    best_move = move
                beta = min(beta, ev)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def _eval(self, board):
        if board.is_checkmate():
            return -10000 if board.turn else 10000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        vals = {chess_lib.PAWN: 100, chess_lib.KNIGHT: 320, chess_lib.BISHOP: 330, chess_lib.ROOK: 500, chess_lib.QUEEN: 900, chess_lib.KING: 0}
        score = 0
        center = {chess_lib.D4, chess_lib.D5, chess_lib.E4, chess_lib.E5}
        for sq, piece in board.piece_map().items():
            v = vals.get(piece.piece_type, 0)
            if sq in center:
                v += 15
            score += v if piece.color == chess_lib.WHITE else -v
        return score

CHESS_BOT = SimpleChessBot(depth=2)

def get_username():
    return current_user.username if current_user.is_authenticated else "Guest"

def get_user_id():
    return current_user.id if current_user.is_authenticated else None

FORBIDDEN_COMMAND_CHARS = {';', '&', '|', '>', '<', '`', '$', '\n', '\r'}

def is_safe_command(cmd):
    cmd_str = cmd.strip() if cmd else ''
    if not cmd_str or any(c in cmd_str for c in FORBIDDEN_COMMAND_CHARS):
        return False
    base = cmd_str.split()[0].lower()
    return base in SAFE_COMMANDS

CHAT_RATELIMIT = {}  # sid -> {count, last_reset}

def check_chat_rate(sid):
    now = datetime.utcnow().timestamp()
    entry = CHAT_RATELIMIT.get(sid, {"count": 0, "last_reset": now})
    if now - entry["last_reset"] > 10:
        entry = {"count": 0, "last_reset": now}
    entry["count"] += 1
    CHAT_RATELIMIT[sid] = entry
    return entry["count"] <= 5

def clean_disconnected_socket(sid, emit_fn=None):
    """Clean up state across all game rooms, monitoring, spectators, and rate limiters when a socket disconnects."""
    CHAT_RATELIMIT.pop(sid, None)

    if sid in PRODUCER_ROOMS:
        del PRODUCER_ROOMS[sid]

    for aid, info in list(AGENTS.items()):
        if info.get("sid") == sid:
            try:
                db_execute("UPDATE client_agents SET status='offline' WHERE agent_id=?", (aid,))
            except Exception:
                pass
            del AGENTS[aid]
            if emit_fn:
                try:
                    emit_fn("agent_offline", {"agent_id": aid}, broadcast=True, namespace="/")
                except Exception:
                    pass
            break

    for rid, rdata in list(TYPING_ROOMS.items()):
        if sid in rdata.get("players", {}):
            pname = rdata["players"][sid].get("username", "A player")
            del rdata["players"][sid]
            if not rdata["players"]:
                del TYPING_ROOMS[rid]
            elif emit_fn:
                try:
                    emit_fn("player_left", {"sid": sid, "username": pname}, room=rid)
                    emit_fn("room_state", rdata, room=rid)
                except Exception:
                    pass

    for rid, rdata in list(CHESS_ROOMS.items()):
        changed = False
        if rdata.get("white") and rdata["white"].get("sid") == sid:
            rdata["white"] = None
            if emit_fn:
                try: emit_fn("opponent_left", {"color": "white"}, room=rid)
                except Exception: pass
            changed = True
        elif rdata.get("black") and rdata["black"].get("sid") == sid:
            rdata["black"] = None
            if emit_fn:
                try: emit_fn("opponent_left", {"color": "black"}, room=rid)
                except Exception: pass
            changed = True
        if sid in rdata.get("spectators", []):
            rdata["spectators"].remove(sid)
            changed = True
        if not rdata.get("white") and not rdata.get("black") and not rdata.get("spectators"):
            del CHESS_ROOMS[rid]

    for rid, rdata in list(CHECKERS_ROOMS.items()):
        changed = False
        if rdata.get("red") and rdata["red"].get("sid") == sid:
            rdata["red"] = None
            if emit_fn:
                try: emit_fn("opponent_left", {"color": "red"}, room=rid)
                except Exception: pass
            changed = True
        elif rdata.get("black") and rdata["black"].get("sid") == sid:
            rdata["black"] = None
            if emit_fn:
                try: emit_fn("opponent_left", {"color": "black"}, room=rid)
                except Exception: pass
            changed = True
        if sid in rdata.get("spectators", []):
            rdata["spectators"].remove(sid)
            changed = True
        if not rdata.get("red") and not rdata.get("black") and not rdata.get("spectators"):
            del CHECKERS_ROOMS[rid]

    for rid, rdata in list(RELAY_ROOMS.items()):
        relay_changed = False
        for tname, tdata in rdata.get("teams", {}).items():
            for leg_num, ldata in tdata.get("legs", {}).items():
                if ldata.get("sid") == sid:
                    ldata["sid"] = None
                    ldata["username"] = None
                    relay_changed = True
        if relay_changed and emit_fn:
            try: emit_fn("relay_state", rdata, room=rid)
            except Exception: pass

    for code, brdata in list(BR_ROOMS.items()):
        if brdata.get("host_sid") == sid:
            if emit_fn:
                try: emit_fn("br_host_disconnected", room=f"br_{code}")
                except Exception: pass
            del BR_ROOMS[code]
        elif sid in brdata.get("players", {}):
            p = brdata["players"].pop(sid, None)
            if emit_fn:
                try: emit_fn("br_player_left", {"sid": sid, "name": p.get("name") if p else ""}, room=f"br_{code}")
                except Exception: pass

    for code, sids in list(MONITOR_SUBSCRIBERS.items()):
        sids.discard(sid)
        if not sids:
            del MONITOR_SUBSCRIBERS[code]

    for rid, sids in list(SPECTATORS.items()):
        sids.discard(sid)
        if not sids:
            del SPECTATORS[rid]

def register_sockets(socketio):

    @socketio.on("connect")
    def handle_connect():
        try:
            print(f"[./] Socket connect: sid={request.sid}")
            emit("connection_status", {"status": "connected", "sid": request.sid})
        except Exception as e:
            print(f"[./] Error in connect handler: {e}")

    # ---------- Global Chat ----------
    @socketio.on("global_message")
    def handle_global_message(data):
        if not check_chat_rate(request.sid):
            emit("global_error", {"msg": "Rate limit: max 5 messages per 10 seconds"})
            return
        msg = data.get("message", "").strip()
        if not msg or len(msg) > 500:
            return
        uname = get_username()
        uid = get_user_id()
        db_execute("INSERT INTO chat_messages (room, user_id, username, message) VALUES (?, ?, ?, ?)",
                   ("global", uid, uname, msg))
        emit("global_message", {"username": uname, "message": msg, "time": datetime.utcnow().isoformat()}, broadcast=True)

    @socketio.on("join_room_chat")
    def handle_join_room_chat(data):
        room = data.get("room")
        if room:
            join_room(room)
            emit("room_chat_status", {"room": room, "status": "joined"})

    @socketio.on("room_message")
    def handle_room_message(data):
        room = data.get("room", "").strip()
        msg = data.get("message", "").strip()
        if not room or not msg or len(msg) > 500:
            return
        uname = get_username()
        uid = get_user_id()
        db_execute("INSERT INTO chat_messages (room, user_id, username, message) VALUES (?, ?, ?, ?)",
                   (room, uid, uname, msg))
        emit("room_message", {"username": uname, "message": msg, "time": datetime.utcnow().isoformat()}, room=room)

    # ---------- Typing Competitions ----------
    @socketio.on("join_typing_room")
    def handle_join_typing_room(data):
        room_id = data.get("room_id")
        if not room_id:
            return
        join_room(room_id)
        if room_id not in TYPING_ROOMS:
            TYPING_ROOMS[room_id] = {
                "state": "lobby", "passage": data.get("passage", ""),
                "players": {}, "start_time": None, "results": []
            }
        TYPING_ROOMS[room_id]["players"][request.sid] = {
            "username": get_username(), "user_id": get_user_id(),
            "progress": 0, "wpm": 0, "accuracy": 0, "finished": False
        }
        emit("room_state", TYPING_ROOMS[room_id], room=room_id)

    @socketio.on("typing_ready")
    def handle_typing_ready(data):
        room_id = data.get("room_id")
        room = TYPING_ROOMS.get(room_id)
        if not room:
            return
        sid = request.sid
        if sid in room["players"]:
            room["players"][sid]["ready"] = True
        total = len(room["players"])
        ready_count = sum(1 for p in room["players"].values() if p.get("ready"))
        emit("ready_update", {"ready_count": ready_count, "total": total}, room=room_id)
        if total >= 1 and all(p.get("ready") for p in room["players"].values()):
            room["state"] = "countdown"
            emit("countdown", {"value": 3}, room=room_id)
            socketio.sleep(1)
            emit("countdown", {"value": 2}, room=room_id)
            socketio.sleep(1)
            emit("countdown", {"value": 1}, room=room_id)
            socketio.sleep(1)
            room["state"] = "racing"
            room["start_time"] = time.time()
            emit("race_start", {"passage": room["passage"], "start_time": room["start_time"]}, room=room_id)

    @socketio.on("progress_update")
    def handle_progress_update(data):
        room_id = data.get("room_id")
        room = TYPING_ROOMS.get(room_id)
        if not room or room["state"] != "racing":
            return
        sid = request.sid
        if sid not in room["players"]:
            return
        room["players"][sid]["progress"] = data.get("progress", 0)
        room["players"][sid]["wpm"] = data.get("wpm", 0)
        room["players"][sid]["accuracy"] = data.get("accuracy", 0)
        emit("player_update", {
            "sid": sid, "username": room["players"][sid]["username"],
            "progress": data.get("progress", 0), "wpm": data.get("wpm", 0), "accuracy": data.get("accuracy", 0)
        }, room=room_id, include_self=False)
        emit("spectator_update", {"room": room_id, "players": room["players"]}, room=f"spec_{room_id}")

    @socketio.on("race_complete")
    def handle_race_complete(data):
        room_id = data.get("room_id")
        room = TYPING_ROOMS.get(room_id)
        if not room:
            return
        sid = request.sid
        if sid in room["players"]:
            room["players"][sid]["finished"] = True
            room["players"][sid]["final_wpm"] = data.get("wpm", 0)
            room["players"][sid]["final_accuracy"] = data.get("accuracy", 0)
            room["results"].append({
                "username": room["players"][sid]["username"], "user_id": room["players"][sid]["user_id"],
                "wpm": data.get("wpm", 0), "accuracy": data.get("accuracy", 0), "net_wpm": data.get("net_wpm", 0)
            })
        if all(p.get("finished") for p in room["players"].values()):
            room["state"] = "complete"
            emit("race_finished", {"results": room["results"]}, room=room_id)
            emit("spectator_finished", {"room": room_id, "results": room["results"]}, room=f"spec_{room_id}")

    @socketio.on("leave_typing_room")
    def handle_leave_typing_room(data):
        room_id = data.get("room_id")
        leave_room(room_id)
        if room_id in TYPING_ROOMS and request.sid in TYPING_ROOMS[room_id]["players"]:
            del TYPING_ROOMS[room_id]["players"][request.sid]
            if not TYPING_ROOMS[room_id]["players"]:
                del TYPING_ROOMS[room_id]

    @socketio.on("spectator_message")
    def handle_spectator_message(data):
        room_id = data.get("room_id")
        msg = data.get("message", "").strip()
        if not room_id or not msg or len(msg) > 500:
            return
        if not check_chat_rate(request.sid):
            emit("spectator_error", {"msg": "Rate limit"})
            return
        uname = get_username()
        emit("spectator_chat", {
            "username": uname,
            "message": msg,
            "time": datetime.utcnow().isoformat()
        }, room=f"spec_{room_id}")

    @socketio.on("join_spectator")
    def handle_join_spectator(data):
        room_id = data.get("room_id")
        game_type = data.get("game_type", "typing")
        if room_id:
            join_room(f"spec_{room_id}")
            SPECTATORS.setdefault(room_id, set()).add(request.sid)
            emit("spectator_joined", {"room": room_id, "game_type": game_type})
            if game_type == "typing" and room_id in TYPING_ROOMS:
                emit("spectator_state", {"players": TYPING_ROOMS[room_id]["players"], "state": TYPING_ROOMS[room_id]["state"]})
            elif game_type == "chess" and room_id in CHESS_ROOMS:
                emit("spectator_state", CHESS_ROOMS[room_id])
            elif game_type == "checkers" and room_id in CHECKERS_ROOMS:
                emit("spectator_state", CHECKERS_ROOMS[room_id])

    # ---------- Team Cognitive Relay ----------
    @socketio.on("join_relay_room")
    def handle_join_relay_room(data):
        room_id = data.get("room_id")
        team = data.get("team", "alpha")
        leg = int(data.get("leg", 1))
        if not room_id:
            return
        join_room(room_id)
        if room_id not in RELAY_ROOMS:
            RELAY_ROOMS[room_id] = {
                "state": "lobby",
                "teams": {
                    "alpha": {
                        "name": "Team Alpha",
                        "active_leg": 1,
                        "legs": {
                            1: {"type": "math", "progress": 0, "target": 5, "cleared": False, "username": None, "sid": None},
                            2: {"type": "pattern", "progress": 0, "target": 2, "cleared": False, "username": None, "sid": None},
                            3: {"type": "typing", "progress": 0, "target": 100, "cleared": False, "username": None, "sid": None}
                        },
                        "finished": False
                    },
                    "beta": {
                        "name": "Team Beta",
                        "active_leg": 1,
                        "legs": {
                            1: {"type": "math", "progress": 0, "target": 5, "cleared": False, "username": None, "sid": None},
                            2: {"type": "pattern", "progress": 0, "target": 2, "cleared": False, "username": None, "sid": None},
                            3: {"type": "typing", "progress": 0, "target": 100, "cleared": False, "username": None, "sid": None}
                        },
                        "finished": False
                    }
                },
                "winner": None
            }

        room = RELAY_ROOMS[room_id]
        if team in room["teams"] and leg in (1, 2, 3):
            room["teams"][team]["legs"][leg]["username"] = get_username()
            room["teams"][team]["legs"][leg]["sid"] = request.sid

        emit("relay_state", room, room=room_id)

    @socketio.on("relay_start")
    def handle_relay_start(data):
        room_id = data.get("room_id")
        room = RELAY_ROOMS.get(room_id)
        if not room:
            return
        room["state"] = "racing"
        emit("relay_started", room, room=room_id)

    @socketio.on("relay_progress")
    def handle_relay_progress(data):
        room_id = data.get("room_id")
        team = data.get("team")
        leg = int(data.get("leg", 1))
        progress = int(data.get("progress", 0))

        room = RELAY_ROOMS.get(room_id)
        if not room or room["state"] != "racing":
            return
        t_data = room["teams"].get(team)
        if not t_data or t_data["active_leg"] != leg:
            return

        leg_obj = t_data["legs"][leg]
        leg_obj["progress"] = progress

        if progress >= leg_obj["target"] and not leg_obj["cleared"]:
            leg_obj["cleared"] = True
            if leg < 3:
                t_data["active_leg"] = leg + 1
                emit("baton_passed", {"team": team, "new_leg": leg + 1}, room=room_id)
            else:
                t_data["finished"] = True
                if not room["winner"]:
                    room["winner"] = team
                    room["state"] = "complete"
                    emit("relay_game_over", {"winner": team, "room": room}, room=room_id)

        emit("relay_state", room, room=room_id)

    # ---------- Classroom Battle Royale ----------
    @socketio.on("br_host_create")
    def handle_br_host_create(data=None):
        import string
        code = "BR-" + "".join(random.choices(string.digits, k=4))
        while code in BR_ROOMS:
            code = "BR-" + "".join(random.choices(string.digits, k=4))
        room_name = f"br_{code}"
        join_room(room_name)
        BR_ROOMS[code] = {
            "host_sid": request.sid,
            "players": {},
            "state": "lobby",
            "round": 0
        }
        emit("br_room_created", {"code": code})

    @socketio.on("br_player_join")
    def handle_br_player_join(data):
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip() or "Tobi Olive"
        if code not in BR_ROOMS:
            emit("br_join_error", {"message": "Invalid or expired Battle Royale PIN."})
            return
        room_name = f"br_{code}"
        join_room(room_name)
        BR_ROOMS[code]["players"][request.sid] = {
            "name": name,
            "lives": 3,
            "sid": request.sid,
            "answered": False,
            "chosen": None
        }
        emit("br_joined_success", {"code": code, "name": name})
        emit("br_player_joined", {"sid": request.sid, "name": name}, room=room_name)

    @socketio.on("br_start_game")
    def handle_br_start_game(data):
        code = (data.get("code") or "").strip().upper()
        if code not in BR_ROOMS:
            return
        from procedural_generator import generate_procedural_math, generate_procedural_code, generate_procedural_pattern
        gen_fn = random.choice([generate_procedural_math, generate_procedural_code, generate_procedural_pattern])
        q = gen_fn(tier=1)
        BR_ROOMS[code]["state"] = "playing"
        BR_ROOMS[code]["round"] = 1
        BR_ROOMS[code]["current_q"] = q
        emit("br_new_question", q, room=f"br_{code}")

    @socketio.on("br_player_submit")
    def handle_br_player_submit(data):
        code = (data.get("code") or "").strip().upper()
        ans = data.get("ans")
        if code not in BR_ROOMS:
            return
        emit("br_answer_recorded", {"sid": request.sid, "ans": ans}, room=f"br_{code}")

    @socketio.on("br_wave_resolved")
    def handle_br_wave_resolved(data):
        code = (data.get("code") or "").strip().upper()
        correct_ans = data.get("correct_ans")
        if code not in BR_ROOMS:
            return
        emit("br_wave_resolved", {"correct_ans": correct_ans}, room=f"br_{code}")

    @socketio.on("br_request_next_question")
    def handle_br_request_next_question(data):
        code = (data.get("code") or "").strip().upper()
        if code not in BR_ROOMS:
            return
        from procedural_generator import generate_procedural_math, generate_procedural_code, generate_procedural_pattern
        gen_fn = random.choice([generate_procedural_math, generate_procedural_code, generate_procedural_pattern])
        q = gen_fn(tier=min(3, BR_ROOMS[code]["round"] + 1))
        BR_ROOMS[code]["round"] += 1
        BR_ROOMS[code]["current_q"] = q
        emit("br_new_question", q, room=f"br_{code}")

    # ---------- Teacher Monitor ----------
    @socketio.on("teacher_subscribe")
    def handle_teacher_subscribe(data):
        code = data.get("classroom_code")
        if code:
            join_room(f"monitor_{code}")
            MONITOR_SUBSCRIBERS.setdefault(code, set()).add(request.sid)

    @socketio.on("student_pulse")
    def handle_student_pulse(data):
        uid = get_user_id()
        if not uid:
            return
        rows = db_fetchall("SELECT classroom_id FROM classroom_members WHERE student_id=?", (uid,))
        for r in rows:
            cls = db_fetchone("SELECT code FROM classrooms WHERE id=?", (r[0],))
            if cls:
                emit("monitor_update", {
                    "username": get_username(), "user_id": uid,
                    "wpm": data.get("wpm", 0), "accuracy": data.get("accuracy", 0),
                    "activity": data.get("activity", "idle"), "room": data.get("room")
                }, room=f"monitor_{cls[0]}")

    # ---------- Client Agent Diagnostics ----------
    @socketio.on("agent_register")
    def handle_agent_register(data):
        agent_id = data.get("agent_id")
        if not agent_id:
            return
        AGENTS[agent_id] = {
            "sid": request.sid,
            "user_id": data.get("user_id"),
            "hostname": data.get("hostname", "Unknown"),
            "ip_address": data.get("ip_address", ""),
            "platform": data.get("platform", ""),
            "last_seen": datetime.utcnow().isoformat()
        }
        db_execute("""
            INSERT INTO client_agents (agent_id, user_id, hostname, ip_address, platform, status, last_seen)
            VALUES (?, ?, ?, ?, ?, 'online', ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                user_id=excluded.user_id, hostname=excluded.hostname,
                ip_address=excluded.ip_address, platform=excluded.platform,
                status='online', last_seen=excluded.last_seen
        """, (agent_id, data.get("user_id"), data.get("hostname"), data.get("ip_address"), data.get("platform"), datetime.utcnow().isoformat()))
        join_room(f"agent_{agent_id}")
        emit("agent_registered", {"agent_id": agent_id, "status": "ok"})
        emit("agent_online", {"agent_id": agent_id, "hostname": data.get("hostname"), "ip_address": data.get("ip_address"), "platform": data.get("platform")}, broadcast=True, namespace="/")

    @socketio.on("agent_heartbeat")
    def handle_agent_heartbeat(data):
        agent_id = data.get("agent_id")
        if agent_id in AGENTS:
            AGENTS[agent_id]["last_seen"] = datetime.utcnow().isoformat()
            db_execute("UPDATE client_agents SET last_seen=? WHERE agent_id=?", (datetime.utcnow().isoformat(), agent_id))

    @socketio.on("agent_output")
    def handle_agent_output(data):
        try:
            agent_id = data.get("agent_id")
            output = data.get("output", "")
            cmd = data.get("command", "")
            db_execute("UPDATE agent_commands SET output=?, status='complete', completed_at=? WHERE agent_id=? AND command=? AND status='pending'",
                       (output, datetime.utcnow().isoformat(), agent_id, cmd))
            emit("producer_output", {
                "agent_id": agent_id,
                "command": cmd,
                "output": output,
                "timestamp": datetime.utcnow().isoformat()
            }, room=f"producer_{agent_id}")
        except Exception as e:
            print(f"[./] Error in handle_agent_output: {e}")

    @socketio.on("producer_subscribe")
    def handle_producer_subscribe(data):
        agent_id = data.get("agent_id")
        if agent_id:
            join_room(f"producer_{agent_id}")
            PRODUCER_ROOMS[request.sid] = agent_id

    @socketio.on("producer_command")
    def handle_producer_command(data):
        agent_id = data.get("agent_id")
        cmd = data.get("command", "").strip()
        if not agent_id or not cmd:
            emit("producer_error", {"msg": "Missing agent_id or command"})
            return
        if not is_safe_command(cmd):
            emit("producer_error", {"msg": f"Command '{cmd}' is not in the safe diagnostics whitelist."})
            return
        if agent_id not in AGENTS:
            emit("producer_error", {"msg": f"Agent '{agent_id}' is not online."})
            return
        db_execute("INSERT INTO agent_commands (agent_id, command, status) VALUES (?, ?, 'pending')",
                   (agent_id, cmd))
        emit("run_command", {"command": cmd}, room=f"agent_{agent_id}")
        emit("producer_ack", {"agent_id": agent_id, "command": cmd, "status": "sent"})

    @socketio.on("disconnect")
    def handle_disconnect():
        clean_disconnected_socket(request.sid, emit_fn=emit)

    # ---------- Chess ----------

    @socketio.on("join_chess_room")
    def handle_join_chess_room(data):
        try:
            room_id = data.get("room_id")
            if not room_id:
                emit("chess_error", {"msg": "No room_id provided"})
                return
            join_room(room_id)
            if room_id not in CHESS_ROOMS:
                CHESS_ROOMS[room_id] = {
                    "white": None, "black": None, "turn": "white",
                    "board": chess_lib.Board().fen() if CHESS_AVAILABLE else "start",
                    "status": "waiting", "spectators": [], "history": []
                }
            room = CHESS_ROOMS[room_id]
            uid = get_user_id()
            uname = get_username()
            if room["white"] is None:
                room["white"] = {"sid": request.sid, "uid": uid, "name": uname}
                emit("chess_assigned", {"color": "white", "white": room["white"], "black": room["black"]})
            elif room["black"] is None and (room["white"]["uid"] != uid or room["white"]["sid"] != request.sid):
                room["black"] = {"sid": request.sid, "uid": uid, "name": uname}
                emit("chess_assigned", {"color": "black", "white": room["white"], "black": room["black"]})
                room["status"] = "active"
                emit("game_start", {"turn": "white", "board": room["board"], "white": room["white"], "black": room["black"]}, room=room_id)
            elif room["white"] and room["white"].get("uid") == uid:
                room["white"]["sid"] = request.sid
                emit("chess_assigned", {"color": "white", "white": room["white"], "black": room["black"]})
            elif room["black"] and room["black"].get("uid") == uid:
                room["black"]["sid"] = request.sid
                emit("chess_assigned", {"color": "black", "white": room["white"], "black": room["black"]})
            else:
                room["spectators"].append(request.sid)
                emit("chess_assigned", {"color": "spectator", "white": room["white"], "black": room["black"]})
            emit("chess_state", room, room=room_id)
            emit("chess_state", room, room=f"spec_{room_id}")
        except Exception as e:
            print(f"[./] Error in join_chess_room: {e}")
            import traceback
            traceback.print_exc()
            emit("chess_error", {"msg": f"Server error: {str(e)}"})

    @socketio.on("chess_move")
    def handle_chess_move(data):
        try:
            room_id = data.get("room_id")
            move_uci = data.get("move")
            room = CHESS_ROOMS.get(room_id)
            if not room or room["status"] != "active":
                return
            uid = get_user_id()
            is_white = room["white"] and (room["white"]["uid"] == uid or room["white"]["sid"] == request.sid)
            is_black = room["black"] and (room["black"]["uid"] == uid or room["black"]["sid"] == request.sid)
            if (room["turn"] == "white" and not is_white) or (room["turn"] == "black" and not is_black):
                emit("chess_error", {"msg": "Not your turn or you are not a player in this room."})
                return
            if not CHESS_AVAILABLE:
                emit("chess_error", {"msg": "Chess engine not installed on server."})
                return
            board = chess_lib.Board(room["board"])
            result = None
            # Handle resign
            if move_uci == 'resign':
                room["status"] = "complete"
                result = "0-1" if is_white else "1-0"
                room["result"] = result
                room["history"].append("resign")
                try:
                    db_execute("""
                        INSERT INTO chess_games (room_id, white_id, black_id, pgn, result, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(room_id) DO UPDATE SET
                            white_id=excluded.white_id, black_id=excluded.black_id,
                            pgn=excluded.pgn, result=excluded.result, status=excluded.status
                    """, (room_id, room["white"]["uid"] if room["white"] else None, room["black"]["uid"] if room["black"] else None, str(board), result, "complete"))
                except Exception:
                    pass
                if result == "1-0":
                    if room["white"] and room["white"]["uid"]: update_elo(room["white"]["uid"], "chess", 1)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "chess", 0)
                else:
                    if room["white"] and room["white"]["uid"]: update_elo(room["white"]["uid"], "chess", 0)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "chess", 1)
                emit("chess_update", {"board": room["board"], "turn": room["turn"], "last_move": "resign", "result": result, "history": room["history"]}, room=room_id)
                emit("chess_update", {"board": room["board"], "turn": room["turn"], "last_move": "resign", "result": result, "history": room["history"]}, room=f"spec_{room_id}")
                return
            try:
                m = chess_lib.Move.from_uci(move_uci)
                if m not in board.legal_moves:
                    emit("chess_error", {"msg": "Illegal move"})
                    return
                board.push(m)
                room["history"].append(move_uci)
            except Exception:
                emit("chess_error", {"msg": "Invalid move format"})
                return
            room["board"] = board.fen()
            room["turn"] = "black" if room["turn"] == "white" else "white"
            if board.is_game_over():
                room["status"] = "complete"
                result = "1-0" if board.result() == "1-0" else "0-1" if board.result() == "0-1" else "draw"
                room["result"] = result
                try:
                    db_execute("""
                        INSERT INTO chess_games (room_id, white_id, black_id, pgn, result, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(room_id) DO UPDATE SET
                            white_id=excluded.white_id, black_id=excluded.black_id,
                            pgn=excluded.pgn, result=excluded.result, status=excluded.status
                    """, (room_id, room["white"]["uid"] if room["white"] else None, room["black"]["uid"] if room["black"] else None, str(board), result, "complete"))
                except Exception:
                    pass
                if result == "1-0":
                    if room["white"] and room["white"]["uid"]: update_elo(room["white"]["uid"], "chess", 1)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "chess", 0)
                elif result == "0-1":
                    if room["white"] and room["white"]["uid"]: update_elo(room["white"]["uid"], "chess", 0)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "chess", 1)
                else:
                    if room["white"] and room["white"]["uid"]: update_elo(room["white"]["uid"], "chess", 0.5)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "chess", 0.5)
            emit("chess_update", {"board": room["board"], "turn": room["turn"], "last_move": move_uci, "result": result, "history": room["history"]}, room=room_id)
            emit("chess_update", {"board": room["board"], "turn": room["turn"], "last_move": move_uci, "result": result, "history": room["history"]}, room=f"spec_{room_id}")
        except Exception as e:
            print(f"[./] Error in chess_move: {e}")
            import traceback
            traceback.print_exc()
            emit("chess_error", {"msg": f"Server error: {str(e)}"})

    @socketio.on("start_chess_bot")
    def handle_start_chess_bot(data):
        try:
            room_id = data.get("room_id")
            if not room_id:
                emit("chess_error", {"msg": "No room_id provided"})
                return
            join_room(room_id)
            uid = get_user_id()
            uname = get_username()
            CHESS_ROOMS[room_id] = {
                "white": {"sid": request.sid, "uid": uid, "name": uname},
                "black": {"sid": "bot", "uid": -1, "name": "Manisoft_Chess[GM]"},
                "turn": "white", "board": chess_lib.Board().fen() if CHESS_AVAILABLE else "start",
                "status": "active", "spectators": [], "history": []
            }
            emit("chess_assigned", {"color": "white"})
            emit("game_start", {"turn": "white", "board": CHESS_ROOMS[room_id]["board"]}, room=room_id)
        except Exception as e:
            print(f"[./] Error in start_chess_bot: {e}")
            import traceback
            traceback.print_exc()
            emit("chess_error", {"msg": f"Server error: {str(e)}"})

    @socketio.on("chess_bot_move")
    def handle_chess_bot_move(data):
        try:
            room_id = data.get("room_id")
            room = CHESS_ROOMS.get(room_id)
            if not room or not CHESS_AVAILABLE or room.get("status") != "active":
                return
            if room["turn"] == "black" and room["black"] and room["black"].get("uid") == -1:
                try:
                    board = chess_lib.Board(room["board"])
                    best = CHESS_BOT.best_move(room["board"], False)
                    if not best and list(board.legal_moves):
                        best = random.choice(list(board.legal_moves))
                    if best:
                        board.push(best)
                        room["board"] = board.fen()
                        room["turn"] = "white"
                        room["history"].append(best.uci())
                        result = None
                        if board.is_game_over():
                            room["status"] = "complete"
                            if board.is_checkmate():
                                result = "0-1"
                                room["result"] = result
                                if room["white"] and room["white"].get("uid"):
                                    update_elo(room["white"]["uid"], "chess", 0)
                            else:
                                result = "1/2-1/2"
                                room["result"] = result
                                if room["white"] and room["white"].get("uid"):
                                    update_elo(room["white"]["uid"], "chess", 0.5)

                        emit("chess_update", {
                            "board": room["board"],
                            "turn": room["turn"],
                            "last_move": best.uci(),
                            "history": room["history"],
                            "result": result
                        }, room=room_id)
                        emit("chess_update", {
                            "board": room["board"],
                            "turn": room["turn"],
                            "last_move": best.uci(),
                            "history": room["history"],
                            "result": result
                        }, room=f"spec_{room_id}")
                    else:
                        emit("chess_error", {"msg": "Bot has no legal moves"}, room=room_id)
                except Exception as e:
                    print(f"[./] Bot move error: {e}")
                    import traceback
                    traceback.print_exc()
                    emit("chess_error", {"msg": f"Bot error: {str(e)}"}, room=room_id)

        except Exception as e:
            print(f"[./] Error in chess_bot_move: {e}")
            import traceback
            traceback.print_exc()
            emit("chess_error", {"msg": f"Bot error: {str(e)}"}, room=room_id)
    # ---------- Checkers ----------
    INITIAL_CHECKERS = [
        [0, -1, 0, -1, 0, -1, 0, -1],
        [-1, 0, -1, 0, -1, 0, -1, 0],
        [0, -1, 0, -1, 0, -1, 0, -1],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [1, 0, 1, 0, 1, 0, 1, 0],
        [0, 1, 0, 1, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0],
    ]

    def checkers_moves(board, turn):
        moves = []
        directions = [(-1, -1), (-1, 1)] if turn == "red" else [(1, -1), (1, 1)]
        king_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for r in range(8):
            for c in range(8):
                piece = board[r][c]
                if piece == 0:
                    continue
                is_red = piece > 0
                is_king = abs(piece) == 2
                if turn == "red" and not is_red:
                    continue
                if turn == "black" and is_red:
                    continue
                dirs = king_dirs if is_king else directions
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        if board[nr][nc] == 0:
                            moves.append({"from": [r, c], "to": [nr, nc], "capture": False})
                        elif (board[nr][nc] > 0) != is_red:
                            jr, jc = nr + dr, nc + dc
                            if 0 <= jr < 8 and 0 <= jc < 8 and board[jr][jc] == 0:
                                moves.append({"from": [r, c], "to": [jr, jc], "capture": True, "captured": [nr, nc]})
        return moves

    def apply_checkers_move(board, move):
        b = [row[:] for row in board]
        fr, fc = move["from"]
        tr, tc = move["to"]
        piece = b[fr][fc]
        b[tr][tc] = piece
        b[fr][fc] = 0
        if move.get("capture"):
            cr, cc = move["captured"]
            b[cr][cc] = 0
        if piece == 1 and tr == 0:
            b[tr][tc] = 2
        if piece == -1 and tr == 7:
            b[tr][tc] = -2
        return b

    class CheckersBot:
        def best_move(self, board, turn):
            moves = checkers_moves(board, turn)
            if not moves:
                return None
            captures = [m for m in moves if m.get("capture")]
            if captures:
                return random.choice(captures)
            return random.choice(moves)

    CHECKERS_BOT = CheckersBot()

    @socketio.on("join_checkers_room")
    def handle_join_checkers_room(data):
        try:
            room_id = data.get("room_id")
            if not room_id:
                emit("checkers_error", {"msg": "No room_id provided"})
                return
            join_room(room_id)
            if room_id not in CHECKERS_ROOMS:
                CHECKERS_ROOMS[room_id] = {
                    "red": None, "black": None, "turn": "red",
                    "board": [row[:] for row in INITIAL_CHECKERS],
                    "status": "waiting", "spectators": [], "history": []
                }
            room = CHECKERS_ROOMS[room_id]
            uid = get_user_id()
            uname = get_username()
            if room["red"] is None:
                room["red"] = {"sid": request.sid, "uid": uid, "name": uname}
                emit("checkers_assigned", {"color": "red", "red": room["red"], "black": room["black"]})
            elif room["black"] is None and (room["red"]["uid"] != uid or room["red"]["sid"] != request.sid):
                room["black"] = {"sid": request.sid, "uid": uid, "name": uname}
                emit("checkers_assigned", {"color": "black", "red": room["red"], "black": room["black"]})
                room["status"] = "active"
                emit("checkers_start", {"turn": "red", "board": room["board"], "red": room["red"], "black": room["black"]}, room=room_id)
            elif room["red"] and room["red"].get("uid") == uid:
                room["red"]["sid"] = request.sid
                emit("checkers_assigned", {"color": "red", "red": room["red"], "black": room["black"]})
            elif room["black"] and room["black"].get("uid") == uid:
                room["black"]["sid"] = request.sid
                emit("checkers_assigned", {"color": "black", "red": room["red"], "black": room["black"]})
            else:
                room["spectators"].append(request.sid)
                emit("checkers_assigned", {"color": "spectator", "red": room["red"], "black": room["black"]})
            emit("checkers_state", room, room=room_id)
            emit("checkers_state", room, room=f"spec_{room_id}")
        except Exception as e:
            print(f"[./] Error in join_checkers_room: {e}")
            import traceback
            traceback.print_exc()
            emit("checkers_error", {"msg": f"Server error: {str(e)}"})

    @socketio.on("checkers_move")
    def handle_checkers_move(data):
        try:
            room_id = data.get("room_id")
            move = data.get("move")
            room = CHECKERS_ROOMS.get(room_id)
            if not room or room["status"] != "active":
                return
            uid = get_user_id()
            is_red = room["red"] and (room["red"]["uid"] == uid or room["red"]["sid"] == request.sid)
            is_black = room["black"] and (room["black"]["uid"] == uid or room["black"]["sid"] == request.sid)
            if (room["turn"] == "red" and not is_red) or (room["turn"] == "black" and not is_black):
                emit("checkers_error", {"msg": "Not your turn or you are not a player in this room."})
                return
            legal = checkers_moves(room["board"], room["turn"])
            matched = None
            for l in legal:
                if l.get("from") == move.get("from") and l.get("to") == move.get("to"):
                    matched = l
                    break
            if not matched:
                emit("checkers_error", {"msg": "Illegal move"})
                return
            room["board"] = apply_checkers_move(room["board"], matched)
            room["turn"] = "black" if room["turn"] == "red" else "red"
            room["history"].append(move)
            opp_moves = checkers_moves(room["board"], room["turn"])
            red_pieces = sum(1 for r in room["board"] for p in r if p > 0)
            black_pieces = sum(1 for r in room["board"] for p in r if p < 0)
            result = None
            if red_pieces == 0:
                result = "black"; room["status"] = "complete"
            elif black_pieces == 0:
                result = "red"; room["status"] = "complete"
            elif not opp_moves:
                result = "red" if room["turn"] == "black" else "black"
                room["status"] = "complete"
            if result:
                try:
                    db_execute("""
                        INSERT INTO checkers_games (room_id, red_id, black_id, board_state, result, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(room_id) DO UPDATE SET
                            red_id=excluded.red_id, black_id=excluded.black_id,
                            board_state=excluded.board_state, result=excluded.result, status=excluded.status
                    """, (room_id, room["red"]["uid"] if room["red"] else None,
                          room["black"]["uid"] if room["black"] else None,
                          json.dumps(room["board"]), result, "complete"))
                except Exception:
                    pass
                if result == "red":
                    if room["red"] and room["red"]["uid"]: update_elo(room["red"]["uid"], "checkers", 1)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "checkers", 0)
                elif result == "black":
                    if room["red"] and room["red"]["uid"]: update_elo(room["red"]["uid"], "checkers", 0)
                    if room["black"] and room["black"]["uid"]: update_elo(room["black"]["uid"], "checkers", 1)
            emit("checkers_update", {"board": room["board"], "turn": room["turn"], "last_move": move, "result": result, "history": room["history"]}, room=room_id)
            emit("checkers_update", {"board": room["board"], "turn": room["turn"], "last_move": move, "result": result, "history": room["history"]}, room=f"spec_{room_id}")
        except Exception as e:
            print(f"[./] Error in checkers_move: {e}")
            import traceback
            traceback.print_exc()
            emit("checkers_error", {"msg": f"Server error: {str(e)}"})
    @socketio.on("start_checkers_bot")
    def handle_start_checkers_bot(data):
        try:
            room_id = data.get("room_id")
            if not room_id:
                emit("checkers_error", {"msg": "No room_id provided"})
                return
            join_room(room_id)
            uid = get_user_id()
            uname = get_username()
            CHECKERS_ROOMS[room_id] = {
                "red": {"sid": request.sid, "uid": uid, "name": uname},
                "black": {"sid": "bot", "uid": -1, "name": "Manisoft_Checkers[M]"},
                "turn": "red", "board": [row[:] for row in INITIAL_CHECKERS],
                "status": "active", "spectators": [], "history": []
            }
            emit("checkers_assigned", {"color": "red"})
            emit("checkers_start", {"turn": "red", "board": CHECKERS_ROOMS[room_id]["board"]}, room=room_id)
        except Exception as e:
            print(f"[./] Error in start_checkers_bot: {e}")
            import traceback
            traceback.print_exc()
            emit("checkers_error", {"msg": f"Server error: {str(e)}"})

    @socketio.on("checkers_bot_move")
    def handle_checkers_bot_move(data):
        try:
            room_id = data.get("room_id")
            room = CHECKERS_ROOMS.get(room_id)
            if not room or room.get("status") != "active":
                return
            if room["turn"] == "black" and room["black"] and room["black"].get("uid") == -1:
                try:
                    move = CHECKERS_BOT.best_move(room["board"], "black")
                    if move:
                        room["board"] = apply_checkers_move(room["board"], move)
                        room["turn"] = "red"
                        room["history"].append(move)
                        emit("checkers_update", {"board": room["board"], "turn": "red", "last_move": move, "history": room["history"]}, room=room_id)
                        emit("checkers_update", {"board": room["board"], "turn": "red", "last_move": move, "history": room["history"]}, room=f"spec_{room_id}")
                    else:
                        emit("checkers_error", {"msg": "Bot has no legal moves"}, room=room_id)
                except Exception as e:
                    emit("checkers_error", {"msg": f"Bot error: {str(e)}"}, room=room_id)


        except Exception as e:
            print(f"[./] Error in checkers_bot_move: {e}")
            import traceback
            traceback.print_exc()
            emit("checkers_error", {"msg": f"Bot error: {str(e)}"}, room=room_id)