import { useState, useEffect, useRef, useCallback } from 'react'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { useAuthStore } from '@/store/authStore'

interface SseEvent {
  id: string
  type: string
  rawData: string
  parsedData: Record<string, unknown> | null
  receivedAt: Date
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

// Known event types
const KNOWN_TYPES = ['sync_started', 'sync_completed', 'sync_failed', 'task_updated'] as const

type KnownType = (typeof KNOWN_TYPES)[number]

const TYPE_BADGE: Record<KnownType | 'unknown', { bg: string; text: string; label: string }> = {
  sync_completed: { bg: 'bg-green-100', text: 'text-green-800', label: 'sync_completed' },
  sync_failed:    { bg: 'bg-red-100',   text: 'text-red-800',   label: 'sync_failed' },
  sync_started:   { bg: 'bg-blue-100',  text: 'text-blue-800',  label: 'sync_started' },
  task_updated:   { bg: 'bg-indigo-100',text: 'text-indigo-800',label: 'task_updated' },
  unknown:        { bg: 'bg-slate-100', text: 'text-slate-600', label: 'unknown' },
}

function typeBadgeStyle(type: string) {
  return TYPE_BADGE[type as KnownType] ?? TYPE_BADGE.unknown
}

function formatTs(date: Date): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date)
  } catch {
    return date.toISOString()
  }
}

function tryParseJson(raw: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed as Record<string, unknown>
    return null
  } catch {
    return null
  }
}

/** Extract the most useful summary fields from parsed event data */
function summaryFields(type: string, data: Record<string, unknown> | null): { label: string; value: string }[] {
  if (!data) return []
  const fields: { label: string; value: string }[] = []

  if (type === 'task_updated') {
    if (data.task_id != null) fields.push({ label: 'task_id', value: String(data.task_id) })
    if (data.status != null) fields.push({ label: 'status', value: String(data.status) })
    if (data.updated_at != null) fields.push({ label: 'updated_at', value: String(data.updated_at) })
  } else {
    // sync_started / sync_completed / sync_failed + generics with job_id
    if (data.job_id != null) fields.push({ label: 'job_id', value: String(data.job_id) })
    if (data.state != null) fields.push({ label: 'state', value: String(data.state) })
    if (data.started_at != null) fields.push({ label: 'started_at', value: String(data.started_at) })
    if (data.completed_at != null) fields.push({ label: 'completed_at', value: String(data.completed_at) })
    if (data.records_synced != null) fields.push({ label: 'records_synced', value: String(data.records_synced) })
    if (data.error != null) fields.push({ label: 'error', value: String(data.error) })
  }

  return fields
}

