import { create } from 'zustand'
import { persist } from 'zustand/middleware'
export type Role = 'CITIZEN'|'REV_OFF'|'REG_OFF'|'PLAN_OFF'|'TAX_OFF'|'STATE_ADMIN'|'NATL_ADMIN'
interface AuthState {
  username: string|null; role: Role|null; jurisdiction: string|null
  accessToken: string|null; refreshToken: string|null
  setAuth: (p: Omit<AuthState,'setAuth'|'clearAuth'>) => void
  clearAuth: () => void
}
export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      username:null, role:null, jurisdiction:null, accessToken:null, refreshToken:null,
      setAuth: p => set(p),
      clearAuth: () => set({ username:null, role:null, jurisdiction:null, accessToken:null, refreshToken:null })
    }),
    { name: 'land-stack-auth' }
  )
)
