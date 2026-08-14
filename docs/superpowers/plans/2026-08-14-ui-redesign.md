# 学习助手 UI 视觉改版 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把学习助手网页从深色主题改成清新浅色（樱花粉紫系），加入原创 SVG 二次元插画（白发红眸红装古风高马尾少女），去除所有 emoji。

**Architecture:** 纯前端 CSS + Vue scoped style 改造，不引入 UI 库、不改后端。全局配色用 CSS 变量集中定义在 `style.css`；三处 SVG 插画（背景花瓣、顶部横幅、吉祥物头像）作为资产放在 `web/src/assets/`；各组件改配色、去 emoji。

**Tech Stack:** Vue 3 + 原生 CSS + 内联/文件 SVG。

## Global Constraints

- **只改前端**：`web/src/` 下的文件。**绝不**改动 `app/`、`tests/`、`focus_blocker.py`、`start.sh` 等后端/脚本。
- **不引入任何 UI 库**（Element/Vant/Tailwind 等），不引入 AI 生成图或网图，不新增 npm 依赖。
- **配色固定值**（樱花粉紫系，逐字使用）：
  - 页面背景 `#FAF7F2`（暖白）
  - 主色 `#F5A0B0`（樱花粉）
  - 辅色 `#B8A7E0`（淡紫）
  - 强调 `#E8899A`（深粉）
  - 卡片背景 `#FFFFFF`（白）
  - 卡片边框 `#F0E6E8`（极淡粉）
  - 正文文字 `#4A4458`（深灰，不用纯黑）
  - 次要文字 `#9A92A8`（灰紫）
  - 吉祥物红装 `#C8474F`（朱红，仅插画内使用）
- **吉祥物特征统一**（三处插画同形象）：白发、红眸、红色交领古装、高马尾、简洁扁平圆润线条。
- **去除所有 emoji**：标题、按钮、列表里所有 emoji（🧘🤖📋✨▶⏸🛑✓↩✕ 等）全部换成纯文字或中性符号（如「专注」「暂停」「结束」「完成」）。
- **验证手段**：`cd web && npm run build` 必须成功；后端无测试变化。视觉冒烟 = 启动前后端后浏览器目测。
- **不要删除 `HelloWorld.vue`**（未使用，但不属本改版范围）；只清理 `style.css` 里它的死样式。

---

### Task 1: 全局主题 —— CSS 变量 + App.vue 骨架

**Files:**
- Modify: `web/src/style.css`（整体重写）
- Modify: `web/src/App.vue`

**Interfaces:**
- Produces（后续任务依赖的 CSS 变量名，必须与之一致）：
  - `--bg`、`--card`、`--border`、`--text`、`--text-dim`、`--primary`、`--primary-deep`、`--secondary`、`--red`
  - `App.vue` 模板结构：`<main>` 内含 `<div class="hero">`（横幅插画占位）+ `<h1>` + 三个组件挂载点。

- [ ] **Step 1: 重写 style.css**

把 `web/src/style.css` 整体替换为（去掉 HelloWorld 死样式和 `prefers-color-scheme: dark` 深色段，统一为樱花粉紫变量）：

```css
:root {
  --bg: #FAF7F2;
  --card: #FFFFFF;
  --border: #F0E6E8;
  --text: #4A4458;
  --text-dim: #9A92A8;
  --primary: #F5A0B0;
  --primary-deep: #E8899A;
  --secondary: #B8A7E0;
  --red: #C8474F;
  --shadow: rgba(184, 167, 224, 0.18) 0 8px 24px -6px;

  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;

  color: var(--text);
  background: var(--bg);
  font: 16px/1.6 var(--sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* { box-sizing: border-box; }

body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--sans); }

h1, h2 { color: var(--text); font-weight: 600; }
h1 { font-size: 30px; letter-spacing: -0.5px; margin: 16px 0 4px; }
h2 { font-size: 20px; margin: 0 0 12px; }

button {
  cursor: pointer;
  border: none;
  border-radius: 10px;
  padding: 9px 18px;
  font-size: 15px;
  font-family: inherit;
  background: var(--primary);
  color: #fff;
  transition: background 0.15s ease, transform 0.05s ease;
}
button:hover { background: var(--primary-deep); }
button:active { transform: translateY(1px); }

button.secondary {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
}
button.secondary:hover { background: var(--border); }

input, textarea {
  font-family: inherit;
  font-size: 15px;
  color: var(--text);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 12px;
  outline: none;
}
input:focus, textarea:focus { border-color: var(--primary); }
```

- [ ] **Step 2: 改造 App.vue**

