#!/usr/bin/env python3
"""
Lumina Video Production Engine
Generates:
  1. videos/lumina_advertisement.mp4 (Commercial / Promo Video)
  2. videos/lumina_walkthrough.mp4 (Platform Tour & Walkthrough Video)
"""

import os
import sys
import math
import struct
import wave
import subprocess
import shutil

ASSETS_DIR = "/data/data/com.termux/files/home/MANISOFT/projects/lumina/videos/assets"
OUTPUT_DIR = "/data/data/com.termux/files/home/MANISOFT/projects/lumina/videos"
WORK_DIR = "/data/data/com.termux/files/home/MANISOFT/projects/lumina/videos/build"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run(cmd, desc=""):
    if desc:
        print(f"==> {desc}")
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Error executing: {cmd}\nSTDERR:\n{res.stderr}")
        raise RuntimeError(f"Command failed with exit code {res.returncode}")
    return res.stdout.strip()

def get_audio_duration(file_path):
    out = run(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'")
    return float(out)

def generate_voice(text, voice, out_path):
    cmd = f"edge-tts --voice {voice} --text \"{text}\" --write-media '{out_path}'"
    run(cmd, f"Generating voice: {text[:40]}...")

def synthesize_music(out_path, total_duration, style="ad"):
    sample_rate = 44100
    num_samples = int(sample_rate * total_duration)
    wav_file = wave.open(out_path, 'w')
    wav_file.setnchannels(2)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)

    # Chords (frequencies)
    # Ad: Dm (146.83, 220, 261.63, 349.23), Bb (116.54, 233.08, 293.66, 349.23), F (87.31, 174.61, 261.63, 349.23), C (130.81, 196.00, 261.63, 329.63)
    chords_ad = [
        [146.83, 220.00, 261.63, 349.23], # Dm
        [116.54, 233.08, 293.66, 349.23], # Bb
        [174.61, 220.00, 261.63, 349.23], # F
        [130.81, 196.00, 246.94, 329.63], # C
    ]
    # Walkthrough: Am (110, 220, 261.63, 329.63), F (87.31, 174.61, 261.63, 349.23), C (130.81, 196.00, 261.63, 329.63), G (98.00, 196.00, 246.94, 293.66)
    chords_wt = [
        [110.00, 220.00, 261.63, 329.63], # Am
        [87.31, 174.61, 261.63, 349.23],  # F
        [130.81, 196.00, 261.63, 329.63], # C
        [98.00, 196.00, 246.94, 293.66],  # G
    ]

    chords = chords_ad if style == "ad" else chords_wt
    chord_duration = 3.2 if style == "ad" else 4.0
    bpm = 112.5 if style == "ad" else 90.0
    beat_dur = 60.0 / bpm

    frames = bytearray()
    chunk_size = 4096

    for chunk_start in range(0, num_samples, chunk_size):
        chunk_end = min(chunk_start + chunk_size, num_samples)
        sub_frames = bytearray()
        for i in range(chunk_start, chunk_end):
            t = i / sample_rate
            
            # Fade in / fade out
            master_vol = 1.0
            if t < 1.5:
                master_vol = t / 1.5
            elif t > total_duration - 2.5:
                master_vol = max(0.0, (total_duration - t) / 2.5)

            # Chord progression
            chord_idx = int((t / chord_duration)) % len(chords)
            active_chord = chords[chord_idx]

            # Synth Pad (warm detuned saw/sine with gentle chorus)
            pad = 0.0
            for freq in active_chord:
                pad += math.sin(2 * math.pi * freq * t) * 0.12
                pad += math.sin(2 * math.pi * (freq * 1.003) * t) * 0.08
                pad += math.sin(2 * math.pi * (freq * 0.997) * t) * 0.08

            # Bass pulse on eighth notes
            beat_phase = (t % beat_dur) / beat_dur
            bass_env = math.exp(-4.5 * beat_phase)
            bass_freq = active_chord[0] * 0.5
            bass = math.sin(2 * math.pi * bass_freq * t) * bass_env * (0.32 if style == "ad" else 0.22)

            # Arpeggio / High shimmer
            arp_step = int((t / (beat_dur / 2.0))) % len(active_chord)
            arp_freq = active_chord[arp_step] * 2.0
            arp_phase = ((t % (beat_dur / 2.0)) / (beat_dur / 2.0))
            arp_env = math.exp(-6.0 * arp_phase)
            arp = math.sin(2 * math.pi * arp_freq * t) * arp_env * (0.16 if style == "ad" else 0.10)

            # Subtle high hat / percussion tick on 16th notes for ad
            hat = 0.0
            if style == "ad":
                hat_phase = (t % (beat_dur / 4.0)) / (beat_dur / 4.0)
                if hat_phase < 0.15:
                    hat = (math.sin(2 * math.pi * 7800 * t) + math.sin(2 * math.pi * 9200 * t)) * 0.04 * (1.0 - hat_phase / 0.15)

            left = (pad + bass + arp + hat) * master_vol
            right = (pad + bass + (arp * 0.85) - hat * 0.5) * master_vol

            # Clamp and convert to 16-bit PCM
            val_l = int(max(-32767, min(32767, left * 18000)))
            val_r = int(max(-32767, min(32767, right * 18000)))
            sub_frames += struct.pack('<hh', val_l, val_r)
        frames += sub_frames

    wav_file.writeframes(frames)
    wav_file.close()
    print(f"Synthesized {style} music: {out_path} ({total_duration:.1f}s)")

