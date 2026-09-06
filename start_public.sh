#!/usr/bin/env bash
# Start Lumina and launch Cloudflare tunnel

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo "=== Starting Lumina v5.2 ==="
# Check if Lumina is running
if ! pgrep -f "python3 app.py" > /dev/null; then
    nohup python3 app.py > lumina_server.log 2>&1 &
    sleep 3
    echo "[✓] Lumina server started on port 8080"
else
    echo "[✓] Lumina server already running"
fi

# Check if tunnel is running
if ! pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "Starting Cloudflare tunnel..."
    nohup cloudflared tunnel --url http://127.0.0.1:8080 > tunnel.log 2>&1 &
    sleep 4
fi

# Print active URL
URL=$(grep -o 'https://[-a-z0-9.]*\.trycloudflare\.com' tunnel.log 2>/dev/null | tail -n 1)
if [ -n "$URL" ]; then
    echo "===================================================="
    echo "🌐 LIVE PUBLIC URL: $URL"
    echo "===================================================="
else
    echo "Tunnel starting up. Check 'cat tunnel.log' for your public URL."
fi
