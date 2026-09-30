import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Battery, Hand, MonitorSmartphone, Wifi } from 'lucide-react'

/** Decorative smartphone visualization — not live device telemetry. */
export function PhoneStudio({ activeLabel }: { activeLabel?: string | null }) {
  const active = (activeLabel || '').toLowerCase()
  const highlight = (...keys: string[]) =>
    keys.some((k) => active.includes(k)) ? 'opacity-100 ring-1 ring-cyan/40' : 'opacity-85'

  return (
    <div className="relative mx-auto flex h-full min-h-[360px] w-full max-w-[380px] items-center justify-center overflow-hidden lg:min-h-[480px]">
      <div className="pointer-events-none absolute inset-6 rounded-full sgte-orb opacity-80 blur-2xl" aria-hidden />

      <motion.div
        className="pointer-events-none absolute h-[76%] w-[76%] rounded-full border border-accent/25"
        animate={{ scale: [1, 1.03, 1], opacity: [0.4, 0.65, 0.4] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        aria-hidden
      />
      <motion.div
        className="pointer-events-none absolute h-[90%] w-[90%] rounded-full border border-dashed border-cyan/30"
        animate={{ rotate: 360 }}
        transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
        aria-hidden
      />

      {/* Floating labels */}
      <FloatLabel className="absolute left-0 top-[18%] hidden sm:flex" delay={0.1} icon={<Battery className="h-3 w-3" />}>
        Battery
      </FloatLabel>
      <FloatLabel className="absolute right-0 top-[30%] hidden sm:flex" delay={0.2} icon={<MonitorSmartphone className="h-3 w-3" />}>
        Display
      </FloatLabel>
      <FloatLabel className="absolute right-1 bottom-[28%] hidden sm:flex" delay={0.3} icon={<Wifi className="h-3 w-3" />}>
        Connectivity
      </FloatLabel>
      <FloatLabel className="absolute left-1 bottom-[16%] hidden sm:flex" delay={0.4} icon={<Hand className="h-3 w-3" />}>
        Touch
      </FloatLabel>

      <motion.div
        className="relative z-10 w-[200px] sm:w-[228px]"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Phone chrome */}
        <div className="rounded-[2.1rem] bg-gradient-to-b from-[#1a3d32] via-navy to-[#032e23] p-[3px] shadow-[0_28px_50px_-20px_rgba(6,78,59,0.55)]">
          <div className="rounded-[1.95rem] bg-gradient-to-b from-[#0a5c45] to-navy p-2">
            <div className="relative overflow-hidden rounded-[1.55rem] bg-gradient-to-b from-[#0b6b4f] via-navy to-[#032e23]">
              <div className="absolute left-1/2 top-2.5 z-20 h-4 w-[4.5rem] -translate-x-1/2 rounded-full bg-black/35" />
              {/* Screen sheen */}
              <div
                className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent"
                aria-hidden
              />

              <div className="relative flex aspect-[9/17.8] flex-col px-3.5 pb-4 pt-10">
                <p className="text-center font-display text-[10px] font-bold uppercase tracking-[0.22em] text-cyan">
                  Studio scan
                </p>
                <p className="mt-1 text-center text-[11px] text-white/70">Grounded diagnostics</p>

                <motion.div
                  className="pointer-events-none absolute inset-x-3 top-14 h-px bg-gradient-to-r from-transparent via-cyan/80 to-transparent"
                  animate={{ top: ['20%', '76%', '20%'] }}
                  transition={{ duration: 5.8, repeat: Infinity, ease: 'easeInOut' }}
                  aria-hidden
                />

                <div className="mt-7 flex flex-1 flex-col justify-center gap-2.5">
                  <MetricRow icon={<Battery className="h-3.5 w-3.5" />} label="Battery" tone={highlight('battery')} />
                  <MetricRow
                    icon={<MonitorSmartphone className="h-3.5 w-3.5" />}
                    label="Display"
                    tone={highlight('display')}
                  />
                  <MetricRow icon={<Hand className="h-3.5 w-3.5" />} label="Touch" tone={highlight('touch')} />
                </div>

                <div className="mt-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-center backdrop-blur-sm">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-cyan">Evidence-first</p>
                  <p className="mt-0.5 text-[11px] text-white/75">Abstain when unsure</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

function MetricRow({
  icon,
  label,
  tone,
}: {
  icon: ReactNode
  label: string
  tone: string
}) {
  return (
    <div className={`flex items-center gap-2 rounded-xl border border-white/10 bg-white/8 px-2.5 py-2 transition ${tone}`}>
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan/20 text-cyan">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-white">{label}</p>
        <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/15">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-cyan to-accent"
            initial={{ width: '40%' }}
            animate={{ width: ['40%', '70%', '52%', '65%'] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>
      </div>
    </div>
  )
}

function FloatLabel({
  children,
  className,
  delay,
  icon,
}: {
  children: ReactNode
  className?: string
  delay: number
  icon: ReactNode
}) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className={`z-20 items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-navy shadow-sm ${className ?? ''}`}
    >
      <span className="text-accent">{icon}</span>
      {children}
    </motion.span>
  )
}