def render_scene(img_path, scene_idx, duration, header, subtitle, voice_wav, out_clip_path, motion_type="zoom_in"):
    # Audio with pre-roll delay of 0.4s
    scene_audio = os.path.join(WORK_DIR, f"scene_audio_{scene_idx}.wav")
    run(f"ffmpeg -y -i '{voice_wav}' -af \"adelay=400|400,apad=pad_dur={duration}\" -t {duration} '{scene_audio}'")

    # Escape strings for drawtext
    header_clean = header.replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")
    subtitle_clean = subtitle.replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")

    # Motion expression
    total_frames = int(duration * 25)
    
    if motion_type == "zoom_in":
        zoom_expr = f"scale=1280:720,zoompan=z='min(zoom+0.00045,1.07)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25"
    elif motion_type == "zoom_out":
        zoom_expr = f"scale=1280:720,zoompan=z='if(lte(zoom,1.0),1.06,max(1.001,zoom-0.00045))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25"
    elif motion_type == "pan_left":
        zoom_expr = f"scale=1280:720,zoompan=z=1.05:d=1:x='(iw-iw/zoom)*(1-on/{total_frames})':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25"
    else: # pan_right
        zoom_expr = f"scale=1280:720,zoompan=z=1.05:d=1:x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25"

    vf = (
        f"{zoom_expr},"
        f"format=yuv420p,"
        f"drawbox=x=40:y=560:w=1200:h=125:color=black@0.82:t=fill,"
        f"drawbox=x=40:y=560:w=6:h=125:color=0x38bdf8:t=fill,"
        f"drawtext=fontfile='{FONT_BOLD}':text='{header_clean}':fontcolor=0x38bdf8:fontsize=24:x=68:y=580,"
        f"drawtext=fontfile='{FONT_REG}':text='{subtitle_clean}':fontcolor=white:fontsize=28:x=68:y=622"
    )

    cmd = (
        f"ffmpeg -y -loop 1 -i '{img_path}' -i '{scene_audio}' "
        f"-vf \"{vf}\" -c:v libx264 -preset veryfast -pix_fmt yuv420p -t {duration} "
        f"-c:a aac -b:a 192k -shortest '{out_clip_path}'"
    )
    run(cmd, f"Rendering scene {scene_idx} ({duration:.1f}s)")

