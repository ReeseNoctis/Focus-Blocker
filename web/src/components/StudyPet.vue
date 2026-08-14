<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import qIdle from '../assets/q-idle.jpg'
import qPoint from '../assets/q-point.jpg'
import qAngry from '../assets/q-angry.jpg'
import qHappy from '../assets/q-happy.jpg'
import qWave from '../assets/q-wave.jpg'

const props = defineProps({
  session: { type: Object, default: () => ({ active: false, paused: false, remaining: 0 }) },
  task: { type: Object, default: null },
})

const POSES = { idle: qIdle, point: qPoint, angry: qAngry, happy: qHappy, wave: qWave }

const LINES = {
  idle: [
    '还不快开始？本座可不是来陪你发呆的。',
    '今日功课呢？本座等着监督你。',
    '把书打开。红尘俗事，先放一边。',
    '发什么呆。坐下来，开始吧。',
  ],
  idleTask: [
    '这本该做的事，还要本座提醒你吗？',
    '准备好了就开始。本座看着呢。',
  ],
  longIdle: [
    '……还在拖。本座已经不太高兴了。',
    '再不动笔，可就要记过了。',
    '偷懒可是逃不过本座的眼睛的。',
  ],
  focus: [
    '很好，继续保持。本座看着你呢。',
    '专心。余光别往窗外飘。',
    '时间还在走，你也别停。',
    '嗯……这才像话。',
    '静心。一口气做到底。',
  ],
  paused: [
    '怎么停下来了？快点回来。',
    '偷懒可是要被本座记下来的。',
    '暂停太久了哦……认真一点。',
    '本座允许你歇一口气，不是让你跑掉。',
  ],
  done: [
    '完成了。勉勉强强……也算不错。',
    '辛苦了。稍微歇一歇也无妨。',
    '今日又赢了一局。下一项呢？',
  ],
}

const POKE_LINES = [
  '本座可不是猫，乱点什么。',
  '手拿开。……也不是完全不许。',
  '专心！不许摸鱼。',
  '哼，被你戳到了。',
  '再点，本座可要记下你了。',
  '喂，学习呢，眼睛往这边看做什么。',
]
const MARKS = ['♡', '！', '♪', '…', '※']

const justFinished = ref(false)
const idleSince = ref(Date.now())
const now = ref(Date.now())
const lineIndex = ref(0)
const poke = ref(null)
const extraPose = ref(null)
const focusAlt = ref(false)
const shownPose = ref('idle')
const layers = ref([{ id: 0, pose: 'idle', src: qIdle, on: true }])

let rotateTimer = null
let tickTimer = null
let doneTimer = null
let pokeTimer = null
let extraTimer = null
let extraLoop = null
let focusTimer = null
let layerId = 0
let moveGen = 0
let pruneTimer = null

const mood = computed(() => {
  if (justFinished.value) return 'done'
  if (props.session?.paused) return 'paused'
  if (props.session?.active) return 'focus'
  if (now.value - idleSince.value > 90_000) return 'longIdle'
  return 'idle'
})

const moodPose = computed(() => {
  if (mood.value === 'done') return 'happy'
  if (mood.value === 'paused' || mood.value === 'longIdle') return 'angry'
  if (mood.value === 'focus') return focusAlt.value ? 'idle' : 'point'
  return extraPose.value || 'idle'
})

const poseKey = computed(() => poke.value?.pose || moodPose.value)

const ARM = new Set(['idle', 'point'])

function pathFromTo(from, to, bridged) {
  if (!from || from === to) return [to]
  if (bridged && ARM.has(from) && ARM.has(to)) return ['wave', to]
  return [to]
}

async function fadeTo(pose) {
  const src = POSES[pose] || qIdle
  if (shownPose.value === pose && layers.value.some((l) => l.on && l.pose === pose)) {
    return
  }
  shownPose.value = pose
  const id = ++layerId
  layers.value.push({ id, pose, src, on: false })
  await nextTick()
  await new Promise((r) => requestAnimationFrame(r))
  for (const l of layers.value) l.on = l.id === id
  clearTimeout(pruneTimer)
  pruneTimer = setTimeout(() => {
    layers.value = layers.value.filter((l) => l.on)
  }, 820)
  await new Promise((r) => setTimeout(r, 420))
}

