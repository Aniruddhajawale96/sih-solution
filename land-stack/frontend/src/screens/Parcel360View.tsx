import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { useAuthStore, type Role } from '@/store/authStore'
import { apiClient } from '@/lib/apiClient'

// ── CITIZEN data masking ───────────────────────────────────────────────────────

export function maskCitizenData(data: unknown, role: Role | null): unknown {
  if (role !== 'CITIZEN') return data

  if (Array.isArray(data)) {
    return data.map(item => maskCitizenData(item, role))
  }

  if (data !== null && typeof data === 'object') {
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      if (key === 'owner_name' && typeof value === 'string') {
        result[key] = value.slice(0, 3) + '***'
      } else if (key === 'transaction_value') {
        result[key] = '[HIDDEN]'
      } else {
        result[key] = maskCitizenData(value, role)
      }
    }
    return result
  }

  return data
}

// ── Tab definitions ────────────────────────────────────────────────────────────

type TabId = 'base' | 'ror' | 'registration' | 'encumbrance' | 'zoning' | 'tax'

interface Tab {
  id: TabId
  label: string
}

const TABS: Tab[] = [
  { id: 'base',         label: 'Base'         },
  { id: 'ror',          label: 'RoR'          },
  { id: 'registration', label: 'Registration' },
  { id: 'encumbrance',  label: 'Encumbrance'  },
  { id: 'zoning',       label: 'Zoning'       },
  { id: 'tax',          label: 'Tax'          },
]

// ── Shared fetch-state UI helpers ──────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="p-6 flex items-center justify-center gap-3 text-slate-500">
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

function DataTable({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return <p className="p-6 text-sm text-slate-400">No data returned.</p>
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <p className="p-6 text-sm text-slate-400">No records found.</p>
    }
    return (
      <div className="p-6 space-y-4">
        {data.map((item, idx) => (
          <div key={idx} className="rounded-lg border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Item {idx + 1}
            </div>
            <FlatRecord obj={item} />
          </div>
        ))}
      </div>
    )
  }

  if (typeof data === 'object') {
    return (
      <div className="p-6">
        <FlatRecord obj={data as Record<string, unknown>} />
      </div>
    )
  }

  return (
    <pre className="p-6 text-xs text-slate-700 whitespace-pre-wrap break-all">
      {String(data)}
    </pre>
  )
}

function FlatRecord({ obj }: { obj: Record<string, unknown> }) {
  const entries = Object.entries(obj)
  if (entries.length === 0) {
    return <p className="p-4 text-sm text-slate-400">Empty record.</p>
  }
  return (
    <dl className="divide-y divide-slate-100">
      {entries.map(([key, value]) => (
        <div key={key} className="grid grid-cols-[200px_1fr] gap-x-4 px-4 py-2.5">
          <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide self-start pt-0.5 break-all">
            {key}
          </dt>
          <dd className="text-sm text-slate-800 break-all">
            {value === null
              ? <span className="text-slate-400 italic">null</span>
              : typeof value === 'object'
                ? <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

// ── Tab panel sub-components ───────────────────────────────────────────────────

interface TabPanelProps {
  ulpin: string
  role: Role | null
}

function BasePanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'base'],
    queryFn: () => apiClient.get(`/parcels/${ulpin}`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load base data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

function RorPanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'ror'],
    queryFn: () => apiClient.get(`/ror/${ulpin}`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load RoR data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

function RegistrationPanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'registration'],
    queryFn: () => apiClient.get(`/parcels/${ulpin}/registration`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load registration data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

function EncumbrancePanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'encumbrance'],
    queryFn: () => apiClient.get(`/parcels/${ulpin}/encumbrance`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load encumbrance data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

function ZoningPanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'zoning'],
    queryFn: () => apiClient.get(`/parcels/${ulpin}/zoning`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load zoning data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

function TaxPanel({ ulpin, role }: TabPanelProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['parcel', ulpin, 'tax'],
    queryFn: () => apiClient.get(`/parcels/${ulpin}/tax`).then(r => r.data),
    enabled: !!ulpin,
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load tax data.'} />
  const maskedData = maskCitizenData(data, role)
  return <DataTable data={maskedData} />
}

// ── Tab content router ─────────────────────────────────────────────────────────

function renderTabContent(tab: TabId, ulpin: string, role: Role | null) {
  const props: TabPanelProps = { ulpin, role }
  switch (tab) {
    case 'base':         return <BasePanel         {...props} />
    case 'ror':          return <RorPanel           {...props} />
    case 'registration': return <RegistrationPanel  {...props} />
    case 'encumbrance':  return <EncumbrancePanel   {...props} />
    case 'zoning':       return <ZoningPanel        {...props} />
    case 'tax':          return <TaxPanel           {...props} />
  }
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function Parcel360View() {
  const { ulpin = '' } = useParams<{ ulpin: string }>()
  const role = useAuthStore(s => s.role)
  const [activeTab, setActiveTab] = useState<TabId>('base')

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
        {/* Page heading */}
        <h1 className="text-2xl font-bold text-slate-800 mb-6">
          Parcel 360°&nbsp;
          <span className="font-mono text-emerald-700">{ulpin}</span>
        </h1>

        {/* CITIZEN privacy banner */}
        {role === 'CITIZEN' && (
          <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
            <svg
              className="mt-0.5 h-4 w-4 shrink-0 text-yellow-500"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            <span>Some fields are masked for privacy.</span>
          </div>
        )}

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
          {renderTabContent(activeTab, ulpin, role)}
        </div>
      </main>

      <Footer />
    </div>
  )
}
