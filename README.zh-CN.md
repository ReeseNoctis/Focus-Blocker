# Focus Blocker

[English](README.md) | **中文**

本地学习工具：专注时在**系统层屏蔽娱乐网站**（改 hosts，不是浏览器插件）。在 **macOS** 上还有网页：任务、计时，以及电子宠物 **绛雪** 监督。

```
开启专注  →  改写 hosts  →  站点解析到 127.0.0.1  →  被屏蔽
结束专注  →  还原 hosts  →  网站恢复
```

请先看下面的对照表，再跳到**你正在用的系统**那一节。

---

## 各系统能用什么

| 能力 | macOS | Linux | Windows |
|---|---|---|---|
| 命令行计时 + 屏蔽网站 | 可以 | 可以 | 可以（UAC） |
| 终端里增删屏蔽名单 | 可以 | 可以 | 可以（管理员） |
| 一条命令启动网页（`./start.sh`） | 可以 | 部分可以（见 Linux） | 不可以 |
| 网页：任务、计时、绛雪 | 可以 | 可以（需自己启动） | 可以（需自己启动） |
| 网页点「专注」**真的屏蔽网站** | 可以（`sudo`） | 可以（`sudo`） | **不可以**（网页调的是 `sudo`，Windows 没有） |
| AI 智能规划（需 DeepSeek Key） | 可以 | 可以 | 可以（不需要管理员） |
| 系统「专注模式」一开就屏蔽 | 可以 | 不可以 | 不可以 |
| 后台守护进程（LaunchAgent） | 可以 | 不可以 | 不可以 |
| macOS 26 的 `schg` 标记 | 可以 | — | — |
| 刷新 DNS 缓存 | 可以 | 可以 | 可以（`ipconfig /flushdns`） |

**想用完整产品：请用 macOS。**  
**Windows / Linux：** 用命令行挡网站。Windows 上网页点「专注」**不会**把网站挡住。

---

## 所有系统都一样的部分

- 屏蔽名单：`config/sites.json`。必须**完全匹配**，`bilibili.com` 和 `www.bilibili.com` 都要写。
- 备份文件在系统 hosts 旁边，名叫 `hosts.focus_blocker_backup`。
- 只改 `# >>> FOCUS_BLOCKER_START` 到 `# <<< FOCUS_BLOCKER_END` 之间的行。
- 请关掉浏览器的「安全 DNS」/ DNS-over-HTTPS，否则会以为没生效。
- AI：把 DeepSeek Key 写进 `config/ai.json`（从 `config/ai.json.example` 复制）。这个文件已被 git 忽略。

hosts 路径：

| 系统 | 文件 |
|---|---|
| macOS / Linux | `/etc/hosts` |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |

---

## macOS（完整功能）

网页、绛雪、点「专注」屏蔽网站、命令行、可选的系统专注模式，都可以用。

### 安装（只需一次）

