import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

// ── Types ─────────────────────────────────────────────────────────────────────

interface AuditEntry {
  entry_id: string
  ulpin: string
  action: string
  actor: string
  timestamp: string
  payload_hash: string
  prev_hash: string
  chain_hash: string
}

type VerifyStatus = 'idle' | 'running' | 'intact' | 'corrupted'

interface VerifyResult {
  status: VerifyStatus
  firstCorruptedId?: string
  entryValidity: Record<string, boolean | null>
}

// ── SHA-256 helper ────────────────────────────────────────────────────────────

async function sha256(input: string): Promise<string> {
  const encoded = new TextEncoder().encode(input)
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', encoded)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

// ── Chain verification ────────────────────────────────────────────────────────

async function verifyChain(entries: AuditEntry[]): Promise<VerifyResult> {
  // Entries arrive newest-first from display; verify in chronological order (oldest-first).
  const chronological = [...entries].reverse()
  const entryValidity: Record<string, boolean | null> = {}

  for (const entry of entries) {
    entryValidity[entry.entry_id] = null
  }

  let firstCorruptedId: string | undefined

  for (const entry of chronological) {
    const recomputed = await sha256(entry.prev_hash + entry.payload_hash)
    const valid = recomputed === entry.chain_hash
    entryValidity[entry.entry_id] = valid
    if (!valid && firstCorruptedId === undefined) {
      firstCorruptedId = entry.entry_id
    }
  }

  return {
    status: firstCorruptedId ? 'corrupted' : 'intact',
    firstCorruptedId,
    entryValidity,
  }
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="flex-1 flex items-center justify-center gap-3 text-slate-400 py-24">
      <svg
        className="animate-spin h-6 w-6 text-slate-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <span className="text-sm font-medium">Loading audit trail…</span>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="max-w-2xl mx-auto mt-8 px-4">
      <div className="p-4 rounded-lg bg-red-900/10 border border-red-800/30 text-red-300 text-sm">
        <span className="font-semibold">Error: </span>{message}
      </div>
    </div>
  )
}

// ── Validity badge ────────────────────────────────────────────────────────────

function ValidityBadge({ valid }: { valid: boolean | null }) {
  if (valid === null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-700 text-slate-400 border border-slate-600">
        —
      </span>
    )
  }
  if (valid) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-900/40 text-emerald-400 border border-emerald-700/50">
        ✓
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-red-900/40 text-red-400 border border-red-700/50">
      ✗
    </span>
  )
}

// ── Verification banner ───────────────────────────────────────────────────────

function VerificationBanner({ result }: { result: VerifyResult }) {
  if (result.status === 'intact') {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-emerald-900/20 border border-emerald-700/40 text-emerald-400">
        <span className="text-xl" aria-hidden="true">🔒</span>
        <div>
          <p className="font-semibold text-sm">Chain Intact ✓</p>
          <p className="text-xs text-emerald-500/80 mt-0.5">
            All SHA-256 chain hashes match. The audit log has not been tampered with.
          </p>
        </div>
      </div>
    )
  }

  if (result.status === 'corrupted') {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-red-900/20 border border-red-700/40 text-red-400">
        <span className="text-xl" aria-hidden="true">⚠️</span>
        <div>
          <p className="font-semibold text-sm">Chain Corrupted ✗</p>
          <p className="text-xs text-red-500/80 mt-0.5">
            First corrupted entry:{' '}
            <span className="font-mono text-red-400">
              {result.firstCorruptedId?.slice(0, 12)}…
            </span>{' '}
            — the audit log may have been tampered with.
          </p>
        </div>
      </div>
    )
  }

  return null
}

// ── Verify button ─────────────────────────────────────────────────────────────

interface VerifyButtonProps {
  verifyStatus: VerifyStatus
  onClick: () => void
}

function VerifyButton({ verifyStatus, onClick }: VerifyButtonProps) {
  const isRunning = verifyStatus === 'running'

  return (
    <button
      onClick={onClick}
      disabled={isRunning}
      className={[
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400',
        isRunning
          ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
          : 'bg-slate-700 hover:bg-slate-600 text-slate-100 border border-slate-600',
      ].join(' ')}
    >
      {isRunning ? (
        <>
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
        </>
      ) : (
        <>
          <svg
            className="h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
          Verify Chain
        </>
      )}
    </button>
  )
}

// ── Audit table ───────────────────────────────────────────────────────────────

