import apiClient from './apiClient'

export interface Project {
    id: string
    name: string
    code: string
    system_name: string
    system_id: string | null
    description: string | null
    status: 'active' | 'completed' | 'archived'
    stage: string | null
    created_by: string
    creator_name: string | null
    member_count: number
    created_at: string
    updated_at: string
}

export interface ProjectMember {
    id: string
    user_id: string
    username: string
    full_name: string
    role: string
    joined_at: string
}

export interface ProjectMemberCandidate {
    id: string
    username: string
    email: string
    full_name: string
    system_roles: string[]
}

export interface ProjectMemberCandidateList {
    items: ProjectMemberCandidate[]
    total: number
    page: number
    page_size: number
}

export interface ProjectMemberCandidateParams {
    keyword?: string
    page?: number
    page_size?: number
    system_role?: string
}

export interface ProjectDetail extends Project {
    members: ProjectMember[]
    current_user_permissions: string[]
}

export interface CreateProjectData {
    name: string
    system_id: string
    description?: string
    stage?: string | null
}

export interface UpdateProjectData {
    name?: string
    description?: string
    status?: 'active' | 'completed' | 'archived'
    stage?: string | null
}

export interface ProjectSearchParams {
    keyword?: string
}

const projectService = {
    list: (params?: ProjectSearchParams) =>
        apiClient.get<Project[]>('/projects', { params }).then((r) => r.data),

    get: (id: string) =>
        apiClient.get<ProjectDetail>(`/projects/${id}`).then((r) => r.data),

    create: (data: CreateProjectData) =>
        apiClient.post<Project>('/projects', data).then((r) => r.data),

    update: (id: string, data: UpdateProjectData) =>
        apiClient.patch<Project>(`/projects/${id}`, data).then((r) => r.data),

    addMember: (projectId: string, userId: string, role: string) =>
        apiClient
            .post<ProjectMember>(`/projects/${projectId}/members`, {
                user_id: userId,
                role,
            })
            .then((r) => r.data),

    listMemberCandidates: (
        projectId: string,
        params?: ProjectMemberCandidateParams,
    ) =>
        apiClient
            .get<ProjectMemberCandidateList>(
                `/projects/${projectId}/member-candidates`,
                { params },
            )
            .then((r) => r.data),

    updateMemberRole: (projectId: string, userId: string, role: string) =>
        apiClient
            .patch<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
                role,
            })
            .then((r) => r.data),

    removeMember: (projectId: string, userId: string) =>
        apiClient.delete(`/projects/${projectId}/members/${userId}`),
}

export default projectService
