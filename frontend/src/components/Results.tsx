import { motion } from 'framer-motion'
import { FileText } from 'lucide-react'
import type { TroubleshootResponse } from '../types/api'
import { countIssues, flattenActions, hasAnyDeeplink } from '../lib/plan'
import { ActionCard } from './ActionCard'
import { CacheBanner } from './CacheBanner'
import { InsightsPanel } from './InsightsPanel'
import { WhySection } from './WhySection'

interface ResultsProps {
  data: TroubleshootResponse
}

export function Results({ data }: ResultsProps) {
  const contexts = data.response.contexts ?? []
  const actions = flattenActions(data)
  const issueCount = countIssues(data)
  const titles = contexts.map((c) => c.title).filter(Boolean)
  const primaryTitle = titles[0] || 'Your guided steps'
  const mode = String(data.meta.execution_mode || 'UNKNOWN').toUpperCase()
  const deeplinkActions = actions.filter(({ action }) =>
    action.stepGroups?.some((g) => g.actionableDeeplink?.deeplink),
  ).length

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="mx-auto w-full max-w-6xl px-5 pb-24 pt-6 sm:px-8"
    >
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.9fr)] lg:items-start">
        <div className="min-w-0 space-y-6">
          <header className="sgte-card overflow-hidden p-0">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-mint/50 px-5 py-3.5">
              <div className="inline-flex items-center gap-2 text-accent">
                <FileText className="h-4 w-4" aria-hidden />
                <p className="text-xs font-semibold uppercase tracking-[0.16em]">
                  Diagnostic report
                </p>
              </div>
              <p className="rounded-full border border-line bg-white px-2.5 py-1 text-[10px] font-bold tracking-wider text-ink-soft">
                {mode}
              </p>
            </div>

            <div className="px-5 py-5 sm:px-6">
              <h1 className="font-display text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">
                {primaryTitle}
              </h1>

              <div className="mt-5 rounded-xl border border-line bg-pale px-4 py-3.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Original user query
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink sm:text-base">
                  &ldquo;{data.query}&rdquo;
                </p>
              </div>

              <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-line bg-white px-3 py-2.5">
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                    Issue
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-navy">
                    {titles.length > 1 ? titles.join(' · ') : primaryTitle}
                  </dd>
                </div>
                <div className="rounded-xl border border-line bg-white px-3 py-2.5">
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                    Actions
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-navy">
                    {issueCount === 1 ? '1 issue' : `${issueCount} issues`}
                    {actions.length ? ` · ${actions.length} steps` : ''}
                  </dd>
                </div>
                <div className="rounded-xl border border-line bg-white px-3 py-2.5">
                  <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                    Catalogue links
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-navy">
                    {hasAnyDeeplink(data)
                      ? `${deeplinkActions} verified`
                      : 'None on this plan'}
                  </dd>
                </div>
              </dl>
            </div>
          </header>

          <CacheBanner meta={data.meta} />

          <div>
            <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-[0.12em] text-muted">
              Recommended actions
            </h2>
            <div className="space-y-4">
              {actions.map(({ action, index }) => (
                <ActionCard key={`${index}-${action.actionName}`} index={index} action={action} />
              ))}
            </div>
          </div>

          <WhySection data={data} />
        </div>

        <aside className="min-w-0 space-y-4 lg:sticky lg:top-20">
          <InsightsPanel data={data} />
        </aside>
      </div>
    </motion.section>
  )
}
