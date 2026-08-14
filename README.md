# Focus Blocker

**English** | [中文](README.zh-CN.md)

A local study assistant that **blocks distracting websites at the system level** while you focus. The web app plans tasks, runs a timer, and is watched by **Jiang Xue** (绛雪), a Q-version companion. When a session starts, `/etc/hosts` is rewritten so blocked sites fail in every browser and app — not just one extension.

```
Focus ON  →  hosts file rewritten  →  sites resolve to 127.0.0.1  →  blocked
Focus OFF →  hosts restored        →  sites work again
```

---

## What you can do

| Feature | What it means |
|---|---|
| **Study web app** | Daily tasks, focus timer, pause / resume / stop |
| **Jiang Xue** | Anime companion who reacts to idle, focusing, paused, and done |
| **AI planner** | Paste a study plan; it splits into editable tasks (DeepSeek key optional) |
| **System block** | Edits `/etc/hosts` (IPv4 + IPv6). Works outside the browser |
| **Shared lock** | Web sessions and macOS Focus Mode can share one block; sites stay blocked until **both** are off |
| **Safe restore** | Backup, signal handlers, and `finally` so a crash does not leave hosts broken |
| **macOS 26** | Handles the `schg` immutable flag on `/etc/hosts` |
| **CLI + TUI** | Optional terminal timer and site manager (`focus_blocker.py`) |

Primary target is **macOS**. The CLI also runs on Linux and Windows.

---

## Deploy the study assistant (macOS)

You should only need **one install command** and **one start command**. Copy each block as a whole.

### 1. Install Python 3.12 and Node.js (once)

If you do not have [Homebrew](https://brew.sh), install it from their site first. Then paste:

```bash
brew install python@3.12 node
```

### 2. Get the project (once)

GitHub → green **Code** → **Download ZIP**, unzip, then open Terminal in that folder.

Or paste:

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
```

### 3. Start

```bash
chmod +x start.sh
./start.sh
```

The first run creates `.venv`, installs Python and frontend packages, copies `config/ai.json` if missing, starts the API and UI, then opens the app.

| | |
|---|---|
| App | [http://localhost:5173](http://localhost:5173) |
| API | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| Stop | `./start.sh stop` |

`./start.sh stop` also **releases the site block**, so killing the app cannot leave websites stuck.

Starting a focus session will ask for **sudo** (or Touch ID). That is required to edit `/etc/hosts`.

---

## Optional: AI planner

1. Run `./start.sh` once (it creates `config/ai.json`).
2. Open `config/ai.json` and replace the placeholder with a [DeepSeek](https://platform.deepseek.com/) API key.
3. In the app, paste a plan into **AI planner** → **Plan** → edit → **Create**.

`config/ai.json` is gitignored. Never commit a real key.

Without a key, everything else still works; only AI planning is disabled.

---

## Optional: skip the sudo password

Only needed if you do not want a password prompt on every focus start.

1. Paste this; it prints **one line** to copy:

```bash
./start.sh visudo-hint
```

2. Paste this to open the sudoers editor:

```bash
sudo visudo
```

3. Put the printed line at the **bottom**, save, quit.

After that, focus start/stop can run with `sudo -n` (no password).

---

## How to use the app

1. Open [http://localhost:5173](http://localhost:5173) (or let `./start.sh` open it).
2. Add tasks under **Today**, or paste a plan into **AI planner**.
3. Click **Focus** on a task (or start a free session on the timer).
4. Distracting sites on the blocklist go down until you stop or the timer ends.
5. Jiang Xue watches the session: she nags if you idle, points while you focus, and reacts if you pause.

Edit the blocklist in `config/sites.json` (or with the CLI manager below). Hosts matching is **exact**: include both `example.com` and `www.example.com`.

---

## CLI (optional)

Same blocker, terminal UI. After `./start.sh` has created `.venv`:

```bash
./.venv/bin/python3 focus_blocker.py          # timed session
./.venv/bin/python3 focus_blocker.py list     # show sites
./.venv/bin/python3 focus_blocker.py manage   # add / remove sites
./.venv/bin/python3 focus_blocker.py config   # open config
```

Headless (Shortcuts, cron, LaunchAgent):

```bash
./.venv/bin/python3 focus_blocker.py --block-only
./.venv/bin/python3 focus_blocker.py --unblock-only
```

---

## macOS Focus Mode (optional)

Block the same sites when a system Focus turns on.

**A. Shortcuts automations** (simple)

Shortcuts → **Automation** → **+** → Personal Automation:

| When | Run Shell Script |
|---|---|
| Focus **Turns On** | `/usr/bin/sudo -n /usr/bin/python3 /ABS/PATH/Focus-Blocker/focus_blocker.py --block-only` |
| Focus **Turns Off** | `/usr/bin/sudo -n /usr/bin/python3 /ABS/PATH/Focus-Blocker/focus_blocker.py --unblock-only` |

Replace `/ABS/PATH` with this folder. Repeat per Focus you use. Prefer the interpreter path from `./start.sh visudo-hint` if you use the venv.

**B. Watcher daemon**

```bash
./.venv/bin/python3 focus_watcher.py            # test in the foreground
./.venv/bin/python3 focus_watcher.py --install  # LaunchAgent
./.venv/bin/python3 focus_watcher.py --uninstall
```

The web app uses lock owner `assistant`. The watcher uses `watcher`. Either one on → sites blocked; both off → sites restored.

---

## Safety

- Backup: `/etc/hosts.focus_blocker_backup`
- Restore on Ctrl+C, signals, and `finally`
- Only lines between `# >>> FOCUS_BLOCKER_START` and `# <<< FOCUS_BLOCKER_END` are touched
- Writes are idempotent (no duplicate rows)
- IPv4 and IPv6

If hosts is left dirty after a crash:

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

During a **CLI** timed session, a local page is also at [http://127.0.0.1:18999](http://127.0.0.1:18999). HTTPS sites still show a connection error when blocked (the tool cannot intercept TLS). Use that URL to see the countdown.

---

## FAQ

**A blocked site still loads.** Turn off browser **Secure DNS** / DNS-over-HTTPS. Confirm in Safari first.

**Sudo keeps asking.** Use the visudo line from `./start.sh visudo-hint`.

**Python / npm missing.** `brew install python@3.12 node`

**Permission denied on `./start.sh`.** `chmod +x start.sh`

**Add or remove sites.** Edit `config/sites.json`, or run `./.venv/bin/python3 focus_blocker.py manage`.

---

## License

MIT
