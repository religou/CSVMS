import apiClient from './apiClient'

// ---------- Types ----------

export interface UncoveredUrsItem {
    id: string
    item_code: string
    description: string
}

export interface UrsTraceReference {
    document_id: string
    doc_number: string
    title: string
    doc_type: string
}

export interface UrsTraceRow {
    urs_item_id: string
    item_code: string
    description: string
    source_document_id: string
    source_doc_number: string
    covered: boolean
    references: UrsTraceReference[]
}

export interface TraceMatrixResponse {
    urs_matrix: UrsTraceRow[]
    uncovered_urs_items: UncoveredUrsItem[]
}

export interface DashboardStats {
    total_documents: number
    status_distribution: Record<string, number>
    type_distribution: Record<string, number>
    workflow_stats: Record<string, number>
    pending_approvals: number
    my_drafts: number
    total_signatures: number
}

// ---------- API ----------

export const traceabilityService = {
    getMatrix: (projectId?: string) =>
        apiClient.get<TraceMatrixResponse>('/traceability/matrix', {
            params: projectId ? { project_id: projectId } : undefined,
        }),
}

export const dashboardService = {
    getStats: (projectId?: string) =>
        apiClient.get<DashboardStats>('/dashboard', {
            params: projectId ? { project_id: projectId } : undefined,
        }),

    getHome: () => apiClient.get<HomeSummary>('/dashboard/home'),
}

export interface HomeDraftItem {
    id: string
    title: string
    doc_type: string
    doc_number: string
    version: string
    project_id: string | null
    updated_at: string
}

export interface HomeSummary {
    project_count: number
    my_draft_count: number
    my_drafts: HomeDraftItem[]
}
