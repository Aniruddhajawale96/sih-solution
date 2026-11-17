import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'
import { useAuthStore } from '@/store/authStore'

// ── TypeScript interfaces ──────────────────────────────────────────────────────

interface StateAnalytics {
  parcels_total: number
  violations: number
  pending_mutations: number
  arrears_total: number
}

interface StateUser {
  username: string
  role: string
  jurisdiction: string | null
  is_active: boolean
}

interface StateAdapterConfig {
  id: number
  state_code: string
  source_field_name: string
  canonical_field_name: string
  unit_conversion_factor: number
  language_code: string
}

// ── Tab definitions ────────────────────────────────────────────────────────────

type TabId = 'analytics' | 'users' | 'adapter'

interface Tab {
  id: TabId
  label: string
}

const TABS: Tab[] = [
  { id: 'analytics', label: 'Analytics' },
  { id: 'users',     label: 'Users'     },
  { id: 'adapter',   label: 'Adapter'   },
]

// ── Shared UI helpers ─────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="p-10 flex items-center justify-center gap-3 text-slate-500">
      <svg
        className="animate-spin h-5 w-5 text-emerald-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <span className="text-sm">Loading…</span>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="m-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
      <span className="font-semibold">Error: </span>{message}
    </div>
  )
}

// ── Placeholder district data (used when API doesn't return district_breakdown) ─

const PLACEHOLDER_DISTRICTS = [
  { district: 'Nashik',    count: 142 },
  { district: 'Pune',      count: 319 },
  { district: 'Nagpur',    count: 207 },
  { district: 'Aurangabad',count: 88  },
  { district: 'Thane',     count: 263 },
]

// ── Tab 1 — Analytics ─────────────────────────────────────────────────────────

function AnalyticsPanel() {
  const jurisdiction = useAuthStore(s => s.jurisdiction)

  const { data, isLoading, isError, error } = useQuery<StateAnalytics>({
    queryKey: ['state', 'analytics', jurisdiction],
    queryFn: () =>
      apiClient.get(`/analytics/state/${encodeURIComponent(jurisdiction ?? '')}`).then(r => r.data),
    enabled: !!jurisdiction,
  })

  if (!jurisdiction) return <ErrorState message="No jurisdiction set for this account." />
  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load analytics.'} />

  const kpis: { label: string; value: number }[] = [
    { label: 'Total Parcels',      value: data?.parcels_total      ?? 0 },
    { label: 'Zoning Violations',  value: data?.violations         ?? 0 },
    { label: 'Pending Mutations',  value: data?.pending_mutations  ?? 0 },
    { label: 'Arrears Total (₹)',  value: data?.arrears_total      ?? 0 },
  ]

  return (
    <div className="p-6 space-y-8">
      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map(kpi => (
          <div
            key={kpi.label}
            className="rounded-xl border border-slate-200 bg-slate-50 p-4 flex flex-col items-center text-center"
          >
            <span className="text-3xl font-bold text-emerald-700">
              {kpi.value.toLocaleString()}
            </span>
            <span className="mt-1 text-xs font-medium text-slate-500 leading-tight">
              {kpi.label}
            </span>
          </div>
        ))}
      </div>

      {/* District breakdown bar chart (placeholder data) */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 mb-3 uppercase tracking-wide">
          Request Counts by District (sample)
        </h3>
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={PLACEHOLDER_DISTRICTS} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="district"
                tick={{ fontSize: 12, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  fontSize: '13px',
                }}
              />
              <Bar dataKey="count" fill="#059669" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ── Tab 2 — Users ─────────────────────────────────────────────────────────────

function UsersPanel() {
  const { data: users, isLoading, isError, error } = useQuery<StateUser[]>({
    queryKey: ['state', 'users'],
    queryFn: () => apiClient.get('/admin/users').then(r => r.data),
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load users.'} />

  if (!users || users.length === 0) {
    return <p className="p-6 text-sm text-slate-400">No users found.</p>
  }

  return (
    <div className="p-6 overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-50 text-left">
            {['Username', 'Role', 'Jurisdiction', 'Status'].map(h => (
              <th
                key={h}
                className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide border-b border-slate-200"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {users.map(user => (
            <tr key={user.username} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-medium text-slate-800">{user.username}</td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
                  {user.role}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-600">{user.jurisdiction ?? '—'}</td>
              <td className="px-4 py-3">
                <span
                  className={[
                    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                    user.is_active
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                      : 'bg-slate-100 text-slate-500 border border-slate-200',
                  ].join(' ')}
                >
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Tab 3 — Adapter ───────────────────────────────────────────────────────────

function AdapterPanel() {
  const jurisdiction = useAuthStore(s => s.jurisdiction)

  const { data: configs, isLoading, isError, error } = useQuery<StateAdapterConfig[]>({
    queryKey: ['state', 'adapters', jurisdiction],
    queryFn: () =>
      apiClient.get(`/admin/state-adapter/${encodeURIComponent(jurisdiction ?? '')}`).then(r => r.data),
    enabled: !!jurisdiction,
  })

  if (!jurisdiction) return <ErrorState message="No jurisdiction set for this account." />
  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load adapter config.'} />

  if (!configs || configs.length === 0) {
    return <p className="p-6 text-sm text-slate-400">No adapter config found for this state.</p>
  }

  return (
    <div className="p-6 overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-50 text-left">
            {['Source Field', 'Canonical Field', 'Unit Factor', 'Language'].map(h => (
              <th
                key={h}
                className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide border-b border-slate-200"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {configs.map(cfg => (
            <tr key={cfg.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-slate-700">{cfg.source_field_name}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-700">{cfg.canonical_field_name}</td>
              <td className="px-4 py-3 text-slate-600">{cfg.unit_conversion_factor}</td>
              <td className="px-4 py-3 text-slate-600">{cfg.language_code}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function StateAdminPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('analytics')

  function renderContent() {
    switch (activeTab) {
      case 'analytics': return <AnalyticsPanel />
      case 'users':     return <UsersPanel />
      case 'adapter':   return <AdapterPanel />
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        {/* Page heading */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">State Admin Panel</h1>
          <p className="text-sm text-slate-500 mt-1">State oversight, user management, and adapter config</p>
        </div>

        {/* Tab strip */}
        <div className="flex border-b border-slate-200 mb-0">
          {TABS.map(tab => {
            const isActive = tab.id === activeTab
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  'px-5 py-3 text-sm font-medium transition-colors whitespace-nowrap',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500',
                  isActive
                    ? 'border-b-2 border-emerald-600 text-emerald-700 -mb-px bg-white'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100',
                ].join(' ')}
                aria-selected={isActive}
                role="tab"
              >
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tab panel */}
        <div
          className="bg-white rounded-b-xl shadow-sm border border-t-0 border-slate-200 min-h-64"
          role="tabpanel"
        >
          {renderContent()}
        </div>
      </main>

      <Footer />
    </div>
  )
}
