import { motion } from 'framer-motion'
import { BookOpen, Zap } from 'lucide-react'
import { formatLatency } from '../lib/plan'
import type { TroubleshootMeta } from '../types/api'

interface CacheBannerProps {
  meta: TroubleshootMeta
}

export function CacheBanner({ meta }: CacheBannerProps) {
  const latency = formatLatency(meta.latency_ms)
  const mode = String(meta.execution_mode || '').toUpperCase()

  if (meta.cache_hit) {
    return (
      <motion.aside
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3 rounded-2xl border border-accent/25 bg-mint px-4 py-3 text-ink"
        role="status"
      >
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-accent text-white">
          <Zap className="h-4 w-4" aria-hidden />
        </span>
        <div>
          <p className="font-display text-sm font-bold text-navy">Fast path</p>
          <p className="mt-0.5 text-sm text-ink-soft">
            Response served from cache
            {latency ? ` · ${latency}` : ''}
            {mode ? ` · ${mode}` : ''}
          </p>
        </div>
      </motion.aside>
    )
  }

  return (
    <motion.aside
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3 rounded-2xl border border-line bg-white px-4 py-3 text-ink"
      role="status"
    >
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-mint text-accent">
        <BookOpen className="h-4 w-4" aria-hidden />
      </span>
      <div>
        <p className="font-display text-sm font-bold text-navy">Evidence-grounded response</p>
        <p className="mt-0.5 text-sm text-ink-soft">
          Built from retrieved troubleshooting evidence
          {latency ? ` · ${latency}` : ''}
          {mode ? ` · ${mode}` : ''}
        </p>
      </div>
    </motion.aside>
  )
}
