export type Channel = 'email' | 'sms' | 'whatsapp' | 'push' | 'social' | 'print'

export interface AudienceFilter {
  segments: string[]
  cities: string[]
  risk_profiles: string[]
  min_income?: number | null
  max_income?: number | null
  min_credit_score?: number | null
  exclude_products: string[]
  kyc_status?: string | null
  consent_required: boolean
  limit: number
}

export interface Campaign {
  id: number
  name: string
  objective: string
  product: string
  channel: Channel
  tone: string
  language: string
  offer_details: string
  call_to_action: string
  audience_filter: AudienceFilter
  status: string
  model_id: string
  created_at: string
}

export interface Customer {
  id: number
  full_name: string
  email: string
  city: string
  segment: string
  risk_profile: string
  annual_income: number
  relationship_years: number
  products_held: string[]
  credit_score: number
  preferred_channel: Channel
  churn_risk: number
  marketing_consent: boolean
  kyc_status: string
}

export interface RunStats {
  audience_size: number
  generated: number
  sent: number
  blocked: number
  opened: number
  clicked: number
  converted: number
}

export interface Run extends RunStats {
  id: number
  campaign_id: number
  status: string
  llm_provider: string
  error: string | null
  started_at: string
  finished_at: string | null
}

export interface Message {
  id: number
  customer_id: number
  customer_name?: string
  segment?: string
  channel: Channel
  subject: string
  body: string
  next_best_action: string
  compliance_status: 'pass' | 'warn' | 'fail'
  compliance_notes: string
  status: string
  propensity: number
  latency_ms: number
}

export interface RunDetail extends Run {
  messages: Message[]
}

export interface Analytics {
  total_campaigns: number
  active_runs: number
  audience_reached: number
  messages_generated: number
  blocked_by_compliance: number
  open_rate: number
  click_rate: number
  conversion_rate: number
  avg_latency_ms: number
  by_channel: Record<string, number>
  by_segment: Record<string, number>
}

export interface StreamEvent {
  type: 'run_started' | 'message' | 'run_completed' | 'run_failed'
  run_id: number
  campaign_id: number
  ts: string
  campaign_name?: string
  audience_size?: number
  llm_provider?: string
  index?: number
  total?: number
  message?: Message
  stats?: RunStats
  error?: string
}
