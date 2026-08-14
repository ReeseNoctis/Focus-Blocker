# 🧘 Focus Blocker

> Block distracting websites at the system level — modify `/etc/hosts` so you can actually get work done.

A cross-platform Python CLI tool that blocks entertainment and social media sites during timed focus sessions. When the timer ends (or you press Ctrl+C), the hosts file is restored automatically. On macOS 26 Tahoe and later, also handles the system immutable flag (`schg`).

---

## How It Works

```
Focus ON  →  hosts file modified  →  sites resolve to 127.0.0.1  →  blocked
Focus OFF →  hosts restored       →  sites accessible again
```

## Features

- **System-level blocking** — modifies `/etc/hosts`, works in every browser and app
- **Auto-elevation** — uses `sudo` (macOS/Linux) or UAC (Windows) to get root
- **Rich TUI** — color-coded countdown timer, progress bar, interactive site manager
- **macOS Focus Mode integration** — auto-block when system Focus Mode turns on (via Shortcuts Automation)
- **Status server** — local timer page at `http://127.0.0.1:18999` during focus sessions
- **Safe-by-default** — automatic backup/restore, signal handlers, `finally` blocks
- **Persistent config** — blocklist stored in `config/sites.json`, edit it directly or via TUI
- **DNS cache flush** — flushes the OS DNS cache for immediate effect
- **Cross-platform** — macOS, Linux, Windows

## Installation

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
pip install rich
```

## 学习助手（Web 界面）

古风二次元风格的学习页：规划每日任务、一键启动专注、计时结束自动完成。白发红眸的电子宠物 **绛雪** 会盯着你的专注状态说话、换动作（等待、指向、挥手、生气、开心），点她也会互动。

### 一键启动

```bash
./start.sh          # 启动前后端并打开浏览器
./start.sh stop     # 停止
```

界面：http://localhost:5173

首次需要先建好 Python 虚拟环境并安装依赖：

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

前端依赖会在 `./start.sh` 时自动 `npm install`。也可手动分开启动：

```bash
./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000
cd web && npm install && npm run dev
```

### 与系统 Focus 勿扰的配合

学习助手与系统 Focus 勿扰通过 `config/block_lock.json` 共享锁协调：
- 两者任一开启，网站即被屏蔽；两者都关闭才解除。
- 屏蔽引擎新增 `--acquire <watcher|assistant>` / `--release <watcher|assistant>` 命令，学习助手用 `assistant`，Focus 守护进程用 `watcher`。

### AI 智能规划

粘贴其他 AI 生成的行程文本，自动拆解成任务清单。

1. 复制 `config/ai.json.example` 为 `config/ai.json`，填入你的 DeepSeek API Key：
   ```bash
   cp config/ai.json.example config/ai.json
   # 编辑 config/ai.json，把 sk-... 换成真实 key
   ```
2. 打开学习助手，在「AI 智能规划」输入框粘贴行程，点「智能规划」。
3. 预览并微调任务（可改标题/时长/删除），点「确认创建」。

> `config/ai.json` 已被 git 忽略，不会提交你的 key。

## Quick Start

```bash
# See what's on the blocklist
python focus_blocker.py list

# Customize the list via TUI manager
python focus_blocker.py manage

