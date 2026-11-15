import axios from 'axios'
import { useAuthStore } from '@/store/authStore'
export const apiClient = axios.create({ baseURL: '/api/v1' })
apiClient.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
