import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Header } from './components/Header'
import { Landing } from './components/Landing'
import { Analyzing } from './components/Analyzing'
import { Results } from './components/Results'
import { FallbackState } from './components/FallbackState'
import { ErrorState } from './components/ErrorState'
import { useHealth } from './hooks/useHealth'
import { troubleshoot } from './lib/api'
import { ApiError } from './types/api'
import type { TroubleshootResponse } from './types/api'

type View =
  | { kind: 'input' }
  | { kind: 'analyzing' }
  | { kind: 'results'; data: TroubleshootResponse }
  | {
      kind: 'fallback'
      variant: 'no_match' | 'no_siis_context' | 'empty_plan'
      query: string
    }
  | { kind: 'error'; message: string; unavailable?: boolean }

function useDemoQueryFlag(): boolean {
  if (typeof window === 'undefined') return false
  return new URLSearchParams(window.location.search).get('demo') === '1'
}

export default function App() {
  const health = useHealth()
  const demoFlag = useDemoQueryFlag()
  const [view, setView] = useState<View>({ kind: 'input' })
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setView({ kind: 'input' })
  }, [])

  const runDiagnosis = useCallback(async (query: string, siis?: string) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setView({ kind: 'analyzing' })

    const started = performance.now()
    try {
      const body =
        siis === undefined ? { query } : { query, siis_response: siis }

      const data = await troubleshoot(body, ctrl.signal)
      const elapsed = performance.now() - started
      const wait = Math.max(0, 450 - elapsed)
      await new Promise((r) => window.setTimeout(r, wait))
      if (ctrl.signal.aborted) return

      if (data.meta.fallback === 'no_match') {
        setView({ kind: 'fallback', variant: 'no_match', query })
      } else if (data.meta.fallback === 'no_siis_context') {
        setView({ kind: 'fallback', variant: 'no_siis_context', query })
      } else if (!(data.response.contexts?.length)) {
        setView({ kind: 'fallback', variant: 'empty_plan', query })
      } else {
        setView({ kind: 'results', data })
      }
    } catch (err) {
      if (ctrl.signal.aborted) return
      if (err instanceof TypeError) {
        setView({
          kind: 'error',
          unavailable: true,
          message:
            'The SGTE API could not be reached. Start the backend (uvicorn on port 8000) and try again.',
        })
        return
      }
      if (err instanceof ApiError) {
        const unavailable = err.status === 0 || err.status >= 500
        setView({
          kind: 'error',
          unavailable,
          message: err.message,
        })
        return
      }
      setView({
        kind: 'error',
        message: "SGTE couldn't complete this diagnosis.",
      })
    }
  }, [])

  const showNew = view.kind !== 'input' && view.kind !== 'analyzing'
  // Health polling retained for demo-chip gating only — not shown as a status badge/banner.
  const demoOffline =
    demoFlag ||
    (health.status === 'ready' &&
      Boolean(health.health.demo_offline || health.health.execution_mode === 'MOCK'))

  return (
    <div className="relative min-h-screen">
      <Header showNew={showNew} onNew={reset} />
      <main className="relative z-0">
        <AnimatePresence mode="wait">
          {view.kind === 'input' ? (
            <Landing key="input" onSubmit={runDiagnosis} demoMode={demoOffline} />
          ) : null}
          {view.kind === 'analyzing' ? <Analyzing key="analyzing" active /> : null}
          {view.kind === 'results' ? <Results key="results" data={view.data} /> : null}
          {view.kind === 'fallback' ? (
            <FallbackState
              key={`fallback-${view.variant}`}
              kind={view.variant}
              query={view.query}
              onRetry={reset}
            />
          ) : null}
          {view.kind === 'error' ? (
            <ErrorState
              key="error"
              message={view.message}
              unavailable={view.unavailable}
              onRetry={reset}
            />
          ) : null}
        </AnimatePresence>
      </main>
    </div>
  )
}
