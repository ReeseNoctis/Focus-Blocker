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
