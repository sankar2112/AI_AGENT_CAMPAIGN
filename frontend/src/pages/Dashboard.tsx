import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, streamUrl } from '../lib/api'
import type { Analytics, Campaign, Run, StreamEvent } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [error, setError] = useState<string | null>(null)
  const [launching, setLaunching] = useState<number | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [a, c, r] = await Promise.all([api.analytics(), api.campaigns(), api.runs()])
      setAnalytics(a)
      setCampaigns(c)
      setRuns(r)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const socket = new WebSocket(streamUrl())
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as StreamEvent
      if (payload.type === 'run_completed' || payload.type === 'run_failed') void refresh()
    }
    return () => socket.close()
  }, [refresh])

  const launch = async (campaign: Campaign) => {
    setLaunching(campaign.id)
    setError(null)
    try {
      const run = await api.launch(campaign.id)
      navigate(`/runs/${run.id}`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLaunching(null)
    }
  }

  const remove = async (campaign: Campaign) => {
    await api.deleteCampaign(campaign.id)
    void refresh()
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Campaign control tower</h1>
          <p>Agentic outreach for banking, financial services and insurance — generated, compliance-checked and delivered in real time.</p>
        </div>
        <button className="primary" onClick={() => navigate('/campaigns/new')}>
          New campaign
        </button>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="kpi-grid">
        <Kpi label="Campaigns" value={analytics?.total_campaigns ?? 0} />
        <Kpi label="Messages generated" value={analytics?.messages_generated ?? 0} />
        <Kpi label="Audience reached" value={analytics?.audience_reached ?? 0} />
        <Kpi label="Blocked by compliance" value={analytics?.blocked_by_compliance ?? 0} tone="danger" />
        <Kpi label="Open rate" value={`${analytics?.open_rate ?? 0}%`} />
        <Kpi label="Click rate" value={`${analytics?.click_rate ?? 0}%`} />
        <Kpi label="Conversion" value={`${analytics?.conversion_rate ?? 0}%`} tone="success" />
        <Kpi label="Avg model latency" value={`${analytics?.avg_latency_ms ?? 0} ms`} />
      </section>

      <div className="split">
        <section className="panel">
          <h2>Campaigns</h2>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Product</th>
                <th>Channel</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr key={campaign.id}>
                  <td>
                    <strong>{campaign.name}</strong>
                    <small>{campaign.objective.replace('_', ' ')}</small>
                  </td>
                  <td>{campaign.product}</td>
                  <td>
                    <span className="chip">{campaign.channel}</span>
                  </td>
                  <td>
                    <span className={`status ${campaign.status}`}>{campaign.status}</span>
                  </td>
                  <td className="row-actions">
                    <button className="primary small" disabled={launching === campaign.id} onClick={() => launch(campaign)}>
                      {launching === campaign.id ? 'Launching…' : 'Launch'}
                    </button>
                    <button className="ghost small" onClick={() => remove(campaign)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {campaigns.length === 0 && (
                <tr>
                  <td colSpan={5}>No campaigns yet — create one to get started.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <h2>Recent runs</h2>
          <ul className="run-list">
            {runs.map((run) => (
              <li key={run.id} onClick={() => navigate(`/runs/${run.id}`)}>
                <div>
                  <strong>Run #{run.id}</strong>
                  <small>
                    {run.generated}/{run.audience_size} generated · {run.converted} converted · {run.llm_provider}
                  </small>
                </div>
                <span className={`status ${run.status}`}>{run.status}</span>
              </li>
            ))}
            {runs.length === 0 && <li className="empty">No runs yet.</li>}
          </ul>
        </section>
      </div>
    </>
  )
}

function Kpi({ label, value, tone }: { label: string; value: string | number; tone?: 'danger' | 'success' }) {
  return (
    <div className={`kpi ${tone ?? ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
