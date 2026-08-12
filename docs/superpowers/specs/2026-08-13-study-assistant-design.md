# 沉浸式学习助手 — 设计规格

> 日期：2026-08-13
> 状态：已评审，待实现
> 目标：把现有 Focus Blocker 升级为可规划每日任务的沉浸式学习助手（第一版 MVP）

---

## 1. 背景与目标

现有项目 `Focus-Blocker` 是一个通过修改 `/etc/hosts` 屏蔽娱乐网站的 Python CLI 工具，包含：

- `focus_blocker.py` — 主 CLI，含 Rich TUI 倒计时、站点管理、hosts 备份/恢复、macOS 26 immutable flag 处理
- `focus_server.py` — 本地 HTTP 状态服务器（端口 18999 / 80）
- `focus_watcher.py` — macOS Focus Mode 自动触发守护进程
- `config/sites.json` — 屏蔽站点列表

**升级目标**：变成一个"沉浸式学习助手"，用户每天在 Web 界面规划任务，为每个任务启动专注时段，计时结束自动标记完成，最终（后续迭代）扩展到统计图表与成就系统。

**MVP 范围**：打通「任务 → 专注 → 完成」核心链路。

---

## 2. 关键决策

| 决策点 | 选择 |
|--------|------|
| 产品形态 | Web 界面为主，CLI 降级为后台引擎 |
| 技术路线 | 前后端分离（Python API + Vue 3） |
| 后端框架 | FastAPI |
| 前端框架 | Vue 3 |
| 数据存储 | SQLite（`tasks` + `focus_sessions` 两张表） |
| 计时权威位置 | 后端（避免浏览器标签页休眠导致计时漂移） |
| 前后端通信 | REST + WebSocket（实时推送倒计时/状态） |
| 屏蔽引擎 | 复用现有 `focus_blocker.py`（hosts 逻辑零改动），新增 `--acquire`/`--release` 协调命令，通过 `sudo -n` 调用 |

---

## 3. 系统架构

```
┌─────────────────────┐   WebSocket / REST   ┌──────────────────────┐
│   Vue 3 前端 (web/)  │ ⇄ ───────────────── │  FastAPI 后端 (app/)  │
│   任务清单 · 专注计时 │                      │  权威计时 · 状态机     │
└─────────────────────┘                      └──────────┬───────────┘
                                                        │ SQLite
                                              ┌─────────▼──────────┐
                                              │   tasks / sessions  │
                                              └────────────────────┘
                                                        │
                                                        │ sudo -n (subprocess)
                                              ┌─────────▼──────────┐
                                              │ focus_blocker.py    │
                                              │ 屏蔽引擎 + 协调锁    │
                                              └─────────▲──────────┘
                                                        │ sudo -n
                                              ┌─────────┴──────────┐
                                              │ focus_watcher.py    │
                                              │ 系统 Focus 联动守护   │
                                              └────────────────────┘
```

**定位说明**：`focus_blocker.py` 及其安全逻辑（备份/恢复、signal 处理、immutable flag）保持原样，作为被后端调用的屏蔽引擎；同时新增 `--acquire`/`--release` 协调命令（见第 12 节）。现有 TUI 降级为手动/调试入口，Web 界面是日常唯一入口。`focus_watcher.py` 从直接调用 `--block-only`/`--unblock-only` 改为调用 `--acquire watcher`/`--release watcher`。

---

## 4. 数据模型（SQLite）

### `tasks` 任务表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| title | TEXT | 任务标题 |
| planned_minutes | INTEGER | 预计时长 |
| status | TEXT | `pending` / `in_progress` / `done` |
| sort_order | INTEGER | 排序权重 |
| created_date | TEXT | 所属日期 `YYYY-MM-DD` |
| focus_seconds | INTEGER | 实际专注秒数（累计） |
| completed_at | TEXT | 完成时间 |

### `focus_sessions` 专注会话表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| task_id | INTEGER FK | 可空（自由专注） |
| start_time | TEXT | 开始时间 |
| end_time | TEXT | 结束时间 |
| duration_seconds | INTEGER | 实际时长 |
| completed | BOOL | 是否自然结束（非中途打断） |

---

## 5. API 设计

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks?date=2026-08-13` | 今日任务列表 |
| POST | `/api/tasks` | 创建任务 |
| PATCH | `/api/tasks/{id}` | 改标题/时长/状态/排序 |
| DELETE | `/api/tasks/{id}` | 删除任务 |

### 会话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sessions/start` | 启动专注（传 task_id + 分钟数）→ 屏蔽 |
| POST | `/api/sessions/stop` | 结束专注 → 解除屏蔽 → 落库 |
| GET | `/api/sessions/current` | 当前会话状态 |

### 实时

| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/ws` | 推送倒计时 / 状态变化 |

---

## 6. 数据流（核心链路）

1. 打开界面 → `GET /api/tasks` 加载今日任务
2. 点「开始专注」→ `POST /api/sessions/start` → 后端 `sudo -n focus_blocker.py --block-only` → 记录 `start_time` → WS 广播
3. 前端 WS 收到倒计时，实时渲染
4. 计时结束 / 点「停止」→ `POST /api/sessions/stop` → `sudo -n ... --unblock-only` → 计算时长写入 `focus_sessions` → 更新 task 状态 → WS 广播

---

## 7. 状态转换规则

**任务状态机**：`pending → in_progress → done`（可回退 `in_progress → pending`）

**会话结束 → 任务状态**：
- 自然计时结束（completed=true）→ 任务自动 `done`
- 中途手动停止（completed=false）→ 任务保持 `in_progress`，由用户决定是否完成

**专注时长累计**：每次结束会话，把 `duration_seconds` 累加到对应 task 的 `focus_seconds`（自由专注的会话不计入任何任务）。

---

## 8. 错误处理

- **sudo 失败**（passwordless 未配置）→ 后端返回明确错误（HTTP 4xx + 提示），会话不启动
- **屏蔽引擎异常** → 不进入专注状态，回滚，前端提示
- **WS 断线** → 前端自动重连，重连后 `GET /api/sessions/current` 对齐状态

---

## 9. 目录结构（规划）

```
Focus-Blocker/
├── app/                      # FastAPI 后端（新增）
│   ├── main.py               # 入口 + 路由挂载
│   ├── db.py                 # SQLite 连接 + 建表
│   ├── models.py             # Pydantic 模型
│   ├── blocker.py            # 封装 sudo 调用 focus_blocker.py
│   ├── session_manager.py    # 会话状态机（权威计时）
│   └── routers/
│       ├── tasks.py
│       └── sessions.py
├── web/                      # Vue 3 前端（新增）
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── TaskList.vue
│   │   │   └── FocusTimer.vue
│   │   ├── api/              # axios 封装 + WS 客户端
│   │   └── main.js
│   └── ...
├── focus_blocker.py          # 屏蔽引擎 + 协调锁（hosts 逻辑不改，新增 --acquire/--release）
├── focus_server.py           # 现有（后续迭代决定去留）
├── focus_watcher.py          # 改动：改调用 --acquire watcher / --release watcher
└── config/
    ├── sites.json            # 现有
    └── block_lock.json       # 新增：共享锁
```

---

## 10. 非目标（本 MVP 不做）

- 统计图表 / 成就系统 / 每日回顾（后续迭代，呼应 C 方向）
- 课程表式的自动时段调度
- 用户账号 / 多设备同步
- 重写或删除现有 `focus_blocker.py` 的屏蔽逻辑

---

## 11. 测试策略

- 后端单元测试：任务 CRUD、会话状态机、专注时长累计
- 屏蔽引擎调用：mock `subprocess` 验证命令参数与失败回滚
- 前端：聚焦核心交互（创建任务 → 启动 → 结束）的冒烟验证

---

## 12. 与系统 Focus 勿扰模式的协调机制（共享锁）

### 问题

存在两条独立的屏蔽触发路径，若不加协调会互相覆盖：

- `focus_watcher.py` 检测系统 Focus 开关 → 触发屏蔽/解除
- 学习助手启动/结束专注 → 触发屏蔽/解除

典型冲突：学习助手启动专注并屏蔽网站，但系统 Focus 未开启，watcher 检测到「Focus 关 + hosts 有屏蔽条目」→ 误判为残留 → 解除学习助手的屏蔽。

### 方案：共享锁（引用计数）

新增 `config/block_lock.json`：

```json
{ "watcher": false, "assistant": false }
```

**核心规则**：网站处于屏蔽状态 ⟺ `watcher` 或 `assistant` 任一为 `true`。只有两个占用者都释放时才真正解除屏蔽。

### 命令（集中在 `focus_blocker.py`）

| 命令 | 动作 |
|------|------|
| `--acquire watcher` | `watcher=true`，若未屏蔽则屏蔽 |
| `--release watcher` | `watcher=false`，若 assistant 仍占用则保持屏蔽，否则解除 |
| `--acquire assistant` | `assistant=true`，若未屏蔽则屏蔽 |
| `--release assistant` | `assistant=false`，若 watcher 仍占用则保持屏蔽，否则解除 |

### 各组件职责

| 组件 | 改动 |
|------|------|
| `focus_blocker.py` | 新增 `--acquire`/`--release` 命令 + 锁文件读写；`block_sites`/`restore_hosts` 等 hosts 操作逻辑零改动 |
| `focus_watcher.py` | 原 `--block-only`/`--unblock-only` 调用改为 `--acquire watcher`/`--release watcher` |
| 学习助手后端 | 启动专注调 `--acquire assistant`，结束调 `--release assistant` |

### 锁文件一致性

- 锁文件读写需原子（先读、改、写回）；若锁文件损坏或缺失，默认 `{watcher:false, assistant:false}` 并重建
- 屏蔽/解除动作仍以 hosts 文件的 `# >>> FOCUS_BLOCKER_START` 标记段为最终事实来源，锁文件仅用于"是否该解除"的决策
