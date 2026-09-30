import type { ActionCategory } from '../types/api'
import { primaryActionableUri } from '../lib/plan'
import type { Action } from '../types/api'
import { ArrowUpRight, Link2, Hand, Settings2 } from 'lucide-react'
import { motion } from 'framer-motion'

const BADGE: Record<ActionCategory, { label: string; className: string }> = {
  auto: {
    label: 'AUTO',
    className: 'bg-mint text-accent ring-1 ring-accent/25',
  },
  manual: {
    label: 'MANUAL',
    className: 'bg-pale text-manual ring-1 ring-line',
  },
  critical: {
    label: 'CRITICAL',
    className: 'bg-critical/10 text-critical ring-1 ring-critical/25',
  },
}

interface ActionCardProps {
  index: number
  action: Action
}

function primaryDeeplinkMeta(action: Action): { uri: string; label: string } | null {
  for (const group of action.stepGroups ?? []) {
    const dl = group.actionableDeeplink
    if (dl?.deeplink) {
      const label = (dl.message || dl.description || action.actionName || '').trim()
      return { uri: dl.deeplink, label: label || 'Catalogue Settings screen' }
    }
  }
  return null
}

export function ActionCard({ index, action }: ActionCardProps) {
  const category = (action.category ?? 'manual') as ActionCategory
  const badge = BADGE[category] ?? BADGE.manual
  const uri = primaryActionableUri(action)
  const deeplinkMeta = primaryDeeplinkMeta(action)
  const steps = action.stepGroups?.flatMap((g) => g.steps) ?? []
  const showOpen = Boolean(uri)

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.05, 0.35), duration: 0.3 }}
      className={`sgte-card p-5 sm:p-6 ${
        category === 'critical' ? 'border-critical/30' : showOpen ? 'border-accent/30' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mint font-display text-sm font-bold text-accent">
          {String(index).padStart(2, '0')}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wider ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>

      <h3 className="mt-4 font-display text-xl font-bold tracking-tight text-navy">
        {action.actionName}
      </h3>
      {action.description ? (
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">{action.description}</p>
      ) : null}

      {steps.length > 0 ? (
        <ol className="mt-4 space-y-2 border-t border-line pt-4">
          {steps.map((step, i) => (
            <li key={`${i}-${step.slice(0, 24)}`} className="flex gap-3 text-sm text-ink">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-mint text-[10px] font-bold text-accent">
                {i + 1}
              </span>
              <span className="leading-relaxed">{step}</span>
            </li>
          ))}
        </ol>
      ) : null}

      {showOpen && uri && deeplinkMeta ? (
        <div className="mt-5 space-y-3 rounded-xl border border-accent/25 bg-mint/50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent">
                <Link2 className="h-3.5 w-3.5" aria-hidden />
                Verified catalogue deeplink
              </p>
              <p className="mt-0.5 text-xs font-medium text-ink-soft">
                Exact Settings screen from the official catalogue (not invented)
              </p>
              <p className="mt-2 text-sm font-semibold text-navy">{deeplinkMeta.label}</p>
              <p
                className="mt-1 break-all font-mono text-[11px] leading-relaxed text-muted"
                title={deeplinkMeta.uri}
              >
                {deeplinkMeta.uri}
              </p>
            </div>
            <a
              href={uri}
              className="sgte-btn-primary inline-flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              aria-label={`Open Settings for ${action.actionName}`}
            >
              <Settings2 className="h-4 w-4" aria-hidden />
              Open Settings
              <ArrowUpRight className="h-4 w-4" aria-hidden />
            </a>
          </div>
        </div>
      ) : (
        <div className="mt-5 rounded-xl border border-line bg-pale p-4">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
            <Hand className="h-3.5 w-3.5" aria-hidden />
            Manual-only action
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            No verified catalogue deeplink — follow the guidance manually. No valid catalogue URI is
            attached for this action.
          </p>
        </div>
      )}
    </motion.article>
  )
}
