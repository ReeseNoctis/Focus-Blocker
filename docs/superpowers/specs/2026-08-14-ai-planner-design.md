# AI 智能任务规划 — 设计规格

> 日期：2026-08-14
> 状态：已评审，待实现
> 目标：为沉浸式学习助手新增「AI 智能规划」——粘贴外部 AI 生成的行程文本，自动拆解成任务清单（任务名 + 持续时长）。

---

## 1. 背景与目标

用户日常使用场景：在**其他网页 AI**（ChatGPT / Claude / DeepSeek 网页等）生成一天的学习行程，然后把那段文本**粘贴进学习助手**，由学习助手自动识别并拆解成一条条任务，用户只需点「启动」开始专注。

当前学习助手已具备任务 CRUD、专注计时、屏蔽引擎等能力（见 `docs/superpowers/specs/2026-08-13-study-assistant-design.md`）。本功能是**新增**的 AI 规划入口，复用现有任务系统。

---

## 2. 关键决策

| 决策点 | 选择 |
|--------|------|
| AI 接入方式 | 真调大模型 API（智能理解任意格式文本，不做固定格式解析） |
| AI 服务 | DeepSeek（OpenAI 兼容接口，模型 `deepseek-chat`） |
| API Key 存储 | 本地 `config/ai.json`，git 忽略，不提交 |
| 输入交互 | 文本框 + 「智能规划」按钮 |
| 任务字段 | 只保留「任务名 + 持续时长」，**无开始时间** |
| 交互流程 | 先预览（可编辑标题/时长/删除）→ 确认创建 |
| 数据落库 | AI 不直接写库，只返回拆解结果；前端确认后复用现有 `POST /api/tasks` 逐条创建 |
| HTTP 客户端 | 复用现有 `httpx`，零新增依赖 |

---

## 3. 系统架构（新增部分）

```
前端 Vue 3
  └─ AiPlanner.vue（输入框 + 任务预览面板）
        │  POST /api/ai/plan  { text: "...", date: "YYYY-MM-DD" }
        ▼
后端 FastAPI
  └─ app/routers/ai.py（新）
        │
        ├─ 读 config/ai.json 获取 DeepSeek key
        ├─ 调 app/ai_client.py 构造 prompt、请求 DeepSeek
        ├─ 解析 AI 返回的 JSON → [{title, planned_minutes}, ...]
        └─ 返回给前端（不落库）
        │
        ▼
前端预览 → 用户确认 → 复用现有 POST /api/tasks 逐条创建 → 刷新任务列表
```

**关键设计**：AI 只负责「理解文本 + 拆解」，不直接写数据库。拆解结果先返回前端预览，用户确认后由前端调用现有 `POST /api/tasks` 逐条创建，复用现有任务 CRUD，不新增重复的落库逻辑。

---

## 4. 数据模型

**任务表不变**。AI 拆解结果是中间产物 `[{title, planned_minutes}]`，最终仍走现有 `tasks` 表。

`planned_minutes` 由 AI 建议，用户在预览阶段可改。

---

## 5. 新增文件

```
config/ai.json                      # 用户填 DeepSeek key（已 git 忽略）
app/ai_client.py                    # 封装 DeepSeek 调用 + prompt + JSON 解析
app/routers/ai.py                   # POST /api/ai/plan 路由
web/src/components/AiPlanner.vue    # 输入框 + 预览面板
```

### `config/ai.json` 结构

```json
{
  "deepseek_api_key": "sk-...",
  "model": "deepseek-chat"
}
```

### `app/ai_client.py` 职责

- `plan_tasks(text: str) -> list[dict]`：读取 key、构造 prompt、请求 DeepSeek、解析返回 JSON，返回 `[{"title": str, "planned_minutes": int}, ...]`。
- prompt 要求 AI 输出**纯 JSON 数组**（不带 markdown 代码块），每个元素含 `title`（任务名）和 `planned_minutes`（建议专注分钟数，正整数，默认 60）。
- 容错解析：AI 返回若包在 ```` ```json ... ``` ```` 代码块里，先剥离代码块再 `json.loads`。

### `app/routers/ai.py`

- `POST /api/ai/plan`，body `{text: str, date?: str}` → `200 {tasks: [{title, planned_minutes}]}`。
- 无 Key / 配置缺失 → 500 + 明确提示。
- DeepSeek 调用失败 → 502 + 错误信息。
- AI 返回非法 JSON → 400 + 提示重试或简化输入。

### `web/src/components/AiPlanner.vue`

- 文本框 + 「智能规划」按钮。
- 预览列表：每项可编辑标题、编辑时长、删除。
- 「确认创建」按钮：逐条调用现有 `POST /api/tasks`，完成后刷新任务列表并清空预览。
- 「全部删除」/「取消」可清空预览。

---

## 6. 数据流

1. 用户粘贴行程文本 → 点「智能规划」。
2. 前端 `POST /api/ai/plan {text}` → 后端 `ai.py`。
3. 后端读 key → 调 DeepSeek（prompt 要求返回 JSON 数组）→ 解析 → 返回 `[{title, planned_minutes}]`。
4. 前端显示预览列表，每项可改标题/时长/删除。
5. 用户点「确认创建」→ 前端循环 `POST /api/tasks` 逐条创建 → 刷新任务列表 → 清空预览。

---

## 7. 错误处理

| 场景 | 处理 |
|------|------|
| 无 Key / 配置缺失 | 后端 500 + 提示「请在 config/ai.json 填入 DeepSeek key」 |
| DeepSeek 调用失败（网络/额度/key 错误） | 后端 502 + 错误信息，前端显示 |
| AI 返回非法 JSON | 后端 400 + 提示「AI 返回格式异常，请重试或简化输入」 |
| 前端预览为空（AI 返回空数组） | 提示「未能识别出任务，请调整输入」 |

---

## 8. 非目标（本功能不做）

- 对话式多轮规划（只做单次文本框输入）。
- 任务带开始/结束时间点（只保留持续时长）。
- AI 直接写数据库（坚持「预览确认后由前端创建」）。
- 规划历史、模板保存、偏好学习。

---

## 9. 测试策略

- 后端单元测试：mock DeepSeek HTTP 调用，验证 prompt 构造、JSON 解析（含代码块剥离）、错误分支（无 Key / 调用失败 / 非法 JSON）。
- 前端：聚焦「输入 → 预览 → 确认创建」的冒烟验证。
- 依赖注入：`ai_client` 的 HTTP 请求可 monkeypatch，测试不真实调用 DeepSeek。
