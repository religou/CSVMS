import apiClient from './apiClient'

// ---------- Types ----------

export interface DocumentItem {
    id: string
    title: string
    doc_type: string
    doc_number: string
    status: string
    version: string
    summary?: string
    system_name?: string
    author_id: string
    author_name?: string
    created_at: string
    updated_at: string
}

export interface DocumentDetail extends DocumentItem {
    content?: string
    versions: DocumentVersion[]
}

export interface DocumentVersion {
    id: string
    version_number: number
    version_label: string
    content?: string
    change_reason?: string
    created_by: string
    created_at: string
}

export interface DocumentListResponse {
    items: DocumentItem[]
    total: number
    page: number
    page_size: number
}

export interface DocumentCreateRequest {
    title: string
    doc_type: string
    system_name?: string
    summary?: string
    content?: string
    project_id?: string
}

export interface DocumentUpdateRequest {
    title?: string
    content?: string
    summary?: string
    system_name?: string
}

// ---------- API ----------

export const documentService = {
    list: (params?: {
        doc_type?: string
        status?: string
        system_name?: string
        keyword?: string
        project_id?: string
        page?: number
        page_size?: number
    }) => apiClient.get<DocumentListResponse>('/documents', { params }),

    get: (id: string) => apiClient.get<DocumentDetail>(`/documents/${id}`),

    create: (data: DocumentCreateRequest) =>
        apiClient.post<DocumentItem>('/documents', data),

    update: (id: string, data: DocumentUpdateRequest) =>
        apiClient.put<DocumentItem>(`/documents/${id}`, data),

    delete: (id: string) => apiClient.delete(`/documents/${id}`),

    getVersions: (id: string) =>
        apiClient.get<DocumentVersion[]>(`/documents/${id}/versions`),
}
