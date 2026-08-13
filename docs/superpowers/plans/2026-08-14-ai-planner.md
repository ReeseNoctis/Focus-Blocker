# AI 智能任务规划 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为学习助手新增 AI 智能规划——粘贴行程文本，自动拆解成任务清单（任务名 + 持续时长），预览确认后创建为今日任务。

**Architecture:** 前端 `AiPlanner.vue` 提交文本到后端 `POST /api/ai/plan`；后端 `app/ai_client.py` 用 `httpx` 调 DeepSeek（OpenAI 兼容，`deepseek-chat`），prompt 要求返回纯 JSON 数组；后端解析后返回 `[{title, planned_minutes}]` 不落库；前端预览可编辑，确认后复用现有 `POST /api/tasks` 逐条创建。

**Tech Stack:** Vue 3（前端）、FastAPI + httpx（后端）、DeepSeek `deepseek-chat`（AI）。

## Global Constraints

- **Python 版本**：`/Users/liuzishan/Focus-Blocker/.venv/bin/python3.12`（用 `./.venv/bin/python3.12 -m pytest` 跑测试）。
- **零新增依赖**：调 DeepSeek 用已安装的 `httpx`（0.28.1），不 `pip install openai`。
- **AI 不写库**：`/api/ai/plan` 只返回 `{tasks: [...]}`，不 INSERT。落库由前端复用现有 `POST /api/tasks` 逐条完成。
- **简化（偏离 spec 的 `date` 字段）**：AI planner 只规划**今日**任务。`/api/ai/plan` 的 body 只有 `{text}`，无 `date`；落库走现有 `create_task`（内部 `date.today()`）。
- **默认时长**：AI 建议 `planned_minutes` 默认 **60** 分钟（不是 25）。
- **Key 存储**：`config/ai.json`，git 忽略（`config/` 下的 `.json` 已部分忽略，但 `ai.json` 需显式加入 `.gitignore`，见 Task 4）。
- **模型**：`deepseek-chat`，可从 `config/ai.json` 的 `model` 字段覆盖，默认 `deepseek-chat`。
- **API 端点**：`https://api.deepseek.com/chat/completions`。
- **界面语言**：中文，暗色主题，emoji 风格，与现有组件一致。
- **无 axios/pinia/vue-router**：前端用原生 `fetch`。

---

### Task 1: AI 客户端 — DeepSeek 调用 + JSON 解析

**Files:**
- Create: `app/ai_client.py`
- Test: `tests/test_ai_client.py`

**Interfaces:**
- Produces:
  - `app.ai_client.plan_tasks(text: str) -> list[dict]` — 返回 `[{"title": str, "planned_minutes": int}, ...]`。
  - `app.ai_client._extract_json(content: str) -> list` — 纯函数，剥离 markdown 代码块后 `json.loads`，供测试。
  - `app.ai_client._load_config() -> dict` — 读 `config/ai.json`，缺失/损坏返回 `{}`。
  - 常量 `API_URL`、`DEFAULT_MODEL`、`CONFIG_FILE`。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_ai_client.py`：

```python
import app.ai_client as ac


def test_extract_json_plain(monkeypatch):
    assert ac._extract_json('[{"title": "a", "planned_minutes": 60}]') == [
        {"title": "a", "planned_minutes": 60}
    ]


def test_extract_json_strips_code_fence(monkeypatch):
    content = '```json\n[{"title": "b", "planned_minutes": 45}]\n```'
    assert ac._extract_json(content) == [{"title": "b", "planned_minutes": 45}]


def test_extract_json_raises_on_non_array(monkeypatch):
    import pytest
    with pytest.raises(ValueError):
        ac._extract_json('{"not": "an array"}')


def test_plan_tasks_normalizes_and_filters(monkeypatch):
    # Fake the HTTP layer so no real DeepSeek call happens.
    captured = {}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content":
                '[{"title":"学英语","planned_minutes":"90"},'
                '{"title":"","planned_minutes":30},'
                '{"title":"刷题","planned_minutes":9999}]'}}]}

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResp()

    monkeypatch.setattr(ac.httpx, "post", fake_post)
    monkeypatch.setattr(ac, "_load_config", lambda: {"deepseek_api_key": "sk-test"})

    tasks = ac.plan_tasks("学英语,刷题")
    assert tasks == [
        {"title": "学英语", "planned_minutes": 90},
        {"title": "刷题", "planned_minutes": 720},  # clamped to max
    ]
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "deepseek-chat"


