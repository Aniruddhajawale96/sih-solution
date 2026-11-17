import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

export const apiClient = axios.create({ baseURL: '/api/v1' })

// ── Request interceptor: attach Bearer token ─────────────────────────────
apiClient.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: unwrap Envelope { success, data, errors } ──────
// The backend wraps every response in an Envelope.  We unwrap it here so
// that calling code receives the inner data directly.
apiClient.interceptors.response.use(
  response => {
    const body = response.data
    // If the response is an envelope with success=true, return the inner data
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) {
        return { ...response, data: body.data }
      }
      // success=false → reject with the first error
      const errs = body.errors ?? []
      const msg = errs.length > 0 ? errs[0].message : 'Unknown error'
      return Promise.reject(new Error(msg))
    }
    // Non-envelope response (e.g. SSE stream) → return as-is
    return response
  },
  async error => {
    // ── Auto-refresh on 401 ──────────────────────────────────────────────
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      useAuthStore.getState().refreshToken
    ) {
      originalRequest._retry = true
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: useAuthStore.getState().refreshToken,
        })
        // data is the envelope; unwrap manually since this bypasses our interceptor
        const newToken = data?.data?.access_token ?? data?.access_token
        if (newToken) {
          useAuthStore.getState().setAuth({
            ...useAuthStore.getState(),
            accessToken: newToken,
          })
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        }
      } catch {
        // Refresh failed → logout
        useAuthStore.getState().clearAuth()
      }
    }

    // ── Normalise error message from envelope ─────────────────────────────
    const errData = error.response?.data
    if (errData && typeof errData === 'object' && 'errors' in errData) {
      const errs = errData.errors ?? []
      const msg = errs.length > 0 ? errs[0].message : error.message
      return Promise.reject(new Error(msg))
    }
    return Promise.reject(error)
  },
)

// ── Helper: call /auth/logout then clear store ────────────────────────────────
export async function logout() {
  const { refreshToken } = useAuthStore.getState()
  try {
    if (refreshToken) {
      await apiClient.post('/auth/logout', { refresh_token: refreshToken })
    }
  } catch {
    // Best-effort: even if the server call fails, clear local state
  } finally {
    useAuthStore.getState().clearAuth()
  }
}