def build_video(scenes, music_style, output_mp4, title):
    print(f"\n=======================================================")
    print(f"PRODUCING: {title}")
    print(f"=======================================================")

    rendered_clips = []
    total_video_duration = 0.0

    # 1. Voice synthesis and duration computation
    for idx, s in enumerate(scenes):
        voice_wav = os.path.join(WORK_DIR, f"{music_style}_voice_{idx}.mp3")
        generate_voice(s["narration"], s["voice"], voice_wav)
        raw_dur = get_audio_duration(voice_wav)
        scene_dur = round(raw_dur + 1.2, 1)
        s["duration"] = scene_dur
        s["voice_wav"] = voice_wav
        total_video_duration += scene_dur
        print(f"Scene {idx+1}: audio={raw_dur:.1f}s -> clip={scene_dur:.1f}s")

    print(f"Total Video Planned Duration: {total_video_duration:.1f}s")

    # 2. Render individual clips
    for idx, s in enumerate(scenes):
        clip_path = os.path.join(WORK_DIR, f"{music_style}_clip_{idx}.mp4")
        render_scene(
            img_path=s["image"],
            scene_idx=f"{music_style}_{idx}",
            duration=s["duration"],
            header=s["header"],
            subtitle=s["subtitle"],
            voice_wav=s["voice_wav"],
            out_clip_path=clip_path,
            motion_type=s.get("motion", "zoom_in")
        )
        rendered_clips.append(clip_path)

    # 3. Concatenate video clips
    concat_list_file = os.path.join(WORK_DIR, f"{music_style}_concat.txt")
    with open(concat_list_file, "w") as f:
        for c in rendered_clips:
            f.write(f"file '{c}'\n")

    combined_video = os.path.join(WORK_DIR, f"{music_style}_combined.mp4")
    run(f"ffmpeg -y -f concat -safe 0 -i '{concat_list_file}' -c copy '{combined_video}'", "Concatenating scenes")

    # 4. Synthesize bespoke music soundtrack
    music_wav = os.path.join(WORK_DIR, f"{music_style}_music.wav")
    synthesize_music(music_wav, total_video_duration + 1.0, style=music_style)

    # 5. Audio mixing: ducking background music under speech + loudnorm
    music_vol = "0.22" if music_style == "ad" else "0.18"
    final_mix_cmd = (
        f"ffmpeg -y -i '{combined_video}' -i '{music_wav}' "
        f"-filter_complex \""
        f"[1:a]volume={music_vol}[music];"
        f"[music][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=100:release=600[ducked_music];"
        f"[0:a][ducked_music]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        f"\" -map 0:v -map \"[aout]\" -c:v copy -c:a aac -b:a 192k '{output_mp4}'"
    )
    run(final_mix_cmd, "Mastering final video with ducked music & EBU R128 loudnorm")

    final_dur = get_audio_duration(output_mp4)
    file_size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
    print(f"\nSUCCESS: {output_mp4}")
    print(f"   Duration: {final_dur:.2f}s | File Size: {file_size_mb:.2f} MB\n")

