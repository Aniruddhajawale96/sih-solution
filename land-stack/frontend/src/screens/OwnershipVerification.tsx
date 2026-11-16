import { useState } from 'react'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/apiClient'
import { maskCitizenData } from '@/screens/Parcel360View'
import { Download } from 'lucide-react'

// ── Shared display helpers ────────────────────────────────────────────────────
// Duplicated here (rather than imported from Parcel360View) to avoid a
// potential circular-dependency issue if Parcel360View ever imports this file.

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
            <FlatRecord obj={item as Record<string, unknown>} />
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

// ── VerificationResult ────────────────────────────────────────────────────────

export interface VerificationResultProps {
  data: unknown
  ulpin: string
}

export function VerificationResult({ data, ulpin }: VerificationResultProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  async function handleDownload() {
    setDownloadError(null)
    setIsDownloading(true)
    try {
      const response = await apiClient.get(`/ror/${ulpin}/certificate`, {
        responseType: 'blob',
      })
      const blobUrl = URL.createObjectURL(response.data as Blob)
      const anchor = document.createElement('a')
      anchor.href = blobUrl
      anchor.download = `ownership-certificate-${ulpin}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      document.body.removeChild(anchor)
      URL.revokeObjectURL(blobUrl)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? 'Failed to download certificate.'
      setDownloadError(message)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Record of Rights
        </h2>
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloading}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isDownloading ? (
            <>
              <svg
                className="animate-spin h-3.5 w-3.5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Downloading…
            </>
          ) : (
            <>
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Download Certificate (PDF)
            </>
          )}
        </button>
      </div>

      {downloadError && (
        <div className="mx-6 mt-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs px-4 py-3">
          <span className="font-semibold">Download failed: </span>{downloadError}
        </div>
      )}

      <DataTable data={data} />
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

type FetchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: unknown }

export default function OwnershipVerification() {
  const role = useAuthStore(s => s.role)

  const [ulpin, setUlpin] = useState('')
  const [fetchState, setFetchState] = useState<FetchState>({ status: 'idle' })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = ulpin.trim()
    if (!trimmed) return

    setFetchState({ status: 'loading' })
    try {
      const { data } = await apiClient.get(`/ror/${trimmed}`)
      setFetchState({ status: 'success', data })
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? 'Failed to fetch Record of Rights.'
      setFetchState({ status: 'error', message })
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8">
        {/* Page heading */}
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Ownership Verification</h1>

        {/* Search form */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 flex flex-col gap-1">
              <label htmlFor="ulpin" className="text-sm font-medium text-slate-700">
                ULPIN
              </label>
              <input
                id="ulpin"
                type="text"
                required
                value={ulpin}
                onChange={e => setUlpin(e.target.value)}
                placeholder="e.g. CH-UT-000001"
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent font-mono"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={fetchState.status === 'loading'}
                className="bg-emerald-600 text-white rounded-lg px-5 py-2 text-sm font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {fetchState.status === 'loading' ? (
                  <span className="flex items-center gap-2">
                    <svg
                      className="animate-spin h-4 w-4"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Verifying…
                  </span>
                ) : (
                  'Verify Ownership'
                )}
              </button>
            </div>
          </form>
        </div>

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

        {/* Result area */}
        {fetchState.status === 'idle' && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-400 text-sm">
            Enter a ULPIN above and click <span className="font-medium text-slate-600">Verify Ownership</span> to view the Record of Rights.
          </div>
        )}

        {fetchState.status === 'error' && (
          <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-5 py-4">
            <span className="font-semibold">Error: </span>{fetchState.message}
          </div>
        )}

        {fetchState.status === 'success' && (
          <VerificationResult data={maskCitizenData(fetchState.data, role)} ulpin={ulpin.trim()} />
        )}
      </main>

      <Footer />
    </div>
  )
}
