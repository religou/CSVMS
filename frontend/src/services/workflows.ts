import apiClient from './apiClient';

// ---------- Types ----------

export interface WorkflowTemplateStep {
  id: string;
  step_order: number;
  name: string;
  step_type: 'review' | 'approve';
  role_id?: string;
  assignee_id?: string;
  project_role?: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  doc_type: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  steps: WorkflowTemplateStep[];
}

export interface WorkflowStep {
  id: string;
  step_order: number;
  name: string;
  step_type: 'review' | 'approve';
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'skipped';
  assignee_id?: string;
  assignee_name?: string;
  acted_by?: string;
  actor_name?: string;
  acted_at?: string;
  comment?: string;
}

export interface WorkflowItem {
  id: string;
  template_id: string;
  document_id: string;
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'cancelled';
  current_step_order: number;
  initiated_by: string;
  initiator_name?: string;
  initiated_at: string;
  completed_at?: string;
  steps: WorkflowStep[];
}

export interface WorkflowActionItem {
  id: string;
  action: 'submit' | 'approve' | 'reject' | 'return' | 'withdraw';
  actor_id: string;
  actor_name?: string;
  comment?: string;
  created_at: string;
}

export interface CreateTemplateRequest {
  name: string;
  doc_type: string;
  description?: string;
  steps: {
    name: string;
    step_type: 'review' | 'approve';
    role_id?: string;
    assignee_id?: string;
    project_role?: string;
  }[];
}

// ---------- API ----------

export const workflowService = {
  // Templates
  listTemplates: () =>
    apiClient.get<WorkflowTemplate[]>('/workflows/templates'),

  getTemplate: (id: string) =>
    apiClient.get<WorkflowTemplate>(`/workflows/templates/${id}`),

  createTemplate: (data: CreateTemplateRequest) =>
    apiClient.post<WorkflowTemplate>('/workflows/templates', data),

  updateTemplate: (id: string, data: CreateTemplateRequest) =>
    apiClient.put<WorkflowTemplate>(`/workflows/templates/${id}`, data),

  // Workflow operations
  submit: (documentId: string) =>
    apiClient.post<WorkflowItem>('/workflows/submit', { document_id: documentId }),

  approve: (workflowId: string, comment?: string) =>
    apiClient.post<WorkflowItem>(`/workflows/${workflowId}/approve`, { comment }),

  reject: (workflowId: string, comment: string) =>
    apiClient.post<WorkflowItem>(`/workflows/${workflowId}/reject`, { comment }),

  return: (workflowId: string, comment: string) =>
    apiClient.post<WorkflowItem>(`/workflows/${workflowId}/return`, { comment }),

  withdraw: (workflowId: string) =>
    apiClient.post<WorkflowItem>(`/workflows/${workflowId}/withdraw`),

  // Queries
  get: (workflowId: string) =>
    apiClient.get<WorkflowItem>(`/workflows/${workflowId}`),

  getByDocument: (documentId: string) =>
    apiClient.get<WorkflowItem | null>(`/workflows/document/${documentId}`),

  getMyPending: () =>
    apiClient.get<WorkflowItem[]>('/workflows/pending/mine'),

  getActions: (workflowId: string) =>
    apiClient.get<WorkflowActionItem[]>(`/workflows/${workflowId}/actions`),
};