def main():
    # =========================================================================
    # VIDEO 1: LUMINA ADVERTISEMENT VIDEO (Commercial / Promo)
    # Voice: en-US-ChristopherNeural (Authoritative, dynamic, cinematic)
    # =========================================================================
    ad_scenes = [
        {
            "image": os.path.join(ASSETS_DIR, "founder.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Across the globe, extraordinary student brilliance remains hidden behind outdated tests and conventional classrooms.",
            "header": "THE COGNITIVE REVOLUTION",
            "subtitle": "Beyond Standardized Testing // Unlocking Latent Genius",
            "motion": "zoom_in"
        },
        {
            "image": os.path.join(ASSETS_DIR, "hero.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Welcome to Lumina. The world's first sovereign cognitive discovery and competitive esports platform.",
            "header": "INTRODUCING LUMINA v5.2",
            "subtitle": "Sovereign Cognitive Engine & Unified Student HUD",
            "motion": "pan_left"
        },
        {
            "image": os.path.join(ASSETS_DIR, "arenas.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Transforming cognitive challenges into thrilling multiplayer arenas—from grandmaster chess and coding to speed typing.",
            "header": "8+ COMPETITIVE ARENAS",
            "subtitle": "Chess • Code Debugger • STEM Olympiad • Speed Typing",
            "motion": "zoom_in"
        },
        {
            "image": os.path.join(ASSETS_DIR, "radar.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Synthesizing deep telemetry into verified institutional dossiers that map directly to top university fellowships.",
            "header": "7-AXIS HOLOGRAPHIC RADAR",
            "subtitle": "Top 2% National Architect // MIT & Cambridge Pathways",
            "motion": "zoom_out"
        },
        {
            "image": os.path.join(ASSETS_DIR, "relay.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Powering smartboard team relays on 100% offline local networks—requiring zero internet connectivity.",
            "header": "TEAM COGNITIVE RELAY",
            "subtitle": "Multiplayer Smartboards // 100% Offline LAN Hotspot",
            "motion": "pan_right"
        },
        {
            "image": os.path.join(ASSETS_DIR, "hero.jpg"),
            "voice": "en-US-ChristopherNeural",
            "narration": "Discover the champions of tomorrow. Unlock human potential. Deploy Lumina today.",
            "header": "DEPLOY LUMINA TODAY",
            "subtitle": "Engineered by ManiSoft // Empowering the Next Generation",
            "motion": "zoom_in"
        }
    ]

    # =========================================================================
    # VIDEO 2: LUMINA WALKTHROUGH VIDEO (Technical Product Tour)
    # Voice: en-US-AndrewMultilingualNeural (Clear, confident, articulate)
    # =========================================================================
    wt_scenes = [
        {
            "image": os.path.join(ASSETS_DIR, "hero.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Welcome to the Lumina platform tour. Lumina delivers an offline-first glassmorphic interface that runs on any school network with zero cloud dependencies.",
            "header": "SYSTEM ARCHITECTURE",
            "subtitle": "Zero-Cloud Glassmorphic Dashboard & Student HUD",
            "motion": "zoom_in"
        },
        {
            "image": os.path.join(ASSETS_DIR, "arenas.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Students train and compete across eight disciplines: including algorithmic code debugging, STEM olympiads, grandmaster chess, and speed typing.",
            "header": "COGNITIVE ARENAS",
            "subtitle": "Multi-Disciplinary Speed, Strategy & Computational Logic",
            "motion": "pan_left"
        },
        {
            "image": os.path.join(ASSETS_DIR, "hero.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Every competition is secured by our keystroke dynamics anti-cheat engine, rejecting artificial jitter and measuring inter-keystroke flight times.",
            "header": "BIOMETRIC INTEGRITY",
            "subtitle": "Keystroke Flight-Time Variance & Anti-Cheat Protection",
            "motion": "zoom_out"
        },
        {
            "image": os.path.join(ASSETS_DIR, "radar.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Student telemetry generates a 7-axis holographic radar, classifying cognitive archetypes and aligning strengths with MIT and Cambridge academic pathways.",
            "header": "7-AXIS TALENT RADAR",
            "subtitle": "Cognitive Archetypes & Global University Pathways",
            "motion": "zoom_in"
        },
        {
            "image": os.path.join(ASSETS_DIR, "relay.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "In the classroom, the Team Cognitive Relay connects interactive smartboards for multi-leg competitions passing the baton from mental math to speed typing.",
            "header": "TEAM COGNITIVE RELAY",
            "subtitle": "Live Interactive Smartboard Arena & Collaborative Passing",
            "motion": "pan_right"
        },
        {
            "image": os.path.join(ASSETS_DIR, "inbox.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Teachers and parents stay informed through automated WhatsApp progress alerts, student dossiers, and direct messaging channels.",
            "header": "PARENT ENGAGEMENT INBOX",
            "subtitle": "Automated WhatsApp Telemetry & Verified Milestone Reports",
            "motion": "zoom_in"
        },
        {
            "image": os.path.join(ASSETS_DIR, "founder.jpg"),
            "voice": "en-US-AndrewMultilingualNeural",
            "narration": "Engineered by ManiSoft for sovereign, equitable deployment worldwide, Lumina democratizes talent discovery for every classroom. Thank you for watching.",
            "header": "SOVEREIGN ENGINEERING",
            "subtitle": "Engineered by ManiSoft // Free for Educational Deployment",
            "motion": "zoom_out"
        }
    ]

    out_ad = os.path.join(OUTPUT_DIR, "lumina_advertisement.mp4")
    out_wt = os.path.join(OUTPUT_DIR, "lumina_walkthrough.mp4")

    build_video(ad_scenes, "ad", out_ad, "VIDEO 1: LUMINA ADVERTISEMENT VIDEO")
    build_video(wt_scenes, "walkthrough", out_wt, "VIDEO 2: LUMINA WALKTHROUGH VIDEO")

    print("\n=======================================================")
    print("BOTH VIDEOS SUCCESSFULLY CREATED!")
    print(f"1. Advertisement: {out_ad}")
    print(f"2. Walkthrough:   {out_wt}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
