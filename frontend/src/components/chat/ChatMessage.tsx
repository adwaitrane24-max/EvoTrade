import React from 'react'
import { ChatMessage as ChatMessageType } from '../../types'

export function ChatMessageBubble({ msg, onQuickReply }: {
  msg: ChatMessageType
  onQuickReply?: (reply: string) => void
}) {
  const isBot = msg.role === 'bot'

  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'} animate-slide-up`}>
      <div className={`max-w-[80%] ${isBot ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
            isBot
              ? 'bg-bg-surface border border-bg-border border-l-2 border-l-accent-primary text-text-primary'
              : 'bg-accent-primary/10 border border-accent-primary/20 text-text-primary'
          }`}
        >
          {msg.text.split('\n').map((line, i) => (
            <p key={i} className={line.startsWith('•') ? 'mt-1' : i > 0 ? 'mt-2' : ''}>
              {line.replace(/\*\*(.*?)\*\*/g, '$1')}
            </p>
          ))}
        </div>

        {isBot && msg.quickReplies && msg.quickReplies.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {msg.quickReplies.map((r) => (
              <button
                key={r}
                onClick={() => onQuickReply?.(r)}
                className="px-3 py-1.5 text-xs rounded-lg border border-accent-primary/30 text-accent-primary hover:bg-accent-primary/10 transition-all duration-150"
              >
                {r}
              </button>
            ))}
          </div>
        )}

        <p className="text-text-muted text-xs mt-1 px-1">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
