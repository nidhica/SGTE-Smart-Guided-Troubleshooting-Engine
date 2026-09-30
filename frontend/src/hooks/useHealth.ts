import { useCallback, useEffect, useState } from 'react'
import { fetchHealth } from '../lib/api'
import type { HealthResponse } from '../types/api'

export type HealthState =
  | { status: 'loading' }
  | { status: 'ready'; health: HealthResponse }
  | { status: 'error' }

export function useHealth(pollMs = 30000): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' })

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const health = await fetchHealth(signal)
      if (signal?.aborted) return
      setState({ status: 'ready', health })
    } catch {
      if (signal?.aborted) return
      setState({ status: 'error' })
    }
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    void refresh(ctrl.signal)
    const id = window.setInterval(() => void refresh(), pollMs)
    return () => {
      ctrl.abort()
      window.clearInterval(id)
    }
  }, [pollMs, refresh])

  return state
}
