import React, { useRef, useEffect } from 'react'
import { ChatMessage as ChatMessageType } from '../../types'
import { ChatMessageBubble } from './ChatMessage'
import { ChatInput } from './ChatInput'

interface Props {
  messages: ChatMessageType[]
  onSend: (text: string) => void
  isTyping: boolean
  disabled?: boolean
}

function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-bg-surface border border-bg-border border-l-2 border-l-accent-primary rounded-xl px-4 py-3">
        <div className="flex gap-1.5 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse-slow"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export function ChatWindow({ messages, onSend, isTyping, disabled }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const lastBotMsg = [...messages].reverse().find((m) => m.role === 'bot')

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((msg) => (
          <ChatMessageBubble
            key={msg.id}
            msg={msg}
            onQuickReply={(reply) => {
              if (!disabled) onSend(reply)
            }}
          />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={onSend} disabled={disabled || isTyping} />
    </div>
  )
}
