import type {
  HealthResponse,
  TroubleshootRequest,
  TroubleshootResponse,
} from '../types/api'
import { ApiError } from '../types/api'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''

async function parseJson(res: Response): Promise<unknown> {
  try {
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { signal })
  if (!res.ok) {
    throw new ApiError('Health check failed', res.status)
  }
  return (await res.json()) as HealthResponse
}

export async function troubleshoot(
  body: TroubleshootRequest,
  signal?: AbortSignal,
): Promise<TroubleshootResponse> {
  const payload: TroubleshootRequest = { query: body.query }
  if (body.siis_response !== undefined) {
    payload.siis_response = body.siis_response
  }

  const res = await fetch(`${API_BASE}/v1/troubleshoot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  const data = await parseJson(res)

  if (!res.ok) {
    const errObj = data as {
      error?: { code?: string; message?: string }
      detail?: string | { msg?: string }[]
    } | null
    const detailMsg =
      typeof errObj?.detail === 'string'
        ? errObj.detail
        : Array.isArray(errObj?.detail)
          ? errObj.detail.map((d) => d?.msg).filter(Boolean).join('; ')
          : undefined
    throw new ApiError(
      errObj?.error?.message || detailMsg || 'SGTE could not complete this diagnosis.',
      res.status,
      errObj?.error?.code,
    )
  }

  return data as TroubleshootResponse
}
