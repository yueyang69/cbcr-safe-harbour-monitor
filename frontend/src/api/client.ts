import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  config.headers.set('X-User-Role', localStorage.getItem('cbcr-role') || 'hq')
  return config
})

api.interceptors.response.use(undefined, (error) => {
  const detail = error.response?.data?.detail
  error.message = typeof detail === 'string' ? detail : 'The API request could not be completed.'
  return Promise.reject(error)
})
