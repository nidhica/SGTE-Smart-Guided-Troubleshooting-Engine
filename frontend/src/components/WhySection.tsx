import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import type { TroubleshootResponse } from '../types/api'
import { hasAnyDeeplink } from '../lib/plan'

interface WhySectionProps {
  data: TroubleshootResponse
}

export function WhySection({ data }: WhySectionProps) {
  const [open, setOpen] = useState(false)
  const titles = (data.response.contexts ?? []).map((c) => c.title).filter(Boolean)
  const hasPlan = titles.length > 0
  const deeplink = hasAnyDeeplink(data)

  return (
    <section className="rounded-2xl border border-line bg-white">
      <button
        type="button"
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="font-display text-sm font-semibold text-navy">
          Why these recommendations?
        </span>
        <ChevronDown
          className={`h-4 w-4 text-ink-soft transition ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-line"
          >
            <div className="space-y-4 px-5 py-4 text-sm leading-relaxed text-ink">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Issue understood as
                </p>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-ink-soft">
                  {hasPlan ? (
                    titles.map((t) => (
                      <li key={t}>
                        <span className="font-medium text-ink">Plan title:</span> {t}
                      </li>
                    ))
                  ) : (
                    <li>No confident issue path from available evidence</li>
                  )}
                </ul>
              </div>

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Evidence
                </p>
                <p className="mt-1.5 text-ink-soft">
                  {hasPlan
                    ? 'Relevant Samsung troubleshooting guidance was selected and used to ground the recommended actions.'
                    : 'No sufficiently relevant troubleshooting evidence was available for this issue.'}
                </p>
              </div>

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Validation
                </p>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-ink-soft">
                  <li>Actions were checked against the identified issue.</li>
                  <li>Unrelated evidence was excluded when it did not fit.</li>
                  <li>
                    {deeplink
                      ? 'At least one action includes an exact Settings catalogue deeplink.'
                      : 'No Settings catalogue deeplink was attached to this plan.'}
                  </li>
                </ul>
              </div>

              {data.query_variations?.length ? (
                <p className="text-xs text-muted">
                  {data.query_variations.length} query variations were prepared for semantic cache
                  coverage (API metadata).
                </p>
              ) : null}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  )
}
