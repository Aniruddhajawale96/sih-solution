import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { useNavigate } from 'react-router-dom'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

// ─── Types ────────────────────────────────────────────────────────────────────

type LayerGroup = {
  label: string
  layerIds: string[]
  alwaysOn?: boolean
}

const LAYER_GROUPS: LayerGroup[] = [
  {
    label: 'Base',
    layerIds: ['parcels-fill', 'parcels-outline'],
    alwaysOn: true,
  },
  {
    label: 'Essential',
    layerIds: ['essential-fill', 'essential-outline'],
  },
  {
    label: 'Additional',
    layerIds: ['additional-fill', 'additional-outline'],
  },
  {
    label: 'Violation',
    layerIds: ['violation-fill', 'violation-outline'],
  },
]

const INDIAN_STATES = [
  'All States',
  'Gujarat',
  'Maharashtra',
  'Rajasthan',
  'Karnataka',
  'Tamil Nadu',
  'Uttar Pradesh',
  'Punjab',
  'Haryana',
  'Chandigarh',
]

interface ParcelResult {
  ulpin: string
  owner_name?: string
  survey_no?: string
  area?: number
  state?: string
  centroid?: [number, number]
  land_use?: string
  district?: string
  taluka?: string
  village?: string
}

// ─── LayerPanel ───────────────────────────────────────────────────────────────

interface LayerPanelProps {
  mapRef: React.RefObject<maplibregl.Map | null>
}

