import apiClient from './apiClient'

export interface DictItem {
    id: string
    category_id: string
    code: string
    label: string
    description: string | null
    sort_order: number
    is_enabled: boolean
    extra: string | null
    permission_profile: string | null
    permission_codes: string[] | null
    created_at: string
}

export interface DictCategory {
    id: string
    code: string
    name: string
    description: string | null
    is_system: boolean
    created_at: string
    items: DictItem[]
}

export interface CreateCategoryData {
    code: string
    name: string
    description?: string
}

export interface UpdateCategoryData {
    name?: string
    description?: string
}

export interface CreateItemData {
    code: string
    label: string
    description?: string
    sort_order?: number
    is_enabled?: boolean
    extra?: string
    permission_profile?: string
    permission_codes?: string[]
}

export interface UpdateItemData {
    label?: string
    description?: string
    sort_order?: number
    is_enabled?: boolean
    extra?: string
    permission_profile?: string
    permission_codes?: string[]
}

const dictService = {
    listCategories: () =>
        apiClient.get<DictCategory[]>('/dict/categories').then((r) => r.data),

    listItems: (categoryCode: string, enabledOnly = true) =>
        apiClient
            .get<DictItem[]>(`/dict/categories/${categoryCode}/items`, {
                params: { enabled_only: enabledOnly },
            })
            .then((r) => r.data),

    createCategory: (data: CreateCategoryData) =>
        apiClient
            .post<DictCategory>('/dict/categories', data)
            .then((r) => r.data),

    updateCategory: (id: string, data: UpdateCategoryData) =>
        apiClient
            .patch<DictCategory>(`/dict/categories/${id}`, data)
            .then((r) => r.data),

    deleteCategory: (id: string) =>
        apiClient.delete(`/dict/categories/${id}`).then((r) => r.data),

    createItem: (categoryId: string, data: CreateItemData) =>
        apiClient
            .post<DictItem>(`/dict/categories/${categoryId}/items`, data)
            .then((r) => r.data),

    updateItem: (itemId: string, data: UpdateItemData) =>
        apiClient
            .patch<DictItem>(`/dict/items/${itemId}`, data)
            .then((r) => r.data),

    deleteItem: (itemId: string) =>
        apiClient.delete(`/dict/items/${itemId}`).then((r) => r.data),
}

export default dictService
