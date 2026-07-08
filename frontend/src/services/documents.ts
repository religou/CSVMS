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
    project_id?: string
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
    summary?: string
    content?: string
    project_id?: string
}

export interface DocumentUpdateRequest {
    title?: string
    content?: string
    summary?: string
}

export interface UrsItem {
    id: string
    document_id: string
    item_code: string
    description: string
    created_at: string
}

export interface UrsItemCreateRequest {
    description: string
}

export interface UrsItemUpdateRequest {
    description?: string
}

export interface UrsReference {
    id: string
    document_id: string
    urs_item_id: string
    item_code: string
    description: string
    source_document_id: string
    source_doc_number: string
    created_at: string
}

export interface UrsReferenceCreateRequest {
    urs_item_id: string
}

// ---------- API ----------

export const documentService = {
    list: (params?: {
        doc_type?: string
        status?: string
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

export const listUrsItems = (documentId: string) =>
    apiClient.get<UrsItem[]>(`/documents/${documentId}/urs-items`)

export const createUrsItem = (documentId: string, data: UrsItemCreateRequest) =>
    apiClient.post<UrsItem>(`/documents/${documentId}/urs-items`, data)

export const updateUrsItem = (
    documentId: string,
    itemId: string,
    data: UrsItemUpdateRequest
) => apiClient.put<UrsItem>(`/documents/${documentId}/urs-items/${itemId}`, data)

export const deleteUrsItem = (documentId: string, itemId: string) =>
    apiClient.delete(`/documents/${documentId}/urs-items/${itemId}`)

export const listUrsReferences = (documentId: string) =>
    apiClient.get<UrsReference[]>(`/documents/${documentId}/urs-references`)

export const createUrsReference = (
    documentId: string,
    data: UrsReferenceCreateRequest
) => apiClient.post<UrsReference>(`/documents/${documentId}/urs-references`, data)

export const deleteUrsReference = (documentId: string, referenceId: string) =>
    apiClient.delete(`/documents/${documentId}/urs-references/${referenceId}`)
