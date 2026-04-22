"""
watchdog.py — Hermes system watchdog daemon.
Runs every 60 seconds. Triggers safemode + repair if 2 consecutive hard failures.
Sends Discord alert on sustained failure.
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from health_checks import run_all_checks, summary, is_safemode_required

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
SAFEMODE_PORT = int(os.environ.get("SAFEMODE_PORT", "7861"))
WEBUI_PORT = int(os.environ.get("WEBUI_PORT", "7860"))
CHECK_INTERVAL = int(os.environ.get("WATCHDOG_INTERVAL", "60"))
STATE_FILE = Path("/opt/repair/watchdog_state.json")


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"consecutive_fails": 0, "safemode_active": False, "last_check": 0}


def save_state(s: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2))


def _run(cmd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def send_discord_alert(message: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    try:
        body = json.dumps({"content": message, "username": "Hermes Watchdog"}).encode()
        req = urllib.request.Request(
            DISCORD_WEBHOOK, body,
            {"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def is_safemode_running() -> bool:
    rc, out = _run(f"curl -sf http://localhost:{SAFEMODE_PORT}/health")
    return rc == 0


def start_safemode() -> None:
    print("[watchdog] Starting safemode server...")
    _run(
        f"nohup python3 /opt/self-healing/safemode_server.py "
        f">> /opt/repair/safemode.log 2>&1 &"
    )


def redirect_nginx_to_safemode() -> None:
    """Patch nginx to send :80 → :7861 (safemode) instead of :7860."""
    nginx_patch = f"""
server {{
    listen 80 default_server;
    location / {{
        proxy_pass http://localhost:{SAFEMODE_PORT};
        proxy_set_header Host $host;
    }}
}}
"""
    try:
        Path("/etc/nginx/conf.d/hermes-safemode.conf").write_text(nginx_patch)
        _run("nginx -t && systemctl reload nginx")
        print("[watchdog] Nginx → safemode mode")
    except Exception as e:
        print(f"[watchdog] Nginx redirect failed: {e}")


def restore_nginx_to_webui() -> None:
    """Remove safemode nginx override."""
    try:
        p = Path("/etc/nginx/conf.d/hermes-safemode.conf")
        if p.exists():
            p.unlink()
        _run("nginx -t && systemctl reload nginx")
        print("[watchdog] Nginx → WebUI mode (restored)")
    except Exception as e:
        print(f"[watchdog] Nginx restore failed: {e}")


def trigger_repair() -> None:
    """POST to safemode server to trigger full repair cycle."""
    try:
        req = urllib.request.Request(
            f"http://localhost:{SAFEMODE_PORT}/repair/trigger",
            b"",
            {"Content-Type": "application/json"},
        )
        req.get_method = lambda: "POST"
        urllib.request.urlopen(req, timeout=5)
        print("[watchdog] Repair triggered via safemode API")
    except Exception as e:
        print(f"[watchdog] Could not trigger repair: {e}")


async def watch_loop() -> None:
    print(f"[watchdog] Started. Interval={CHECK_INTERVAL}s")
    state = load_state()

    while True:
        try:
            t = time.monotonic()
            results = run_all_checks()
            s = summary(results)
            elapsed = time.monotonic() - t

            timestamp = time.strftime("%H:%M:%S")
            print(f"[watchdog {timestamp}] {s['passed']}/{s['total']} OK, "
                  f"{s['failed_hard']} hard, {s['failed_soft']} soft ({elapsed:.1f}s)")

            if s["failed_hard"] == 0:
                # System healthy
                state["consecutive_fails"] = 0
                if state.get("safemode_active"):
                    print("[watchdog] System recovered — exiting safemode")
                    restore_nginx_to_webui()
                    state["safemode_active"] = False
                    send_discord_alert("✅ Hermes system recovered — all checks passing")
            else:
                state["consecutive_fails"] += 1
                print(f"[watchdog] Consecutive failures: {state['consecutive_fails']}")
                print(f"[watchdog] Hard failures: {s['hard_failures']}")

                if state["consecutive_fails"] >= 2:
                    # Enter safemode
                    if not state.get("safemode_active"):
                        print("[watchdog] ENTERING SAFEMODE")
                        state["safemode_active"] = True
                        if not is_safemode_running():
                            start_safemode()
                            await asyncio.sleep(3)
                        redirect_nginx_to_safemode()
                        trigger_repair()
                        send_discord_alert(
                            f"⚠️ Hermes entered SAFEMODE — {s['failed_hard']} hard failure(s): "
                            + ", ".join(f['name'] for f in s['hard_failures'])
                        )
                    else:
                        # Already in safemode, re-trigger if repair not running
                        trigger_repair()

            state["last_check"] = time.time()
            save_state(state)

        except Exception as e:
            print(f"[watchdog] Error in watch loop: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(watch_loop())
