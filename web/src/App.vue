<script setup>
import { ref } from 'vue'
import TaskList from './components/TaskList.vue'
import FocusTimer from './components/FocusTimer.vue'
import AiPlanner from './components/AiPlanner.vue'
import StudyPet from './components/StudyPet.vue'
import scene from './assets/bg-scene.jpg'

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
const session = ref({ active: false, paused: false, remaining: 0, total_seconds: 0 })

function onFinished() {
  activeTask.value = null
  listVersion.value++
}
function onSession(s) {
  session.value = s
}
</script>

<template>
  <div class="world">
    <div class="scene" aria-hidden="true">
      <img class="scene-img" :src="scene" alt="" />
      <div class="mist"></div>
      <div class="clouds"></div>
      <div class="petals">
        <i v-for="n in 16" :key="n" />
      </div>
    </div>
    <div class="frame" aria-hidden="true"></div>

    <div class="page">
      <header class="title-block">
        <p class="kicker">白发红眸 · 古风监督</p>
        <h1>绛雪监学<span class="seal">监</span></h1>
        <p class="sub">绛雪会盯着你把功课做完</p>
      </header>

      <div class="layout">
        <div class="col">
          <AiPlanner @created="listVersion++" />
          <FocusTimer
            :task="activeTask"
            @finished="onFinished"
            @session="onSession"
          />
          <TaskList :date="today" :refresh-key="listVersion" @start="(t) => (activeTask = t)" />
        </div>
        <StudyPet :session="session" :task="activeTask" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.world { min-height: 100vh; position: relative; }
.scene {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.scene-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 42%;
  transform: scale(1.04);
}
.mist {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 50% at 50% 0%, rgba(255, 244, 230, 0.2), transparent 55%),
    linear-gradient(180deg, rgba(255, 244, 230, 0.06) 0%, rgba(255, 236, 214, 0.12) 48%, rgba(60, 24, 18, 0.16) 100%);
}
.clouds {
  position: absolute;
  left: -10%;
  top: 0;
  width: 120%;
  height: 220px;
  background: url('./assets/bg-clouds.svg') repeat-x;
  background-size: 900px 180px;
  opacity: 0.55;
  animation: drift 48s linear infinite;
}
.petals { position: absolute; inset: 0; }
.petals i {
  position: absolute;
  top: -24px;
  width: 11px;
  height: 9px;
  background: radial-gradient(circle at 30% 30%, #f7c4c8, #e8899a 70%);
  border-radius: 80% 0 70% 10%;
  opacity: 0.75;
  animation: fall linear infinite;
}
.petals i:nth-child(1)  { left: 6%;  animation-duration: 11s; animation-delay: 0s; }
.petals i:nth-child(2)  { left: 14%; animation-duration: 14s; animation-delay: -3s; }
.petals i:nth-child(3)  { left: 22%; animation-duration: 10s; animation-delay: -6s; }
.petals i:nth-child(4)  { left: 31%; animation-duration: 16s; animation-delay: -2s; }
.petals i:nth-child(5)  { left: 39%; animation-duration: 12s; animation-delay: -8s; }
.petals i:nth-child(6)  { left: 47%; animation-duration: 15s; animation-delay: -4s; }
.petals i:nth-child(7)  { left: 55%; animation-duration: 11s; animation-delay: -9s; }
.petals i:nth-child(8)  { left: 62%; animation-duration: 13s; animation-delay: -1s; }
.petals i:nth-child(9)  { left: 70%; animation-duration: 17s; animation-delay: -7s; }
.petals i:nth-child(10) { left: 76%; animation-duration: 12s; animation-delay: -5s; }
.petals i:nth-child(11) { left: 83%; animation-duration: 14s; animation-delay: -11s; }
.petals i:nth-child(12) { left: 88%; animation-duration: 10s; animation-delay: -2.5s; }
.petals i:nth-child(13) { left: 93%; animation-duration: 16s; animation-delay: -6.5s; }
.petals i:nth-child(14) { left: 18%; animation-duration: 18s; animation-delay: -13s; width: 8px; height: 7px; }
.petals i:nth-child(15) { left: 58%; animation-duration: 9s;  animation-delay: -4.5s; width: 8px; height: 7px; }
.petals i:nth-child(16) { left: 41%; animation-duration: 13s; animation-delay: -10s; width: 14px; height: 11px; }

.frame {
  position: fixed;
  inset: 10px;
  z-index: 2;
  pointer-events: none;
  border: 2px solid rgba(177, 50, 56, 0.28);
  box-shadow:
    inset 0 0 0 6px rgba(232, 201, 137, 0.18),
    inset 0 0 40px rgba(90, 40, 28, 0.08);
}

.page {
  position: relative;
  z-index: 1;
  max-width: 1040px;
  margin: 0 auto;
  padding: 28px 22px 64px;
}
.title-block {
  text-align: center;
  margin-bottom: 28px;
  padding: 8px 12px 16px;
}
.kicker {
  margin: 0 0 4px;
  font-family: var(--display);
  font-size: 16px;
  letter-spacing: 0.32em;
  color: var(--ink);
  text-shadow: 0 1px 0 rgba(255, 248, 232, 0.85);
}
h1 {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 58px;
  font-weight: 400;
  color: var(--ink);
  text-shadow:
    0 1px 0 #fff6e4,
    0 10px 28px rgba(255, 244, 224, 0.75);
}
.seal {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--red);
  color: var(--red);
  font-size: 22px;
  letter-spacing: 0;
  transform: rotate(11deg);
  background: rgba(255, 248, 236, 0.55);
  box-shadow: inset 0 0 0 3px rgba(177, 50, 56, 0.15);
}
.sub {
  margin: 8px 0 0;
  font-family: var(--display);
  font-size: 18px;
  letter-spacing: 0.2em;
  color: var(--text);
  text-shadow: 0 1px 0 rgba(255, 248, 232, 0.8);
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 28px;
  align-items: start;
}

@keyframes drift {
  from { transform: translateX(0); }
  to { transform: translateX(-18%); }
}
@keyframes fall {
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  12% { opacity: 0.8; }
  100% { transform: translateY(110vh) rotate(360deg); opacity: 0.15; }
}

@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  h1 { font-size: 40px; }
  .frame { inset: 6px; }
}
</style>
