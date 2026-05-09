import React from 'react'
import { motion } from 'framer-motion'
import { Chromosome } from '../../types'

function fmt(key: string, val: number): string {
  if (key.includes('pct') || key.includes('weight')) return `${(val * 100).toFixed(1)}%`
  if (key.includes('ma_')) return `${Math.round(val)}`
  return val.toFixed(1)
}

export function ChromosomeCard({ chrom, isTop }: { chrom: Chromosome; isTop?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25 }}
      className={`rounded-xl border p-4 transition-all duration-300 ${
        isTop
          ? 'bg-accent-primary/5 border-accent-primary/40 shadow-[0_0_12px_rgba(59,130,246,0.15)]'
          : 'bg-bg-surface border-bg-border opacity-60'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-text-muted font-mono">{chrom.id}</span>
        {chrom.fitness !== undefined && (
          <span className={`text-sm font-mono font-semibold ${isTop ? 'text-accent-primary' : 'text-text-secondary'}`}>
            {chrom.fitness.toFixed(4)}
          </span>
        )}
      </div>
      {chrom.genes && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(chrom.genes).slice(0, 6).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs">
              <span className="text-text-muted truncate">{k.replace(/_/g, ' ')}</span>
              <span className="font-mono text-text-secondary ml-1">{fmt(k, v as number)}</span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
