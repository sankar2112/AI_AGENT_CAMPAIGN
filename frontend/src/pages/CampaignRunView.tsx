import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, streamUrl } from '../lib/api'
import type { Message, RunStats, StreamEvent } from '../types'

const emptyStats: RunStats = {
  audience_size: 0,
  generated: 0,
  sent: 0,
  blocked: 0,
  opened: 0,
  clicked: 0,
  converted: 0,
}

export default function CampaignRunView() {
  const { runId } = useParams()
  const id = Number(runId)
  const [stats, setStats] = useState<RunStats>(emptyStats)
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState('loading')
  const [provider, setProvider] = useState('')
  const [connected, setConnected] = useState(false)
  const feedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.run(id).then((run) => {
      setStats(run)
      setMessages(run.messages)
      setStatus(run.status)
      setProvider(run.llm_provider)
    })

    const socket = new WebSocket(streamUrl(id))
    socket.onopen = () => setConnected(true)
    socket.onclose = () => setConnected(false)
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as StreamEvent
      if (payload.run_id !== id) return
      if (payload.stats) setStats(payload.stats)
      if (payload.llm_provider) setProvider(payload.llm_provider)
      if (payload.type === 'run_started') setStatus('running')
      if (payload.type === 'run_completed') setStatus('completed')
      if (payload.type === 'run_failed') setStatus('failed')
      if (payload.type === 'message' && payload.message) {
        const incoming = payload.message
        setMessages((prev) => (prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming]))
      }
    }
    return () => socket.close()
  }, [id])

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages.length])

  const progress = stats.audience_size ? Math.round((stats.generated / stats.audience_size) * 100) : 0

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Live run #{id}</h1>
          <p>
            <span className={`status ${status}`}>{status}</span>
            <span className={`chip ${connected ? 'live' : ''}`}>{connected ? 'streaming' : 'disconnected'}</span>
            <span className="chip">{provider}</span>
          </p>
        </div>
      </header>

      <section className="panel">
        <div className="progress">
          <span style={{ width: `${progress}%` }} />
        </div>
        <div className="funnel">
          <Stat label="Audience" value={stats.audience_size} />
          <Stat label="Generated" value={stats.generated} />
          <Stat label="Sent" value={stats.sent} />
          <Stat label="Blocked" value={stats.blocked} tone="danger" />
          <Stat label="Opened" value={stats.opened} />
          <Stat label="Clicked" value={stats.clicked} />
          <Stat label="Converted" value={stats.converted} tone="success" />
        </div>
      </section>

      <section className="panel feed" ref={feedRef}>
        <h2>Agent output</h2>
        {messages.map((message) => (
          <article key={message.id} className={`message ${message.compliance_status}`}>
            <header>
              <div>
                <strong>{message.customer_name ?? `Customer #${message.customer_id}`}</strong>
                <small>
                  {message.segment ? `${message.segment} · ` : ''}
                  {message.channel} · propensity {(message.propensity * 100).toFixed(0)}% · {message.latency_ms} ms
                </small>
              </div>
              <div className="badges">
                <span className={`status ${message.status}`}>{message.status}</span>
                <span className={`compliance ${message.compliance_status}`}>{message.compliance_status}</span>
              </div>
            </header>
            {message.subject && <p className="subject">{message.subject}</p>}
            <pre>{message.body}</pre>
            <footer>
              <span>Next best action: {message.next_best_action || '—'}</span>
              <span className="notes">{message.compliance_notes}</span>
            </footer>
          </article>
        ))}
        {messages.length === 0 && <p className="empty">Waiting for the agent to generate the first message…</p>}
      </section>
    </>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'danger' | 'success' }) {
  return (
    <div className={`stat ${tone ?? ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
