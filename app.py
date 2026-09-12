#!/usr/bin/env python3
"""Lumina v5.0 - Talent Discovery Platform"""
import os
import sys
from flask import Flask, render_template, request
from config import SECRET_KEY, CORS_ORIGIN
from extensions import socketio, login_manager
from db import close_db
from models import init_db, User

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["CORS_ORIGIN"] = CORS_ORIGIN
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Dynamic async_mode: eventlet for production, threading for local/Termux
    try:
        import eventlet
        socketio.init_app(app, cors_allowed_origins=CORS_ORIGIN, async_mode="eventlet")
        print("[./] Using eventlet async mode")
    except (ImportError, ValueError) as e:
        socketio.init_app(app, cors_allowed_origins=CORS_ORIGIN, async_mode="threading")
        print(f"[./] Eventlet unavailable ({e}), using threading async mode")
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

    from routes import register_routes
    register_routes(app)

    from sockets import register_sockets
    register_sockets(socketio)

    @app.context_processor
    def inject_global_vars():
        unread = 0
        from flask_login import current_user
        from db import db_fetchone
        if current_user.is_authenticated:
            try:
                dm_row = db_fetchone("SELECT COUNT(*) FROM direct_messages WHERE receiver_id=? AND read_at IS NULL", (current_user.id,))
                dm_count = dm_row[0] if dm_row and dm_row[0] else 0

                ps_row = db_fetchone("SELECT COUNT(*) FROM parent_student_messages WHERE student_id=? AND read_at IS NULL", (current_user.id,))
                ps_count = ps_row[0] if ps_row and ps_row[0] else 0

                unread = max(dm_count, ps_count) if (dm_count and ps_count) else (dm_count + ps_count)
            except Exception:
                pass
        return {
            "unread_inbox_count": unread
        }

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    @app.errorhandler(404)
    def not_found(e):
        from flask import request, jsonify
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import request, jsonify
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template("500.html"), 500

    app.teardown_appcontext(close_db)

    with app.app_context():
        try:
            init_db()
        except Exception as e:
            print(f"[WARNING] init_db error (non-fatal): {e}")

    # ============================================================================
    # 24/7 FLEET KEEP-ALIVE ANTI-SLEEP WORKER
    # Pings all ManiSoft cloud services on Render every 9 minutes
    # ============================================================================
    if not getattr(app, "_keep_alive_started", False):
        app._keep_alive_started = True
        import threading, time, urllib.request
        fleet_urls = [
            "https://manisoft-passmaster-ai.onrender.com",
            "https://manisoft-lumina.onrender.com",
            "https://manisoft-panel.onrender.com",
            "https://manisoft-starshine.onrender.com",
            "https://manisoft-strike-ops.onrender.com",
            "https://manisoft-subway-surfers.onrender.com",
            "https://manisoft-aether-transport.onrender.com"
        ]
        def _fleet_loop():
            time.sleep(25)
            while True:
                for u in fleet_urls:
                    try:
                        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ManiSoft-Lumina-KeepAlive/2.0"})
                        with urllib.request.urlopen(req, timeout=15) as r:
                            r.read(100)
                    except Exception:
                        pass
                time.sleep(540) # 9 minutes
        threading.Thread(target=_fleet_loop, daemon=True, name="LuminaKeepAliveWorker").start()

    return app

if __name__ == "__main__":
    if not os.environ.get("SECRET_KEY"):
        print("WARNING: Using default SECRET_KEY. Set SECRET_KEY env var for production.")

    app = create_app()

    print("\n✅ Registered routes:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint not in ('static',):
            print(f"  {rule.methods - {'OPTIONS', 'HEAD'}} -> {rule.endpoint} -> {rule.rule}")
    print()

    from config import PORT, HOST
    port = PORT
    host = HOST

    print(f"🚀 Starting Lumina v5.0 on http://{host}:{port}")
    print("Press Ctrl+C to stop\n")

    try:
        is_debug = os.environ.get("FLASK_ENV", "development") != "production"
        socketio.run(app, host=host, port=port, debug=is_debug, use_reloader=False)
    except PermissionError as e:
        print(f"\n❌ Port {port} is blocked or in use.")
        print(f"   Error: {e}")
        print(f"\n   FIX: Try a different port:")
        print(f"      set PORT=3000")
        print(f"      python app.py")
        sys.exit(1)

