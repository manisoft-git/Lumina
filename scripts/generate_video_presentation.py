#!/usr/bin/env python3
"""
Lumina v5.1 — Cognitive Learning & Gaming Platform
In-Depth Technical Presentation Video Generator
720p 16:9, cybernetic purple/gold glassmorphic slides, neural voiceover, ambient music.
"""

import os, subprocess
from PIL import Image, ImageDraw, ImageFont

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR  = os.path.join(BASE_DIR, "static")
TEMP_DIR    = "/tmp/lumina_video_build"
FINAL_VIDEO = os.path.join(OUTPUT_DIR, "lumina_presentation.mp4")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

WIDTH, HEIGHT, FPS = 1280, 720, 25

BG_DEEP  = (8,  4, 20)
BG_CARD  = (14, 8, 32)
ACCENT1  = (180, 100, 255)   # purple
ACCENT2  = (255, 200, 60)    # gold
ACCENT3  = (60, 220, 255)    # cyan
TEXT_HI  = (240, 230, 255)
TEXT_MID = (190, 170, 220)
GRID_COL = (30, 18, 55)

def lf(path, size):
    try:    return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def grid(draw):
    for x in range(0, WIDTH, 60):
        draw.line([(x,0),(x,HEIGHT)], fill=(*GRID_COL, 20))
    for y in range(0, HEIGHT, 60):
        draw.line([(0,y),(WIDTH,y)], fill=(*GRID_COL, 20))

def glow(draw, x1, y1, x2, y2, col):
    for i in range(5, 0, -1):
        draw.rectangle([x1-i,y1-i,x2+i,y2+i], outline=(*col[:3], int(35*i/5)))
    draw.rectangle([x1,y1,x2,y2], outline=(*col[:3], 200), width=2)

def badge(draw, x, y, label, col, font):
    tw = int(draw.textlength(label, font=font))
    p  = 10
    draw.rounded_rectangle([x,y,x+tw+p*2,y+28], radius=6,
                            fill=(*col[:3],35), outline=(*col[:3],180), width=1)
    draw.text((x+p, y+4), label, font=font, fill=col)
    return tw+p*2+8

