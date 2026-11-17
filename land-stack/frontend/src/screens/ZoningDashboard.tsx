import { useRef, useState } from 'react'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ZoningPublic {
  ulpin: string
  master_plan_zone: string
  permissible_use: string
  far_permitted: number
  far_existing: number
  violation_flag: boolean
}

interface ChangeDetectionResponse {
  ulpin: string
  changed_area_sqm: number
  far_existing_est: number
  violation_flag: boolean
}

// ─── ZoningLookupPanel ────────────────────────────────────────────────────────

function ZoningLookupPanel() {
  const [ulpin, setUlpin] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ZoningPublic | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleLookup() {
    const trimmed = ulpin.trim()
    if (!trimmed) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const { data } = await apiClient.get<ZoningPublic>(`/zoning/${encodeURIComponent(trimmed)}`)
      setResult(data)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } }; message?: string })
          ?.response?.data?.detail ??
        (err as { message?: string })?.message ??
        'Lookup failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleLookup()
  }

  return (
    <div className="flex flex-col gap-5 h-full">
      <div>
        <h2 className="text-lg font-bold text-slate-800">Zoning Record Lookup</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Enter a ULPIN to fetch its master-plan zone and FAR data.
        </p>
      </div>

      {/* ULPIN input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={ulpin}
          onChange={e => { setUlpin(e.target.value); setError(null); setResult(null) }}
          onKeyDown={handleKeyDown}
          placeholder="e.g. CH-01-001-0001"
          className="flex-1 text-sm rounded-lg border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <button
          onClick={handleLookup}
          disabled={!ulpin.trim() || loading}
          className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {loading ? 'Looking up…' : 'Look up'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl px-5 py-4 space-y-3">
          {/* Violation badge */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              {result.ulpin}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${
                result.violation_flag
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {result.violation_flag ? '⚠ Violation' : '✓ Compliant'}
            </span>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
            <div>
              <dt className="text-xs text-slate-500">Master Plan Zone</dt>
              <dd className="text-sm font-medium text-slate-800 mt-0.5">{result.master_plan_zone}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Permissible Use</dt>
              <dd className="text-sm font-medium text-slate-800 mt-0.5">{result.permissible_use}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">FAR Permitted</dt>
              <dd className="text-sm font-medium text-slate-800 mt-0.5">{result.far_permitted}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">FAR Existing</dt>
              <dd className={`text-sm font-medium mt-0.5 ${result.violation_flag ? 'text-red-600' : 'text-slate-800'}`}>
                {result.far_existing}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}

// ─── ChangeDetectionPanel ─────────────────────────────────────────────────────

function ChangeDetectionPanel() {
  const [beforeFile, setBeforeFile] = useState<File | null>(null)
  const [afterFile, setAfterFile] = useState<File | null>(null)
  const [ulpin, setUlpin] = useState('')
  const [farPermitted, setFarPermitted] = useState('')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ChangeDetectionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const beforeRef = useRef<HTMLInputElement>(null)
  const afterRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    if (!beforeFile || !afterFile || !ulpin.trim() || !farPermitted) return
    setUploading(true)
    setResult(null)
    setError(null)

    const formData = new FormData()
    formData.append('before_image', beforeFile)
    formData.append('after_image', afterFile)
    formData.append('ulpin', ulpin.trim())
    formData.append('far_permitted', farPermitted)

    try {
      const { data } = await apiClient.post<ChangeDetectionResponse>(
        '/ml/change-detection',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      setResult(data)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string }; statusText?: string }; message?: string })
          ?.response?.data?.detail ??
        (err as { message?: string })?.message ??
        'Upload failed. Please try again.'
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  function handleReset() {
    setBeforeFile(null)
    setAfterFile(null)
    setUlpin('')
    setFarPermitted('')
    setResult(null)
    setError(null)
    if (beforeRef.current) beforeRef.current.value = ''
    if (afterRef.current) afterRef.current.value = ''
  }

  const canSubmit = !!beforeFile && !!afterFile && !!ulpin.trim() && !!farPermitted

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-800">Change Detection</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Upload before/after satellite images to detect FAR changes and flag violations.
        </p>
      </div>

      {/* ULPIN input */}
      <div>
        <label className="block text-xs font-semibold text-slate-600 mb-1">ULPIN</label>
        <input
          type="text"
          value={ulpin}
          onChange={e => setUlpin(e.target.value)}
          placeholder="e.g. CH-01-001-0001"
          className="w-full text-sm rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      {/* FAR Permitted input */}
      <div>
        <label className="block text-xs font-semibold text-slate-600 mb-1">FAR Permitted</label>
        <input
          type="number"
          step="0.01"
          min="0"
          value={farPermitted}
          onChange={e => setFarPermitted(e.target.value)}
          placeholder="e.g. 1.5"
          className="w-full text-sm rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      {/* File pickers */}
      <div className="grid grid-cols-2 gap-3">
        {/* Before image */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Before Image</label>
          <div
            onClick={() => beforeRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl px-3 py-4 cursor-pointer hover:border-emerald-400 hover:bg-emerald-50 transition-colors"
          >
            {beforeFile ? (
              <span className="text-xs font-medium text-emerald-700 truncate max-w-full text-center">{beforeFile.name}</span>
            ) : (
              <span className="text-xs text-slate-500 text-center">Click to select<br />before image</span>
            )}
            <input
              ref={beforeRef}
              type="file"
              accept="image/*"
              onChange={e => setBeforeFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
          </div>
        </div>

        {/* After image */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">After Image</label>
          <div
            onClick={() => afterRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl px-3 py-4 cursor-pointer hover:border-emerald-400 hover:bg-emerald-50 transition-colors"
          >
            {afterFile ? (
              <span className="text-xs font-medium text-emerald-700 truncate max-w-full text-center">{afterFile.name}</span>
            ) : (
              <span className="text-xs text-slate-500 text-center">Click to select<br />after image</span>
            )}
            <input
              ref={afterRef}
              type="file"
              accept="image/*"
              onChange={e => setAfterFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleUpload}
          disabled={!canSubmit || uploading}
          className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
        >
          {uploading ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Analysing…
            </>
          ) : (
            'Run Detection'
          )}
        </button>
        {(beforeFile || afterFile || result) && (
          <button
            onClick={handleReset}
            className="px-4 py-2.5 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm flex gap-2 items-start">
          <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="flex flex-col gap-3 bg-slate-50 border border-slate-200 rounded-xl px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Changed Area</span>
              <span className="text-2xl font-bold text-emerald-700 mt-0.5">
                {result.changed_area_sqm.toFixed(1)} m²
              </span>
            </div>
            <span
              className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${
                result.violation_flag
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {result.violation_flag ? '⚠ Violation flagged' : '✓ No violation'}
            </span>
          </div>
          <div className="text-xs text-slate-600">
            Estimated FAR existing: <span className="font-semibold">{result.far_existing_est}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── ZoningDashboard ──────────────────────────────────────────────────────────

export default function ZoningDashboard() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 px-4 py-8 max-w-7xl mx-auto w-full">
        {/* Page heading */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Zoning &amp; Change Detection</h1>
          <p className="text-slate-500 text-sm mt-1">
            Look up zoning records by ULPIN and run satellite change-detection analysis
          </p>
        </div>

        {/* Two-column layout */}
        <div className="flex flex-col md:flex-row gap-6">
          {/* ── Left: Zoning Lookup (50%) ── */}
          <div className="w-full md:w-1/2">
            <div className="bg-white rounded-xl shadow-md border border-slate-200 px-6 py-6 h-full">
              <ZoningLookupPanel />
            </div>
          </div>

          {/* ── Right: ChangeDetectionPanel (50%) ── */}
          <div className="w-full md:w-1/2">
            <div className="bg-white rounded-xl shadow-md border border-slate-200 px-6 py-6 h-full">
              <ChangeDetectionPanel />
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
