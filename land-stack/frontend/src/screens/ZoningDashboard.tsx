import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { useQuery } from '@tanstack/react-query'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Violation {
  ulpin: string
  lat: number
  lng: number
  violation_type: string
  severity: 'high' | 'medium' | 'low'
}

interface ChangeDetectionResult {
  changes_detected: number
  flagged_ulpins: string[]
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SEVERITY_COLOR: Record<Violation['severity'], string> = {
  high: '#ef4444',
  medium: '#f97316',
  low: '#eab308',
}

function severityLabel(s: Violation['severity']): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// ─── ViolationMap ─────────────────────────────────────────────────────────────

interface ViolationMapProps {
  violations: Violation[]
}

function ViolationMap({ violations }: ViolationMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  // Track any pending 'load' callback so we can cancel it before re-registering.
  // Without this, every render that fires before the map loads queues another
  // addMarkers call via map.once, resulting in duplicate markers (bug fix).
  const pendingAddMarkersRef = useRef<(() => void) | null>(null)

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [78.9629, 20.5937],
      zoom: 5,
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.ScaleControl(), 'bottom-left')

    mapRef.current = map

    return () => {
      // Cancel any pending load listener before destroying the map
      if (pendingAddMarkersRef.current) {
        map.off('load', pendingAddMarkersRef.current)
        pendingAddMarkersRef.current = null
      }
      markersRef.current.forEach((m) => m.remove())
      markersRef.current = []
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Add / refresh markers whenever violations change
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Cancel any previously queued load listener before proceeding.
    // If we don't do this, multiple renders before map.load fires will stack up
    // separate once('load', addMarkers) calls, each adding the full marker set.
    if (pendingAddMarkersRef.current) {
      map.off('load', pendingAddMarkersRef.current)
      pendingAddMarkersRef.current = null
    }

    // Remove existing markers
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []

    function addMarkers() {
      pendingAddMarkersRef.current = null
      violations.forEach((v) => {
        // Coloured dot element
        const el = document.createElement('div')
        el.style.cssText = `
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background-color: ${SEVERITY_COLOR[v.severity]};
          border: 2px solid white;
          box-shadow: 0 1px 4px rgba(0,0,0,0.4);
          cursor: pointer;
        `

        // Build popup with DOM nodes rather than setHTML to prevent XSS.
        // The original code used setHTML with raw string interpolation of
        // server-provided values (ulpin, violation_type) — a stored XSS vector.
        const popupEl = document.createElement('div')
        popupEl.style.cssText = 'font-family:sans-serif;font-size:13px;line-height:1.5;padding:4px 2px'

        const title = document.createElement('div')
        title.style.cssText = 'font-weight:700;color:#1e293b;margin-bottom:4px'
        title.textContent = v.ulpin
        popupEl.appendChild(title)

        const typeLine = document.createElement('div')
        typeLine.style.color = '#475569'
        const typeLabel = document.createElement('span')
        typeLabel.style.fontWeight = '600'
        typeLabel.textContent = 'Type: '
        typeLine.appendChild(typeLabel)
        typeLine.appendChild(document.createTextNode(v.violation_type))
        popupEl.appendChild(typeLine)

        const sevLine = document.createElement('div')
        sevLine.style.color = '#475569'
        const sevLabel = document.createElement('span')
        sevLabel.style.fontWeight = '600'
        sevLabel.textContent = 'Severity: '
        sevLine.appendChild(sevLabel)
        const sevValue = document.createElement('span')
        sevValue.style.cssText = `color:${SEVERITY_COLOR[v.severity]};font-weight:600`
        sevValue.textContent = severityLabel(v.severity)
        sevLine.appendChild(sevValue)
        popupEl.appendChild(sevLine)

        const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
          .setDOMContent(popupEl)

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([v.lng, v.lat])
          .setPopup(popup)
          .addTo(map!)

        el.addEventListener('click', () => marker.togglePopup())
        markersRef.current.push(marker)
      })
    }

    if (map.loaded()) {
      addMarkers()
    } else {
      pendingAddMarkersRef.current = addMarkers
      map.once('load', addMarkers)
    }
  }, [violations])

  return <div ref={containerRef} className="w-full h-full rounded-xl overflow-hidden" />
}

