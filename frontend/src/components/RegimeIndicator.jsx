/**
 * RegimeIndicator.jsx — Coloured badge showing current market regime.
 */

const REGIME_CONFIG = {
  bull:     { label: 'Bull',     dot: 'bg-emerald-400', badge: 'bg-emerald-900/60 text-emerald-300 border border-emerald-700', pulse: true },
  bear:     { label: 'Bear',     dot: 'bg-red-400',     badge: 'bg-red-900/60 text-red-300 border border-red-700',         pulse: false },
  sideways: { label: 'Sideways', dot: 'bg-yellow-400',  badge: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700', pulse: false },
  crash:    { label: 'Crash',    dot: 'bg-rose-400',    badge: 'bg-rose-900/60 text-rose-300 border border-rose-700',       pulse: true },
}

const DEFAULT = { label: 'Detecting…', dot: 'bg-gray-500', badge: 'bg-gray-800 text-gray-400 border border-gray-700', pulse: false }

export default function RegimeIndicator({ regime }) {
  const cfg = REGIME_CONFIG[regime?.toLowerCase()] || DEFAULT

  return (
    <span className={`badge ${cfg.badge} gap-2`}>
      <span className="relative flex h-2 w-2">
        {cfg.pulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${cfg.dot}`} />
      </span>
      {cfg.label}
    </span>
  )
}