SCENES = [
    {
        "title": "LUMINA v5.1",
        "subtitle": "Cognitive Learning & Competitive Gaming Platform",
        "body": [
            "An all-in-one school platform: typing, chess, maths & more",
            "8 cognitive and strategy arenas built for student growth",
            "Ghost Racing — race against your personal best keystroke replay",
            "Real-time classroom monitoring for teachers",
            "Parent portal with student growth telemetry",
        ],
        "tags": ["Flask", "SocketIO", "SQLite", "Python", "Web Audio API"],
        "voiceover": (
            "Lumina version five point one. A full-stack cognitive learning and competitive gaming platform "
            "designed for schools and students. "
            "Lumina combines eight cognitive arenas — typing races, chess, maths sprint, memory palace, "
            "reaction tests, pattern match, word blitz, and checkers with an ELO rating system — "
            "into one seamless school application. "
            "It features ghost racing, where students race against their own keystroke replay. "
            "And real-time classroom monitoring so teachers can see every student's live performance."
        ),
    },
    {
        "title": "8 COGNITIVE ARENAS",
        "subtitle": "Gamified Learning Across Every Domain",
        "body": [
            "⌨  Typing Races       — WPM, accuracy, ghost replays",
            "♟  Chess               — AI Grandmaster bot, ELO ratings",
            "♦  Checkers            — Full AI with ELO ladder",
            "🔢 Math Sprint         — Timed arithmetic challenges",
            "🧠 Memory Palace       — Pattern memorisation drills",
            "⚡ Reaction Test       — Millisecond-precision reflex",
        ],
        "tags": ["Gamification", "ELO Rating", "AI Bots", "Ghost Replay", "Leaderboard"],
        "voiceover": (
            "Lumina offers eight distinct cognitive arenas. "
            "Typing Races measure words-per-minute and accuracy, with ghost replays to race against. "
            "Chess pits students against an AI Grandmaster bot with a full ELO rating system. "
            "Checkers also has ELO-rated AI. "
            "Math Sprint provides timed arithmetic challenges. "
            "Memory Palace drills pattern memorisation. "
            "And the Reaction Test measures millisecond-precision reflexes. "
            "Every arena is designed to build a real, measurable cognitive skill."
        ),
    },
    {
        "title": "GHOST RACING SYSTEM",
        "subtitle": "Race Your Personal Best — Keystroke Replay Engine",
        "body": [
            "Every keystroke is recorded with microsecond timestamps",
            "Ghost replays your exact typing rhythm in real-time",
            "Compete against classroom champions or your personal best",
            "Zero-latency Web Audio API synthesiser for audio feedback",
            "Leaderboard persists top scores per passage per class",
        ],
        "tags": ["Keystroke Replay", "Web Audio API", "Real-Time", "Leaderboard", "SQLite"],
        "voiceover": (
            "The Ghost Racing system is one of Lumina's most powerful features. "
            "Every keystroke is recorded with microsecond timestamps. "
            "When you race, your ghost — your personal best — types alongside you in real-time, "
            "using the exact rhythm from your previous session. "
            "You can also race against classroom champions. "
            "A zero-latency Web Audio API synthesiser provides instant audio feedback on every keystroke. "
            "And the leaderboard persists top scores per passage, per class, per school."
        ),
    },
    {
        "title": "TEACHER & CLASSROOM SUITE",
        "subtitle": "Educator Tools Built for Real Schools",
        "body": [
            "Full roster management — add, edit, remove students",
            "Live student monitor — see every student's screen in real-time",
            "Custom passage creation for personalised typing drills",
            "Differentiated homework assignments per student",
            "CSV gradebook export for school record systems",
            "13 automated unit and integration tests",
        ],
        "tags": ["Roster Mgmt", "Live Monitor", "CSV Export", "Homework", "Tests"],
        "voiceover": (
            "Lumina's Teacher Suite gives educators real power. "
            "Full roster management lets teachers add, edit, or remove students. "
            "A live student monitor shows every student's performance in real-time during sessions. "
            "Teachers can create custom typing passages tailored to their curriculum. "
            "Differentiated homework lets teachers assign different challenges to different students. "
            "And a CSV gradebook export integrates with any school record system. "
            "Thirteen automated unit and integration tests verify the entire system is working perfectly."
        ),
    },
    {
        "title": "ANTI-CHEAT & INTEGRITY",
        "subtitle": "Fair Competition Enforcement Engine",
        "body": [
            "Keystroke cadence analysis — detects paste/macro injection",
            "Tab-focus monitoring — flags suspicious window switches",
            "Copy-paste event interception at the browser level",
            "Anomaly detection on WPM spike patterns",
            "All violations logged to the Lumina audit database",
        ],
        "tags": ["Anti-Cheat", "Cadence Analysis", "Anomaly Detection", "Audit Log", "Integrity"],
        "voiceover": (
            "Lumina takes academic integrity seriously. "
            "The anti-cheat engine analyses keystroke cadence to detect paste injection or macro bots. "
            "Tab-focus monitoring flags suspicious window switches mid-race. "
            "Copy-paste events are intercepted at the browser level. "
            "And anomaly detection catches unnatural WPM spikes. "
            "Every violation is logged to the Lumina audit database for teacher review. "
            "Fair competition is not optional — it is enforced."
        ),
    },
    {
        "title": "DEPLOYMENT & ARCHITECTURE",
        "subtitle": "Flask + SocketIO + SQLite — Runs Everywhere",
        "body": [
            "Backend: Python Flask with Flask-SocketIO real-time engine",
            "Database: SQLite (zero-config, runs on Termux/Android)",
            "Frontend: Vanilla JS + Web Audio API + CSS animations",
            "Runs on Replit, Render, Termux, or any Python environment",
            "No PostgreSQL needed — SQLite handles all persistence",
        ],
        "tags": ["Flask", "SocketIO", "SQLite", "Render", "Termux"],
        "voiceover": (
            "Lumina is architected for maximum portability. "
            "The backend is Python Flask with Flask-SocketIO for real-time multiplayer. "
            "SQLite handles all persistence — no PostgreSQL required. "
            "This means Lumina runs on Replit, Render dot com, local machines, and even Android via Termux. "
            "The frontend uses vanilla JavaScript, the Web Audio A-P-I, and CSS animations — "
            "no heavy framework, fast everywhere. "
            "Lumina is a fully self-contained learning ecosystem that runs on almost any device."
        ),
    },
]

