import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type { Customer } from '../types'

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState('all')

  useEffect(() => {
    api.customers().then(setCustomers).catch(() => setCustomers([]))
  }, [])

  const segments = useMemo(() => ['all', ...new Set(customers.map((c) => c.segment))], [customers])
  const filtered = customers.filter(
    (c) =>
      (segment === 'all' || c.segment === segment) &&
      (query === '' || `${c.full_name} ${c.email} ${c.city}`.toLowerCase().includes(query.toLowerCase())),
  )

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Customer book</h1>
          <p>{filtered.length} of {customers.length} customers · consent and KYC aware</p>
        </div>
        <div className="filters">
          <input placeholder="Search name, email, city" value={query} onChange={(e) => setQuery(e.target.value)} />
          <select value={segment} onChange={(e) => setSegment(e.target.value)}>
            {segments.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </header>

      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Segment</th>
              <th>City</th>
              <th>Risk</th>
              <th>Credit score</th>
              <th>Products</th>
              <th>Churn risk</th>
              <th>Consent</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id}>
                <td>
                  <strong>{c.full_name}</strong>
                  <small>{c.email}</small>
                </td>
                <td>
                  <span className="chip">{c.segment}</span>
                </td>
                <td>{c.city}</td>
                <td>{c.risk_profile}</td>
                <td>{c.credit_score}</td>
                <td className="products">{c.products_held.join(', ')}</td>
                <td>
                  <div className="meter">
                    <span style={{ width: `${Math.round(c.churn_risk * 100)}%` }} />
                  </div>
                </td>
                <td>{c.marketing_consent ? 'yes' : 'no'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
