import { useState, useCallback } from 'react'
import api from '../lib/api'

export function useApi<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const call = useCallback(async (method: 'get' | 'post', url: string, data?: unknown): Promise<T | null> => {
    setLoading(true)
    setError(null)
    try {
      const res = method === 'post'
        ? await api.post<T>(url, data)
        : await api.get<T>(url)
      return res.data
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail
        || (e as { message?: string })?.message
        || 'Request failed'
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { call, loading, error }
}