def render_scene(scene, idx):
    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_DEEP)
    draw = ImageDraw.Draw(img, "RGBA")
    grid(draw)

    fn_sm = lf(FONT_MONO, 13)
    draw.text((40, 22), f"SCENE {idx+1:02d}/{len(SCENES):02d}  //  LUMINA v5.1",
              font=fn_sm, fill=(*ACCENT1[:3], 160))
    draw.rectangle([40, 44, WIDTH-40, 46], fill=ACCENT1)
    draw.rectangle([40, 47, WIDTH//2, 48], fill=(*ACCENT2[:3], 120))

    ft = lf(FONT_BOLD, 46)
    draw.text((40, 62), scene["title"], font=ft, fill=TEXT_HI)
    fs = lf(FONT_REG, 20)
    draw.text((40, 118), scene["subtitle"], font=fs, fill=ACCENT2)

    cy, ch = 155, 340
    draw.rounded_rectangle([30, cy, WIDTH-30, cy+ch], radius=12, fill=(*BG_CARD, 220))
    glow(draw, 30, cy, WIDTH-30, cy+ch, ACCENT1)

    fb = lf(FONT_REG, 19)
    for i, line in enumerate(scene["body"]):
        y = cy + 22 + i*52
        draw.ellipse([50,y+7,60,y+17], fill=ACCENT2)
        draw.text((72, y), line, font=fb, fill=TEXT_MID)
        draw.line([(72,y+32),(WIDTH-50,y+32)], fill=(*GRID_COL,60))

    tag_y = cy+ch+22
    fm = lf(FONT_MONO, 14)
    xc = 40
    for tag in scene["tags"]:
        xc += badge(draw, xc, tag_y, tag, ACCENT3, fm)

    draw.rectangle([40, HEIGHT-44, WIDTH-40, HEIGHT-42], fill=(*ACCENT1[:3], 60))
    draw.text((40, HEIGHT-36), "LUMINA v5.1  //  COGNITIVE LEARNING & GAMING PLATFORM",
              font=fn_sm, fill=(*ACCENT1[:3], 100))

    fd = os.path.join(TEMP_DIR, f"s{idx:02d}"); os.makedirs(fd, exist_ok=True)
    p  = os.path.join(fd, "frame.png"); img.save(p); return p

def synth(text, out):
    try:
        r = subprocess.run(["edge-tts","--voice","en-US-ChristopherNeural","--rate","+5%",
                            "--text",text,"--write-media",out], capture_output=True, timeout=120)
        if r.returncode==0 and os.path.exists(out): return True
    except: pass
    try: subprocess.run(["gtts-cli","--lang","en",text,"--output",out],capture_output=True,timeout=90)
    except: pass
    return os.path.exists(out)

def dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",path],capture_output=True,text=True)
    try: return float(r.stdout.strip())
    except: return 8.0

def clip(idx, frame, audio):
    out = os.path.join(TEMP_DIR, f"clip_{idx:02d}.mp4")
    d   = dur(audio)+1.2
    subprocess.run([
        "ffmpeg","-y","-loop","1","-i",frame,"-i",audio,
        "-vf",f"scale={WIDTH}:{HEIGHT},zoompan=z='min(zoom+0.0008,1.04)':d={int(d*FPS)}:s={WIDTH}x{HEIGHT}:fps={FPS}",
        "-c:v","libx264","-preset","fast","-crf","22",
        "-c:a","aac","-b:a","128k","-t",str(d),"-pix_fmt","yuv420p",out
    ], capture_output=True)
    return out

def ambient(duration, out):
    subprocess.run([
        "ffmpeg","-y","-f","lavfi","-i",
        f"aevalsrc=0.06*sin(2*PI*60*t)*exp(-0.25*(t mod 2))+0.04*sin(2*PI*120*t)+0.03*sin(2*PI*240*t):s=44100:d={duration}",
        "-af","aecho=0.5:0.5:80:0.35,lowpass=f=700,volume=0.35",out
    ], capture_output=True)

def main():
    print("="*60)
    print(" LUMINA v5.1 — VIDEO PRESENTATION GENERATOR")
    print("="*60)
    clips = []
    for i, scene in enumerate(SCENES):
        print(f"\n📹 Scene {i+1}/{len(SCENES)}: {scene['title']}")
        frame = render_scene(scene, i)
        ao    = os.path.join(TEMP_DIR, f"vo_{i:02d}.mp3")
        synth(scene["voiceover"], ao)
        clips.append(clip(i, frame, ao))
        print("  ✅ Done")

    lf_path = os.path.join(TEMP_DIR, "concat.txt")
    with open(lf_path,"w") as f:
        for c in clips: f.write(f"file '{c}'\n")
    raw = os.path.join(TEMP_DIR, "raw.mp4")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lf_path,"-c","copy",raw],capture_output=True)

    total = dur(raw)
    amb   = os.path.join(TEMP_DIR, "ambient.wav")
    ambient(int(total)+5, amb)

    print("\n🎚  Mastering...")
    subprocess.run([
        "ffmpeg","-y","-i",raw,"-i",amb,
        "-filter_complex","[0:a]volume=1.0[va];[1:a]volume=0.12[vb];[va][vb]amix=inputs=2:duration=first[aout]",
        "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","144k",FINAL_VIDEO
    ], capture_output=True)

    size = os.path.getsize(FINAL_VIDEO)/(1024*1024)
    d2   = dur(FINAL_VIDEO)
    print(f"\n🎉 {FINAL_VIDEO}")
    print("="*60)
    print(f" [SUCCESS] {WIDTH}x{HEIGHT}  {d2:.1f}s  {size:.2f}MB")
    print("="*60)

if __name__ == "__main__":
    main()
