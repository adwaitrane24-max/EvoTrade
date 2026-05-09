import React from 'react'
import { Signal } from '../../types'

export function SignalBadge({ signal }: { signal: Signal }) {
  const cls = {
    BUY: 'badge-buy',
    SELL: 'badge-sell',
    HOLD: 'badge-hold',
  }[signal]
  return <span className={cls}>{signal}</span>
}