# Start a focus session
python focus_blocker.py
```

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `python focus_blocker.py` | Start a focus session with countdown timer |
| `python focus_blocker.py manage` | Interactive TUI site manager |
| `python focus_blocker.py list` | Show blocked sites |
| `python focus_blocker.py config` | Open config file in editor |
| `python focus_blocker.py --help` | Show usage |

### Headless / Automation

```bash
python focus_blocker.py --block-only    # Block sites, no timer, exit
python focus_blocker.py --unblock-only  # Restore hosts, exit
```

These are designed for Shortcuts, cron, or LaunchAgent integration.

## macOS Focus Mode Integration (recommended for macOS 26+)

Automatically block distracting sites when you turn on macOS Focus Mode.

### Step 1: Configure passwordless sudo

```bash
sudo visudo
```

Add at the bottom:
```
YOUR_USERNAME ALL=(ALL) NOPASSWD: /usr/bin/python3 /path/to/Focus-Blocker/focus_blocker.py *
```

### Step 2: Create Shortcuts Automations

Open **Shortcuts** → **Automation** tab → **+** → **Create Personal Automation**:

| Trigger | Action (Run Shell Script) |
|---------|--------------------------|
| Focus **Turns On** | `/usr/bin/sudo -n /usr/bin/python3 /path/to/Focus-Blocker/focus_blocker.py --block-only` |
| Focus **Turns Off** | `/usr/bin/sudo -n /usr/bin/python3 /path/to/Focus-Blocker/focus_blocker.py --unblock-only` |

Repeat for each Focus Mode you use.

### Focus Watcher Daemon (alternative)

The `focus_watcher.py` runs as a background LaunchAgent, polls Focus Mode status, and triggers blocking/unblocking.

```bash
python focus_watcher.py           # Test in foreground
python focus_watcher.py --install  # Install as LaunchAgent
python focus_watcher.py --uninstall # Remove
```

## Configuration

The blocklist is at `config/sites.json` in the project folder:

```json
{
  "sites": [
    "www.bilibili.com",
    "bilibili.com",
    "www.youtube.com",
    "youtube.com"
  ]
}
```

Edit it directly, or use `python focus_blocker.py manage` for the interactive TUI, or `python focus_blocker.py config` to open it in your editor.

### Important: subdomains matter

DNS blocking via `hosts` is **exact-match only**. You usually need both the apex domain and the `www` subdomain:

```json
{ "sites": ["bilibili.com", "www.bilibili.com"] }
```

## Focus Timer Page

During a focus session, a local HTTP server runs automatically. Bookmark:

```
http://127.0.0.1:18999
```

Shows remaining time, blocked sites, and motivational messages. Auto-updating countdown.

## Safety Mechanisms

1. **Backup before modification** — hosts file copied to `/etc/hosts.focus_blocker_backup`
2. **Guaranteed restore** — `finally` block ensures restore even on crash
3. **Signal handlers** — SIGINT/SIGTERM trigger clean restore
4. **Marker-line isolation** — only touches lines between `# >>> FOCUS_BLOCKER_START` and `# <<< FOCUS_BLOCKER_END`
5. **Idempotent writes** — never duplicates entries
6. **Stale backup detection** — interactive prompt if backup exists
7. **Immutable flag handling** — macOS 26's `schg` flag on `/etc/hosts` is handled automatically
8. **IPv4 + IPv6** — all sites blocked on both protocols

### Worst-case recovery

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

## Platform Notes

### macOS
- macOS 26 Tahoe sets the `schg` (system immutable) flag on `/etc/hosts` — the script handles this automatically
- DNS flushed via `dscacheutil -flushcache` + `mDNSResponder` restart
- Touch ID works for sudo in the terminal

### Note on HTTPS and the timer page
Most sites use HTTPS — when blocked, the browser shows a connection error rather than the timer page (we can't intercept encrypted traffic). The timer page is available at `http://127.0.0.1:18999` anytime during a focus session.

### Browsers and DNS-over-HTTPS
Chrome, Firefox, and other browsers may use DNS-over-HTTPS which bypasses the system hosts file. Disable "Secure DNS" in your browser settings for the block to work.

## FAQ

### Q: I can still access a blocked site in my browser
**A:** Check if your browser has DNS-over-HTTPS (Secure DNS) enabled — this bypasses the system hosts file. Turn it off in browser settings. Also try in Safari first to verify the system-level block works.

### Q: What if my computer crashes?
The backup file at `/etc/hosts.focus_blocker_backup` contains your original hosts. Run the recovery command above.

### Q: How do I add/remove sites?
Edit `config/sites.json` in the project folder, or run `python focus_blocker.py manage`.

## License

MIT
