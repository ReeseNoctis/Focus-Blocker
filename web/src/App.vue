<script setup>
import { ref } from 'vue'
import TaskList from './components/TaskList.vue'

const today = new Date().toISOString().slice(0, 10)
const activeTask = ref(null)
</script>

<template>
  <main>
    <h1>🧘 沉浸式学习助手</h1>
    <TaskList :date="today" @start="(t) => (activeTask = t)" />
  </main>
</template>

<style>
body { margin: 0; background: #0d0d0d; color: #eee; font-family: -apple-system, sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 24px; }
h1 { text-align: center; }
</style>
