import type { Action, GoalContext, TroubleshootResponse } from '../types/api'

export function countIssues(data: TroubleshootResponse): number {
  return data.response.contexts?.length ?? 0
}

export function flattenActions(data: TroubleshootResponse): Array<{
  context: GoalContext
  action: Action
  index: number
}> {
  const out: Array<{ context: GoalContext; action: Action; index: number }> = []
  let i = 0
  for (const context of data.response.contexts ?? []) {
    for (const action of context.actions ?? []) {
      i += 1
      out.push({ context, action, index: i })
    }
  }
  return out
}

export function primaryActionableUri(action: Action): string | null {
  for (const group of action.stepGroups ?? []) {
    const uri = group.actionableDeeplink?.deeplink
    if (uri) return uri
  }
  return null
}

export function hasAnyDeeplink(data: TroubleshootResponse): boolean {
  return flattenActions(data).some(({ action }) => primaryActionableUri(action) !== null)
}

export function formatLatency(ms: number | undefined): string | null {
  if (ms === undefined || Number.isNaN(ms)) return null
  if (ms < 10) return `${ms.toFixed(1)} ms`
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

export function formatCost(usd: number | undefined): string | null {
  if (usd === undefined || Number.isNaN(usd)) return null
  return `$${usd.toFixed(2)}`
}
