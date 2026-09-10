# Lumina Test Suite
import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent / "test_lumina.db"
os.environ["LUMINA_DB"] = str(TEST_DB_PATH)
