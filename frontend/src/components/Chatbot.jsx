import { useState, useRef, useEffect } from 'react'

const QUESTIONS = [
  "What is your name, trader?",
  "How much capital do you want to invest? (in USD)",
  "What is your current portfolio value (existing holdings)?",
  "What is your monthly income?",
  "What is your risk appetite? (Conservative / Moderate / Aggressive)",
  "What is your investment horizon? (Short-term / Mid-term / Long-term)",
  "Are there any sectors you prefer? (e.g., Tech, Energy, Healthcare, or 'No preference')",
]

const PROFILE_KEYS = ['name', 'capital', 'portfolio', 'income', 'risk', 'horizon', 'sectors']

export default function Chatbot({ onComplete }) {
  const [messages, setMessages] = useState([
    { type: 'system', text: 'Initializing EvoTrade Neural Interface...' },
  ])
  const [qIndex, setQIndex] = useState(-1)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const answers = useRef({})
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  // Start first question after boot
  useEffect(() => {
    const t1 = setTimeout(() => {
      setMessages(m => [...m, { type: 'system', text: 'Connection established. Secure channel active.' }])
    }, 800)
    const t2 = setTimeout(() => {
      setMessages(m => [...m, { type: 'system', text: 'Welcome to EvoTrade. Let\'s build your trading profile.' }])
    }, 1800)
    const t3 = setTimeout(() => {
      setQIndex(0)
      setMessages(m => [...m, { type: 'question', text: QUESTIONS[0] }])
    }, 2800)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [])

  // Focus input when question appears
  useEffect(() => {
    if (qIndex >= 0 && !loading) inputRef.current?.focus()
  }, [qIndex, loading])

  const handleSubmit = (e) => {
    e.preventDefault()
    const val = input.trim()
    if (!val || loading) return

    answers.current[PROFILE_KEYS[qIndex]] = val
    setMessages(m => [...m, { type: 'user', text: val }])
    setInput('')

    const nextQ = qIndex + 1
    if (nextQ < QUESTIONS.length) {
      setTimeout(() => {
        setQIndex(nextQ)
        setMessages(m => [...m, { type: 'question', text: QUESTIONS[nextQ] }])
      }, 500)
    } else {
      // All questions answered → loading sequence
      setTimeout(() => {
        setLoading(true)
        setMessages(m => [...m, { type: 'system', text: 'Analyzing your financial profile...' }])
      }, 600)
    }
  }

  // Loading progress animation
  useEffect(() => {
    if (!loading) return
    const iv = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(iv)
          setTimeout(() => onComplete(answers.current), 400)
          return 100
        }
        return p + 2
      })
    }, 60)
    return () => clearInterval(iv)
  }, [loading, onComplete])

  const renderProgressBar = (label, pct) => {
    const filled = Math.floor(pct / 4)
    const bar = '█'.repeat(filled) + '░'.repeat(25 - filled)
    return (
      <div className="font-mono text-xs">
        <span className="text-evo-muted">{label} </span>
        <span className="text-evo-green">[{bar}]</span>
        <span className="text-evo-text ml-2">{pct}%</span>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-evo-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-evo-border flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-evo-green animate-pulse-green" />
        <span className="font-mono text-sm text-evo-green">EvoTrade Terminal</span>
        <span className="text-evo-muted text-xs font-mono">v1.0.0</span>
        <span className="ml-auto text-evo-muted text-xs font-mono">SESSION ACTIVE</span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className="animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
            {msg.type === 'system' && (
              <p className="font-mono text-sm text-evo-muted">
                <span className="text-evo-green">[EvoTrade]</span>{' '}
                <span className="text-evo-green/60">&gt;_</span> {msg.text}
              </p>
            )}
            {msg.type === 'question' && (
              <p className="font-mono text-sm text-evo-green">
                <span className="text-evo-green">[EvoTrade]</span>{' '}
                <span className="text-evo-green/60">&gt;_</span> {msg.text}
              </p>
            )}
            {msg.type === 'user' && (
              <p className="font-mono text-sm text-evo-text">
                <span className="text-evo-muted">&gt;</span> {msg.text}
              </p>
            )}
          </div>
        ))}

        {/* Loading progress */}
        {loading && (
          <div className="mt-4 space-y-2 animate-fade-in">
            {renderProgressBar('Risk Analysis   ', Math.min(progress * 1.2, 100) | 0)}
            {renderProgressBar('Data Processing ', Math.min(progress * 1.0, 100) | 0)}
            {renderProgressBar('Model Training  ', Math.min(progress * 0.85, 100) | 0)}
            <div className="mt-3 font-mono text-xs text-evo-muted">
              {progress < 100 ? 'Processing...' : '✓ Profile analysis complete.'}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit}
        className="px-6 py-4 border-t border-evo-border flex items-center gap-3">
        <span className="text-evo-green font-mono text-sm">&gt;</span>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading || qIndex < 0}
          placeholder={loading ? 'Analyzing...' : qIndex < 0 ? 'Initializing...' : 'Type your answer...'}
          className="flex-1 bg-transparent border-none outline-none font-mono text-sm text-evo-text
            placeholder:text-evo-muted/40 caret-evo-green"
        />
        {!loading && qIndex >= 0 && (
          <span className="w-2 h-4 bg-evo-green animate-blink" />
        )}
      </form>
    </div>
  )
}
