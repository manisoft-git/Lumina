import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATABASE_URL = os.environ.get("DATABASE_URL")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
TEACHER_KEY = os.environ.get("TEACHER_KEY", "LUMINA_EDU_2026")

# Dynamic CORS: allow the app's own domain plus localhost for dev
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# Production settings
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

def get_db_path():
    db_env = os.environ.get("LUMINA_DB")
    if db_env:
        return Path(db_env)
    if "unittest" in sys.modules or "pytest" in sys.modules:
        return BASE_DIR / "tests" / "test_lumina.db"
    try:
        from flask import current_app
        if current_app:
            if current_app.config.get("DATABASE_PATH"):
                return Path(current_app.config["DATABASE_PATH"])
            if current_app.config.get("TESTING"):
                return BASE_DIR / "tests" / "test_lumina.db"
    except Exception:
        pass
    return BASE_DIR / "lumina.db"

