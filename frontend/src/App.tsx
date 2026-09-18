import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './lib/api'
import Dashboard from './pages/Dashboard'
import CampaignBuilder from './pages/CampaignBuilder'
import CampaignRunView from './pages/CampaignRunView'
import Customers from './pages/Customers'
import './styles.css'

export default function App() {
  const [health, setHealth] = useState<{ llm_provider: string; model_id: string } | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">BFSI</span>
          <div>
            <strong>Agent Campaigns</strong>
            <small>Bedrock Nova</small>
          </div>
        </div>
        <nav>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/campaigns/new">New campaign</NavLink>
          <NavLink to="/customers">Customer book</NavLink>
        </nav>
        <div className="provider-card">
          <span className={`dot ${health?.llm_provider === 'bedrock' ? 'live' : 'mock'}`} />
          <div>
            <strong>{health?.llm_provider === 'bedrock' ? 'Bedrock live' : 'Offline generator'}</strong>
            <small>{health?.model_id ?? 'unavailable'}</small>
          </div>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/campaigns/new" element={<CampaignBuilder />} />
          <Route path="/runs/:runId" element={<CampaignRunView />} />
          <Route path="/customers" element={<Customers />} />
        </Routes>
      </main>
    </div>
  )
}
