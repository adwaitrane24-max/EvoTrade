/**
 * websocket.js — WebSocket client hook.
 * Connects to the FastAPI /ws endpoint and dispatches typed events
 * into a shared state object via registered listeners.
 */

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

class EvoTradeSocket {
  constructor() {
    this._ws = null
    this._listeners = {}
    this._reconnectDelay = 2000
    this._intentionalClose = false
  }

  connect() {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) return

    this._intentionalClose = false
    this._ws = new WebSocket(WS_URL)

    this._ws.onopen = () => {
      console.log('[WS] Connected to EvoTrade backend')
      this._emit('connection', { status: 'connected' })
      this._reconnectDelay = 2000
    }

    this._ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        this._emit(payload.type, payload)
        this._emit('*', payload) // wildcard listener
      } catch (err) {
        console.warn('[WS] Failed to parse message:', event.data)
      }
    }

    this._ws.onclose = () => {
      this._emit('connection', { status: 'disconnected' })
      if (!this._intentionalClose) {
        console.log(`[WS] Disconnected. Reconnecting in ${this._reconnectDelay}ms…`)
        setTimeout(() => this.connect(), this._reconnectDelay)
        this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, 15000)
      }
    }

    this._ws.onerror = (err) => {
      console.error('[WS] Error:', err)
    }
  }

  disconnect() {
    this._intentionalClose = true
    this._ws?.close()
  }

  on(eventType, handler) {
    if (!this._listeners[eventType]) this._listeners[eventType] = []
    this._listeners[eventType].push(handler)
    return () => this.off(eventType, handler) // returns unsubscribe fn
  }

  off(eventType, handler) {
    if (!this._listeners[eventType]) return
    this._listeners[eventType] = this._listeners[eventType].filter((h) => h !== handler)
  }

  _emit(eventType, data) {
    ;(this._listeners[eventType] || []).forEach((h) => h(data))
  }

  get isConnected() {
    return this._ws?.readyState === WebSocket.OPEN
  }
}

// Singleton shared across the app
export const socket = new EvoTradeSocket()

// ── REST helpers ─────────────────────────────────────────────────────────────

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function post(path, body = {}) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(`${API}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  onboard: (data) => post('/onboard', data),
  start: () => post('/start'),
  pause: () => post('/pause'),
  resume: () => post('/resume'),
  emergencyStop: () => post('/emergency_stop'),
  status: () => get('/status'),
}
