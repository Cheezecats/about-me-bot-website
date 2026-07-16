# Durable JamChat backend on macOS

The current Cloudflare Quick Tunnel is still temporary, but this `launchd` service keeps the FastAPI backend running and restarts it after a crash or reboot.

From the project root, run:

```bash
mkdir -p logs
sed "s|__PROJECT_ROOT__|$(pwd)|g" deploy/com.jamchat.backend.plist.template > "$HOME/Library/LaunchAgents/com.jamchat.backend.plist"
launchctl bootout gui/$(id -u) "$HOME/Library/LaunchAgents/com.jamchat.backend.plist" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.jamchat.backend.plist"
launchctl kickstart -k gui/$(id -u)/com.jamchat.backend
```

Verify it with:

```bash
curl "http://127.0.0.1:8000/api/health?deep=true"
tail -f logs/jamchat-backend.log
```

To stop it:

```bash
launchctl bootout gui/$(id -u) "$HOME/Library/LaunchAgents/com.jamchat.backend.plist"
```
