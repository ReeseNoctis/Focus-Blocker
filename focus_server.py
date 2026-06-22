#!/usr/bin/env python3
"""
🧘 Focus Blocker — Local Status Server
======================================
A lightweight HTTP server that runs during focus sessions, serving:
  - A "Focus Mode Active" page on port 80 (intercepts HTTP to blocked sites)
  - A status page on port 18999 for manual checking
  - JSON API for timer state

Lifecycle: started by --block-only, stopped by --unblock-only
"""

from __future__ import annotations

import json
import os
import sys
import signal
import time
import socket
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT_HTTP = 80
PORT_STATUS = 18999
CONFIG_DIR = Path(__file__).resolve().parent / "config"

# ── HTML page ──────────────────────────────────────────────────

PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧘 Focus Mode Active</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
    background: #000; color: #fff;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; text-align: center;
  }
  .container { max-width: 600px; padding: 40px 24px; }
  h1 { font-size: 72px; margin-bottom: 8px; }
  .label { font-size: 28px; font-weight: 600; color: #5e5; margin-bottom: 16px; }
  .time { font-size: 56px; font-weight: 700; font-variant-numeric: tabular-nums; margin: 32px 0; }
  .time.ending { color: #f55; }
  .time.warning { color: #fa0; }
  .time.focus   { color: #5e5; }
  .sites { font-size: 14px; color: #666; margin-top: 32px; line-height: 1.8; }
  .message { font-size: 18px; color: #888; margin-top: 20px; }
  .quote { font-size: 16px; color: #444; margin-top: 40px; }
</style>
<script>
fetch("http://127.0.0.1:18999/state").then(r => r.json()).then(s => {
  if (!s.active) return;
  function tick() {
    let now = Date.now() / 1000;
    let start = s.server_start || now;
    let elapsed = now - start;
    let remaining = s.total > 0 ? Math.max(0, s.total - elapsed) : -1;
    let el = document.getElementById("time");
    if (remaining < 0) {
      el.textContent = "∞"; el.className = "time focus";
      document.getElementById("percent").textContent = "";
    } else {
      let h = Math.floor(remaining / 3600);
      let m = Math.floor((remaining % 3600) / 60);
      let sec = remaining % 60;
      el.textContent = h > 0
        ? String(h).padStart(2,'0')+":"+String(m).padStart(2,'0')+":"+String(sec).padStart(2,'0')
        : String(m).padStart(2,'0')+":"+String(sec).padStart(2,'0');
      let ratio = s.total > 0 ? remaining / s.total : 1;
      el.className = "time " + (ratio > 0.5 ? "focus" : ratio > 0.15 ? "warning" : "ending");
      document.getElementById("percent").textContent = Math.round((1-ratio)*100)+"% complete";
    }
  }
  tick(); setInterval(tick, 1000);
}).catch(() => {});
</script>
</head>
<body>
<div class="container">
  <h1>🧘</h1>
  <div class="label">Focus Mode Active</div>
  <div id="time" class="time focus">--:--</div>
  <div id="percent" style="color:#666;font-size:16px;"></div>
  <div class="message">This site is blocked during your focus session.</div>
  <div class="message">回到工作中 — 专注结束后会自动解封 🎯</div>
  <div class="sites">{sites_list}</div>
  <div class="quote">"专注是成功的钥匙。"</div>
</div>
</body>
</html>"""

# ── State ─────────────────────────────────────────────────────

_server_start_time: float | None = None
_total_seconds: int = 0
_blocked_sites: list[str] = []


def _load_sites() -> list[str]:
    try:
        data = json.loads((CONFIG_DIR / "sites.json").read_text())
        return data.get("sites", [])
    except Exception:
        return []


def is_port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            return False
    except OSError:
        return True


# ── Request handler ──────────────────────────────────────────

class FocusHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _serve_json(self, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _get_state(self) -> dict:
        if _total_seconds > 0 and _server_start_time:
            elapsed = time.monotonic() - _server_start_time
            remaining = max(0, int(_total_seconds - elapsed))
        else:
            elapsed = 0
            remaining = -1
        return {
            "active": True,
            "total": _total_seconds,
            "elapsed": int(elapsed),
            "remaining": remaining,
            "server_start": _server_start_time,
            "sites": _blocked_sites,
        }

    def do_GET(self):
        if self.path == "/state":
            return self._serve_json(self._get_state())
        self._serve_timer_page()

    def _serve_timer_page(self):
        sites_html = "<br>".join(
            f"  &#x1F6AB; {s}" for s in _blocked_sites[:20]
        )
        if len(_blocked_sites) > 20:
            sites_html += f"<br>  ... and {len(_blocked_sites) - 20} more"
        self._serve_html(PAGE_HTML.replace("{sites_list}", sites_html))


# ── Server lifecycle ──────────────────────────────────────────

def start_server(sites: list[str], total_seconds: int = 0) -> bool:
    global _server_start_time, _total_seconds, _blocked_sites
    _server_start_time = time.monotonic()
    _total_seconds = total_seconds
    _blocked_sites = sites

    started_any = False
    for port in [PORT_STATUS, PORT_HTTP]:
        if is_port_in_use(port):
            print(f"  ⚠️  Port {port} already in use — skipping")
            continue
        try:
            server = HTTPServer(("127.0.0.1", port), FocusHandler)
            pid = os.fork()
            if pid == 0:
                signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                sys.exit(0)
            else:
                server.server_close()
                started_any = True
                print(f"  🌐 Server on port {port} (pid {pid})")
        except Exception as exc:
            print(f"  ❌ Port {port}: {exc}")

    return started_any


def stop_server() -> None:
    for port in [str(PORT_STATUS), str(PORT_HTTP)]:
        try:
            r = subprocess.run(
                ["lsof", "-ti", f"TCP:{port}"],
                capture_output=True, text=True, timeout=5,
            )
            for p in r.stdout.strip().split():
                os.kill(int(p), signal.SIGTERM)
        except Exception:
            pass


# ── CLI ───────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python focus_server.py start|stop [total_seconds]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        sites = _load_sites()
        total = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        start_server(sites, total)
    elif cmd == "stop":
        stop_server()
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
