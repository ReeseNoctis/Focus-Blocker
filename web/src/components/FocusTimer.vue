<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { startSession, stopSession, pauseSession, resumeSession, currentSession, connectWs } from '../api/client'

const props = defineProps({ task: { type: Object, default: null } })
const emit = defineEmits(['finished'])

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

<style scoped>
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
</style>
