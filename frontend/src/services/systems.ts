import apiClient from './apiClient'

export interface SystemItem {
    id: string
    code: string
    name: string
    vendor: string | null
    version: string | null
    description: string | null
    gxp_category: string | null
    gamp5_category: string | null
    owner_id: string | null
    owner_name: string | null
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface SystemListResponse {
    items: SystemItem[]
    total: number
    page: number
    page_size: number
}

export interface CreateSystemData {
    code: string
    name: string
    vendor?: string
    version?: string
    description?: string
    gxp_category?: string
    gamp5_category?: string
    owner_id?: string
}

export interface UpdateSystemData {
    name?: string
    vendor?: string
    version?: string
    description?: string
    gxp_category?: string
    gamp5_category?: string
    owner_id?: string
    is_active?: boolean
}

const systemService = {
    list: (params?: {
        page?: number
        page_size?: number
        search?: string
        active_only?: boolean
    }) =>
        apiClient
            .get<SystemListResponse>('/systems', { params })
            .then((r) => r.data),

    get: (id: string) =>
        apiClient.get<SystemItem>(`/systems/${id}`).then((r) => r.data),

    create: (data: CreateSystemData) =>
        apiClient.post<SystemItem>('/systems', data).then((r) => r.data),

    update: (id: string, data: UpdateSystemData) =>
        apiClient.patch<SystemItem>(`/systems/${id}`, data).then((r) => r.data),

    delete: (id: string) =>
        apiClient.delete(`/systems/${id}`).then((r) => r.data),
}

export default systemService
