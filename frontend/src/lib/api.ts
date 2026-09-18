import type { Analytics, AudienceFilter, Campaign, Customer, Run, RunDetail } from '../types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `${response.status} ${response.statusText}`)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export const api = {
  health: () => request<{ status: string; llm_provider: string; model_id: string; region: string }>('/api/health'),
  analytics: () => request<Analytics>('/api/analytics/overview'),
  campaigns: () => request<Campaign[]>('/api/campaigns'),
  campaign: (id: number) => request<Campaign>(`/api/campaigns/${id}`),
  createCampaign: (payload: Partial<Campaign>) =>
    request<Campaign>('/api/campaigns', { method: 'POST', body: JSON.stringify(payload) }),
  deleteCampaign: (id: number) => request<void>(`/api/campaigns/${id}`, { method: 'DELETE' }),
  launch: (id: number, delayMs = 400) =>
    request<Run>(`/api/campaigns/${id}/launch`, {
      method: 'POST',
      body: JSON.stringify({ simulate_engagement: true, delay_ms: delayMs }),
    }),
  runs: () => request<Run[]>('/api/runs'),
  run: (id: number) => request<RunDetail>(`/api/runs/${id}`),
  campaignRuns: (id: number) => request<Run[]>(`/api/campaigns/${id}/runs`),
  customers: () => request<Customer[]>('/api/customers?limit=200'),
  previewAudience: (filter: AudienceFilter) =>
    request<Customer[]>('/api/customers/preview-audience', { method: 'POST', body: JSON.stringify(filter) }),
}

export function streamUrl(runId?: number): string {
  const base = import.meta.env.VITE_WS_BASE
  const origin = base ?? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  return `${origin}/ws/campaigns${runId ? `?run_id=${runId}` : ''}`
}
