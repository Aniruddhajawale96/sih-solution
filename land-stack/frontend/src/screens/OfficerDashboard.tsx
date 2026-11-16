import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

interface WorkflowTask {
  task_id: string
  request_id: string
  service_type: string
  ulpin: string
  submitted_by?: string
  assigned_at: string
  status: 'pending' | 'in_review' | 'approved' | 'rejected'
}

const SERVICE_TYPE_LABELS: Record<string, string> = {
  mutation: 'Mutation',
  encumbrance: 'Encumbrance',
  registration: 'Registration',
  building_permission: 'Building Permission',
  tax_assessment: 'Tax Assessment',
  zoning_change: 'Zoning Change',
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

interface PendingTasksCardProps {
  tasks: WorkflowTask[]
}

function PendingTasksCard({ tasks }: PendingTasksCardProps) {
  const navigate = useNavigate()
  const pending = tasks.filter(t => t.status === 'pending' || t.status === 'in_review')

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      {/* Summary row */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Pending Tasks</h2>
        <span className="inline-flex items-center gap-1.5 bg-indigo-100 text-indigo-800 text-sm font-medium px-3 py-1 rounded-full">
          <span className="text-base">📋</span>
          {pending.length} task{pending.length !== 1 ? 's' : ''} awaiting review
        </span>
      </div>

      {pending.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <p className="text-4xl mb-3">🎉</p>
          <p className="font-medium text-slate-700">No pending tasks — you're all caught up!</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 uppercase text-xs tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Task ID</th>
                <th className="px-4 py-3 text-left font-semibold">Request ID</th>
                <th className="px-4 py-3 text-left font-semibold">Service</th>
                <th className="px-4 py-3 text-left font-semibold">ULPIN</th>
                <th className="px-4 py-3 text-left font-semibold">Submitted By</th>
                <th className="px-4 py-3 text-left font-semibold">Assigned At</th>
                <th className="px-4 py-3 text-left font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pending.map(task => (
                <tr key={task.task_id} className="hover:bg-indigo-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                    {task.task_id}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                    {task.request_id}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="inline-block bg-indigo-100 text-indigo-800 text-xs font-medium px-2 py-0.5 rounded">
                      {SERVICE_TYPE_LABELS[task.service_type] ?? task.service_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700 whitespace-nowrap">
                    {task.ulpin}
                  </td>
                  <td className="px-4 py-3 text-slate-700 whitespace-nowrap">
                    {task.submitted_by ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                    {formatDate(task.assigned_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      onClick={() => navigate(`/officer/workflow?task_id=${encodeURIComponent(task.task_id)}`)}
                      className="inline-flex items-center gap-1 bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg hover:bg-indigo-800 transition-colors"
                    >
                      Review →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function OfficerDashboard() {
  const { data, isLoading, isError, error } = useQuery<WorkflowTask[]>({
    queryKey: ['workflow', 'tasks'],
    queryFn: async () => {
      const { data } = await apiClient.get<WorkflowTask[]>('/workflow/tasks')
      return data
    },
  })

  return (
    <div className="min-h-screen flex flex-col bg-indigo-50">
      <TopNav />
      <main className="flex-1 px-4 py-8 max-w-7xl mx-auto w-full">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Officer Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">Your assigned tasks and pending approvals</p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-20 text-indigo-600">
            <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span className="text-sm font-medium">Loading tasks…</span>
          </div>
        )}

        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            <strong>Failed to load tasks.</strong>{' '}
            {(error as { message?: string })?.message ?? 'Please try again.'}
          </div>
        )}

        {!isLoading && !isError && data && (
          <PendingTasksCard tasks={data} />
        )}
      </main>
      <Footer />
    </div>
  )
}
