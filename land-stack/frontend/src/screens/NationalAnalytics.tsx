import { useQuery } from '@tanstack/react-query'
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

interface StateBreakdownItem {
  state: string
  parcels: number
  requests: number
  violations: number
}

interface NationalAnalytics {
  total_parcels_nationwide: number
  total_states_onboarded: number
  active_requests_nationwide: number
  violations_nationwide: number
  sync_coverage_pct: number
  state_breakdown: StateBreakdownItem[]
}

// ── Placeholder data (used when API returns no state_breakdown) ───────────────

const PLACEHOLDER_STATES: StateBreakdownItem[] = [
  { state: 'Gujarat',     parcels: 12450, requests: 320, violations: 45  },
  { state: 'Maharashtra', parcels: 24100, requests: 580, violations: 132 },
  { state: 'Rajasthan',   parcels: 18300, requests: 410, violations: 67  },
  { state: 'Karnataka',   parcels: 15600, requests: 290, violations: 88  },
  { state: 'Tamil Nadu',  parcels: 20800, requests: 490, violations: 103 },
]

// ── Shared UI helpers ─────────────────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="flex-1 flex items-center justify-center gap-3 text-slate-500 py-24">
      <svg
        className="animate-spin h-6 w-6 text-blue-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <span className="text-sm">Loading national analytics…</span>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex-1 flex items-start justify-center pt-16 px-4">
      <div className="max-w-lg w-full p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
        <span className="font-semibold">Error: </span>{message}
      </div>
    </div>
  )
}

// ── KPI card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string
  value: string | number
}

function KpiCard({ label, value }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 flex flex-col items-center text-center">
      <span className="text-3xl font-bold text-blue-700">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
      <span className="mt-1 text-xs font-medium text-slate-500 leading-tight">{label}</span>
    </div>
  )
}

// ── Chart section ─────────────────────────────────────────────────────────────

interface ChartSectionProps {
  title: string
  data: StateBreakdownItem[]
  dataKey: keyof StateBreakdownItem
  barColor: string
}

function ChartSection({ title, data, dataKey, barColor }: ChartSectionProps) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-600 mb-3 uppercase tracking-wide">
        {title}
      </h3>
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#dbeafe" />
            <XAxis
              dataKey="state"
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
                border: '1px solid #dbeafe',
                fontSize: '13px',
              }}
            />
            <Bar dataKey={dataKey as string} fill={barColor} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function NationalAnalytics() {
  const { data, isLoading, isError, error } = useQuery<NationalAnalytics>({
    queryKey: ['national', 'analytics'],
    queryFn: () => apiClient.get('/analytics/national').then(r => r.data),
  })

  const chartData =
    data?.state_breakdown && data.state_breakdown.length > 0
      ? data.state_breakdown
      : PLACEHOLDER_STATES

  const kpis: KpiCardProps[] = [
    {
      label: 'Total Parcels Nationwide',
      value: data?.total_parcels_nationwide ?? 0,
    },
    {
      label: 'States Onboarded',
      value: data?.total_states_onboarded ?? 0,
    },
    {
      label: 'Active Requests',
      value: data?.active_requests_nationwide ?? 0,
    },
    {
      label: 'Open Violations',
      value: data?.violations_nationwide ?? 0,
    },
    {
      label: 'Sync Coverage',
      value: `${data?.sync_coverage_pct ?? 0}%`,
    },
  ]

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 flex flex-col">
        {isLoading && <LoadingSpinner />}
        {isError && (
          <ErrorBanner message={(error as Error)?.message ?? 'Failed to load national analytics.'} />
        )}

        {!isLoading && !isError && (
          <div className="max-w-6xl w-full mx-auto px-4 py-8 space-y-8">
            {/* Page heading */}
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-blue-100">
                <svg
                  className="h-6 w-6 text-blue-700"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800">National Analytics Dashboard</h1>
                <p className="text-sm text-slate-500 mt-0.5">
                  DoLR — nationwide land registry aggregates across all onboarded states
                </p>
              </div>
            </div>

            {/* KPI row */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {kpis.map(kpi => (
                <KpiCard key={kpi.label} label={kpi.label} value={kpi.value} />
              ))}
            </div>

            {/* Charts */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-8">
              <ChartSection
                title="Parcels by State"
                data={chartData}
                dataKey="parcels"
                barColor="#1d4ed8"
              />
              <ChartSection
                title="Service Requests by State"
                data={chartData}
                dataKey="requests"
                barColor="#0369a1"
              />
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}
