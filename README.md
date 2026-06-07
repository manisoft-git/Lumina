# Lumina v5.1 — Talent Discovery Platform

Lumina is a gamified talent discovery platform for students. It combines typing races, chess, checkers, math sprints, memory challenges, reaction tests, and more into a competitive, classroom-friendly environment.

## Features

- **Typing Races**: Solo practice and real-time multiplayer competitions
- **Chess Arena**: Rated matches with AI Grandmaster Bot
- **Checkers**: Classic strategy with ELO ratings
- **Math Sprint**: 60-second mental arithmetic challenges
- **Memory Palace**: Simon Says pattern sequences
- **Reaction Test**: Measure reflexes in milliseconds
- **Pattern Match**: Visual sequence puzzles
- **Word Blitz**: Form words from random letters
- **Tournaments**: Single-elimination brackets across all games
- **Classrooms**: Teacher-created rooms with student codes
- **Badges & XP**: Gamified progression system
- **Leaderboards**: Weekly, daily, and all-time rankings
- **Analytics**: Keyboard heatmaps, progress charts, skill radar
- **Producer Panel**: Remote diagnostics and system oversight
- **Parent Portal**: Track student progress with a unique code
- **API Access**: REST API with key-based authentication

## Quick Start (Local / Termux / Replit)

### Option A: Replit (Easiest — No Install, No Credit Card)
1. Go to [replit.com](https://replit.com) and sign up with Google/GitHub
2. Click **Create** → **Import from GitHub**
3. Paste your repo URL: `https://github.com/YOUR_USERNAME/lumina`
4. Replit will auto-detect Python and install dependencies
5. Click **Run** (green button at top)
6. Your app will be live at `https://luma.YOUR_USERNAME.repl.co`

**Note:** Replit sleeps after 5 min of inactivity. It wakes automatically on next visit (takes ~10 seconds).

### Option B: Local / Termux
```bash
# 1. Clone and enter directory
cd Lumina_v5.1

# 2. Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies (SQLite + threading mode, works everywhere)
pip install -r requirements.txt

# 4. Run the app
python app.py

# 5. Open http://localhost:8080 in your browser
# On Termux/Android: open http://127.0.0.1:8080 in your phone browser
```

### Termux / Android Notes
- **No PostgreSQL needed** — SQLite is used by default
- **No eventlet needed** — Falls back to threading mode automatically
- If you want eventlet later: `pip install eventlet` (requires gcc)
- If you get "port blocked" errors: `export PORT=5000` then `python app.py`

## Production Deployment

### Option A: Replit (Free, No Credit Card, Instant)

**Best for:** Quick deployment, testing, small classrooms.

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Lumina v5.1"
   git remote add origin https://github.com/YOUR_USERNAME/lumina.git
   git push -u origin main
   ```

2. **Import to Replit**
   - Go to [replit.com](https://replit.com)
   - Click **Create** → **Import from GitHub**
   - Paste: `https://github.com/YOUR_USERNAME/lumina`
   - Click **Import from GitHub**

3. **Configure**
   - Replit auto-detects Python
   - In **Secrets** (lock icon in sidebar):
     - `SECRET_KEY` = `python -c "import secrets; print(secrets.token_hex(32))"`
     - `TEACHER_KEY` = `YOUR_SCHOOL_KEY`
     - `CORS_ORIGIN` = `*`
   - Click **Run** (green button)

4. **Done**
   - URL: `https://luma.YOUR_USERNAME.repl.co`
   - Share this URL with students

**Note:** Replit sleeps after 5 min of inactivity. First visit after sleep takes ~10 seconds to wake. For always-on, use UptimeRobot (free) to ping every 5 minutes.

### Option B: Render.com (Free Tier — Requires Credit Card)

1. Push code to GitHub
2. Connect repo to [Render](https://render.com)
3. Use `render.yaml` (included) or manual setup:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:10000 app:create_app()`
   - **Environment Variables**:
     - `SECRET_KEY` — generate a random string
     - `TEACHER_KEY` — your teacher registration key
     - `DATABASE_URL` — optional, for PostgreSQL (SQLite used by default)

### Option B: Docker

```bash
docker build -t lumina .
docker run -p 8080:8080 -e SECRET_KEY=your-secret lumina
```

### Option C: Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/lumina
gcloud run deploy lumina --image gcr.io/YOUR_PROJECT/lumina --platform managed
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `dev-secret-change-me` | Flask session encryption |
| `TEACHER_KEY` | Yes | `LUMINA_EDU_2026` | Key for teacher registration |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `PORT` | No | `8080` | Server port |
| `HOST` | No | `0.0.0.0` | Bind address |
| `CORS_ORIGIN` | No | `*` | Allowed origins for WebSocket |
| `DEBUG` | No | `False` | Enable debug mode |

## Client Agent (Remote Diagnostics)

Run on student machines to enable remote diagnostics from the Producer Panel:

```bash
python Lumina.py --server https://your-lumina-app.com
```

## API Documentation

Visit `/api_docs` after logging in to generate API keys and view endpoints.

## License

MIT License — Free for educational use.
