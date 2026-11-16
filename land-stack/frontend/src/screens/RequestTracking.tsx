import { useQuery } from '@tanstack/react-query'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

interface ServiceRequest {
  request_id: string
  service_type: string
  ulpin: string
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'completed'
  priority: 'normal' | 'urgent'
  created_at: string
  description?: string
}

const SERVICE_TYPE_LABELS: Record<string, string> = {
  mutation:         'Mutation / Name Change',
  encumbrance_cert: 'Encumbrance Certificate',
  ownership_cert:   'Ownership Certificate',
  land_use_change:  'Land Use Change',
  boundary_dispute: 'Boundary Dispute Resolution',
}

function serviceTypeLabel(raw: string): string {
  return SERVICE_TYPE_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const STATUS_STYLES: Record<ServiceRequest['status'], string> = {
  pending:     'bg-yellow-100 text-yellow-800 border-yellow-300',
  in_progress: 'bg-blue-100 text-blue-800 border-blue-300',
  approved:    'bg-green-100 text-green-800 border-green-300',
  rejected:    'bg-red-100 text-red-800 border-red-300',
  completed:   'bg-emerald-100 text-emerald-800 border-emerald-300',
}

const STATUS_LABELS: Record<ServiceRequest['status'], string> = {
  pending:     'Pending',
  in_progress: 'In Progress',
  approved:    'Approved',
  rejected:    'Rejected',
  completed:   'Completed',
}

function StatusBadge({ status }: { status: ServiceRequest['status'] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-700 border-slate-300'}`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: ServiceRequest['priority'] }) {
  if (priority === 'urgent') {
    return (
      <span className="inline-flex items-center rounded-full border border-orange-300 bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
        Urgent
      </span>
    )
  }
  return (
    <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
      Normal
    </span>
  )
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

async function fetchRequests(): Promise<ServiceRequest[]> {
  const { data } = await apiClient.get<ServiceRequest[]>('/citizen/requests')
  return data
}

export default function RequestTracking() {
  const { data, isLoading, isError, error } = useQuery<ServiceRequest[], Error>({
    queryKey: ['citizen', 'requests'],
    queryFn: fetchRequests,
  })

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />

      <main className="flex-1 bg-slate-50 py-10 px-4">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">Request Tracking</h1>
          <p className="text-slate-500 text-sm mb-6">
            All service requests you have submitted. Click a request to view details.
          </p>

          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-20 text-slate-500 gap-3">
              <svg
                className="animate-spin h-6 w-6 text-blue-600"
                xmlns="http://www.w3.org/2000/svg"
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
              <span className="text-sm">Loading your requests…</span>
            </div>
          )}

          {/* Error */}
          {isError && (
            <div className="flex items-start gap-3 rounded-lg border border-red-300 bg-red-50 p-4 text-red-800 mb-6">
              <span className="text-lg">⚠️</span>
              <div>
                <p className="font-semibold">Failed to load requests</p>
                <p className="text-sm mt-0.5">
                  {(error as Error)?.message ?? 'An unexpected error occurred. Please try again.'}
                </p>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && data && data.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl bg-white py-20 shadow-sm border border-slate-100 text-center px-6">
              <span className="text-5xl mb-4">📭</span>
              <p className="text-slate-700 font-semibold mb-1">No service requests found.</p>
              <p className="text-slate-500 text-sm">
                Submit one from the{' '}
                <a href="/service-request" className="text-blue-600 underline hover:text-blue-800">
                  Service Request Portal
                </a>
                .
              </p>
            </div>
          )}

          {/* Table */}
          {!isLoading && !isError && data && data.length > 0 && (
            <div className="overflow-x-auto rounded-xl shadow-sm border border-slate-200 bg-white">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-200 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
                    <th className="px-4 py-3 whitespace-nowrap">Request ID</th>
                    <th className="px-4 py-3 whitespace-nowrap">Service Type</th>
                    <th className="px-4 py-3 whitespace-nowrap">ULPIN</th>
                    <th className="px-4 py-3 whitespace-nowrap">Status</th>
                    <th className="px-4 py-3 whitespace-nowrap">Priority</th>
                    <th className="px-4 py-3 whitespace-nowrap">Submitted At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.map(req => (
                    <tr
                      key={req.request_id}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-700 whitespace-nowrap">
                        {req.request_id}
                      </td>
                      <td className="px-4 py-3 text-slate-800 whitespace-nowrap">
                        {serviceTypeLabel(req.service_type)}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600 whitespace-nowrap">
                        {req.ulpin}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <StatusBadge status={req.status} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <PriorityBadge priority={req.priority} />
                      </td>
                      <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                        {formatDate(req.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
