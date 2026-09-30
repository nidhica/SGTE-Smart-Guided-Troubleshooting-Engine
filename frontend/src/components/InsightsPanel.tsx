import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Sparkles, ShieldCheck, ListTree, Zap, GitBranch } from 'lucide-react'
import type { TroubleshootResponse } from '../types/api'
import { countIssues, flattenActions, formatCost, formatLatency, hasAnyDeeplink } from '../lib/plan'

interface InsightsPanelProps {
  data: TroubleshootResponse
}

export function InsightsPanel({ data }: InsightsPanelProps) {
  const [open, setOpen] = useState(false)
  const issues = countIssues(data)
  const actions = flattenActions(data)
  const titles = (data.response.contexts ?? []).map((c) => c.title).filter(Boolean)
  const deeplinkCount = actions.filter(({ action }) =>
    action.stepGroups?.some((g) => g.actionableDeeplink?.deeplink),
  ).length
  const latency = formatLatency(data.meta.latency_ms)
  const cost = formatCost(data.meta.cost_usd)

  return (
    <section className="overflow-hidden rounded-2xl border border-line bg-gradient-to-b from-navy to-[#043528] text-white shadow-lg">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-2 font-display text-sm font-semibold tracking-wide">
          <Sparkles className="h-4 w-4 text-cyan" aria-hidden />
          SGTE Insights
        </span>
        <ChevronDown className={`h-4 w-4 text-white/70 transition ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-white/10"
          >
            <div className="border-b border-white/10 px-5 py-4">
              <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-cyan">
                <GitBranch className="h-3.5 w-3.5" aria-hidden />
                Pipeline
              </p>
              <ol className="mt-3 space-y-2 text-sm text-white/85">
                <li>
                  <span className="text-white/45">1.</span> User issue
                </li>
                <li>
                  <span className="text-white/45">2.</span> SGTE understands
                </li>
                <li>
                  <span className="text-white/45">3.</span> Evidence grounded
                </li>
                <li>
                  <span className="text-white/45">4.</span> Action plan
                  {titles[0] ? (
                    <span className="block pl-4 text-xs text-white/55">→ {titles[0]}</span>
                  ) : null}
                </li>
                <li>
                  <span className="text-white/45">5.</span>{' '}
                  {hasAnyDeeplink(data)
                    ? 'Settings deeplink available'
                    : 'Settings deeplink when available'}
                </li>
              </ol>
            </div>

            <div className="grid gap-4 px-5 py-5 sm:grid-cols-2">
              <InsightBlock
                icon={<ListTree className="h-4 w-4" />}
                title="Query"
                rows={[
                  ['Input', data.query],
                  ['Plan title(s)', titles.join(' · ') || '—'],
                  ['Issues (contexts)', String(issues)],
                  ['Actions', String(actions.length)],
                ]}
              />
              <InsightBlock
                icon={<Zap className="h-4 w-4" />}
                title="Cache"
                rows={[
                  ['Status', data.meta.cache_hit ? 'HIT · Fast path' : 'MISS · Cold path'],
                  ...(latency ? ([['Latency', latency]] as [string, string][]) : []),
                  ...(cost ? ([['Cost', cost]] as [string, string][]) : []),
                  ...(data.meta.model ? ([['Model', data.meta.model]] as [string, string][]) : []),
                  [
                    'Execution',
                    String(data.meta.execution_mode || 'UNKNOWN').toUpperCase(),
                  ],
                ]}
              />
              <InsightBlock
                icon={<ShieldCheck className="h-4 w-4" />}
                title="Deeplink"
                rows={[
                  ['Actions with Settings link', String(deeplinkCount)],
                  [
                    'Catalogue links present',
                    hasAnyDeeplink(data) ? 'Yes' : 'None on this plan',
                  ],
                ]}
              />
              <InsightBlock
                icon={<Sparkles className="h-4 w-4" />}
                title="Response"
                rows={[
                  ['Fallback', data.meta.fallback ?? 'none'],
                  ['Variations', String(data.query_variations?.length ?? 0)],
                ]}
              />
            </div>
            {data.query_variations?.length ? (
              <div className="border-t border-white/10 px-5 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-white/50">
                  Query variations
                </p>
                <ul className="mt-2 max-h-40 space-y-1.5 overflow-y-auto text-xs text-white/75">
                  {data.query_variations.map((v) => (
                    <li key={v} className="leading-snug">
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  )
}

function InsightBlock({
  icon,
  title,
  rows,
}: {
  icon: ReactNode
  title: string
  rows: [string, string][]
}) {
  return (
    <div className="rounded-xl bg-white/5 p-3.5 ring-1 ring-white/10">
      <p className="mb-2 inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-cyan">
        {icon}
        {title}
      </p>
      <dl className="space-y-1.5">
        {rows.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[1fr_1.4fr] gap-2 text-xs">
            <dt className="text-white/45">{k}</dt>
            <dd className="break-words text-white/90">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