// ─── ChangeDetectionPanel ─────────────────────────────────────────────────────

function ChangeDetectionPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ChangeDetectionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setResult(null)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await apiClient.post<ChangeDetectionResult>(
        '/zoning/change-detection',
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

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    setResult(null)
    setError(null)
  }

  function handleReset() {
    setFile(null)
    setResult(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-800">Change Detection</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Upload a GeoJSON or ZIP file to detect land-use changes.
        </p>
      </div>

      {/* Upload box */}
      <div
        onClick={() => inputRef.current?.click()}
        className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-slate-300 rounded-xl px-6 py-8 cursor-pointer hover:border-emerald-400 hover:bg-emerald-50 transition-colors"
      >
        <svg
          className="w-10 h-10 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
        {file ? (
          <div className="text-center">
            <p className="text-sm font-medium text-emerald-700 truncate max-w-[180px]">{file.name}</p>
            <p className="text-xs text-slate-500 mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-sm font-medium text-slate-600">Click to select file</p>
            <p className="text-xs text-slate-400 mt-0.5">.geojson or .zip</p>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".geojson,.zip"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
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
        {(file || result) && (
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
        <div className="flex flex-col gap-4 bg-slate-50 border border-slate-200 rounded-xl px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Changes Detected</span>
              <span className="text-3xl font-bold text-emerald-700 mt-0.5">{result.changes_detected}</span>
            </div>
            <div className="ml-auto">
              <span
                className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${
                  result.changes_detected > 0
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-green-100 text-green-700'
                }`}
              >
                {result.changes_detected > 0 ? '⚠ Review needed' : '✓ No changes'}
              </span>
            </div>
          </div>

          {result.flagged_ulpins.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                Flagged ULPINs ({result.flagged_ulpins.length})
              </p>
              <ul className="space-y-1 max-h-48 overflow-y-auto pr-1">
                {result.flagged_ulpins.map((ulpin) => (
                  <li
                    key={ulpin}
                    className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-700"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                    {ulpin}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── ZoningDashboard ──────────────────────────────────────────────────────────

export default function ZoningDashboard() {
  const {
    data: violations,
    isLoading,
    isError,
    error,
  } = useQuery<Violation[]>({
    queryKey: ['zoning', 'violations'],
    queryFn: async () => {
      const { data } = await apiClient.get<Violation[]>('/zoning/violations')
      return data
    },
  })

  const violationList = violations ?? []

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 px-4 py-8 max-w-7xl mx-auto w-full">
        {/* Page heading */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Zoning &amp; Violation Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">
            FAR violations map and satellite change-detection analysis
          </p>
        </div>

        {/* Two-column layout */}
        <div className="flex flex-col md:flex-row gap-6">
          {/* ── Left: ViolationMap (60%) ── */}
          <div className="flex flex-col gap-3 w-full md:w-[60%]">
            {/* Violations count badge */}
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-slate-700">Violation Map</h2>
              {!isLoading && !isError && (
                <span className="inline-flex items-center gap-1.5 bg-red-100 text-red-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-red-500"
                    aria-hidden="true"
                  />
                  {violationList.length} violation{violationList.length !== 1 ? 's' : ''}
                </span>
              )}
              {isLoading && (
                <svg className="w-4 h-4 text-slate-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
            </div>

            {/* Severity legend */}
            <div className="flex items-center gap-4 text-xs text-slate-500">
              {(['high', 'medium', 'low'] as const).map((s) => (
                <span key={s} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full border border-white shadow"
                    style={{ backgroundColor: SEVERITY_COLOR[s] }}
                  />
                  {severityLabel(s)}
                </span>
              ))}
            </div>

            {isError && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
                <strong>Failed to load violations.</strong>{' '}
                {(error as { message?: string })?.message ?? 'Please try again.'}
              </div>
            )}

            {/* Map container — fixed height so MapLibre renders correctly */}
            <div className="rounded-xl overflow-hidden shadow-md border border-slate-200" style={{ height: '480px' }}>
              <ViolationMap violations={violationList} />
            </div>
          </div>

          {/* ── Right: ChangeDetectionPanel (40%) ── */}
          <div className="w-full md:w-[40%]">
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
