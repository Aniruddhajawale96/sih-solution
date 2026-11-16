import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

// ── TypeScript interfaces ──────────────────────────────────────────────────────

interface StateAnalytics {
  total_parcels: number
  active_requests: number
  completed_this_month: number
  violations_open: number
  officers_active: number
  district_breakdown?: { district: string; count: number }[]
}

interface StateUser {
  user_id: string
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

interface Adapter {
  adapter_id: string
  name: string
  state: string
  status: 'online' | 'offline' | 'error'
  last_sync?: string
  records_synced?: number
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
  const { data, isLoading, isError, error } = useQuery<StateAnalytics>({
    queryKey: ['state', 'analytics'],
    queryFn: () => apiClient.get('/admin/state/analytics').then(r => r.data),
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load analytics.'} />

  const kpis: { label: string; value: number }[] = [
    { label: 'Total Parcels',          value: data?.total_parcels        ?? 0 },
    { label: 'Active Requests',        value: data?.active_requests      ?? 0 },
    { label: 'Completed This Month',   value: data?.completed_this_month ?? 0 },
    { label: 'Open Violations',        value: data?.violations_open      ?? 0 },
    { label: 'Active Officers',        value: data?.officers_active      ?? 0 },
  ]

  const chartData =
    data?.district_breakdown && data.district_breakdown.length > 0
      ? data.district_breakdown
      : PLACEHOLDER_DISTRICTS

  return (
    <div className="p-6 space-y-8">
      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
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

      {/* District breakdown bar chart */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 mb-3 uppercase tracking-wide">
          Request Counts by District
        </h3>
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
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
  const queryClient = useQueryClient()

  const { data: users, isLoading, isError, error } = useQuery<StateUser[]>({
    queryKey: ['state', 'users'],
    queryFn: () => apiClient.get('/admin/state/users').then(r => r.data),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ user_id, is_active }: { user_id: string; is_active: boolean }) =>
      apiClient.patch(`/admin/state/users/${user_id}/active`, { is_active }).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['state', 'users'] }),
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
            {['Username', 'Email', 'Role', 'Created', 'Status', 'Action'].map(h => (
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
          {users.map(user => {
            const isPending =
              toggleMutation.isPending &&
              (toggleMutation.variables as { user_id: string } | undefined)?.user_id === user.user_id

            return (
              <tr key={user.user_id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-800">{user.username}</td>
                <td className="px-4 py-3 text-slate-600">{user.email}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
                    {user.role}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
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
                <td className="px-4 py-3">
                  <button
                    onClick={() =>
                      toggleMutation.mutate({ user_id: user.user_id, is_active: !user.is_active })
                    }
                    disabled={isPending}
                    className={[
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500',
                      isPending ? 'opacity-50 cursor-not-allowed' : '',
                      user.is_active
                        ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        : 'bg-emerald-600 hover:bg-emerald-700 text-white',
                    ].join(' ')}
                  >
                    {isPending ? '…' : user.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Tab 3 — Adapter ───────────────────────────────────────────────────────────

const STATUS_STYLES: Record<Adapter['status'], string> = {
  online:  'bg-emerald-50 text-emerald-700 border-emerald-100',
  offline: 'bg-slate-100 text-slate-500 border-slate-200',
  error:   'bg-red-50 text-red-600 border-red-100',
}

const STATUS_DOTS: Record<Adapter['status'], string> = {
  online:  'bg-emerald-500',
  offline: 'bg-slate-400',
  error:   'bg-red-500',
}

function AdapterPanel() {
  const queryClient = useQueryClient()

  const { data: adapters, isLoading, isError, error } = useQuery<Adapter[]>({
    queryKey: ['state', 'adapters'],
    queryFn: () => apiClient.get('/admin/state/adapters').then(r => r.data),
  })

  // Track per-adapter sync loading
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set())

  const syncMutation = useMutation({
    mutationFn: (adapter_id: string) =>
      apiClient.post(`/admin/state/adapters/${adapter_id}/sync`).then(r => r.data),
    onMutate: (adapter_id) => {
      setSyncingIds(prev => new Set([...prev, adapter_id]))
    },
    onSettled: (_data, _err, adapter_id) => {
      setSyncingIds(prev => {
        const next = new Set(prev)
        next.delete(adapter_id)
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['state', 'adapters'] })
    },
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load adapters.'} />

  if (!adapters || adapters.length === 0) {
    return <p className="p-6 text-sm text-slate-400">No adapters configured.</p>
  }

  return (
    <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {adapters.map(adapter => {
        const isSyncing = syncingIds.has(adapter.adapter_id)

        return (
          <div
            key={adapter.adapter_id}
            className="rounded-xl border border-slate-200 bg-slate-50 p-5 flex flex-col gap-3"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-800 text-sm">{adapter.name}</p>
                <p className="text-xs text-slate-400 mt-0.5">{adapter.state}</p>
              </div>
              <span
                className={[
                  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border',
                  STATUS_STYLES[adapter.status],
                ].join(' ')}
              >
                <span
                  className={['h-1.5 w-1.5 rounded-full', STATUS_DOTS[adapter.status]].join(' ')}
                />
                {adapter.status.charAt(0).toUpperCase() + adapter.status.slice(1)}
              </span>
            </div>

            {/* Stats */}
            <dl className="space-y-1">
              <div className="flex justify-between text-xs">
                <dt className="text-slate-500">Last sync</dt>
                <dd className="text-slate-700 font-medium">
                  {adapter.last_sync
                    ? new Date(adapter.last_sync).toLocaleString()
                    : '—'}
                </dd>
              </div>
              <div className="flex justify-between text-xs">
                <dt className="text-slate-500">Records synced</dt>
                <dd className="text-slate-700 font-medium">
                  {adapter.records_synced !== undefined
                    ? adapter.records_synced.toLocaleString()
                    : '—'}
                </dd>
              </div>
            </dl>

            {/* Trigger Sync button */}
            <button
              onClick={() => syncMutation.mutate(adapter.adapter_id)}
              disabled={isSyncing}
              className={[
                'mt-auto w-full py-2 rounded-lg text-xs font-semibold transition-colors',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500',
                isSyncing
                  ? 'bg-emerald-100 text-emerald-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white',
              ].join(' ')}
            >
              {isSyncing ? 'Syncing…' : 'Trigger Sync'}
            </button>
          </div>
        )
      })}
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
          <p className="text-sm text-slate-500 mt-1">State oversight, user management, and adapter control</p>
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