interface AuditTableProps {
  entries: AuditEntry[]
  entryValidity: Record<string, boolean | null>
}

function AuditTable({ entries, entryValidity }: AuditTableProps) {
  if (entries.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-slate-500">
        No audit entries found for this parcel.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-800/60 text-left">
            {['Timestamp', 'Action', 'Actor', 'Entry ID', 'Chain Hash', 'Valid'].map(h => (
              <th
                key={h}
                className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide border-b border-slate-700"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {entries.map(entry => {
            const valid = entryValidity[entry.entry_id] ?? null
            const isCorrupted = valid === false

            return (
              <tr
                key={entry.entry_id}
                className={[
                  'transition-colors',
                  isCorrupted
                    ? 'bg-red-900/10 hover:bg-red-900/20'
                    : 'hover:bg-slate-800/40',
                ].join(' ')}
              >
                {/* Timestamp */}
                <td className="px-4 py-3 whitespace-nowrap text-slate-300 font-mono text-xs">
                  {new Date(entry.timestamp).toLocaleString(undefined, {
                    dateStyle: 'short',
                    timeStyle: 'medium',
                  })}
                </td>

                {/* Action */}
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-700 text-slate-200 border border-slate-600">
                    {entry.action}
                  </span>
                </td>

                {/* Actor */}
                <td className="px-4 py-3 text-slate-300 text-xs">{entry.actor}</td>

                {/* Entry ID (truncated) */}
                <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">
                  <span title={entry.entry_id}>
                    {entry.entry_id.slice(0, 8)}…
                  </span>
                </td>

                {/* Chain hash (truncated) */}
                <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">
                  <span title={entry.chain_hash}>
                    {entry.chain_hash.slice(0, 12)}…
                  </span>
                </td>

                {/* Validity badge */}
                <td className="px-4 py-3">
                  <ValidityBadge valid={valid} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function AuditTrailViewer() {
  const { ulpin } = useParams<{ ulpin: string }>()

  const [verifyResult, setVerifyResult] = useState<VerifyResult>({
    status: 'idle',
    entryValidity: {},
  })

  const { data: entries, isLoading, isError, error } = useQuery<AuditEntry[]>({
    queryKey: ['audit', ulpin],
    queryFn: () => apiClient.get(`/analytics/audit/${ulpin}`).then(r => r.data),
    enabled: Boolean(ulpin),
  })

  // Sort newest-first for display
  const sortedEntries = entries
    ? [...entries].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )
    : []

  async function handleVerify() {
    if (!sortedEntries.length) return

    setVerifyResult({ status: 'running', entryValidity: {} })

    const result = await verifyChain(sortedEntries)
    setVerifyResult(result)
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-100">
      <TopNav />

      <main className="flex-1 flex flex-col">
        {isLoading && <LoadingSpinner />}

        {isError && (
          <ErrorBanner message={(error as Error)?.message ?? 'Failed to load audit trail.'} />
        )}

        {!isLoading && !isError && (
          <div className="max-w-6xl w-full mx-auto px-4 py-8 space-y-6">

            {/* Page heading */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-slate-700 border border-slate-600">
                  <svg
                    className="h-6 w-6 text-slate-300"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                    />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-100">Audit Trail</h1>
                  <p className="text-sm text-slate-400 mt-0.5 font-mono">
                    ULPIN: <span className="text-slate-300">{ulpin}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {sortedEntries.length > 0 && (
                  <span className="text-xs text-slate-500">
                    {sortedEntries.length} entr{sortedEntries.length === 1 ? 'y' : 'ies'}
                  </span>
                )}
                <VerifyButton
                  verifyStatus={verifyResult.status}
                  onClick={handleVerify}
                />
              </div>
            </div>

            {/* Verification result banner */}
            {(verifyResult.status === 'intact' || verifyResult.status === 'corrupted') && (
              <VerificationBanner result={verifyResult} />
            )}

            {/* Audit log table */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 shadow-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-slate-500" aria-hidden="true" />
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                  Hash-chained tamper-evident log
                </span>
              </div>

              <AuditTable
                entries={sortedEntries}
                entryValidity={verifyResult.entryValidity}
              />
            </div>

            {/* Footer note */}
            <p className="text-xs text-slate-600 text-center pb-2">
              Chain hash = SHA-256(prev_hash ∥ payload_hash). Verification runs client-side using the Web Crypto API.
            </p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}