把 `web/src/App.vue` 的 `<template>` 和 `<style>` 改为（`<script setup>` 逻辑不动）：

```vue
<template>
  <main>
    <div class="hero">
      <img class="banner" src="./assets/banner-girl.svg" alt="学习少女插画" />
    </div>
    <h1>沉浸式学习助手</h1>
    <AiPlanner @created="listVersion++" />
    <FocusTimer :task="activeTask" @finished="onFinished" />
    <TaskList :date="today" :refresh-key="listVersion" @start="(t) => (activeTask = t)" />
  </main>
</template>

<style scoped>
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}
.hero { text-align: center; margin-bottom: 8px; }
.banner {
  width: 100%;
  max-width: 560px;
  border-radius: 16px;
  display: block;
  margin: 0 auto;
}
h1 {
  text-align: center;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
</style>
```

- [ ] **Step 3: 构建验证**

Run: `cd web && npm run build`
Expected: 构建成功（`banner-girl.svg` 尚不存在会构建报错——这是预期，Task 2 会创建它；若构建因缺文件失败，属正常，继续 Task 2 后重验）。

- [ ] **Step 4: 提交**

```bash
git add web/src/style.css web/src/App.vue
git commit -m "feat: sakura-pink light theme (global CSS vars + App shell)"
```

---

### Task 2: SVG 插画资产 —— 背景花瓣 + 横幅 + 吉祥物头像

**Files:**
- Create: `web/src/assets/bg-petals.svg`
- Create: `web/src/assets/banner-girl.svg`
- Create: `web/src/assets/avatar-girl.svg`

**Interfaces:**
- Produces（后续任务引用的资产路径）：
  - `./assets/bg-petals.svg`（背景花瓣，App.vue 用 `background-image` 引用）
  - `./assets/banner-girl.svg`（顶部横幅，App.vue `<img>` 引用）
  - `./assets/avatar-girl.svg`（吉祥物头像，FocusTimer.vue 引用）

- [ ] **Step 1: 创建吉祥物头像 avatar-girl.svg**

吉祥物：白发、红眸、红色交领古装、高马尾、简洁扁平圆润。写一个 200×200 的圆形头像 SVG：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <clipPath id="circle"><circle cx="100" cy="100" r="100"/></clipPath>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#F5A0B0"/>
      <stop offset="1" stop-color="#B8A7E0"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#circle)">
    <rect width="200" height="200" fill="url(#bg)"/>
    <!-- 白色头发（含高马尾，画在脸部之后、衣领之上） -->
    <ellipse cx="100" cy="72" rx="46" ry="40" fill="#F7F5F8"/>
    <!-- 高马尾（向后甩出） -->
    <path d="M118 60 Q150 40 158 74 Q160 92 144 96 Q130 98 122 82 Z" fill="#F7F5F8"/>
    <path d="M120 62 Q146 46 154 76 Q156 92 142 95" fill="none" stroke="#DCD6E2" stroke-width="2"/>
    <!-- 脸 -->
    <ellipse cx="100" cy="86" rx="34" ry="32" fill="#FDEBDD"/>
    <!-- 刘海 -->
    <path d="M66 72 Q78 50 100 52 Q124 52 134 74 Q124 60 100 62 Q78 62 66 72 Z" fill="#F7F5F8"/>
    <!-- 红眸 -->
    <circle cx="86" cy="88" r="4.5" fill="#C8474F"/>
    <circle cx="114" cy="88" r="4.5" fill="#C8474F"/>
    <circle cx="86.8" cy="86.6" r="1.4" fill="#fff"/>
    <circle cx="114.8" cy="86.6" r="1.4" fill="#fff"/>
    <!-- 嘴 -->
    <path d="M94 100 Q100 105 106 100" fill="none" stroke="#D88A8F" stroke-width="2" stroke-linecap="round"/>
    <!-- 红色交领古装 -->
    <path d="M64 120 Q100 106 136 120 L132 152 Q100 164 68 152 Z" fill="#C8474F"/>
    <path d="M88 118 L100 132 L112 118 Q100 124 88 118 Z" fill="#A2363E"/>
    <!-- 发簪（古风元素） -->
    <line x1="128" y1="56" x2="146" y2="48" stroke="#E8899A" stroke-width="3" stroke-linecap="round"/>
    <circle cx="147" cy="47" r="3" fill="#E8899A"/>
  </g>
  <circle cx="100" cy="100" r="99" fill="none" stroke="#F0E6E8" stroke-width="2"/>
