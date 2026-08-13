const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function fetchTasks(date) {
  return request(`/api/tasks?date=${encodeURIComponent(date)}`)
}
export function createTask(title, plannedMinutes = 25) {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify({ title, planned_minutes: plannedMinutes }) })
}
export function updateTask(id, patch) {
  return request(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
}
export function deleteTask(id) {
  return request(`/api/tasks/${id}`, { method: 'DELETE' })
}
export function startSession(taskId, minutes) {
  return request('/api/sessions/start', { method: 'POST', body: JSON.stringify({ task_id: taskId, minutes }) })
}
export function stopSession(completed) {
  return request('/api/sessions/stop', { method: 'POST', body: JSON.stringify({ completed }) })
}
export function currentSession() {
  return request('/api/sessions/current')
}
let currentWs = null
let closed = false

export function connectWs(onState) {
  closed = false
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws`)
  currentWs = ws
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'state') onState(msg.state)
    } catch (_) { /* ignore non-JSON frames */ }
  }
  ws.onclose = () => {
    if (!closed) setTimeout(() => { if (!closed) connectWs(onState) }, 2000)
  }
  return () => {
    closed = true
    if (currentWs) currentWs.close()
  }
}
