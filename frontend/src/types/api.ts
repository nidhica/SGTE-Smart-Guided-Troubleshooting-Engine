/** Types matching the existing SGTE FastAPI contract. No invented fields. */

export type ActionCategory = 'auto' | 'manual' | 'critical'

export interface Deeplink {
  deeplink: string
  description: string
  message?: string
  originalType?: string | null
  classes?: string[] | null
}

export interface ValidationDeeplink {
  deeplink: string
  key: string
  resultType?: string | null
  condition?: string | null
  value?: string | null
}

export interface StepGroup {
  steps: string[]
  actionableDeeplink?: Deeplink | null
  validationDeeplink?: ValidationDeeplink | null
}

export interface Action {
  actionName: string
  description: string
  stepGroups: StepGroup[]
  category?: ActionCategory | null
}

export interface GoalContext {
  goal: string
  title: string
  score: number
  actions: Action[]
}

export interface ContextDeeplinkResponse {
  contexts: GoalContext[]
}

export interface TroubleshootMeta {
  latency_ms: number
  cache_hit: boolean
  model: string
  cost_usd: number
  fallback?: 'no_match' | 'no_siis_context' | string
  execution_mode?: 'MOCK' | 'LIVE' | string
}

export interface TroubleshootRequest {
  query: string
  siis_response?: string
}

export interface TroubleshootResponse {
  query: string
  query_variations: string[]
  response: ContextDeeplinkResponse
  meta: TroubleshootMeta
}

export interface HealthResponse {
  status: string
  cache?: string
  catalogue?: string
  siis?: string
  execution_mode?: 'MOCK' | 'LIVE' | string
  llm_provider?: string
  demo_offline?: boolean
  production_authorized?: boolean
  implementation_gate_satisfied?: boolean
}

export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}
