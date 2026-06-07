#!/usr/bin/env python3
"""Lumina v5.0 - Talent Discovery Platform"""
import os
import sys
from flask import Flask, render_template
from config import SECRET_KEY, CORS_ORIGIN
from extensions import socketio, login_manager
from db import close_db
from models import init_db, User

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["CORS_ORIGIN"] = CORS_ORIGIN

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

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

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
        socketio.run(app, host=host, port=port, debug=True, use_reloader=False)
    except PermissionError as e:
        print(f"\n❌ Port {port} is blocked or in use.")
        print(f"   Error: {e}")
        print(f"\n   FIX: Try a different port:")
        print(f"      set PORT=3000")
        print(f"      python app.py")
        sys.exit(1)

