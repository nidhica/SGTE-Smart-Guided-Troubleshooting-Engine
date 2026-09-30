import { useId, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowRight,
  BatteryCharging,
  ChevronDown,
  Info,
  MessageSquareText,
  MonitorSmartphone,
  Search,
  Settings2,
  Wifi,
  Hand,
  Stethoscope,
} from 'lucide-react'
import { PhoneStudio } from './PhoneStudio'
import { CATEGORY_FLOWS, type CategoryFlow } from '../lib/categories'

const EXAMPLES: { label: string; query: string }[] = [
  { label: 'Black screen', query: 'My phone screen is completely black.' },
  {
    label: 'Screen flickering',
    query: 'My display keeps flickering whenever I open an app.',
  },
  {
    label: 'Touch not responding',
    query: 'My phone detects my touch very slowly and sometimes doesn\'t respond.',
  },
  {
    label: 'Screen cracked',
    query: 'My phone screen is cracked and I can barely see the display.',
  },
  {
    label: 'Change time format',
    query: 'I want to change the time format on my phone to 24 hour.',
  },
]

/** Official-pack demo chips (Phase 15). */
const DEMO_SCENARIOS: { label: string; query: string; hint: string }[] = [
  {
    label: 'A · Supported',
    hint: 'Official Q2 — supported black-screen plan',
    query:
      'My Galaxy S22 screen turns completely blank or white and no text appears when I search for a stock price or use the Smart Tutor app, and it happens with other apps too.',
  },
  {
    label: 'B · Catalogue link',
    hint: 'Official Q19 — may include exact catalogue deeplink',
    query:
      'My Galaxy S22 screen inputs are delayed and the touch responsiveness is laggy, causing a noticeable delay when I try to interact with the phone.',
  },
  {
    label: 'C · Multi-symptom',
    hint: 'Official Q1 — blank/flash + Gmail context',
    query:
      'My Samsung A115G tablet screen flashes and then goes completely blank whenever I tap to open an email in Gmail, and after it works for a short time it goes blank again.',
  },
  {
    label: 'D · Abstain',
    hint: 'Out-of-scope — should abstain (no_match)',
    query: 'How do I bake sourdough bread in a home oven?',
  },
  {
    label: 'E · Unresolved',
    hint: 'Official Q5 — unresolved / corpus-limited evidence',
    query:
      'My Galaxy tablet screen stays completely blank when I try to use Smart Switch to scan the QR code for transferring data from my Galaxy S25 phone, so the transfer can\'t proceed.',
  },
]

/** Category cards populate grounded example text only — they never invent a diagnosis. */
const CATEGORY_ICONS: Record<CategoryFlow['id'], typeof BatteryCharging> = {
  battery: BatteryCharging,
  display: MonitorSmartphone,
  touch: Hand,
  connectivity: Wifi,
}

const HOW_STEPS = [
  {
    title: 'Describe',
    body: 'Tell us the issue and when it happens — in everyday language.',
    icon: MessageSquareText,
  },
  {
    title: 'Diagnose',
    body: 'SGTE retrieves Samsung support evidence and builds a grounded plan when sufficient support exists.',
    icon: Search,
  },
  {
    title: 'Resolve',
    body: 'Follow ordered steps and open verified Settings deeplinks when the catalogue matches.',
    icon: Settings2,
  },
]

interface LandingProps {
  onSubmit: (query: string, siis?: string) => void
  disabled?: boolean
  demoMode?: boolean
}

