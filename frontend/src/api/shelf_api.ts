import { http } from './http'
import type { ApiEnvelope } from './types'

export interface ShelfOut {
  shelf_id: string
  name: string
  created_at: string
  updated_at: string
}

export interface ShelfListOut {
  shelves: ShelfOut[]
}

export interface ShelfDeleteOut {
  shelf_id: string
  deleted: boolean
  files_returned_to_root: number
}

export const shelfApi = {
  list() {
    return http.get<ApiEnvelope<ShelfListOut>>('/shelves')
  },
  create(name: string) {
    return http.post<ApiEnvelope<ShelfOut>>('/shelves', { name })
  },
  rename(shelfId: string, name: string) {
    return http.post<ApiEnvelope<ShelfOut>>(`/shelves/${shelfId}/rename`, { name })
  },
  delete(shelfId: string) {
    return http.post<ApiEnvelope<ShelfDeleteOut>>(`/shelves/${shelfId}/delete`)
  },
}
