import React from 'react'

const TOTAL = 5

export function GenerationProgress({ current, completed }: { current: number; completed: number }) {
  return (
    <div className="flex gap-3 items-center">
      {Array.from({ length: TOTAL }, (_, i) => {
        const gen = i + 1
        const isDone = gen <= completed
        const isActive = gen === current && gen > completed
        return (
          <div
            key={gen}
            className={`flex-1 h-10 rounded-lg border flex items-center justify-center text-sm font-mono transition-all duration-500 ${
              isDone
                ? 'bg-accent-primary/15 border-accent-primary text-accent-primary'
                : isActive
                ? 'bg-accent-secondary/15 border-accent-secondary text-accent-secondary animate-pulse'
                : 'bg-bg-elevated border-bg-border text-text-muted'
            }`}
          >
            Gen {gen}
          </div>
        )
      })}
    </div>
  )
}