export function Landing({ onSubmit, disabled, demoMode }: LandingProps) {
  const [query, setQuery] = useState('')
  const [siis, setSiis] = useState('')
  const [showSiis, setShowSiis] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const queryId = useId()
  const siisId = useId()
  const canSubmit = query.trim().length > 0 && !disabled

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
      className="pb-24"
    >
      <section className="mx-auto grid w-full max-w-6xl gap-10 px-5 pt-8 sm:px-8 sm:pt-10 lg:grid-cols-[minmax(0,1.12fr)_minmax(280px,0.88fr)] lg:items-center lg:gap-12">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
            SGTE | Troubleshooting Studio
          </div>

          <h1 className="mt-5 font-display text-[2.15rem] font-extrabold leading-[1.12] tracking-tight text-navy sm:text-4xl lg:text-[2.7rem]">
            Something wrong with
            <br />
            <span className="sgte-gradient-text">your device?</span>
          </h1>

          <p className="mt-4 max-w-xl text-base leading-relaxed text-ink-soft sm:text-[1.05rem]">
            Get clear, grounded troubleshooting steps for your Samsung device. SGTE uses verified
            Samsung support evidence and provides exact Settings links when available.
          </p>

          <form
            className="mt-8"
            onSubmit={(e) => {
              e.preventDefault()
              if (!canSubmit) return
              onSubmit(query.trim(), showSiis ? siis : undefined)
            }}
          >
            <label htmlFor={queryId} className="sr-only">
              Device issue description
            </label>
            <div className="sgte-input-shell rounded-2xl p-2.5">
              <div className="flex gap-2 px-2 pt-2">
                <Stethoscope className="mt-1 h-5 w-5 shrink-0 text-accent" aria-hidden />
                <textarea
                  id={queryId}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value)
                    setActiveCategory(null)
                  }}
                  rows={3}
                  maxLength={2000}
                  placeholder="Describe what's wrong with your device..."
                  disabled={disabled}
                  className="w-full resize-y rounded-xl border-0 bg-transparent py-1 text-base leading-relaxed text-ink placeholder:text-muted focus:outline-none focus:ring-0 disabled:opacity-50"
                />
              </div>
              <div className="mt-2 flex flex-col gap-3 px-2 pb-1.5 sm:flex-row sm:items-center sm:justify-between">
                <span className={`text-xs ${query.length >= 2000 ? 'text-warn' : 'text-muted'}`}>
                  {query.length}/2000
                  {!query.trim() && !disabled ? (
                    <span className="ml-2">Enter a complaint to start</span>
                  ) : null}
                </span>
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className="sgte-btn-primary inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Start Diagnosis
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </button>
              </div>
            </div>

            <p className="mt-6 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
              Quick-select categories
            </p>
            <div
              className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
              role="group"
              aria-label="Problem categories"
            >
              {CATEGORY_FLOWS.map((cat) => {
                const Icon = CATEGORY_ICONS[cat.id]
                const selected = activeCategory === cat.id
                return (
                  <button
                    key={cat.id}
                    type="button"
                    disabled={disabled}
                    onClick={() => {
                      setQuery(cat.query)
                      setActiveCategory(cat.id)
                    }}
                    className={`group flex items-start gap-3 rounded-2xl border bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-accent/45 hover:shadow-md disabled:opacity-40 ${
                      selected ? 'border-accent/50 shadow-md' : 'border-line'
                    }`}
                  >
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-mint text-accent">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="font-display text-sm font-bold text-navy">{cat.label}</span>
                        <ArrowRight className="h-4 w-4 text-accent opacity-60 transition group-hover:translate-x-0.5 group-hover:opacity-100" />
                      </span>
                      <span className="mt-1 block text-xs text-ink-soft">{cat.example}</span>
                    </span>
                  </button>
                )
              })}
            </div>
            {activeCategory ? (
              <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Supported problems in this category">
                {(CATEGORY_FLOWS.find((c) => c.id === activeCategory)?.options || []).map((opt) => {
                  const selected = query === opt.query
                  return (
                    <button
                      key={opt.query}
                      type="button"
                      disabled={disabled}
                      onClick={() => setQuery(opt.query)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition disabled:opacity-40 ${
                        selected
                          ? 'border-accent/50 bg-mint text-navy'
                          : 'border-line bg-white text-ink-soft hover:border-accent/40 hover:text-navy'
                      }`}
                    >
                      {opt.label}
                    </button>
                  )
                })}
              </div>
            ) : null}
            <p className="mt-2 text-xs text-muted">
              Categories fill a supported example complaint — they do not invent a troubleshooting
              result. Choose Start Diagnosis to run the grounded plan.
            </p>

            <div className="mt-6 border-t border-line pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowSiis((v) => !v)}
                  className="inline-flex items-center gap-2 text-sm font-medium text-ink-soft transition hover:text-navy"
                  aria-expanded={showSiis}
                >
                  <ChevronDown
                    className={`h-4 w-4 transition ${showSiis ? 'rotate-180' : ''}`}
                    aria-hidden
                  />
                  Have troubleshooting context?
                </button>
                <span className="relative inline-flex">
                  <button
                    type="button"
                    className="inline-flex rounded-full p-1 text-ink-soft hover:text-accent"
                    aria-label="What is troubleshooting context?"
                    aria-expanded={showHelp}
                    onClick={() => setShowHelp((v) => !v)}
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                  <AnimatePresence>
                    {showHelp ? (
                      <motion.span
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 4 }}
                        className="absolute left-0 top-7 z-10 w-64 rounded-xl border border-line bg-white p-3 text-xs leading-relaxed text-ink-soft shadow-lg sm:left-auto sm:right-0"
                        role="tooltip"
                      >
                        Optional support article or prior troubleshooting text. When provided, SGTE
                        grounds the plan in that context instead of inventing steps.
                      </motion.span>
                    ) : null}
                  </AnimatePresence>
                </span>
              </div>
              <AnimatePresence initial={false}>
                {showSiis ? (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <label htmlFor={siisId} className="mt-3 block text-sm text-ink-soft">
                      Paste support context (optional)
                    </label>
                    <textarea
                      id={siisId}
                      value={siis}
                      onChange={(e) => setSiis(e.target.value)}
                      rows={3}
                      placeholder="Paste support article or troubleshooting context"
                      className="mt-2 w-full rounded-xl border border-line bg-white px-4 py-3 text-sm text-ink placeholder:text-muted"
                    />
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </form>
        </div>

        <div className="relative mx-auto w-full max-w-[340px] lg:mx-0 lg:max-w-none">
          <PhoneStudio activeLabel={activeCategory} />
        </div>
      </section>

      {/* How SGTE works */}
      <section className="mx-auto mt-16 w-full max-w-6xl px-5 sm:px-8" aria-labelledby="how-sgte">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">How SGTE works</p>
        <h2 id="how-sgte" className="mt-2 font-display text-2xl font-bold text-navy sm:text-3xl">
          Describe → Diagnose → Resolve
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {HOW_STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <motion.article
                key={step.title}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: i * 0.06 }}
                className="sgte-card flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-accent">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                </div>
                <h3 className="mt-4 font-display text-lg font-bold text-navy">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{step.body}</p>
              </motion.article>
            )
          })}
        </div>
      </section>

      {/* Demo scenarios */}
      <section
        className="mx-auto mt-16 w-full max-w-6xl px-5 sm:px-8"
        aria-labelledby="demo-scenarios"
      >
        <div className="rounded-3xl border border-line bg-mint/60 px-5 py-8 sm:px-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Demo scenarios
          </p>
          <h2 id="demo-scenarios" className="mt-2 font-display text-2xl font-bold text-navy sm:text-3xl">
            {demoMode ? 'Try these example complaints to see how SGTE works.' : 'Example complaints'}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-ink-soft">
            {demoMode
              ? 'Selecting a scenario loads the full complaint into the studio — it does not fabricate a result.'
              : 'Load an example into the input, then start diagnosis.'}
          </p>

          <div
            className="mt-6 flex flex-wrap gap-2.5"
            aria-label={demoMode ? 'Demo scenarios' : 'Example issues'}
          >
            {(demoMode ? DEMO_SCENARIOS : EXAMPLES.map((e) => ({ ...e, hint: '' }))).map((ex) => (
              <button
                key={ex.label}
                type="button"
                title={'hint' in ex ? ex.hint : undefined}
                disabled={disabled}
                onClick={() => {
                  setQuery(ex.query)
                  setActiveCategory(null)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                className="rounded-full border border-accent/35 bg-white px-4 py-2 text-sm font-medium text-navy transition hover:bg-accent hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40"
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      </section>
    </motion.div>
  )
}