async function goTo(target, bridged) {
  const my = ++moveGen
  const steps = pathFromTo(shownPose.value, target, bridged)
  for (const pose of steps) {
    if (my !== moveGen) return
    await fadeTo(pose)
  }
}

const moodLabel = computed(() => ({
  idle: '等待开始',
  longIdle: '有些不满',
  focus: '陪伴专注',
  paused: '正在督促',
  done: '予以嘉奖',
}[mood.value]))

const line = computed(() => {
  if (poke.value) return poke.value.line
  if (mood.value === 'focus' && props.session?.remaining > 0 && props.session.remaining <= 180) {
    return '最后几分钟了，不许走神。'
  }
  if (mood.value === 'idle' && props.task) {
    const list = LINES.idleTask
    return `「${props.task.title}」——${list[lineIndex.value % list.length]}`
  }
  const list = LINES[mood.value] || LINES.idle
  return list[lineIndex.value % list.length]
})

function startRotate() {
  clearInterval(rotateTimer)
  rotateTimer = setInterval(() => { lineIndex.value += 1 }, 16_000)
}

function onPoke() {
  const poses = ['wave', 'happy', 'angry', 'point']
  poke.value = {
    pose: poses[Math.floor(Math.random() * poses.length)],
    line: POKE_LINES[Math.floor(Math.random() * POKE_LINES.length)],
    mark: MARKS[Math.floor(Math.random() * MARKS.length)],
  }
  clearTimeout(pokeTimer)
  pokeTimer = setTimeout(() => { poke.value = null }, 2400)
}

watch(poseKey, (next, prev) => {
  if (!prev) {
    shownPose.value = next
    layers.value = [{ id: ++layerId, pose: next, src: POSES[next] || qIdle, on: true }]
    return
  }
  goTo(next, !poke.value)
}, { immediate: true })

watch(mood, () => {
  lineIndex.value = 0
  startRotate()
}, { immediate: true })

watch(() => props.session?.active, (active, wasActive) => {
  if (active) {
    idleSince.value = Date.now()
    justFinished.value = false
    clearTimeout(doneTimer)
  } else {
    idleSince.value = Date.now()
    if (wasActive) {
      justFinished.value = true
      extraPose.value = 'happy'
      clearTimeout(doneTimer)
      doneTimer = setTimeout(() => {
        justFinished.value = false
        extraPose.value = null
      }, 10_000)
    }
  }
})

tickTimer = setInterval(() => { now.value = Date.now() }, 5000)

onMounted(() => {
  Object.values(POSES).forEach((src) => { const img = new Image(); img.src = src })
})

extraLoop = setInterval(() => {
  if (poke.value) return
  if (mood.value !== 'idle') return
  extraPose.value = 'wave'
  clearTimeout(extraTimer)
  extraTimer = setTimeout(() => { extraPose.value = null }, 2800)
}, 9000)

focusTimer = setInterval(() => {
  if (mood.value === 'focus' && !poke.value) focusAlt.value = !focusAlt.value
}, 9000)

onUnmounted(() => {
  clearInterval(rotateTimer)
  clearInterval(tickTimer)
  clearInterval(extraLoop)
  clearInterval(focusTimer)
  clearTimeout(doneTimer)
  clearTimeout(pokeTimer)
  clearTimeout(extraTimer)
  clearTimeout(pruneTimer)
})
</script>

