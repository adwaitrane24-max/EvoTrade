import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    console.error('[API Error]', err?.response?.data || err.message)
    return Promise.reject(err)
  }
)

export default api