def test_plan_tasks_raises_without_key(monkeypatch):
    import pytest
    monkeypatch.setattr(ac, "_load_config", lambda: {})
    with pytest.raises(RuntimeError):
        ac.plan_tasks("anything")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python3.12 -m pytest tests/test_ai_client.py -v`
Expected: 全部 FAIL（`ModuleNotFoundError: No module named 'app.ai_client'`）。

- [ ] **Step 3: 写实现**

创建 `app/ai_client.py`：

```python
"""DeepSeek client for AI task planning."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "ai.json"
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_MINUTES = 60
MAX_MINUTES = 720

_PROMPT = """你是学习任务规划助手。用户会给你一段学习/工作行程描述，请拆解成任务清单。

要求：
1. 只输出 JSON 数组，不要任何其他文字或 markdown 代码块。
2. 每个元素是对象，含两个字段：
   - "title": 任务名（简洁、具体、可直接执行）
   - "planned_minutes": 建议专注时长（正整数分钟，默认 60）
3. 合并同类小任务，拆解过大任务，使每个任务时长在 15-120 分钟之间。
4. 保持原意的先后顺序。

用户输入：
{text}

请输出 JSON 数组："""


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _extract_json(content: str) -> list:
    """Parse a JSON array from DeepSeek output, tolerating code fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("expected a JSON array")
    return data


