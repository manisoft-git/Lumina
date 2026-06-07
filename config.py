import os
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
    return BASE_DIR / "lumina.db"
