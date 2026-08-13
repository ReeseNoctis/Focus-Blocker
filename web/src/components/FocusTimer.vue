<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { startSession, stopSession, currentSession, connectWs } from '../api/client'

const props = defineProps({ task: { type: Object, default: null } })
const emit = defineEmits(['finished'])

const state = ref({ active: false, remaining: 0, total_seconds: 0 })
const planned = ref(25)
let closeWs = null

function fmt(s) {
  const m = Math.floor(s / 60), sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

async function begin() {
  await startSession(props.task?.id ?? null, planned.value)
  emit('finished')  // prompt parent to refresh task list
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
    state.value = { active: false, remaining: 0, total_seconds: 0 }
  }
}

onUnmounted(() => closeWs && closeWs())
closeWs = connectWs((s) => { state.value = s })
currentSession().then((s) => { state.value = s })

// auto-complete: when remaining hits 0, stop as completed
let lastRemaining = null
watch(() => state.value.remaining, async (r) => {
  if (state.value.active && r === 0 && lastRemaining !== 0) {
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
      <button class="stop" @click="stop">🛑 停止（不计完成）</button>
    </div>
    <div v-else class="idle">
      <div class="task-name">{{ props.task ? props.task.title : '自由专注' }}</div>
      <input v-model.number="planned" type="number" min="1" />
      <button @click="begin">▶ 开始专注</button>
    </div>
  </section>
</template>

<style scoped>
.timer { max-width: 640px; margin: 24px auto; padding: 24px; border: 1px solid #333; border-radius: 12px; text-align: center; }
.clock { font-size: 56px; font-variant-numeric: tabular-nums; margin: 12px 0; }
button { margin: 0 8px; padding: 8px 16px; }
</style>
