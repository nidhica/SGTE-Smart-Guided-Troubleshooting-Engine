import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

/** Illustrative pipeline stages — not live backend telemetry. */
const STAGES = [
  { id: 'understand', label: 'Understanding issue' },
  { id: 'evidence', label: 'Finding relevant evidence' },
  { id: 'plan', label: 'Building troubleshooting plan' },
  { id: 'check', label: 'Checking actions' },
  { id: 'settings', label: 'Resolving Settings actions' },
] as const

interface AnalyzingProps {
  active: boolean
}

export function Analyzing({ active }: AnalyzingProps) {
  const [focus, setFocus] = useState(0)

  useEffect(() => {
    if (!active) return
    setFocus(0)
    const timers = [
      window.setTimeout(() => setFocus(1), 400),
      window.setTimeout(() => setFocus(2), 900),
      window.setTimeout(() => setFocus(3), 1400),
      window.setTimeout(() => setFocus(4), 1900),
    ]
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [active])

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="mx-auto flex w-full max-w-xl flex-col items-center px-5 py-16 sm:px-8"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="relative mb-8 flex h-16 w-16 items-center justify-center">
        <motion.span
          className="absolute inset-0 rounded-full border-2 border-accent/25"
          animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0.2, 0.5] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          aria-hidden
        />
        <motion.span
          className="absolute inset-2 rounded-full border-2 border-cyan/40 border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.95, ease: 'linear' }}
          aria-hidden
        />
        <span className="h-3 w-3 rounded-full bg-accent" aria-hidden />
      </div>
      <h2 className="font-display text-2xl font-bold tracking-tight text-navy">
        Building your troubleshooting plan…
      </h2>
      <p className="mt-2 text-center text-sm text-ink-soft">
        Working through the diagnosis pipeline. Stage highlights are illustrative while the request
        is in flight — not live progress percentages.
      </p>

      <ol className="mt-10 w-full space-y-2.5">
        {STAGES.map((stage, i) => {
          const current = i === focus
          const passed = i < focus
          return (
            <li
              key={stage.id}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition ${
                current
                  ? 'border-accent/35 bg-white sgte-glow'
                  : passed
                    ? 'border-line bg-mint/40'
                    : 'border-transparent bg-transparent opacity-45'
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                  current
                    ? 'bg-accent text-white'
                    : passed
                      ? 'bg-mint text-accent'
                      : 'border border-line text-muted'
                }`}
                aria-hidden
              >
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">{stage.label}</p>
                {current ? (
                  <p className="text-xs text-accent">In progress</p>
                ) : passed ? (
                  <p className="text-xs text-ink-soft">Continuing…</p>
                ) : (
                  <p className="text-xs text-muted">Waiting</p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </motion.section>
  )
}
