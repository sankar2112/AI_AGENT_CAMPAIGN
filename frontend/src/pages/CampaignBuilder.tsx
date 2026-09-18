import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { AudienceFilter, Campaign, Channel, Customer } from '../types'

const SEGMENTS = ['mass', 'affluent', 'hni', 'nri', 'sme']
const PRODUCTS = [
  'savings_account',
  'credit_card',
  'home_loan',
  'personal_loan',
  'auto_loan',
  'term_insurance',
  'health_insurance',
  'mutual_fund_sip',
  'fixed_deposit',
  'demat_account',
]

const emptyFilter: AudienceFilter = {
  segments: [],
  cities: [],
  risk_profiles: [],
  min_income: null,
  max_income: null,
  min_credit_score: null,
  exclude_products: [],
  kyc_status: 'verified',
  consent_required: true,
  limit: 10,
}

export default function CampaignBuilder() {
  const navigate = useNavigate()
  const [form, setForm] = useState<Partial<Campaign>>({
    name: '',
    objective: 'cross_sell',
    product: '',
    channel: 'email',
    tone: 'professional',
    language: 'English',
    offer_details: '',
    call_to_action: 'Apply now',
  })
  const [filter, setFilter] = useState<AudienceFilter>(emptyFilter)
  const [preview, setPreview] = useState<Customer[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const id = setTimeout(() => {
      api.previewAudience(filter).then(setPreview).catch(() => setPreview([]))
    }, 250)
    return () => clearTimeout(id)
  }, [filter])

  const toggle = (key: 'segments' | 'exclude_products', value: string) =>
    setFilter((f) => ({
      ...f,
      [key]: f[key].includes(value) ? f[key].filter((v) => v !== value) : [...f[key], value],
    }))

  const submit = async (launchNow: boolean) => {
    setSaving(true)
    setError(null)
    try {
      const campaign = await api.createCampaign({ ...form, audience_filter: filter })
      if (launchNow) {
        const run = await api.launch(campaign.id)
        navigate(`/runs/${run.id}`)
      } else {
        navigate('/dashboard')
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const valid = Boolean(form.name && form.product && preview.length > 0)

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Design a campaign</h1>
          <p>The agent personalises every message per customer, then guardrails run before delivery.</p>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <div className="split">
        <section className="panel">
          <h2>Brief</h2>
          <div className="form-grid">
            <label>
              Campaign name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Festive home loan balance transfer" />
            </label>
            <label>
              Product
              <input value={form.product} onChange={(e) => setForm({ ...form, product: e.target.value })} placeholder="Home Loan Balance Transfer" />
            </label>
            <label>
              Objective
              <select value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })}>
                <option value="cross_sell">Cross-sell</option>
                <option value="upsell">Upsell</option>
                <option value="acquisition">Acquisition</option>
                <option value="retention">Retention</option>
                <option value="collections">Collections reminder</option>
                <option value="onboarding">Onboarding nudge</option>
              </select>
            </label>
            <label>
              Channel
              <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value as Channel })}>
                <option value="whatsapp">WhatsApp</option>
                <option value="email">Email</option>
                <option value="sms">SMS</option>
                <option value="push">Push notification</option>
                <option value="social">Social media</option>
                <option value="print">Print / branch</option>
              </select>
            </label>
            <label>
              Tone
              <select value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })}>
                <option value="professional">Professional</option>
                <option value="consultative">Consultative</option>
                <option value="friendly">Friendly</option>
                <option value="reassuring">Reassuring</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>
            <label>
              Language
              <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {['English', 'Hindi', 'Tamil', 'Telugu', 'Marathi'].map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="wide">
              Offer details (the only figures the agent may quote)
              <textarea
                rows={3}
                value={form.offer_details}
                onChange={(e) => setForm({ ...form, offer_details: e.target.value })}
                placeholder="Processing fee waived until 31 Dec; rates from 8.4% p.a. for eligible applicants."
              />
            </label>
            <label className="wide">
              Call to action
              <input value={form.call_to_action} onChange={(e) => setForm({ ...form, call_to_action: e.target.value })} />
            </label>
          </div>
        </section>

        <section className="panel">
          <h2>Audience</h2>
          <div className="field-label">Segments</div>
          <div className="pills">
            {SEGMENTS.map((s) => (
              <button key={s} className={filter.segments.includes(s) ? 'pill active' : 'pill'} onClick={() => toggle('segments', s)}>
                {s}
              </button>
            ))}
          </div>

          <div className="field-label">Exclude customers who already hold</div>
          <div className="pills">
            {PRODUCTS.map((p) => (
              <button
                key={p}
                className={filter.exclude_products.includes(p) ? 'pill active' : 'pill'}
                onClick={() => toggle('exclude_products', p)}
              >
                {p.replace(/_/g, ' ')}
              </button>
            ))}
          </div>

          <div className="form-grid">
            <label>
              Min credit score
              <input
                type="number"
                value={filter.min_credit_score ?? ''}
                onChange={(e) => setFilter({ ...filter, min_credit_score: e.target.value ? Number(e.target.value) : null })}
              />
            </label>
            <label>
              Min annual income
              <input
                type="number"
                value={filter.min_income ?? ''}
                onChange={(e) => setFilter({ ...filter, min_income: e.target.value ? Number(e.target.value) : null })}
              />
            </label>
            <label>
              Audience cap
              <input type="number" value={filter.limit} onChange={(e) => setFilter({ ...filter, limit: Number(e.target.value) || 1 })} />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={filter.consent_required}
                onChange={(e) => setFilter({ ...filter, consent_required: e.target.checked })}
              />
              Only customers with marketing consent
            </label>
          </div>

          <div className="preview">
            <strong>{preview.length}</strong> customers match this filter
            <ul>
              {preview.slice(0, 6).map((c) => (
                <li key={c.id}>
                  {c.full_name} · {c.segment} · {c.city}
                </li>
              ))}
            </ul>
          </div>

          <div className="actions">
            <button className="ghost" disabled={saving || !valid} onClick={() => submit(false)}>
              Save draft
            </button>
            <button className="primary" disabled={saving || !valid} onClick={() => submit(true)}>
              {saving ? 'Working…' : 'Save & launch live'}
            </button>
          </div>
        </section>
      </div>
    </>
  )
}
