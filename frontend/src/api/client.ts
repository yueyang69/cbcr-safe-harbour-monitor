import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  // Per-request role override takes precedence (used by the demo identity
  // switcher to enumerate entities as HQ). Only inject the current role when
  // the caller did not set it explicitly.
  if (!config.headers.has('X-User-Role')) {
    config.headers.set('X-User-Role', localStorage.getItem('cbcr-role') || 'hq')
  }
  // Send the simulated "current logged-in entity" only when one is selected,
  // so HQ/reviewer requests never carry a stale entity header.
  const entityId = localStorage.getItem('cbcr-entity')
  if (entityId) config.headers.set('X-Entity-Id', entityId)
  return config
})

api.interceptors.response.use(undefined, (error) => {
  const detail = error.response?.data?.detail
  error.message = typeof detail === 'string' ? detail : 'The API request could not be completed.'
  return Promise.reject(error)
})
