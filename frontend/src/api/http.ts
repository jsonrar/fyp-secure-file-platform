import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
})

interface ApiFailureBody {
  message?: string
  data?: {
    error_code?: string
    details?: unknown
  }
}

/**
 * Turn an API failure into something a user can act on.
 *
 * The backend answers with `{message, data:{error_code, details}}`, and field
 * validation arrives as a list of locations. Surfacing that beats the bare
 * "Request failed with status code 422" axios produces by default.
 */
export function apiErrorMessage(error: unknown, fallback = 'Request failed'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback
  }

  if (error.response === undefined) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }

  const body = error.response.data as ApiFailureBody | undefined
  const details = body?.data?.details
  if (Array.isArray(details) && details.length > 0) {
    const described = details
      .map((detail) => {
        const item = detail as { location?: unknown[]; message?: string }
        const field = Array.isArray(item.location)
          ? item.location.filter((part) => part !== 'body').join('.')
          : ''
        return field ? `${field}: ${item.message ?? 'invalid value'}` : (item.message ?? '')
      })
      .filter(Boolean)
    if (described.length > 0) {
      return described.join('; ')
    }
  }

  return body?.message ?? fallback
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
