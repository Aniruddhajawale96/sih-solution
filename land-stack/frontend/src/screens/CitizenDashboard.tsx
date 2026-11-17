import { useNavigate } from 'react-router-dom'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { useAuthStore } from '@/store/authStore'

/**
 * Citizen landing page — shown after a successful citizen login.
 * Previously this file was an erroneous copy of OfficerLogin that rendered
 * a second login form here instead of post-login content (bug fix).
 */
export default function CitizenDashboard() {
  const navigate = useNavigate()
  const { username, clearAuth } = useAuthStore()

  function handleLogout() {
    clearAuth()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <TopNav />

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="bg-white rounded-2xl shadow-lg p-10 w-full max-w-lg text-center">
          <p className="text-5xl mb-4">👤</p>
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Welcome{username ? `, ${username}` : ''}
          </h1>
          <p className="text-slate-500 text-sm mb-8">
            What would you like to do today?
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
            {/* Service Request Portal */}
            <button
              onClick={() => navigate('/citizen/services')}
              className="flex flex-col gap-2 p-5 rounded-xl border border-slate-200 bg-slate-50 hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
            >
              <span className="text-2xl">📋</span>
              <span className="font-semibold text-slate-800 text-sm">Submit a Request</span>
              <span className="text-xs text-slate-500 leading-snug">
                Apply for mutations, encumbrance certificates, land-use changes, and more.
              </span>
            </button>

            {/* Request Tracking */}
            <button
              onClick={() => navigate('/citizen/requests')}
              className="flex flex-col gap-2 p-5 rounded-xl border border-slate-200 bg-slate-50 hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
            >
              <span className="text-2xl">🔍</span>
              <span className="font-semibold text-slate-800 text-sm">Track Requests</span>
              <span className="text-xs text-slate-500 leading-snug">
                View the status of all service requests you have submitted.
              </span>
            </button>

            {/* Map Explorer */}
            <button
              onClick={() => navigate('/map')}
              className="flex flex-col gap-2 p-5 rounded-xl border border-slate-200 bg-slate-50 hover:border-emerald-300 hover:bg-emerald-50 transition-colors text-left"
            >
              <span className="text-2xl">🗺️</span>
              <span className="font-semibold text-slate-800 text-sm">Map Explorer</span>
              <span className="text-xs text-slate-500 leading-snug">
                Browse parcel boundaries and search by ULPIN or owner name.
              </span>
            </button>

            {/* Verify Ownership */}
            <button
              onClick={() => navigate('/parcel/CH-UT-000001/verify')}
              className="flex flex-col gap-2 p-5 rounded-xl border border-slate-200 bg-slate-50 hover:border-emerald-300 hover:bg-emerald-50 transition-colors text-left"
            >
              <span className="text-2xl">✅</span>
              <span className="font-semibold text-slate-800 text-sm">Verify Ownership</span>
              <span className="text-xs text-slate-500 leading-snug">
                Look up the Record of Rights and download an ownership certificate.
              </span>
            </button>
          </div>

          <button
            onClick={handleLogout}
            className="mt-8 text-sm text-slate-400 hover:text-red-500 transition-colors underline"
          >
            Sign out
          </button>
        </div>
      </main>

      <Footer />
    </div>
  )
}
