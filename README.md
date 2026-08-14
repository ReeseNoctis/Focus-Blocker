# Focus Blocker

**English** | [中文](README.zh-CN.md)

A local study tool that **blocks distracting websites at the OS level** (by editing the system hosts file) while you focus. On macOS you also get a web app with tasks, a timer, and **Jiang Xue** (绛雪), a companion who watches the session.

```
Focus ON  →  hosts file rewritten  →  sites resolve to 127.0.0.1  →  blocked
Focus OFF →  hosts restored        →  sites work again
```

This is **not** a browser extension. Blocked sites fail in every app that uses the system DNS.

---

## Support by operating system

Read **your** column first. Full setup for each OS is below.

| Capability | macOS | Linux | Windows |
|---|---|---|---|
| CLI timed focus + site block | Yes | Yes | Yes (UAC) |
| TUI to list / add / remove sites | Yes | Yes | Yes (run as Administrator) |
| One-command web app (`./start.sh`) | Yes | Partial (see Linux) | No |
| Web: tasks, timer, Jiang Xue | Yes | Yes, if you start it yourself | Yes, if you start it yourself |
| Web **Focus** button actually blocks sites | Yes (`sudo`) | Yes (`sudo`) | **No** (web calls `sudo`, which Windows does not have) |
| AI planner (needs DeepSeek key) | Yes | Yes | Yes (does not need admin) |
| Auto-block when system Focus Mode turns on | Yes | No | No |
| Background watcher (LaunchAgent) | Yes | No | No |
| `/etc/hosts` `schg` flag (macOS 26) | Yes | — | — |
| DNS cache flush | Yes | Yes | Yes (`ipconfig /flushdns`) |

**Recommended:** macOS, if you want the full product.  
**Windows / Linux:** use the CLI to block sites. The web UI on Windows will **not** block the internet when you click Focus.

---

## Shared ideas (all platforms)

- Blocklist file: `config/sites.json`. Matching is **exact** — list both `bilibili.com` and `www.bilibili.com`.
- Hosts backup: next to the real hosts file, named `hosts.focus_blocker_backup`.
- Only lines between `# >>> FOCUS_BLOCKER_START` and `# <<< FOCUS_BLOCKER_END` are changed.
- Turn **off** browser Secure DNS / DNS-over-HTTPS, or the block will look like it “does nothing”.
- AI planner: put a DeepSeek key in `config/ai.json` (copied from `config/ai.json.example`). The file is gitignored.

Hosts paths:

| OS | Hosts file |
|---|---|
| macOS / Linux | `/etc/hosts` |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |

---

## macOS (full product)

You get everything: web app, Jiang Xue, site block from the Focus button, CLI, optional Focus Mode automation.

### Install (once)

