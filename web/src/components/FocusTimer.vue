<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { startSession, stopSession, pauseSession, resumeSession, currentSession, connectWs } from '../api/client'

const props = defineProps({ task: { type: Object, default: null } })
const emit = defineEmits(['finished', 'session'])

const state = ref({ active: false, paused: false, remaining: 0, total_seconds: 0 })
const planned = ref(60)
let closeWs = null

// When the selected task changes, prefill the focus duration with that
// task's planned_minutes so "▶ 专注" uses the right time (not a stale default).
watch(() => props.task, (t) => {
  if (t && t.planned_minutes > 0) {
    planned.value = t.planned_minutes
  }
})

function fmt(s) {
  const m = Math.floor(s / 60), sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

async function begin() {
  await startSession(props.task?.id ?? null, planned.value)
  emit('finished')  // prompt parent to refresh task list
}

async function pause() {
  await pauseSession()
}

async function resume() {
  await resumeSession()
}

// Stop a session, treating "already ended" (watchdog won the race → 409) as a
// successful finish. Returns true on success, false when the session was
// already completed elsewhere. Always refreshes the task list via 'finished'.
async function doStop(completed) {
  let resp
  try {
    resp = await stopSession(completed)
  } catch (e) {
    if (/no active session|already running|409/.test(e.message || '')) {
      // Session already ended server-side — still refresh the list.
      emit('finished')
      return false
    }
    throw e
  }
  emit('finished')
  if (resp?.warning) window.alert(resp.warning)
  return true
}

async function stop() {
  const stopped = await doStop(false)
  if (!stopped) {
    // 409 path: no stop ran, so the local timer state is stale — clear it.
    state.value = { active: false, paused: false, remaining: 0, total_seconds: 0 }
  }
}

onUnmounted(() => closeWs && closeWs())
closeWs = connectWs((s) => { state.value = s })
currentSession().then((s) => { state.value = s })
watch(state, (s) => emit('session', s), { deep: true, immediate: true })

// auto-complete: when remaining hits 0, stop as completed (only while actively
// counting — a paused session must never auto-complete).
let lastRemaining = null
watch(() => state.value.remaining, async (r) => {
  if (state.value.active && !state.value.paused && r === 0 && lastRemaining !== 0) {
    lastRemaining = 0
    await doStop(true)
  } else if (r !== 0) {
    lastRemaining = r
  }
})
</script>

<template>
  <section class="timer">
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
      <div class="idle-row">
        <input v-model.number="planned" type="number" min="1" />
        <span class="mins-label">分钟</span>
      </div>
      <button @click="begin">开始专注</button>
    </div>
  </section>
</template>

<style scoped>
.timer {
  margin: 0 0 20px;
  padding: 28px 24px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
  text-align: center;
  position: relative;
  backdrop-filter: blur(10px);
}
.clock {
  font-family: var(--display);
  font-size: 68px;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
  margin: 8px 0;
  color: var(--ink);
  letter-spacing: 0.1em;
  text-shadow: 0 2px 0 rgba(255, 248, 232, 0.7);
}
.pause-label { color: var(--red); margin-bottom: 10px; font-size: 18px; font-family: var(--display); }
.task-name { color: var(--text); margin-bottom: 12px; font-size: 24px; font-family: var(--display); letter-spacing: 0.12em; }
.controls { display: flex; justify-content: center; gap: 10px; }
.stop { color: var(--text-dim); }
.idle-row { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 12px; }
.mins-label { color: var(--text-dim); font-size: 14px; }
input { width: 90px; text-align: center; }
</style>