</svg>
```

- [ ] **Step 2: 创建顶部横幅 banner-girl.svg**

横向 1200×300 场景：暖白渐变天空 + 樱花，画面中一个简洁扁平少女（同一形象）坐在樱花树下看书：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300" width="1200" height="300">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FDF5F4"/>
      <stop offset="0.6" stop-color="#FAF0F6"/>
      <stop offset="1" stop-color="#F0EAF7"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="300" fill="url(#sky)"/>
  <!-- 樱花树 -->
  <path d="M150 300 Q160 220 200 180 Q220 200 210 300 Z" fill="#B08968"/>
  <path d="M200 180 Q140 150 120 110 Q200 100 260 130 Q300 110 340 120 Q320 170 260 190 Z" fill="#F5C4CE"/>
  <circle cx="140" cy="120" r="10" fill="#F5A0B0"/><circle cx="220" cy="105" r="12" fill="#F0B6C4"/>
  <circle cx="300" cy="115" r="10" fill="#F5A0B0"/><circle cx="180" cy="130" r="9" fill="#F0C6D2"/>
  <!-- 飘落花瓣 -->
  <circle cx="420" cy="60" r="7" fill="#F5A0B0"/><circle cx="560" cy="40" r="6" fill="#E8C3E0"/>
  <circle cx="760" cy="70" r="7" fill="#F0B6C4"/><circle cx="980" cy="50" r="6" fill="#F5A0B0"/>
  <!-- 少女（同形象，简化全身：白发高马尾 + 红装 + 看书） -->
  <g transform="translate(720 40)">
    <ellipse cx="0" cy="180" rx="90" ry="14" fill="#EADFEC"/>
    <path d="M-14 60 Q12 34 44 42 Q52 78 40 108 Q12 118 -18 108 Z" fill="#F7F5F8"/>
    <path d="M40 48 Q70 34 80 62 Q78 82 62 88 Q48 84 44 68 Z" fill="#F7F5F8"/>
    <ellipse cx="12" cy="96" rx="26" ry="24" fill="#FDEBDD"/>
    <circle cx="2" cy="98" r="3.5" fill="#C8474F"/><circle cx="22" cy="98" r="3.5" fill="#C8474F"/>
    <path d="M6 108 Q12 112 18 108" fill="none" stroke="#D88A8F" stroke-width="2" stroke-linecap="round"/>
    <path d="M-18 130 Q12 118 42 130 L38 172 Q12 180 -14 172 Z" fill="#C8474F"/>
    <path d="M2 128 L12 140 L22 128 Q12 134 2 128 Z" fill="#A2363E"/>
    <rect x="-26" y="120" width="52" height="8" rx="4" fill="#fff"/>
    <rect x="-26" y="132" width="52" height="8" rx="4" fill="#fff" opacity="0.85"/>
  </g>
  <!-- 标题留白区提示（装饰性星点） -->
  <circle cx="180" cy="60" r="3" fill="#B8A7E0"/><circle cx="640" cy="90" r="3" fill="#B8A7E0"/>
  <circle cx="1100" cy="120" r="4" fill="#D6CCEA"/><circle cx="320" cy="90" r="3" fill="#D6CCEA"/>
</svg>
```

- [ ] **Step 3: 创建背景花瓣 bg-petals.svg**

极淡、半透明的散落花瓣 + 星星，用于整页背景（`pointer-events: none`）：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">
  <g fill="#F5A0B0" opacity="0.12">
    <path d="M120 140 Q132 128 144 140 Q132 152 120 140 Z"/>
    <path d="M520 320 Q530 310 540 320 Q530 330 520 320 Z"/>
    <path d="M980 200 Q992 186 1004 200 Q992 214 980 200 Z"/>
    <path d="M300 620 Q312 608 324 620 Q312 632 300 620 Z"/>
    <path d="M860 560 Q872 548 884 560 Q872 572 860 560 Z"/>
    <path d="M680 90 Q688 82 696 90 Q688 98 680 90 Z"/>
    <path d="M160 420 Q170 410 180 420 Q170 430 160 420 Z"/>
  </g>
  <g fill="#B8A7E0" opacity="0.15">
    <path d="M400 80 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 Z"/>
    <path d="M1080 360 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 Z"/>
    <path d="M240 700 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 Z"/>
    <path d="M760 240 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 Z"/>
  </g>
