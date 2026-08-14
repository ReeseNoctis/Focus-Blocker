<script setup>
import { ref, onMounted, watch } from 'vue'
import { fetchTasks, createTask, updateTask, deleteTask } from '../api/client'

const props = defineProps({ date: String, refreshKey: Number })
const emit = defineEmits(['start'])

const tasks = ref([])
const newTitle = ref('')
const newMinutes = ref(25)

async function load() {
  tasks.value = await fetchTasks(props.date)
}
async function add() {
  if (!newTitle.value.trim()) return
  await createTask(newTitle.value.trim(), newMinutes.value)
  newTitle.value = ''
  newMinutes.value = 25
  await load()
}
async function toggle(id, status) {
  await updateTask(id, { status })
  await load()
}
async function remove(id) {
  await deleteTask(id)
  await load()
}
onMounted(load)
watch(() => props.date, load)
watch(() => props.refreshKey, load)
</script>

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

<style scoped>
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
</style>
