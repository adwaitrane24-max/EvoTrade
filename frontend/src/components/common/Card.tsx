import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean
}

export function Card({ elevated, className = '', children, ...props }: CardProps) {
  const bg = elevated ? 'bg-bg-elevated' : 'bg-bg-surface'
  return (
    <div
      className={`${bg} border border-bg-border rounded-xl p-6 hover:border-accent-primary/20 transition-all duration-200 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