<template>
  <aside class="pet" :class="[mood, shownPose]">
    <div class="bubble" :key="line">
      <p>{{ line }}</p>
    </div>
    <button class="stage" type="button" @click="onPoke" :aria-label="'点一点绛雪'">
      <span v-if="poke" class="mark">{{ poke.mark }}</span>
      <span class="clip">
        <span class="mover">
          <img
            v-for="layer in layers"
            :key="layer.id"
            class="portrait"
            :class="{ on: layer.on }"
            :src="layer.src"
            alt=""
          />
        </span>
      </span>
      <span class="plate">
        <span class="name">绛雪</span>
        <span class="role">学习监督 · {{ moodLabel }}</span>
        <span class="hint">点一点她</span>
      </span>
    </button>
  </aside>
</template>

<style scoped>
.pet {
  position: sticky;
  top: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bubble {
  position: relative;
  background: rgba(255, 248, 236, 0.9);
  border: 1px solid var(--border);
  border-radius: 18px 18px 18px 6px;
  padding: 12px 14px;
  box-shadow: var(--shadow);
  min-height: 68px;
  backdrop-filter: blur(8px);
  animation: bubble-in 0.35s ease;
}
.bubble p {
  margin: 0;
  font-family: var(--display);
  font-size: 18px;
  line-height: 1.55;
  color: var(--text);
  letter-spacing: 0.08em;
}
.bubble::after {
  content: '';
  position: absolute;
  left: 36px;
  bottom: -8px;
  border-width: 8px 8px 0 0;
  border-style: solid;
  border-color: rgba(255, 248, 236, 0.95) transparent transparent transparent;
}
.stage {
  position: relative;
  display: block;
  width: 100%;
  padding: 0;
  overflow: hidden;
  border: none;
  border-radius: 28px;
  background: transparent;
  box-shadow: none;
  letter-spacing: 0;
  text-shadow: none;
  color: inherit;
  cursor: pointer;
  font-family: inherit;
}
.stage:hover,
.stage:active {
  filter: none;
  transform: none;
  box-shadow: none;
  background: transparent;
}
.clip {
  position: relative;
  display: block;
  height: 430px;
  overflow: hidden;
  -webkit-mask-image: radial-gradient(ellipse 74% 80% at 50% 46%, #000 56%, transparent 76%);
  mask-image: radial-gradient(ellipse 74% 80% at 50% 46%, #000 56%, transparent 76%);
}
.mover {
  position: absolute;
  inset: 0;
  animation: bob 3.6s ease-in-out infinite;
}
.portrait {
  position: absolute;
  left: -12%;
  top: -8%;
  width: 124%;
  height: 124%;
  max-width: none;
  object-fit: cover;
  object-position: center 12%;
  opacity: 0;
  transform: scale(0.98);
  transition: opacity 0.78s ease-in-out, transform 0.78s ease-in-out;
  pointer-events: none;
}
.portrait.on {
  opacity: 1;
  transform: scale(1);
}

.mark {
  position: absolute;
  top: 18px;
  right: 22px;
  z-index: 2;
  font-family: var(--display);
  font-size: 34px;
  color: var(--red);
  text-shadow: 0 2px 0 rgba(255, 248, 232, 0.9);
  animation: mark-pop 0.45s ease;
  pointer-events: none;
}
.plate {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 28px 12px 10px;
  background: linear-gradient(transparent, rgba(74, 30, 28, 0.72));
  color: #fff6e4;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.name {
  font-family: var(--display);
  font-size: 26px;
  letter-spacing: 0.2em;
}
.role {
  font-family: var(--display);
  font-size: 14px;
  letter-spacing: 0.14em;
  opacity: 0.92;
}
.hint {
  margin-top: 4px;
  font-size: 11px;
  letter-spacing: 0.16em;
  opacity: 0.75;
}

@keyframes bob {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(0, -10px, 0); }
}
@keyframes mark-pop {
  0% { transform: scale(0.4) translateY(8px); opacity: 0; }
  60% { transform: scale(1.2) translateY(-4px); opacity: 1; }
  100% { transform: scale(1) translateY(0); }
}
@keyframes bubble-in {
  from { transform: translateY(6px); opacity: 0.4; }
  to { transform: none; opacity: 1; }
}

@media (max-width: 860px) {
  .pet { position: static; }
  .clip { height: 300px; }
}
</style>
