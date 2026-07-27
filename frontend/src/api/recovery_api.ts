import { http } from './http'

export const recoveryApi = {
  createRequest(payload: unknown) {
    return http.post('/recovery/request', payload)
  },
  approve(requestId: number) {
    return http.post(`/recovery/${requestId}/approve`)
  },
  execute(requestId: number) {
    return http.post(`/recovery/${requestId}/execute`)
  },
  listRequests() {
    return http.get('/recovery/requests')
  },
}
