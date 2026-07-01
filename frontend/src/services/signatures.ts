import apiClient from './apiClient';

// ---------- Types ----------

export interface SignatureItem {
  id: string;
  user_id: string;
  signer_name?: string;
  document_id: string;
  document_version: string;
  meaning: string;
  content_hash: string;
  ip_address?: string;
  timestamp: string;
  is_valid: boolean;
}

export interface SignatureRequest {
  username: string;
  password: string;
  document_id: string;
  meaning: string;
  workflow_id?: string;
  workflow_step_id?: string;
}

export interface AuditLogItem {
  id: string;
  user_id?: string;
  username: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  resource_name?: string;
  field_changed?: string;
  old_value?: string;
  new_value?: string;
  reason?: string;
  timestamp: string;
  ip_address?: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
}

// ---------- API ----------

export const signatureService = {
  sign: (data: SignatureRequest) =>
    apiClient.post<SignatureItem>('/signatures', data),

  getDocumentSignatures: (documentId: string) =>
    apiClient.get<SignatureItem[]>(`/signatures/document/${documentId}`),

  verify: (signatureId: string) =>
    apiClient.get<{ signature_id: string; is_valid: boolean }>(`/signatures/${signatureId}/verify`),
};

export const auditService = {
  list: (params?: {
    resource_type?: string;
    resource_id?: string;
    user_id?: string;
    action?: string;
    start_time?: string;
    end_time?: string;
    page?: number;
    page_size?: number;
  }) => apiClient.get<AuditLogListResponse>('/audit-logs', { params }),

  getResourceTrail: (resourceType: string, resourceId: string) =>
    apiClient.get<AuditLogItem[]>(`/audit-logs/resource/${resourceType}/${resourceId}`),
};
