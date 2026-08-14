# Focus Blocker

[English](README.md) | **中文**

本地学习助手：专注时在**系统层屏蔽娱乐网站**。网页端负责任务、计时，并由二次元电子宠物 **绛雪** 监督。开始专注后会改写 `/etc/hosts`，所有浏览器和 App 里这些站点都会打不开，不是只拦某一个插件。

```
开启专注  →  改写 hosts  →  站点解析到 127.0.0.1  →  被屏蔽
结束专注  →  还原 hosts  →  网站恢复
```

---

## 能做什么

| 功能 | 说明 |
|---|---|
| **学习网页** | 今日任务、专注计时、暂停 / 继续 / 结束 |
| **绛雪** | 按空闲、专注、暂停、完成换动作和台词，可以点她 |
| **AI 智能规划** | 粘贴一段行程，拆成可改的任务（DeepSeek Key 可选） |
| **系统屏蔽** | 改 `/etc/hosts`（IPv4 + IPv6），不依赖浏览器扩展 |
| **共享锁** | 网页专注和 macOS 专注模式可以共用一把锁；**两边都关**才解除屏蔽 |
| **安全还原** | 备份、信号处理、`finally`，避免 hosts 改坏回不来 |
| **macOS 26** | 自动处理 `/etc/hosts` 上的 `schg` 不可变标记 |
| **命令行** | 可选终端计时和站点管理（`focus_blocker.py`） |

主力环境是 **macOS**。命令行也可在 Linux / Windows 使用。

---

## 部署学习助手（macOS）

正常情况只需要 **一条安装** 和 **一条启动**。下面每一块整段复制即可。

### 1. 安装 Python 3.12 和 Node.js（只需一次）

没有 [Homebrew](https://brew.sh) 的话，先按官网安装。然后整段粘贴：

```bash
brew install python@3.12 node
```

### 2. 拿到项目（只需一次）

GitHub 绿色 **Code** → **Download ZIP**，解压后在该文件夹打开终端。

或整段粘贴：

```bash
git clone https://github.com/ReeseNoctis/Focus-Blocker.git
cd Focus-Blocker
```

### 3. 启动

```bash
chmod +x start.sh
./start.sh
```

第一次运行会自动创建 `.venv`、安装 Python 和前端依赖、在缺少时复制 `config/ai.json`，然后打开网页。

| | |
|---|---|
| 界面 | [http://localhost:5173](http://localhost:5173) |
| API | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| 停止 | `./start.sh stop` |

`./start.sh stop` 会**同时解除网站屏蔽**，避免只杀进程却把网站一直挡住。

开始专注时会要 **sudo**（或 Touch ID），因为必须改 `/etc/hosts`。

---

## 可选：AI 智能规划

1. 先跑一次 `./start.sh`（会生成 `config/ai.json`）。
2. 打开 `config/ai.json`，把占位内容换成 [DeepSeek](https://platform.deepseek.com/) API Key。
3. 在页面「AI 智能规划」里粘贴行程 → **智能规划** → 改一改 → **确认创建**。

`config/ai.json` 已被 git 忽略，不要提交真实 key。

没有 key 时其它功能都能用，只是智能规划不可用。

---

## 可选：免输 sudo 密码

不想每次开始专注都输密码时再做。

1. 整段粘贴，终端会打印 **一行** 配置，复制它：

```bash
./start.sh visudo-hint
```

2. 打开 sudoers 编辑器：

```bash
sudo visudo
```

3. 把那一行贴到**文件最底部**，保存退出。

之后专注开始 / 结束可以用 `sudo -n`，不再弹密码。

---

## 怎么用网页

1. 打开 [http://localhost:5173](http://localhost:5173)（或让 `./start.sh` 自动打开）。
2. 在「今日任务」里添加，或把行程贴进「AI 智能规划」。
3. 点任务上的「专注」，或在计时器里直接开始。
4. 屏蔽名单里的网站会无法访问，直到结束或倒计时走完。
5. 绛雪会跟着状态变化：你发呆会催，专注时盯着你，暂停会不高兴。

屏蔽名单在 `config/sites.json`（也可用下面的命令行管理）。hosts **必须完全匹配**：`example.com` 和 `www.example.com` 都要写。

---

## 命令行（可选）

和网页用同一套屏蔽。先让 `./start.sh` 建好 `.venv`：

```bash
./.venv/bin/python3 focus_blocker.py          # 带倒计时的专注
./.venv/bin/python3 focus_blocker.py list     # 查看名单
./.venv/bin/python3 focus_blocker.py manage   # 增删站点
./.venv/bin/python3 focus_blocker.py config   # 打开配置
```

给快捷指令 / cron / LaunchAgent 用的无界面模式：

```bash
./.venv/bin/python3 focus_blocker.py --block-only
./.venv/bin/python3 focus_blocker.py --unblock-only
```

---

## macOS 专注模式（可选）

系统专注一开，就屏蔽同一批网站。

**A. 快捷指令自动化**（简单）

快捷指令 → **自动化** → **+** → 个人自动化：

| 时机 | 运行 Shell 脚本 |
|---|---|
| 专注模式 **打开** | `/usr/bin/sudo -n /usr/bin/python3 /绝对路径/Focus-Blocker/focus_blocker.py --block-only` |
| 专注模式 **关闭** | `/usr/bin/sudo -n /usr/bin/python3 /绝对路径/Focus-Blocker/focus_blocker.py --unblock-only` |

把 `/绝对路径` 换成本仓库目录。你常用的每种专注模式都建一套。若走虚拟环境，解释器路径用 `./start.sh visudo-hint` 打出来的那条。

**B. 后台守护进程**

```bash
./.venv/bin/python3 focus_watcher.py            # 前台试跑
./.venv/bin/python3 focus_watcher.py --install  # 装成 LaunchAgent
./.venv/bin/python3 focus_watcher.py --uninstall
```

网页端锁的主人是 `assistant`，守护进程是 `watcher`。任一开启就屏蔽；两个都关才恢复。

---

## 安全机制

- 备份：`/etc/hosts.focus_blocker_backup`
- Ctrl+C、信号、`finally` 都会还原
- 只改 `# >>> FOCUS_BLOCKER_START` 和 `# <<< FOCUS_BLOCKER_END` 之间的行
- 写入幂等，不会重复加条目
- 同时拦 IPv4 和 IPv6

万一崩溃后 hosts 没还原：

```bash
sudo cp /etc/hosts.focus_blocker_backup /etc/hosts
```

**命令行**带倒计时的专注期间，本机还有 [http://127.0.0.1:18999](http://127.0.0.1:18999)。被拦的 HTTPS 站点仍会显示连接失败（无法拦截 TLS）。看剩余时间请用这个地址。

---

## 常见问题

**网站还能打开。** 关掉浏览器的「安全 DNS」/ DNS-over-HTTPS。先用 Safari 验证系统层是否生效。

**每次都要输 sudo。** 用 `./start.sh visudo-hint` 打出的那一行配置 visudo。

**提示没有 Python / npm。** `brew install python@3.12 node`

**`./start.sh` 没权限。** `chmod +x start.sh`

**增删屏蔽站点。** 编辑 `config/sites.json`，或运行 `./.venv/bin/python3 focus_blocker.py manage`。

---

## 许可证

MIT