function LayerPanel({ mapRef }: LayerPanelProps) {
  const [expanded, setExpanded] = useState(true)
  const [visibility, setVisibility] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(LAYER_GROUPS.map((g) => [g.label, true]))
  )
  const [selectedState, setSelectedState] = useState('All States')

  function toggleGroup(label: string, layerIds: string[], alwaysOn?: boolean) {
    if (alwaysOn) return
    const map = mapRef.current
    if (!map) return

    const next = !visibility[label]
    setVisibility((prev) => ({ ...prev, [label]: next }))

    for (const layerId of layerIds) {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', next ? 'visible' : 'none')
      }
    }
  }

  function handleStateChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value
    setSelectedState(value)
    console.log('[LayerPanel] state filter changed:', value)
  }

  return (
    <div className="absolute top-4 left-4 z-10 bg-white rounded-xl shadow-lg border border-gray-200 w-56">
      {/* Header / collapse button */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 rounded-xl transition-colors"
        aria-expanded={expanded}
        aria-controls="layer-panel-body"
      >
        <span className="flex items-center gap-2">
          {/* Layers icon */}
          <svg
            className="w-4 h-4 text-emerald-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7"
            />
          </svg>
          Layers
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Panel body */}
      {expanded && (
        <div id="layer-panel-body" className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
          {/* Layer group toggles */}
          {LAYER_GROUPS.map(({ label, layerIds, alwaysOn }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{label}</span>
              <button
                role="switch"
                aria-checked={visibility[label]}
                aria-label={`Toggle ${label} layer`}
                disabled={alwaysOn}
                onClick={() => toggleGroup(label, layerIds, alwaysOn)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500
                  ${visibility[label] ? 'bg-emerald-500' : 'bg-gray-300'}
                  ${alwaysOn ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform
                    ${visibility[label] ? 'translate-x-4' : 'translate-x-1'}`}
                />
              </button>
            </div>
          ))}

          {/* Divider */}
          <hr className="border-gray-100" />

          {/* State filter */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              State Filter
            </label>
            <select
              value={selectedState}
              onChange={handleStateChange}
              className="w-full text-sm border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            >
              {INDIAN_STATES.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── SearchBar ────────────────────────────────────────────────────────────────

interface SearchBarProps {
  mapRef: React.RefObject<maplibregl.Map | null>
  onSelectParcel: (parcel: ParcelResult) => void
}

function SearchBar({ mapRef, onSelectParcel }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ParcelResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value
    setQuery(value)

    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (!value.trim()) {
      setResults([])
      setOpen(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await apiClient.get<ParcelResult[]>('/parcels/search', {
          params: { q: value.trim() },
        })
        setResults(res.data ?? [])
        setOpen(true)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
  }

  function handleSelect(parcel: ParcelResult) {
    setOpen(false)
    setQuery(parcel.ulpin)

    if (parcel.centroid) {
      const [lng, lat] = parcel.centroid
      mapRef.current?.flyTo({ center: [lng, lat], zoom: 14 })
    }

    onSelectParcel(parcel)
  }

  return (
    <div ref={containerRef} className="absolute top-4 left-64 right-4 z-10">
      <div className="relative">
        {/* Input */}
        <div className="flex items-center bg-white rounded-xl shadow-lg border border-gray-200 px-3 py-2 gap-2">
          <svg
            className="w-4 h-4 text-gray-400 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 1 0 6.75 6.75a7.5 7.5 0 0 0 10.6 10.6z"
            />
          </svg>
          <input
            type="text"
            value={query}
            onChange={handleChange}
            placeholder="Search by ULPIN, owner name, or survey number…"
            className="flex-1 text-sm text-gray-700 placeholder-gray-400 bg-transparent outline-none"
          />
          {loading && (
            <svg
              className="w-4 h-4 text-emerald-500 animate-spin shrink-0"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
          )}
        </div>

        {/* Dropdown results */}
        {open && results.length > 0 && (
          <ul className="absolute top-full mt-1 left-0 right-0 bg-white rounded-xl shadow-xl border border-gray-200 max-h-64 overflow-y-auto z-20">
            {results.map((parcel) => (
              <li key={parcel.ulpin}>
                <button
                  onClick={() => handleSelect(parcel)}
                  className="w-full text-left px-4 py-2.5 hover:bg-emerald-50 transition-colors border-b border-gray-100 last:border-0"
                >
                  <span className="text-sm font-medium text-gray-800">{parcel.ulpin}</span>
                  {(parcel.owner_name || parcel.survey_no) && (
                    <span className="text-xs text-gray-500 ml-2">
                      {parcel.owner_name && parcel.owner_name}
                      {parcel.owner_name && parcel.survey_no && ' · '}
                      {parcel.survey_no && `Survey ${parcel.survey_no}`}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* No results message */}
        {open && !loading && results.length === 0 && query.trim() && (
          <div className="absolute top-full mt-1 left-0 right-0 bg-white rounded-xl shadow-xl border border-gray-200 px-4 py-3 z-20">
            <p className="text-sm text-gray-500">No parcels found for "{query}".</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── ParcelPreview sidebar ────────────────────────────────────────────────────

interface ParcelPreviewProps {
  parcel: ParcelResult
  onClose: () => void
}

function ParcelPreview({ parcel, onClose }: ParcelPreviewProps) {
  const navigate = useNavigate()

  const rows: { label: string; value: string | number | undefined }[] = [
    { label: 'ULPIN', value: parcel.ulpin },
    { label: 'Owner', value: parcel.owner_name },
    { label: 'Survey No.', value: parcel.survey_no },
    { label: 'Area', value: parcel.area != null ? `${parcel.area} sq m` : undefined },
    { label: 'State', value: parcel.state },
    { label: 'District', value: parcel.district },
    { label: 'Taluka', value: parcel.taluka },
    { label: 'Village', value: parcel.village },
    { label: 'Land Use', value: parcel.land_use },
  ]

  return (
    <div className="absolute top-0 right-0 h-full w-80 z-10 bg-white shadow-xl border-l border-slate-200 overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 sticky top-0 bg-white z-10">
        <div>
          <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide">Parcel Preview</p>
          <h2 className="text-sm font-semibold text-gray-800 mt-0.5 truncate max-w-[200px]">
            {parcel.ulpin}
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close parcel preview"
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Detail rows */}
      <div className="px-5 py-4 flex-1 space-y-3">
        {rows.map(({ label, value }) =>
          value != null ? (
            <div key={label} className="flex flex-col gap-0.5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
              <span className="text-sm text-gray-800">{value}</span>
            </div>
          ) : null
        )}

        {parcel.centroid && (
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Coordinates</span>
            <span className="text-sm text-gray-800 font-mono">
              {parcel.centroid[1].toFixed(5)}, {parcel.centroid[0].toFixed(5)}
            </span>
          </div>
        )}
      </div>

      {/* Footer CTA */}
      <div className="px-5 py-4 border-t border-slate-200 sticky bottom-0 bg-white">
        <button
          onClick={() => navigate(`/parcel/${parcel.ulpin}`)}
          className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
        >
          View Full Details
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// ─── GisMapExplorer ───────────────────────────────────────────────────────────

export default function GisMapExplorer() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [selectedParcel, setSelectedParcel] = useState<ParcelResult | null>(null)

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [78.9629, 20.5937],
      zoom: 5,
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.ScaleControl(), 'bottom-left')

    map.on('load', () => {
      map.addSource('parcels', {
        type: 'vector',
        tiles: ['/tiles/public.parcels/{z}/{x}/{y}.pbf'],
        minzoom: 10,
        maxzoom: 18,
      })

      map.addLayer({
        id: 'parcels-fill',
        type: 'fill',
        source: 'parcels',
        'source-layer': 'public.parcels',
        paint: {
          'fill-color': '#10b981',
          'fill-opacity': 0.25,
        },
      })

      map.addLayer({
        id: 'parcels-outline',
        type: 'line',
        source: 'parcels',
        'source-layer': 'public.parcels',
        paint: {
          'line-color': '#059669',
          'line-width': 1,
        },
      })

      // Map click handler: open ParcelPreview when a parcel polygon is clicked
      map.on('click', 'parcels-fill', (e) => {
        const feature = e.features?.[0]
        if (!feature) return

        const props = feature.properties as Record<string, unknown>
        const parcel: ParcelResult = {
          ulpin: String(props.ulpin ?? props.id ?? ''),
          owner_name: props.owner_name != null ? String(props.owner_name) : undefined,
          survey_no: props.survey_no != null ? String(props.survey_no) : undefined,
          area: props.area != null ? Number(props.area) : undefined,
          state: props.state != null ? String(props.state) : undefined,
          district: props.district != null ? String(props.district) : undefined,
          taluka: props.taluka != null ? String(props.taluka) : undefined,
          village: props.village != null ? String(props.village) : undefined,
          land_use: props.land_use != null ? String(props.land_use) : undefined,
          centroid:
            props.centroid_lng != null && props.centroid_lat != null
              ? [Number(props.centroid_lng), Number(props.centroid_lat)]
              : e.lngLat
              ? [e.lngLat.lng, e.lngLat.lat]
              : undefined,
        }

        setSelectedParcel(parcel)
      })

      // Change cursor to pointer when hovering over a parcel
      map.on('mouseenter', 'parcels-fill', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'parcels-fill', () => {
        map.getCanvas().style.cursor = ''
      })
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <div className="flex-1 relative" style={{ minHeight: '600px' }}>
        <LayerPanel mapRef={mapRef} />
        <SearchBar mapRef={mapRef} onSelectParcel={setSelectedParcel} />
        <div ref={mapContainerRef} className="absolute inset-0" />
        {selectedParcel && (
          <ParcelPreview parcel={selectedParcel} onClose={() => setSelectedParcel(null)} />
        )}
      </div>
      <Footer />
    </div>
  )
}
