import { WsEvent } from '../types'

type Handler = (event: WsEvent) => void

class WsManager {
  private ws: WebSocket | null = null
  private handlers: Set<Handler> = new Set()
  private userId = 'default'
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private backoff = 1000

  connect(userId = 'default') {
    this.userId = userId
    this._open()
  }

  private _open() {
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) return
    try {
      this.ws = new WebSocket('ws://localhost:8000/ws')
      this.ws.onopen = () => {
        this.backoff = 1000
        this.ws!.send(JSON.stringify({ type: 'AUTH', user_id: this.userId }))
        this._notify({ type: 'WS_CONNECTED', timestamp: new Date().toISOString(), data: {} })
      }
      this.ws.onmessage = (e) => {
        try {
          const msg: WsEvent = JSON.parse(e.data)
          this._notify(msg)
        } catch {}
      }
      this.ws.onclose = () => {
        this._notify({ type: 'WS_DISCONNECTED', timestamp: new Date().toISOString(), data: {} })
        this._scheduleReconnect()
      }
      this.ws.onerror = () => {
        this.ws?.close()
      }
    } catch (e) {
      this._scheduleReconnect()
    }
  }

  private _scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.backoff = Math.min(this.backoff * 2, 30000)
      this._open()
    }, this.backoff)
  }

  private _notify(event: WsEvent) {
    this.handlers.forEach((h) => h(event))
  }

  subscribe(handler: Handler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  send(msg: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsManager = new WsManager()
