import axios from 'axios'

export const http = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
