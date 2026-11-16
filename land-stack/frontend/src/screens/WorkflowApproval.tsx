import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

interface TaskDetail {
  task_id: string
  request_id: string
  service_type: string
  ulpin: string
  submitted_by?: string
  submitted_at: string
  description?: string
  status: string
  priority?: string
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

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-4 py-3 border-b border-slate-100 last:border-0">
      <span className="w-36 shrink-0 text-sm text-slate-500 font-medium">{label}</span>
      <span className="text-sm text-slate-800 break-all">{value}</span>
    </div>
  )
}

export default function WorkflowApproval() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const taskId = searchParams.get('task_id') ?? ''

  const [comment, setComment] = useState('')
  const [commentError, setCommentError] = useState('')
  const [actionResult, setActionResult] = useState<{ type: 'approve' | 'reject'; ok: boolean } | null>(null)
  const [actionDone, setActionDone] = useState(false)

  const { data: task, isLoading, isError, error } = useQuery<TaskDetail>({
    queryKey: ['workflow', 'task', taskId],
    queryFn: async () => {
      const { data } = await apiClient.get<TaskDetail>(`/workflow/tasks/${encodeURIComponent(taskId)}`)
      return data
    },
    enabled: !!taskId,
  })

  const approveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/workflow/tasks/${encodeURIComponent(taskId)}/approve`, { comment })
    },
    onSuccess: () => {
      setActionResult({ type: 'approve', ok: true })
      setActionDone(true)
      setTimeout(() => navigate('/officer/dashboard'), 2000)
    },
    onError: () => {
      setActionResult({ type: 'approve', ok: false })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/workflow/tasks/${encodeURIComponent(taskId)}/reject`, { comment })
    },
    onSuccess: () => {
      setActionResult({ type: 'reject', ok: true })
      setActionDone(true)
      setTimeout(() => navigate('/officer/dashboard'), 2000)
    },
    onError: () => {
      setActionResult({ type: 'reject', ok: false })
    },
  })

  function handleApprove() {
    setCommentError('')
    approveMutation.mutate()
  }

  function handleReject() {
    if (!comment.trim()) {
      setCommentError('A comment is required when rejecting a task.')
      return
    }
    setCommentError('')
    rejectMutation.mutate()
  }

  const actionInFlight = approveMutation.isPending || rejectMutation.isPending

  return (
    <div className="min-h-screen flex flex-col bg-indigo-50">
      <TopNav />
      <main className="flex-1 px-4 py-8 max-w-3xl mx-auto w-full">
        {/* Page header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/officer/dashboard')}
            className="text-sm text-indigo-700 hover:text-indigo-900 font-medium mb-2 inline-flex items-center gap-1"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-2xl font-bold text-slate-800">Mutation / Approval Workflow</h1>
          <p className="text-slate-500 text-sm mt-1">Review the task details and approve or reject</p>
        </div>

        {/* No task_id guard */}
        {!taskId && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg px-4 py-3 text-sm">
            No task selected. Please go back to the dashboard and select a task to review.
          </div>
        )}

        {/* Loading */}
        {taskId && isLoading && (
          <div className="flex items-center justify-center py-20 text-indigo-600">
            <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span className="text-sm font-medium">Loading task…</span>
          </div>
        )}

        {/* Fetch error */}
        {taskId && isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            <strong>Failed to load task.</strong>{' '}
            {(error as { message?: string })?.message ?? 'Please try again.'}
          </div>
        )}

        {/* Task detail card */}
        {task && (
          <div className="bg-white rounded-xl shadow-md overflow-hidden">
            {/* Card header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Task Detail</h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">{task.task_id}</p>
              </div>
              <div className="flex items-center gap-2">
                {task.priority && (
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                    task.priority === 'high'
                      ? 'bg-red-100 text-red-700'
                      : task.priority === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)} priority
                  </span>
                )}
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                  task.status === 'pending'
                    ? 'bg-yellow-100 text-yellow-700'
                    : task.status === 'in_review'
                    ? 'bg-blue-100 text-blue-700'
                    : task.status === 'approved'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                }`}>
                  {task.status.replace('_', ' ')}
                </span>
              </div>
            </div>

            {/* Detail rows */}
            <div className="px-6 py-2">
              <DetailRow label="Request ID" value={<span className="font-mono">{task.request_id}</span>} />
              <DetailRow
                label="Service Type"
                value={
                  <span className="inline-block bg-indigo-100 text-indigo-800 text-xs font-medium px-2 py-0.5 rounded">
                    {SERVICE_TYPE_LABELS[task.service_type] ?? task.service_type}
                  </span>
                }
              />
              <DetailRow label="ULPIN" value={<span className="font-mono">{task.ulpin}</span>} />
              <DetailRow label="Submitted By" value={task.submitted_by ?? '—'} />
              <DetailRow label="Submitted At" value={formatDate(task.submitted_at)} />
              {task.description && (
                <DetailRow label="Description" value={task.description} />
              )}
            </div>

            {/* Action section */}
            <div className="px-6 py-5 bg-slate-50 border-t border-slate-100">
              {/* Success banner */}
              {actionResult?.ok && (
                <div className="mb-4 bg-green-50 border border-green-200 text-green-800 rounded-lg px-4 py-3 text-sm font-medium">
                  {actionResult.type === 'approve'
                    ? '✅ Task approved successfully. Redirecting to dashboard…'
                    : '✅ Task rejected. Redirecting to dashboard…'}
                </div>
              )}

              {/* Action error banners */}
              {approveMutation.isError && !actionResult?.ok && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
                  <strong>Approval failed.</strong>{' '}
                  {(approveMutation.error as { message?: string })?.message ?? 'Please try again.'}
                </div>
              )}
              {rejectMutation.isError && !actionResult?.ok && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
                  <strong>Rejection failed.</strong>{' '}
                  {(rejectMutation.error as { message?: string })?.message ?? 'Please try again.'}
                </div>
              )}

              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Comment
                <span className="ml-1 text-slate-400 font-normal text-xs">(required for rejection)</span>
              </label>
              <textarea
                value={comment}
                onChange={e => { setComment(e.target.value); setCommentError('') }}
                disabled={actionDone || actionInFlight}
                rows={3}
                placeholder="Add a note about your decision…"
                className={`w-full text-sm rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none disabled:opacity-50 disabled:cursor-not-allowed ${
                  commentError ? 'border-red-400 bg-red-50' : 'border-slate-300 bg-white'
                }`}
              />
              {commentError && (
                <p className="mt-1 text-xs text-red-600">{commentError}</p>
              )}

              <div className="mt-4 flex items-center gap-3">
                {/* Approve */}
                <button
                  onClick={handleApprove}
                  disabled={actionDone || actionInFlight}
                  className="inline-flex items-center gap-2 bg-green-600 text-white text-sm font-semibold px-5 py-2.5 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {approveMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                      Approving…
                    </>
                  ) : (
                    '✓ Approve'
                  )}
                </button>

                {/* Reject */}
                <button
                  onClick={handleReject}
                  disabled={actionDone || actionInFlight}
                  className="inline-flex items-center gap-2 bg-red-600 text-white text-sm font-semibold px-5 py-2.5 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {rejectMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                      Rejecting…
                    </>
                  ) : (
                    '✗ Reject'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
