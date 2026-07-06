import apiClient from './apiClient';

// ---------- Types ----------

export interface TraceLinkItem {
  id: string;
  source_document_id: string;
  source_doc_number?: string;
  source_title?: string;
  source_doc_type?: string;
  source_section?: string;
  target_document_id: string;
  target_doc_number?: string;
  target_title?: string;
  target_doc_type?: string;
  target_section?: string;
  link_type: string;
  description?: string;
  created_at: string;
}

export interface CoverageItem {
  total: number;
  covered: number;
  rate: number;
  expected_targets: string[];
}

export interface GapItem {
  document_id: string;
  doc_number: string;
  title: string;
  doc_type: string;
  missing_targets: string[];
}

export interface TraceMatrixResponse {
  links: TraceLinkItem[];
  coverage: Record<string, CoverageItem>;
  gaps: GapItem[];
}

export interface DashboardStats {
  total_documents: number;
  status_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  workflow_stats: Record<string, number>;
  pending_approvals: number;
  my_drafts: number;
  total_signatures: number;
}

export interface CreateTraceLinkRequest {
  source_document_id: string;
  target_document_id: string;
  source_section?: string;
  target_section?: string;
  link_type?: string;
  description?: string;
}

// ---------- API ----------

export const traceabilityService = {
  createLink: (data: CreateTraceLinkRequest) =>
    apiClient.post<TraceLinkItem>('/traceability/links', data),

  deleteLink: (linkId: string) =>
    apiClient.delete(`/traceability/links/${linkId}`),

  getDocumentTraces: (documentId: string) =>
    apiClient.get<{ upstream: TraceLinkItem[]; downstream: TraceLinkItem[] }>(
      `/traceability/document/${documentId}`
    ),

  getMatrix: (projectId?: string) =>
    apiClient.get<TraceMatrixResponse>('/traceability/matrix', {
      params: projectId ? { project_id: projectId } : undefined,
    }),
};

export const dashboardService = {
  getStats: (projectId?: string) =>
    apiClient.get<DashboardStats>('/dashboard', {
      params: projectId ? { project_id: projectId } : undefined,
    }),
};