先装 [Homebrew](https://brew.sh)，再整段粘贴：

```bash
brew install python@3.12 node
```

拿代码：GitHub → **Code** → **Download ZIP**，或：

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
```

### 启动 / 停止

```bash
chmod +x start.sh
./start.sh
```

第一次会建 `.venv`、装依赖、必要时复制 `config/ai.json`，然后打开浏览器。

| | |
|---|---|
| 界面 | [http://localhost:5173](http://localhost:5173) |
| API | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| 停止 | `./start.sh stop` |

`./start.sh stop` 会**同时解除屏蔽**。开始专注时会要 **sudo** 或 Touch ID。

### 怎么用网页

1. 在「今日任务」添加，或把行程贴进「AI 智能规划」。
2. 点「专注」，或在计时器里直接开始。
3. 名单里的网站会打不开，直到结束或倒计时走完。
4. 绛雪会跟着空闲 / 专注 / 暂停 / 完成变化，可以点她。

### 可选：AI Key

先跑一次 `./start.sh`，打开 `config/ai.json`，贴上 [DeepSeek](https://platform.deepseek.com/) Key。没有 Key 只影响智能规划。

### 可选：免输 sudo 密码

```bash
./start.sh visudo-hint
```

复制打印出来的**那一行**，然后：

```bash
sudo visudo
```

贴到**文件最底部**，保存退出。

### 可选：命令行

```bash
./.venv/bin/python3 focus_blocker.py
./.venv/bin/python3 focus_blocker.py list
./.venv/bin/python3 focus_blocker.py manage
./.venv/bin/python3 focus_blocker.py --block-only
./.venv/bin/python3 focus_blocker.py --unblock-only
```

命令行计时期间还有 [http://127.0.0.1:18999](http://127.0.0.1:18999)。

### 可选：跟着系统专注模式

**A. 快捷指令**

快捷指令 → **自动化** → **+** → 个人自动化：

| 时机 | 运行 Shell 脚本 |
|---|---|
| 专注 **打开** | `/usr/bin/sudo -n /usr/bin/python3 /绝对路径/Focus-Blocker/focus_blocker.py --block-only` |
| 专注 **关闭** | `/usr/bin/sudo -n /usr/bin/python3 /绝对路径/Focus-Blocker/focus_blocker.py --unblock-only` |

`/绝对路径` 换成这个文件夹。用虚拟环境时，Python 路径用 `./start.sh visudo-hint` 打出来的。每种专注模式都建一套。

**B. 后台守护**

```bash
./.venv/bin/python3 focus_watcher.py
./.venv/bin/python3 focus_watcher.py --install
./.venv/bin/python3 focus_watcher.py --uninstall
```

网页锁主人是 `assistant`，守护进程是 `watcher`。任一开启就屏蔽；两个都关才恢复。

### hosts 没还原时

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

---

## Linux

可以用：**命令行屏蔽网站**（sudo）。也可以跑**网页**；若 `sudo` 可用，点「专注」**可以**屏蔽。  
没有：macOS 专注模式、LaunchAgent、`./start.sh` 自动打开浏览器（`open` 是 macOS 命令）。

### 安装（只需一次）

Debian / Ubuntu 整段粘贴：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git
```

然后：

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### 命令行（Linux 上推荐这样用）

```bash
./.venv/bin/python3 focus_blocker.py
./.venv/bin/python3 focus_blocker.py list
./.venv/bin/python3 focus_blocker.py manage
```

第一次开始专注会要 **sudo**，才能改 `/etc/hosts`。

### 网页（可选）

若已有 `bash`、Python、`npm`，`./start.sh` 有可能能跑，但不会自动打开浏览器。也可以自己开两个终端：

```bash
./.venv/bin/python3 -m uvicorn app.main:app --port 8000
```

```bash
cd web && npm install && npm run dev
```

浏览器打开 [http://localhost:5173](http://localhost:5173)。想让「专注」免密改 hosts，按 macOS 那样配 visudo（venv 建好后跑 `./start.sh visudo-hint`）。

### hosts 没还原时

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

---

## Windows

可以用：**命令行屏蔽网站**（UAC），改的是 `C:\Windows\System32\drivers\etc\hosts`。

不可以用：

- `./start.sh`（这是 bash 脚本）
- 网页点「专注」去挡网站（后端调用 `sudo -n`，Windows 没有）
- macOS 专注模式 / 守护进程

网页（任务、计时、绛雪、AI）你可以自己把 Python 和 Node 跑起来，但点「专注」**不会**改 hosts。要挡网站请用命令行。

不要用 WSL 指望挡住 Windows 上的 Chrome / Edge。WSL 有自己的 hosts。

### 安装（只需一次）

1. 安装 [Python 3](https://www.python.org/downloads/)，勾选 **Add python.exe to PATH**。
2. GitHub → **Code** → **Download ZIP** 解压。  
   或：`git clone https://github.com/ReeseNoctis/Focus-Blocker.git`

在 **命令提示符** 或 PowerShell 进入项目文件夹，整段粘贴：

```bat
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 用命令行挡网站

**以管理员身份运行**，或在弹出的 UAC 窗口点允许：

```bat
.venv\Scripts\python focus_blocker.py
```

其它：

```bat
.venv\Scripts\python focus_blocker.py list
.venv\Scripts\python focus_blocker.py manage
.venv\Scripts\python focus_blocker.py --block-only
.venv\Scripts\python focus_blocker.py --unblock-only
```

### 只开网页（不会系统屏蔽）

只想看绛雪 / 任务 / AI，并且接受「专注」挡不住网站时再用。

终端 1：

```bat
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

安装 [Node.js](https://nodejs.org/) 后，终端 2：

```bat
cd web
npm install
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)。

可选 AI：把 `config\ai.json.example` 复制为 `config\ai.json`，填入 DeepSeek Key。

### hosts 没还原时

用**管理员**记事本，或在管理员命令提示符粘贴：

```bat
copy /Y C:\Windows\System32\drivers\etc\hosts.focus_blocker_backup C:\Windows\System32\drivers\etc\hosts
```

然后：

```bat
ipconfig /flushdns
```

---

## 常见问题

**网站还能打开。** 关掉安全 DNS / DNS-over-HTTPS。macOS 先用 Safari 试。

**macOS 每次都要 sudo。** `./start.sh visudo-hint`，再 `sudo visudo`。

**Windows 网页里点专注，YouTube 还在。** 这是预期行为。请用管理员运行 `.venv\Scripts\python focus_blocker.py`。

**`./start.sh` 没权限。** `chmod +x start.sh`

---

## 许可证

MIT