</svg>
```

- [ ] **Step 4: 构建验证 + 提交**

Run: `cd web && npm run build`
Expected: 构建成功（App.vue 引用的 banner-girl.svg 现已存在）。

```bash
git add web/src/assets/bg-petals.svg web/src/assets/banner-girl.svg web/src/assets/avatar-girl.svg
git commit -m "feat: add original SVG illustrations (banner, avatar, petals)"
```

---

### Task 3: FocusTimer 样式 + 吉祥物头像

**Files:**
- Modify: `web/src/components/FocusTimer.vue`

**Interfaces:**
- Consumes: `./assets/avatar-girl.svg`（Task 2）、全局 CSS 变量（Task 1）。
- Produces: 无新接口；改样式 + 去 emoji，保持 `props`/`emits`/函数逻辑不变。

- [ ] **Step 1: 改模板（去 emoji，加头像）**

把 `<template>` 改为（`<script setup>` 完全不动）：

```vue
<template>
  <section class="timer">
    <img class="avatar" src="../assets/avatar-girl.svg" alt="吉祥物" />
    <div v-if="state.active" class="counting">
      <div class="clock">{{ fmt(state.remaining) }}</div>
      <div class="pause-label" v-if="state.paused">已暂停</div>
      <div class="controls">
        <button v-if="state.paused" @click="resume">继续</button>
        <button v-else @click="pause">暂停</button>
        <button class="secondary stop" @click="stop">结束</button>
      </div>
    </div>
    <div v-else class="idle">
      <div class="task-name">{{ props.task ? props.task.title : '自由专注' }}</div>
      <input v-model.number="planned" type="number" min="1" />
      <button @click="begin">开始专注</button>
    </div>
  </section>
