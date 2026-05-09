import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatWindow } from '../components/chat/ChatWindow'
import { useChatStore } from '../stores/chatStore'
import { ChatMessage, ChatResponse } from '../types'
import api from '../lib/api'

const USER_ID = 'evotrade-demo-user'

function makeMsg(role: 'bot' | 'user', text: string, quickReplies?: string[]): ChatMessage {
  return { id: crypto.randomUUID(), role, text, timestamp: Date.now(), quickReplies }
}

export function ChatOnboardingPage() {
  const navigate = useNavigate()
  const { messages, addMessage, setProfile, setProfileId, setStep, setComplete, isComplete, profile } = useChatStore()
  const [isTyping, setIsTyping] = useState(false)
  const [showCta, setShowCta] = useState(false)
  const initiated = useRef(false)

  // Kick off first bot message on mount
  useEffect(() => {
    if (initiated.current || messages.length > 0) return
    initiated.current = true
    sendToBackend('')
  }, [])

  useEffect(() => {
    if (isComplete) setShowCta(true)
  }, [isComplete])

  const sendToBackend = async (userText: string) => {
    if (userText) {
      addMessage(makeMsg('user', userText))
    }
    setIsTyping(true)
    try {
      const res = await api.post<ChatResponse>('/api/chat/message', {
        user_id: USER_ID,
        message: userText,
      })
      const data = res.data
      // Natural delay
      await new Promise((r) => setTimeout(r, 600))
      setIsTyping(false)
      addMessage(makeMsg('bot', data.bot_message, data.quick_replies ?? undefined))
      setStep(data.step)
      setProfile(data.profile_so_far)
      if (data.is_complete) setComplete(true)
    } catch (e) {
      setIsTyping(false)
      addMessage(makeMsg('bot', 'Sorry, something went wrong. Please refresh and try again.'))
    }
  }

  const handleSend = (text: string) => {
    if (isComplete) return
    sendToBackend(text)
  }

  const handleBeginEvolution = async () => {
    try {
      const res = await api.post('/api/chat/finalize', { user_id: USER_ID, profile })
      setProfileId(res.data.profile_id)
      navigate('/evolution')
    } catch {
      navigate('/evolution')
    }
  }

  return (
    <div className="h-full flex flex-col items-center justify-center pr-[240px]">
      <div className="w-full max-w-[720px] h-full flex flex-col">
        {/* Header */}
        <div className="px-6 pt-8 pb-4">
          <h1 className="text-xl font-semibold text-text-primary">Strategy Onboarding</h1>
          <p className="text-sm text-text-secondary mt-1">Answer a few questions and EvoTrade will evolve your custom strategy.</p>
        </div>

        {/* Chat area */}
        <div className="flex-1 overflow-hidden border border-bg-border rounded-xl mx-4 mb-4 bg-bg-base">
          <ChatWindow
            messages={messages}
            onSend={handleSend}
            isTyping={isTyping}
            disabled={isComplete}
          />
        </div>

        {/* CTA */}
        {showCta && (
          <div className="px-4 pb-6 animate-slide-up">
            <button
              onClick={handleBeginEvolution}
              className="w-full py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold rounded-xl text-sm transition-all duration-200"
            >
              Begin Evolution →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
