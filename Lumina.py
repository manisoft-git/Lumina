#!/usr/bin/env python3
"""
Lumina v5.1 — Student Client
Double-click to launch: opens the Lumina web app in your browser
and connects this computer for remote teacher diagnostics.
"""
import os
import sys
import socket
import platform
import time
import argparse
import webbrowser
import threading

try:
    import socketio
except ImportError:
    print("=" * 50)
    print("  Lumina needs python-socketio")
    print("  Install: pip install python-socketio")
    print("=" * 50)
    input("Press Enter to exit...")
    sys.exit(1)

SAFE_COMMANDS = {
    'ipconfig', 'ifconfig', 'ping', 'hostname', 'whoami', 'systeminfo',
    'netstat', 'tasklist', 'ver', 'date', 'time', 'dir', 'ls', 'pwd',
    'echo', 'cls', 'clear', 'path', 'vol', 'driverquery', 'getmac',
    'nslookup', 'tracert', 'traceroute', 'route', 'arp', 'net', 'wmic',
    'uname', 'uptime', 'ps', 'df', 'free'
}

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

FORBIDDEN_COMMAND_CHARS = {';', '&', '|', '>', '<', '`', '$', '\n', '\r'}

def is_safe(cmd):
    cmd_str = cmd.strip() if cmd else ''
    if not cmd_str or any(c in cmd_str for c in FORBIDDEN_COMMAND_CHARS):
        return False
    base = cmd_str.split()[0].lower()
    return base in SAFE_COMMANDS

def open_browser(url):
    """Open the Lumina web app in the default browser."""
    try:
        webbrowser.open(url, new=2)  # new=2 opens in new tab
        print(f"[./] Opened browser: {url}")
    except Exception as e:
        print(f"[./] Could not open browser: {e}")
        print(f"[./] Please manually open: {url}")

def main():
    parser = argparse.ArgumentParser(description="Lumina Student Client")
    parser.add_argument("--server", default=None, help="Lumina server URL (e.g., https://lumina.onrender.com)")
    parser.add_argument("--agent-id", default=None, help="Unique agent ID")
    parser.add_argument("--user-id", default=None, help="Associated user ID")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    args = parser.parse_args()

    # Interactive server URL prompt if not provided
    server_url = args.server
    if not server_url:
        print("=" * 50)
        print("  Lumina v5.1 — Student Client")
        print("=" * 50)
        print()
        print("Enter your school's Lumina server address.")
        print("Examples:")
        print("  https://lumina-school.onrender.com")
        print("  http://192.168.1.5:8080")
        print("  http://localhost:8080")
        print("=" * 50)
        server_url = input("\nServer URL: ").strip()
        if not server_url:
            server_url = "http://127.0.0.1:8080"
            print(f"Using default: {server_url}")

    # Ensure URL has protocol
    if not server_url.startswith("http://") and not server_url.startswith("https://"):
        server_url = "http://" + server_url

    agent_id = args.agent_id or f"agent-{platform.node()}-{int(time.time())}"
    sio = socketio.Client(reconnection=False)

    @sio.event
    def connect():
        print(f"[./] Connected to Lumina server: {server_url}")
        sio.emit("agent_register", {
            "agent_id": agent_id,
            "user_id": args.user_id,
            "hostname": platform.node(),
            "ip_address": get_ip(),
            "platform": f"{platform.system()} {platform.release()}"
        })

    @sio.event
    def disconnect():
        print("[./] Disconnected from server.")

    @sio.on("run_command")
    def on_run_command(data):
        cmd = data.get("command", "").strip()
        print(f"[./] Received command: {cmd}")
        if not is_safe(cmd):
            sio.emit("agent_output", {
                "agent_id": agent_id,
                "command": cmd,
                "output": f"ERROR: Command '{cmd}' is not in the safe diagnostics whitelist."
            })
            return
        try:
            stream = os.popen(cmd)
            output = stream.read()
            stream.close()
            if not output:
                output = "[Command executed successfully with no output]"
        except Exception as e:
            output = f"ERROR: {str(e)}"
        sio.emit("agent_output", {
            "agent_id": agent_id,
            "command": cmd,
            "output": output
        })
        print(f"[./] Sent output for: {cmd}")

    @sio.on("agent_registered")
    def on_registered(data):
        print(f"[./] Agent registered: {data}")

    print(f"[./] Starting Lumina Client v5.1")
    print(f"[./] Agent ID: {agent_id}")
    print(f"[./] Server: {server_url}")
    print(f"[./] Press Ctrl+C to stop\n")

    # Open browser in a separate thread so agent connection isn't blocked
    if not args.no_browser:
        browser_url = server_url
        threading.Thread(target=open_browser, args=(browser_url,), daemon=True).start()

    while True:
        try:
            sio.connect(server_url, namespaces=["/"])
            while sio.connected:
                sio.emit("agent_heartbeat", {"agent_id": agent_id})
                time.sleep(15)
        except KeyboardInterrupt:
            print("\n[./] Shutting down.")
            try:
                sio.disconnect()
            except Exception:
                pass
            break
        except Exception as e:
            print(f"[./] Connection error: {e}. Retrying in 5s...")
            try:
                sio.disconnect()
            except Exception:
                pass
            time.sleep(5)

if __name__ == "__main__":
    main()
