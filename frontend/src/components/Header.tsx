import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Info, X } from 'lucide-react'

interface HeaderProps {
  onNew?: () => void
  showNew?: boolean
}

export function Header({ onNew, showNew }: HeaderProps) {
  const [aboutOpen, setAboutOpen] = useState(false)

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-line bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-3.5 sm:px-8">
          <button
            type="button"
            onClick={onNew}
            className="group min-w-0 text-left"
            aria-label="SGTE home — new troubleshooting session"
          >
            <p className="font-display text-xl font-extrabold tracking-tight text-navy transition group-hover:text-accent sm:text-2xl">
              SGTE
            </p>
            <p className="hidden text-[11px] tracking-wide text-ink-soft sm:block">
              Smart Guided Troubleshooting Engine
            </p>
          </button>

          <nav className="flex items-center gap-2 sm:gap-3" aria-label="Primary">
            {showNew && onNew ? (
              <button
                type="button"
                onClick={onNew}
                className="rounded-full border border-line bg-white px-3.5 py-1.5 text-sm font-medium text-ink transition hover:border-accent/40 hover:bg-mint"
              >
                New session
              </button>
            ) : null}

            <button
              type="button"
              onClick={() => setAboutOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1.5 text-sm font-medium text-ink-soft transition hover:border-accent/40 hover:text-navy"
            >
              <Info className="h-3.5 w-3.5" aria-hidden />
              <span className="hidden sm:inline">About</span>
            </button>
          </nav>
        </div>
      </header>

      <AnimatePresence>
        {aboutOpen ? (
          <motion.div
            className="fixed inset-0 z-50 flex items-end justify-center bg-navy/35 p-4 backdrop-blur-sm sm:items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setAboutOpen(false)}
            role="presentation"
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-labelledby="sgte-about-title"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              onClick={(e) => e.stopPropagation()}
              className="sgte-card relative w-full max-w-lg p-6 text-left"
            >
              <button
                type="button"
                className="absolute right-4 top-4 rounded-full p-1.5 text-ink-soft transition hover:bg-mint hover:text-navy"
                onClick={() => setAboutOpen(false)}
                aria-label="Close about"
              >
                <X className="h-4 w-4" />
              </button>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">About</p>
              <h2 id="sgte-about-title" className="mt-2 font-display text-2xl font-bold text-navy">
                Smart Guided Troubleshooting Engine
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">
                SGTE turns a natural-language Galaxy device complaint into an evidence-grounded
                action plan. It retrieves Samsung SIIS troubleshooting guidance and attaches exact
                official-catalogue Settings deeplinks when available. When evidence is insufficient,
                it returns <span className="font-medium text-ink">no_match</span> instead of
                inventing steps.
              </p>
              <ul className="mt-4 space-y-2 rounded-xl border border-line bg-mint/50 p-4 text-sm text-ink-soft">
                <li>· Samsung PRISM GenAI Hackathon 2026</li>
                <li>· Demo may run in MOCK mode — not live-provider validation</li>
                <li>· Production authorization gate remains unsatisfied</li>
              </ul>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  )
}
