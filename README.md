# Lumina v5.2 — Cognitive Talent Discovery & Competitive Esports Platform

Lumina is a gamified cognitive talent discovery and competitive esports platform designed for schools, classrooms, and ambitious students. It turns cognitive challenges (typing, chess, checkers, mental math, pattern induction, memory spans, and reflex tests) into validated academic talent profiles, institutional reports, and thrilling multiplayer arenas.

## Key Features

- **Cognitive Talent Discovery Engine**: Standardized assessment synthesizing student telemetry into 7 cognitive domains, a composite Lumina Talent Index (LTI, 200–1000 scale), Cognitive Archetypes, and personalized adaptive weakness training.
- **Academic & Career Pathways**: Direct mapping of cognitive strengths to university curriculums (e.g., MIT EECS, Aerospace, Brain & Cognitive Sciences) and real-world high-impact roles.
- **Institutional Talent Dossiers**: Official, printable/PDF-ready student dossiers with cryptographic verification hashes (`SHA256`) and percentile distributions.
- **Team Cognitive Relay (Esports)**: 3-Leg cooperative interdisciplinary relay (`/relay/<room_id>`): Leg 1 (Mental Arithmetic) → Leg 2 (Inductive Pattern Logic) → Leg 3 (Speed Typing Anchor) with real-time baton passes and team victory podiums.
- **Neurodiversity & Accessibility Matrix**: Built for dyslexic and neurodivergent learners with OpenDyslexic typography anchoring, Bionic Reading eye-saccade fixation, and synthesized 432Hz binaural focus soundscapes.
- **Cognitive Stealth Assessment & Micro-Metrics**: Real-time Attentional Stamina Ratio (ASR) phase curves, Error Recovery Velocity (ERV in milliseconds), and Socratic cognitive debriefs.
- **Zero-Cloud Global Offline Hub**: Deployable on any local Wi-Fi router, budget Android phone (via Termux), or Raspberry Pi (`/offline-hub`) with local QR code pairing—requiring **zero internet connectivity** for equitable access in underserved schools.
- **Classroom Live Projector Arena**: Dedicated widescreen projector/smartboard mode (`/classroom/projector/<code>`) with animated racer avatars, live telemetry, podium celebrations, and confetti effects.
- **Keystroke Dynamics Anti-Cheat Engine**: Biomechanical flight-time analysis, inter-keystroke interval (IKI) entropy checks, and bulk paste rejection to protect competitive and academic integrity.
- **Ghost Racing & Combo Audio**: Race against your personal best or classroom champions using real keystroke replays, paired with a zero-latency Web Audio API synthesizer.
- **8 Cognitive & Strategy Arenas**: Typing races, Chess with AI Grandmaster bot, Checkers with ELO ratings, Math Sprint, Memory Palace, Reaction Test, Pattern Match, and Word Blitz.
- **Teacher & Classroom Suite**: Roster management, student live monitor, custom passage creation, differentiated homework, and CSV gradebook exports.
- **Parent Portal**: Direct parent access codes with student growth telemetry and links to the verified Talent Dossier.
- **Automated Test Suite**: 13 unit and integration tests verifying the cognitive engine, anti-cheat, innovations, and API endpoints (`python run_tests.py`).

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
