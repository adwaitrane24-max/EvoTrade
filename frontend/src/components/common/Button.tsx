import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: ButtonProps) {
  const base = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-accent-primary hover:bg-accent-primary/90 text-white',
    ghost: 'border border-bg-border text-text-secondary hover:border-accent-primary/40 hover:text-text-primary',
    danger: 'bg-signal-sell/10 border border-signal-sell/40 text-signal-sell hover:bg-signal-sell/20',
  }
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  }
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}
