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
  try {
    for (const t of tasks.value) {
      await createTask(t.title, t.planned_minutes)
    }
    emit('created')
    clearAll()
  } catch (e) {
    error.value = `创建任务失败: ${e.message}（部分任务可能已创建，请检查列表后再试）`
  }
}
</script>

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

<style scoped>
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
</style>
