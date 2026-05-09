import React, { useState, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

export function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState('')

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-3 items-center p-4 border-t border-bg-border bg-bg-base">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        placeholder="Type your answer..."
        className="flex-1 bg-bg-surface border border-bg-border rounded-lg px-4 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary/50 transition-all duration-150 disabled:opacity-40"
        autoFocus
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="w-10 h-10 rounded-lg bg-accent-primary hover:bg-accent-primary/90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all duration-150"
      >
        <Send size={16} className="text-white" />
      </button>
    </div>
  )
}