def plan_tasks(text: str) -> list[dict]:
    """Return [{"title", "planned_minutes"}] for the given free-text schedule."""
    cfg = _load_config()
    key = cfg.get("deepseek_api_key")
    if not key:
        raise RuntimeError("missing DeepSeek API key (config/ai.json)")
    model = cfg.get("model") or DEFAULT_MODEL

    prompt = _PROMPT.format(text=text)
    resp = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "stream": False,
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text[:200]}")

    content = resp.json()["choices"][0]["message"]["content"]
    tasks: list[dict] = []
    for item in _extract_json(content):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        try:
            minutes = int(item.get("planned_minutes", DEFAULT_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_MINUTES
        minutes = max(1, min(minutes, MAX_MINUTES))
        tasks.append({"title": title, "planned_minutes": minutes})
    return tasks
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_ai_client.py -v`
Expected: 5 passed。

- [ ] **Step 5: 提交**

```bash
git add app/ai_client.py tests/test_ai_client.py
git commit -m "feat: AI client for DeepSeek task planning"
```

---

### Task 2: AI 路由 — POST /api/ai/plan

**Files:**
- Create: `app/routers/ai.py`
- Modify: `app/main.py`（挂载 ai 路由）
- Test: `tests/test_ai.py`

**Interfaces:**
- Consumes: `plan_tasks`（Task 1）。
- Produces:
  - `POST /api/ai/plan` body `{text: str}` → `200 {tasks: [{title, planned_minutes}]}`。
  - 错误分支：无 Key → `500`（`"请在 config/ai.json 填入 DeepSeek API Key"`）；DeepSeek 调用失败 → `502`；非法 JSON → `400`。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_ai.py`：

```python
from fastapi.testclient import TestClient
import app.ai_client as ac


def _client(monkeypatch, plan_tasks):
    monkeypatch.setattr(ac, "plan_tasks", plan_tasks)
    from app.main import app
    return TestClient(app)


def test_plan_returns_tasks(monkeypatch):
    def fake(text):
        return [{"title": "学英语", "planned_minutes": 60}]
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "学英语"})
    assert r.status_code == 200
    assert r.json() == {"tasks": [{"title": "学英语", "planned_minutes": 60}]}


def test_plan_missing_key_returns_500(monkeypatch):
    def fake(text):
        raise RuntimeError("missing DeepSeek API key")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 500


def test_plan_api_error_returns_502(monkeypatch):
    def fake(text):
        raise RuntimeError("DeepSeek API error 401")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 502


def test_plan_bad_json_returns_400(monkeypatch):
    def fake(text):
        raise ValueError("bad json")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 400
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python3.12 -m pytest tests/test_ai.py -v`
Expected: 全部 FAIL（`ModuleNotFoundError: No module named 'app.routers.ai'`）。

- [ ] **Step 3: 写实现**

创建 `app/routers/ai.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai_client import plan_tasks

router = APIRouter(prefix="/api/ai", tags=["ai"])


class PlanRequest(BaseModel):
    text: str


class PlanTask(BaseModel):
    title: str
    planned_minutes: int


class PlanResponse(BaseModel):
    tasks: list[PlanTask]


@router.post("/plan", response_model=PlanResponse)
def ai_plan(body: PlanRequest):
    try:
        tasks = plan_tasks(body.text)
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith("missing"):
            raise HTTPException(500, "请在 config/ai.json 填入 DeepSeek API Key")
        raise HTTPException(502, f"DeepSeek 调用失败: {msg}")
    except ValueError:
        raise HTTPException(400, "AI 返回格式异常，请重试或简化输入")
    return {"tasks": tasks}
```

修改 `app/main.py`，把 `from app.routers import tasks, sessions` 改为 `from app.routers import ai, tasks, sessions`，并在文件末尾 `app.include_router(sessions.router)` 之后新增 `app.include_router(ai.router)`。

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_ai.py -v`
Expected: 4 passed。

- [ ] **Step 5: 提交**

```bash
git add app/routers/ai.py app/main.py tests/test_ai.py
git commit -m "feat: AI plan endpoint POST /api/ai/plan"
```

---

### Task 3: 前端 — AiPlanner 组件

**Files:**
- Create: `web/src/components/AiPlanner.vue`
- Modify: `web/src/App.vue`（挂载 AiPlanner）

**Interfaces:**
- Consumes: `POST /api/ai/plan`（Task 2）、`POST /api/tasks`（现有）、`fetchTasks`（现有 `web/src/api/client.js`）。
- Produces: `AiPlanner` 组件，`emits: ['created']`（创建成功后通知父组件刷新任务列表）。

- [ ] **Step 1: 写 AiPlanner 组件**

创建 `web/src/components/AiPlanner.vue`：

```vue
<script setup>
import { ref } from 'vue'
import { createTask } from '../api/client'

const emit = defineEmits(['created'])

const text = ref('')
const tasks = ref([])      // 预览列表 [{title, planned_minutes}]
const loading = ref(false)
const error = ref('')

async function plan() {
  if (!text.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/ai/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value.trim() }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    const data = await res.json()
    tasks.value = data.tasks || []
    if (tasks.value.length === 0) error.value = '未能识别出任务，请调整输入'
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function updateTitle(i, v) { tasks.value[i].title = v }
function updateMinutes(i, v) {
  const n = parseInt(v, 10)
  tasks.value[i].planned_minutes = Number.isFinite(n) && n > 0 ? n : 60
}
function removeTask(i) { tasks.value.splice(i, 1) }
function clearAll() { tasks.value = []; text.value = ''; error.value = '' }

async function confirm() {
  for (const t of tasks.value) {
    await createTask(t.title, t.planned_minutes)
  }
  emit('created')
  clearAll()
}
</script>

<template>
  <section class="ai-planner">
    <h2>🤖 AI 智能规划</h2>
    <p class="hint">粘贴其他 AI 生成的行程，自动拆解成任务</p>
    <textarea
      v-model="text"
      rows="4"
      placeholder="例如：上午学英语 90 分钟，然后刷 3 道 LeetCode，下午复习高数"
    ></textarea>
    <button class="plan-btn" :disabled="loading" @click="plan">
      {{ loading ? '规划中…' : '✨ 智能规划' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="tasks.length" class="preview">
      <div v-for="(t, i) in tasks" :key="i" class="preview-row">
        <input v-model="t.title" class="p-title" @input="updateTitle(i, $event.target.value)" />
        <input
          v-model.number="t.planned_minutes"
          type="number"
          min="1"
          class="p-mins"
          @input="updateMinutes(i, $event.target.value)"
        />
        <span class="p-unit">分钟</span>
        <button class="del" @click="removeTask(i)">✕</button>
      </div>
      <div class="preview-actions">
        <button class="confirm-btn" @click="confirm">✅ 确认创建（{{ tasks.length }} 项）</button>
        <button class="cancel-btn" @click="clearAll">清空</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ai-planner { max-width: 640px; margin: 0 auto 24px; padding: 20px; border: 1px solid #333; border-radius: 12px; }
.hint { color: #888; font-size: 13px; margin-top: 0; }
textarea { width: 100%; box-sizing: border-box; padding: 10px; background: #111; color: #eee; border: 1px solid #333; border-radius: 8px; font-family: inherit; resize: vertical; }
.plan-btn { margin-top: 10px; padding: 8px 16px; cursor: pointer; }
.error { color: #e88; font-size: 14px; }
.preview { margin-top: 16px; }
.preview-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.p-title { flex: 1; padding: 6px; background: #111; color: #eee; border: 1px solid #333; border-radius: 6px; }
.p-mins { width: 64px; padding: 6px; background: #111; color: #eee; border: 1px solid #333; border-radius: 6px; }
.p-unit { color: #888; font-size: 13px; }
.del { color: #c66; border: none; background: none; cursor: pointer; }
.preview-actions { margin-top: 12px; display: flex; gap: 10px; }
.confirm-btn { padding: 8px 16px; cursor: pointer; }
.cancel-btn { padding: 8px 16px; cursor: pointer; color: #999; }
</style>
```

- [ ] **Step 2: 挂载到 App.vue**

当前 `web/src/App.vue` 内容已知（见下）。把它的 `<script setup>` 和 `<template>` 改为：

```vue
<script setup>
import { ref } from 'vue'
import TaskList from './components/TaskList.vue'
import FocusTimer from './components/FocusTimer.vue'
import AiPlanner from './components/AiPlanner.vue'

function localDateStr() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
const today = localDateStr()
const activeTask = ref(null)
const listVersion = ref(0)

function onFinished() {
  activeTask.value = null
  listVersion.value++  // refresh the task list so status/focus_seconds update
}
</script>

<template>
  <main>
    <h1>🧘 沉浸式学习助手</h1>
    <AiPlanner @created="listVersion++" />
    <FocusTimer :task="activeTask" @finished="onFinished" />
    <TaskList :date="today" :refresh-key="listVersion" @start="(t) => (activeTask = t)" />
  </main>
</template>
```

`<style>` 块保持不变（暗色主题）。`AiPlanner` 插在 `<h1>` 之后、`<FocusTimer>` 之前。

- [ ] **Step 3: 冒烟验证构建**

Run: `cd web && npm run build`
Expected: 构建成功，无报错。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/AiPlanner.vue web/src/App.vue
git commit -m "feat: AI planner component with preview and confirm"
```

---

### Task 4: 配置与 README + 端到端验收

**Files:**
- Modify: `.gitignore`（加 `config/ai.json`）
- Modify: `README.md`（补 AI 规划说明）
- Create: `config/ai.json.example`（模板，不含真实 key）

**Interfaces:**
- Consumes: 全部已有组件。

- [ ] **Step 1: 忽略真实 key 文件 + 提供模板**

在 `.gitignore` 的「Runtime files」段落新增一行：

```
config/ai.json
```

创建 `config/ai.json.example`（提交此模板，不含真实 key）：

```json
{
  "deepseek_api_key": "sk-在此填入你的 key",
  "model": "deepseek-chat"
}
```

- [ ] **Step 2: 更新 README**

在 README 的「🧘 学习助手（Web 界面）」章节末尾追加：

```markdown
### 🤖 AI 智能规划

粘贴其他 AI 生成的行程文本，自动拆解成任务清单。

1. 复制 `config/ai.json.example` 为 `config/ai.json`，填入你的 DeepSeek API Key：
   ```bash
   cp config/ai.json.example config/ai.json
   # 编辑 config/ai.json，把 sk-... 换成真实 key
   ```
2. 打开学习助手，在「AI 智能规划」输入框粘贴行程，点「✨ 智能规划」。
3. 预览并微调任务（可改标题/时长/删除），点「✅ 确认创建」。

> `config/ai.json` 已被 git 忽略，不会提交你的 key。
```

- [ ] **Step 3: 端到端验收**

```bash
# 1. 配置真实 key（用户手动做，实现者不代填）
# cp config/ai.json.example config/ai.json  然后填入真实 key

# 2. 起后端
./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000

# 3. 起前端
cd web && npm run dev

# 4. 浏览器:粘贴行程 → 智能规划 → 预览 → 确认创建 → 任务列表出现新任务
```

Expected: 能真实调用 DeepSeek 拆解文本，任务成功创建（需用户提供真实 key；若无 key 则验证「无 key 报错提示」路径）。

- [ ] **Step 4: 提交**

```bash
git add .gitignore README.md config/ai.json.example
git commit -m "docs: AI planner config template and usage"
```

---

## 任务依赖图

```
Task 1（ai_client）→ Task 2（路由）→ Task 3（前端组件）→ Task 4（配置 + 验收）
```

建议顺序：1 → 2 → 3 → 4。
