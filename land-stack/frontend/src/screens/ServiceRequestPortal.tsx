import { useState } from 'react'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'

const SERVICE_TYPES = [
  { value: 'mutation',         label: 'Mutation / Name Change' },
  { value: 'encumbrance_cert', label: 'Encumbrance Certificate' },
  { value: 'ownership_cert',   label: 'Ownership Certificate' },
  { value: 'land_use_change',  label: 'Land Use Change' },
  { value: 'boundary_dispute', label: 'Boundary Dispute Resolution' },
]

interface FormState {
  service_type: string
  ulpin: string
  description: string
  priority: 'normal' | 'urgent'
}

const DEFAULT_FORM: FormState = {
  service_type: 'mutation',
  ulpin: '',
  description: '',
  priority: 'normal',
}

export default function ServiceRequestPortal() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [successId, setSuccessId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setSuccessId(null)
    setError(null)

    try {
      const { data } = await apiClient.post('/citizen/service-request', form)
      const id: string = data.request_id ?? data.ticket_number ?? data.id ?? 'N/A'
      setSuccessId(id)
      setForm(DEFAULT_FORM)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to submit request. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />

      <main className="flex-1 bg-slate-50 py-10 px-4">
        <div className="max-w-xl mx-auto">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">Service Request Portal</h1>
          <p className="text-slate-500 text-sm mb-6">
            Submit a land-related service request. Your request will be tracked and processed by the
            relevant officer.
          </p>

          {/* Success banner */}
          {successId && (
            <div className="mb-5 flex items-start gap-3 rounded-lg border border-green-300 bg-green-50 p-4 text-green-800">
              <span className="text-lg">✅</span>
              <div>
                <p className="font-semibold">Request submitted successfully!</p>
                <p className="text-sm mt-0.5">
                  Your ticket ID is <span className="font-mono font-bold">{successId}</span>. You
                  can track its status in the Request Tracking screen.
                </p>
              </div>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mb-5 flex items-start gap-3 rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">
              <span className="text-lg">⚠️</span>
              <div>
                <p className="font-semibold">Submission failed</p>
                <p className="text-sm mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="bg-white rounded-xl shadow-md p-8 space-y-5"
          >
            {/* Service Type */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Service Type <span className="text-red-500">*</span>
              </label>
              <select
                name="service_type"
                value={form.service_type}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {SERVICE_TYPES.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* ULPIN */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                ULPIN (Parcel ID) <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="ulpin"
                value={form.ulpin}
                onChange={handleChange}
                required
                placeholder="e.g. CH-UT-000001"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Description{' '}
                <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={4}
                placeholder="Provide any additional details about your request…"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Priority <span className="text-red-500">*</span>
              </label>
              <select
                name="priority"
                value={form.priority}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="normal">Normal</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-700 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Submitting…' : 'Submit Request'}
            </button>
          </form>
        </div>
      </main>

      <Footer />
    </div>
  )
}