</template>
```

- [ ] **Step 2: 改样式**

把 `<style scoped>` 整体替换为：

```css
.timer {
  max-width: 640px;
  margin: 24px auto;
  padding: 28px 24px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
  text-align: center;
  position: relative;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: block;
  margin: 0 auto 8px;
  border: 2px solid var(--border);
}
.clock {
  font-size: 64px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin: 8px 0;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.pause-label { color: var(--primary-deep); margin-bottom: 10px; font-size: 14px; }
.task-name { color: var(--text); margin-bottom: 12px; font-size: 18px; }
.controls { display: flex; justify-content: center; gap: 10px; }
.stop { color: var(--text-dim); }
input { width: 90px; text-align: center; margin: 0 8px 12px; }
```

- [ ] **Step 3: 构建验证**

Run: `cd web && npm run build`
Expected: 构建成功。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/FocusTimer.vue
git commit -m "feat: restyle FocusTimer with mascot avatar and no emoji"
```

---

### Task 4: TaskList 样式 + 去 emoji

**Files:**
- Modify: `web/src/components/TaskList.vue`

**Interfaces:**
- Consumes: 全局 CSS 变量（Task 1）。
- Produces: 无新接口；`props`/`emits`/函数不变。

- [ ] **Step 1: 改模板（去 emoji，按钮换文字）**

把 `<template>` 改为（`<script setup>` 完全不动）：

```vue
<template>
  <section class="task-list">
    <h2>今日任务</h2>
    <form @submit.prevent="add" class="add-form">
      <input v-model="newTitle" placeholder="输入任务，如：复习数学第三章" />
      <input v-model.number="newMinutes" type="number" min="1" class="mins" />
      <button type="submit">添加</button>
    </form>
    <ul>
      <li v-for="t in tasks" :key="t.id" :class="t.status">
        <span class="title">{{ t.title }}</span>
        <span class="meta">{{ Math.round(t.focus_seconds / 60) }} 分钟 / 计划 {{ t.planned_minutes }} 分钟</span>
        <button v-if="t.status !== 'done'" class="focus-btn" @click="emit('start', t)">专注</button>
        <button v-if="t.status === 'pending'" class="secondary" @click="toggle(t.id, 'done')">完成</button>
        <button v-else-if="t.status === 'done'" class="secondary" @click="toggle(t.id, 'pending')">撤销</button>
        <button class="del" @click="remove(t.id)">删除</button>
      </li>
    </ul>
  </section>
</template>
```

- [ ] **Step 2: 改样式**

把 `<style scoped>` 整体替换为：

```css
.task-list { max-width: 640px; margin: 0 auto; padding: 0 0 24px; }
.add-form { display: flex; gap: 8px; margin-bottom: 16px; }
.add-form input[type=text] { flex: 1; }
.add-form .mins { width: 64px; }
ul { list-style: none; padding: 0; }
li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 10px;
  box-shadow: var(--shadow);
}
li.done .title { text-decoration: line-through; color: var(--text-dim); }
.title { flex: 1; font-weight: 500; }
.meta { color: var(--text-dim); font-size: 13px; }
.focus-btn { background: var(--primary); color: #fff; }
.del { background: transparent; color: var(--text-dim); font-size: 14px; }
```

- [ ] **Step 3: 构建验证**

Run: `cd web && npm run build`
Expected: 构建成功。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/TaskList.vue
git commit -m "feat: restyle TaskList with card list and no emoji"
```

---

### Task 5: AiPlanner 样式 + 去 emoji

**Files:**
- Modify: `web/src/components/AiPlanner.vue`

**Interfaces:**
- Consumes: 全局 CSS 变量（Task 1）。
- Produces: 无新接口；`emits`/函数不变。

- [ ] **Step 1: 改模板（去 emoji）**

把 `<template>` 改为（`<script setup>` 完全不动）：

```vue
<template>
  <section class="ai-planner">
    <h2>AI 智能规划</h2>
    <p class="hint">粘贴其他 AI 生成的行程，自动拆解成任务</p>
    <textarea
      v-model="text"
      rows="4"
      placeholder="例如：上午学英语 90 分钟，然后刷 3 道 LeetCode，下午复习高数"
    ></textarea>
    <button class="plan-btn" :disabled="loading" @click="plan">
      {{ loading ? '规划中…' : '智能规划' }}
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
        <button class="del" @click="removeTask(i)">删除</button>
      </div>
      <div class="preview-actions">
        <button class="confirm-btn" @click="confirm">确认创建（{{ tasks.length }} 项）</button>
        <button class="secondary cancel-btn" @click="clearAll">清空</button>
      </div>
    </div>
  </section>
</template>
```

- [ ] **Step 2: 改样式**

把 `<style scoped>` 整体替换为：

```css
.ai-planner {
  max-width: 640px;
  margin: 0 auto 24px;
  padding: 22px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.hint { color: var(--text-dim); font-size: 13px; margin-top: 0; }
textarea { width: 100%; resize: vertical; }
.plan-btn { margin-top: 10px; }
.error { color: var(--primary-deep); font-size: 14px; }
.preview { margin-top: 16px; }
.preview-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.p-title { flex: 1; }
.p-mins { width: 64px; }
.p-unit { color: var(--text-dim); font-size: 13px; }
.del { background: transparent; color: var(--text-dim); font-size: 14px; }
.preview-actions { margin-top: 12px; display: flex; gap: 10px; }
```

- [ ] **Step 3: 构建验证**

Run: `cd web && npm run build`
Expected: 构建成功。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/AiPlanner.vue
git commit -m "feat: restyle AiPlanner card and no emoji"
```

---

### Task 6: 背景花瓣接入 + 端到端视觉冒烟

**Files:**
- Modify: `web/src/style.css`（在全局 body 上接入背景花瓣层）

**Interfaces:**
- Consumes: `./assets/bg-petals.svg`（Task 2）。

- [ ] **Step 1: 接入背景花瓣**

背景是整页的，应在**全局** `style.css` 的 `body` 上加（而不是 scoped 组件里，避免层级问题）。在 `web/src/style.css` 里，把现有的：

```css
body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--sans); }
```

替换为（`background-image` 用相对 style.css 的路径 `src/assets/bg-petals.svg`，平铺）：

```css
body {
  margin: 0;
  background-color: var(--bg);
  background-image: url('./assets/bg-petals.svg');
  background-repeat: repeat;
  background-size: 1200px 800px;
  color: var(--text);
  font-family: var(--sans);
}
```

> 注：`style.css` 位于 `web/src/`，`./assets/bg-petals.svg` 解析为 `web/src/assets/bg-petals.svg`，与 Task 2 创建的路径一致。花瓣 SVG 本身已是半透明（opacity 0.12–0.15），无需再叠 opacity。

- [ ] **Step 2: 启动前后端冒烟验证**

Run:
```bash
cd /Users/liuzishan/Focus-Blocker
./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000 &
cd web && npm run dev
```
Expected: 浏览器打开 http://localhost:5173，确认——暖白背景 + 樱花花瓣、顶部横幅少女插画、吉祥物头像、粉紫渐变时钟、白卡片任务列表、**全文无 emoji**。

- [ ] **Step 3: 提交**

```bash
git add web/src/App.vue
git commit -m "feat: add cherry-blossom petal background"
```

---

## 任务依赖图

```
Task 1（全局变量 + App 骨架）→ Task 2（SVG 资产）→ Task 3/4/5（组件样式，可并行）→ Task 6（背景接入 + 冒烟）
```

建议顺序：1 → 2 → 3 → 4 → 5 → 6。Task 2 必须在 Task 1 之后（App.vue 引用了 banner-girl.svg）；Task 6 依赖 Task 2 的背景花瓣。