function StatusDot({ status }: { status: ConnectionStatus }) {
  if (status === 'connected') {
    return (
      <span className="inline-flex items-center gap-1.5 text-green-700 text-sm font-medium">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
        </span>
        Connected
      </span>
    )
  }
  if (status === 'connecting') {
    return (
      <span className="inline-flex items-center gap-1.5 text-yellow-700 text-sm font-medium">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-500" />
        </span>
        Connecting…
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-red-700 text-sm font-medium">
      <span className="relative flex h-2.5 w-2.5">
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
      </span>
      Disconnected
    </span>
  )
}

function EventRow({ event }: { event: SseEvent }) {
  const [expanded, setExpanded] = useState(false)
  const badge = typeBadgeStyle(event.type)
  const summary = summaryFields(event.type, event.parsedData)

  return (
    <div className="border-b border-slate-100 last:border-0 px-4 py-3 hover:bg-slate-50 transition-colors">
      <div className="flex items-start gap-3 flex-wrap">
        {/* Timestamp */}
        <span className="text-xs text-slate-400 font-mono whitespace-nowrap pt-0.5 w-20 shrink-0">
          {formatTs(event.receivedAt)}
        </span>

        {/* Type badge */}
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${badge.bg} ${badge.text}`}>
          {event.type}
        </span>

        {/* Summary fields */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 flex-1 min-w-0">
          {summary.map(f => (
            <span key={f.label} className="text-xs text-slate-600">
              <span className="text-slate-400 font-medium">{f.label}:</span>{' '}
              <span className="font-mono break-all">{f.value}</span>
            </span>
          ))}
          {summary.length === 0 && event.parsedData == null && (
            <span className="text-xs text-slate-400 italic">raw data</span>
          )}
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium shrink-0 ml-auto"
        >
          {expanded ? 'Hide JSON ▲' : 'Show JSON ▼'}
        </button>
      </div>

      {/* Expandable raw JSON */}
      {expanded && (
        <div className="mt-2 ml-24">
          <pre className="text-xs bg-slate-100 text-slate-700 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">
            {event.rawData
              ? (() => { try { return JSON.stringify(JSON.parse(event.rawData), null, 2) } catch { return event.rawData } })()
              : '(empty)'}
          </pre>
        </div>
      )}
    </div>
  )
}

const MAX_EVENTS = 100
let eventCounter = 0

export default function SyncMonitor() {
  const accessToken = useAuthStore(s => s.accessToken)
  const [events, setEvents] = useState<SseEvent[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const esRef = useRef<EventSource | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    // Clean up any existing connection
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    setStatus('connecting')

    const url = accessToken
      ? `/api/v1/workflow/events/stream?token=${encodeURIComponent(accessToken)}`
      : '/api/v1/workflow/events/stream'

    const es = new EventSource(url)
    esRef.current = es

    function pushEvent(type: string, rawData: string) {
      const entry: SseEvent = {
        id: String(++eventCounter),
        type,
        rawData,
        parsedData: tryParseJson(rawData),
        receivedAt: new Date(),
      }
      setEvents(prev => [entry, ...prev].slice(0, MAX_EVENTS))
    }

    es.onopen = () => setStatus('connected')

    // Handle known event types
    for (const t of KNOWN_TYPES) {
      es.addEventListener(t, (e: MessageEvent) => {
        pushEvent(t, e.data ?? '')
      })
    }

    // Generic "message" fallback for events without a type field
    es.onmessage = (e: MessageEvent) => {
      pushEvent('message', e.data ?? '')
    }

    es.onerror = () => {
      setStatus('disconnected')
      es.close()
      esRef.current = null
      // Attempt reconnect after 5 seconds
      reconnectTimer.current = setTimeout(() => connect(), 5000)
    }
  }, [accessToken])

  useEffect(() => {
    connect()
    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
    }
  }, [connect])

  function clearLog() {
    setEvents([])
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />
      <main className="flex-1 px-4 py-8 max-w-6xl mx-auto w-full">
        {/* Page header */}
        <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Cross-Department Sync Monitor</h1>
            <p className="text-slate-500 text-sm mt-1">Live event feed from <code className="font-mono text-xs bg-slate-100 px-1 rounded">/workflow/events/stream</code></p>
          </div>
          <div className="flex items-center gap-4">
            <StatusDot status={status} />
            <button
              onClick={clearLog}
              className="text-sm font-medium text-slate-600 hover:text-red-600 border border-slate-300 hover:border-red-300 px-3 py-1.5 rounded-lg transition-colors"
            >
              Clear Log
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="mb-4 flex flex-wrap gap-2 items-center">
          <span className="text-xs text-slate-400 font-medium mr-1">Event types:</span>
          {(Object.entries(TYPE_BADGE) as [string, { bg: string; text: string; label: string }][]).map(([, v]) => (
            <span key={v.label} className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.bg} ${v.text}`}>
              {v.label}
            </span>
          ))}
        </div>

        {/* Event log */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {/* Table header */}
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Event Log
            </span>
            <span className="text-xs text-slate-400">
              {events.length === 0
                ? 'No events yet'
                : `${events.length} event${events.length !== 1 ? 's' : ''} (newest first)`}
            </span>
          </div>

          {events.length === 0 ? (
            <div className="py-20 text-center text-slate-400">
              <p className="text-4xl mb-3">📡</p>
              <p className="font-medium text-slate-500">
                {status === 'connecting'
                  ? 'Connecting to event stream…'
                  : status === 'disconnected'
                  ? 'Disconnected. Will retry in 5 seconds.'
                  : 'Waiting for events…'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {events.map(ev => (
                <EventRow key={ev.id} event={ev} />
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
