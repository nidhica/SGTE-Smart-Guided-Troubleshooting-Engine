import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, SearchX, FileWarning, Inbox } from 'lucide-react'

export type FallbackKind = 'no_match' | 'no_siis_context' | 'empty_plan'

interface FallbackStateProps {
  kind: FallbackKind
  query?: string
  onRetry: () => void
}

function noMatchEvidenceNote(query: string | undefined): string {
  const q = (query || '').toLowerCase()
  if (
    /\bflicker/.test(q) &&
    /\b(display|screen)\b/.test(q) &&
    !/\b(camera|video|recorded)\b/.test(q)
  ) {
    return 'The available troubleshooting evidence does not contain a sufficiently relevant path for this display-flicker issue.'
  }
  if (/\bcake\b|\brecipe\b|\bcook\b|\bbread\b|\bbake\b|\bsourdough\b/.test(q)) {
    return 'This request is outside device troubleshooting scope, so SGTE abstains rather than inventing steps.'
  }
  return 'The available troubleshooting evidence did not contain a sufficiently relevant path for this specific issue.'
}

export function FallbackState({ kind, query, onRetry }: FallbackStateProps) {
  const [whyOpen, setWhyOpen] = useState(kind === 'no_match')

  if (kind === 'no_match') {
    return (
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-xl px-5 py-14 sm:px-8"
      >
        <div className="text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-line bg-mint">
            <SearchX className="h-6 w-6 text-accent" aria-hidden />
          </div>
          <h2 className="font-display text-2xl font-bold text-navy">
            We couldn&apos;t find a supported solution.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-soft">
            Try describing the symptoms in more detail. SGTE only provides troubleshooting steps when
            sufficient evidence exists.
          </p>
          {query ? (
            <p className="mt-4 rounded-xl border border-line bg-white px-4 py-3 text-left text-sm text-ink">
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-muted">
                Your query
              </span>
              <span className="mt-1 block">&ldquo;{query}&rdquo;</span>
            </p>
          ) : null}
        </div>

        <div className="mt-6 rounded-2xl border border-line bg-white px-4 py-4 text-left">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
            Try describing
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-soft">
            <li>what you see on the screen</li>
            <li>when the problem happens</li>
            <li>what you were trying to do</li>
          </ul>
        </div>

        <div className="mt-4 rounded-2xl border border-line bg-white">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3.5 text-left"
            onClick={() => setWhyOpen((v) => !v)}
            aria-expanded={whyOpen}
          >
            <span className="font-display text-sm font-semibold text-navy">
              Why no recommendation?
            </span>
            <ChevronDown
              className={`h-4 w-4 text-ink-soft transition ${whyOpen ? 'rotate-180' : ''}`}
              aria-hidden
            />
          </button>
          <AnimatePresence initial={false}>
            {whyOpen ? (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden border-t border-line"
              >
                <p className="px-4 py-3.5 text-sm leading-relaxed text-ink-soft">
                  {noMatchEvidenceNote(query)} This is an intentional abstention, not a system
                  failure.
                </p>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>

        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onRetry}
            className="sgte-btn-primary rounded-full px-5 py-2.5 text-sm font-semibold"
          >
            New session
          </button>
        </div>
      </motion.section>
    )
  }

  const other =
    kind === 'no_siis_context'
      ? {
          title: 'Troubleshooting context is required',
          body: 'This request needs usable troubleshooting evidence or support context before grounded steps can be produced.',
          icon: 'file' as const,
        }
      : {
          title: 'No troubleshooting actions were returned',
          body: 'SGTE completed the request, but the response did not include any actions. Try a different description or add optional support context.',
          icon: 'inbox' as const,
        }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-xl px-5 py-16 text-center sm:px-8"
    >
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-line bg-white">
        {other.icon === 'file' ? (
          <FileWarning className="h-6 w-6 text-warn" aria-hidden />
        ) : (
          <Inbox className="h-6 w-6 text-ink-soft" aria-hidden />
        )}
      </div>
      <h2 className="font-display text-2xl font-bold text-navy">{other.title}</h2>
      <p className="mt-3 text-sm leading-relaxed text-ink-soft">{other.body}</p>
      <button
        type="button"
        onClick={onRetry}
        className="sgte-btn-primary mt-8 rounded-full px-5 py-2.5 text-sm font-semibold"
      >
        New session
      </button>
    </motion.section>
  )
}