Need [Homebrew](https://brew.sh) first. Then paste:

```bash
brew install python@3.12 node
```

Get the repo (GitHub → **Code** → **Download ZIP**, or):

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
```

### Start / stop

```bash
chmod +x start.sh
./start.sh
```

First run creates `.venv`, installs packages, copies `config/ai.json` if missing, then opens the browser.

| | |
|---|---|
| App | [http://localhost:5173](http://localhost:5173) |
| API | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| Stop | `./start.sh stop` |

`./start.sh stop` also **unblocks sites**. Starting Focus will ask for **sudo** or Touch ID.

### Use the web app

1. Add tasks under **Today**, or paste a plan into **AI planner**.
2. Click **Focus** (or start a free session on the timer).
3. Listed sites go down until you stop or the timer ends.
4. Jiang Xue reacts to idle / focusing / paused / done. You can click her.

### Optional: AI key

After the first `./start.sh`, open `config/ai.json` and paste a [DeepSeek](https://platform.deepseek.com/) key. Without it, only AI planning is disabled.

### Optional: no sudo password

```bash
./start.sh visudo-hint
```

Copy the **one line** it prints. Then:

```bash
sudo visudo
```

Paste that line at the **bottom**, save, quit.

### Optional: CLI

```bash
./.venv/bin/python3 focus_blocker.py
./.venv/bin/python3 focus_blocker.py list
./.venv/bin/python3 focus_blocker.py manage
./.venv/bin/python3 focus_blocker.py --block-only
./.venv/bin/python3 focus_blocker.py --unblock-only
```

CLI sessions also serve [http://127.0.0.1:18999](http://127.0.0.1:18999).

### Optional: follow macOS Focus Mode

**A. Shortcuts**

Shortcuts → **Automation** → **+** → Personal Automation:

| When | Run Shell Script |
|---|---|
| Focus **Turns On** | `/usr/bin/sudo -n /usr/bin/python3 /ABS/PATH/Focus-Blocker/focus_blocker.py --block-only` |
| Focus **Turns Off** | `/usr/bin/sudo -n /usr/bin/python3 /ABS/PATH/Focus-Blocker/focus_blocker.py --unblock-only` |

Use this folder as `/ABS/PATH`. Prefer the Python path from `./start.sh visudo-hint` if you use the venv. Repeat for each Focus you use.

**B. Watcher daemon**

```bash
./.venv/bin/python3 focus_watcher.py
./.venv/bin/python3 focus_watcher.py --install
./.venv/bin/python3 focus_watcher.py --uninstall
```

Web app lock owner = `assistant`. Watcher = `watcher`. Either on → blocked; both off → restored.

### If hosts is left dirty

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

---

## Linux

You get: **CLI site blocking** (sudo). You can run the **web UI**, and the Focus button **can** block sites if `sudo` works. You do **not** get macOS Focus Mode, LaunchAgent, or `./start.sh` auto-opening a browser (`open` is macOS-only).

### Install (once)

Debian / Ubuntu example — paste:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git
```

Then:

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### CLI (this is the supported Linux workflow)

```bash
./.venv/bin/python3 focus_blocker.py
./.venv/bin/python3 focus_blocker.py list
./.venv/bin/python3 focus_blocker.py manage
```

The first focus run will ask for **sudo** so it can edit `/etc/hosts`.

### Web UI (optional)

`./start.sh` may work if `bash`, Python, and `npm` exist. It will not call `open`. Or start the two processes yourself:

```bash
./.venv/bin/python3 -m uvicorn app.main:app --port 8000
```

In another terminal:

```bash
cd web && npm install && npm run dev
```

Then open [http://localhost:5173](http://localhost:5173). For the Focus button to block sites without a password prompt, add a visudo line like macOS (`./start.sh visudo-hint` after a venv exists).

### If hosts is left dirty

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

---

## Windows

You get: **CLI site blocking** via UAC, editing `C:\Windows\System32\drivers\etc\hosts`.

You do **not** get:

- `./start.sh` (it is a bash script)
- Site block from the web **Focus** button (the server runs `sudo -n`, which is not available)
- macOS Focus Mode / watcher

The web page (tasks, timer, Jiang Xue, AI planner) can still be opened if you start Python and Node yourself, but clicking Focus **will not** take sites down. Use the CLI to block.

Do **not** use WSL expecting Windows Chrome/Edge to be blocked. WSL has its own hosts file.

### Install (once)

1. Install [Python 3](https://www.python.org/downloads/) (check **Add python.exe to PATH**).
2. GitHub → **Code** → **Download ZIP**, unzip.  
   Or Git: `git clone https://github.com/ReeseNoctis/Focus-Blocker.git`

In **Command Prompt** or PowerShell, `cd` into the folder, then paste:

```bat
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Block sites (CLI)

Run this **as Administrator**, or accept the UAC dialog when it appears:

```bat
.venv\Scripts\python focus_blocker.py
```

Other commands:

```bat
.venv\Scripts\python focus_blocker.py list
.venv\Scripts\python focus_blocker.py manage
.venv\Scripts\python focus_blocker.py --block-only
.venv\Scripts\python focus_blocker.py --unblock-only
```

### Web UI only (no system block)

Only if you still want Jiang Xue / tasks / AI, knowing Focus will not edit hosts.

Terminal 1:

```bat
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Install [Node.js](https://nodejs.org/), then terminal 2:

```bat
cd web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

Optional AI: copy `config\ai.json.example` to `config\ai.json` and paste a DeepSeek key.

### If hosts is left dirty

Open Notepad **as Administrator**, or paste in an elevated Command Prompt:

```bat
copy /Y C:\Windows\System32\drivers\etc\hosts.focus_blocker_backup C:\Windows\System32\drivers\etc\hosts
```

Then:

```bat
ipconfig /flushdns
```

---

## FAQ

**A blocked site still loads.** Disable Secure DNS / DNS-over-HTTPS. On macOS, try Safari first.

**macOS keeps asking for sudo.** `./start.sh visudo-hint`, then `sudo visudo`.

**Windows Focus in the browser does nothing to YouTube.** Expected. Use `.venv\Scripts\python focus_blocker.py` as Administrator.

**Permission denied on `./start.sh`.** `chmod +x start.sh`

---

## License

MIT
