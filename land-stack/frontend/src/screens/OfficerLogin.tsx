import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { apiClient } from '@/lib/apiClient'
import { useAuthStore, Role } from '@/store/authStore'

function roleToRoute(role: Role): string {
  switch (role) {
    case 'CITIZEN':     return '/citizen/services'
    case 'REV_OFF':
    case 'REG_OFF':
    case 'PLAN_OFF':
    case 'TAX_OFF':     return '/officer/dashboard'
    case 'STATE_ADMIN': return '/admin/state'
    case 'NATL_ADMIN':  return '/admin/national'
    default:            return '/'
  }
}

interface LoginResponse {
  access_token: string
  refresh_token?: string
  user: {
    username: string
    role: Role
    jurisdiction?: string
  }
}

export default function OfficerLogin() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const setAuth  = useAuthStore(s => s.setAuth)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { data } = await apiClient.post<LoginResponse>('/auth/login', { email, password })
      setAuth({
        username:     data.user.username,
        role:         data.user.role,
        jurisdiction: data.user.jurisdiction ?? null,
        accessToken:  data.access_token,
        refreshToken: data.refresh_token ?? null,
      })
      navigate(roleToRoute(data.user.role))
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? 'Login failed. Please check your credentials.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <main className="flex-1 flex items-center justify-center bg-indigo-50">
        <div className="bg-white rounded-xl shadow-lg p-10 w-full max-w-sm">
          <p className="text-5xl mb-3 text-center">🛡️</p>
          <h2 className="text-2xl font-bold text-slate-800 mb-1 text-center">Staff Sign In</h2>
          <p className="text-slate-500 text-sm text-center mb-6">Officer &amp; Admin portal — Land Stack</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label htmlFor="email" className="text-sm font-medium text-slate-700">
                Work Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="officer@gov.in"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="password" className="text-sm font-medium text-slate-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="bg-indigo-700 text-white rounded-lg py-2 text-sm font-semibold hover:bg-indigo-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </main>
      <Footer />
    </div>
  )
}
