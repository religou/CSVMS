import apiClient from './apiClient'

export interface UserItem {
    id: string
    username: string
    email: string
    full_name: string
    is_active: boolean
    is_locked: boolean
    roles: RoleItem[]
}

export interface RoleItem {
    id: string
    name: string
    display_name: string
    description?: string
}

export interface PermissionItem {
    id: string
    code: string
    resource_type: string
    action: string
    display_name: string
}

export interface RoleDetailItem extends RoleItem {
    is_system: boolean
    permissions: PermissionItem[]
}

export interface CreateUserRequest {
    username: string
    email: string
    full_name: string
    password: string
    role_codes: string[]
}

export interface CreateRoleRequest {
    name: string
    display_name: string
    description?: string
}

export interface UpdateRoleRequest {
    display_name?: string
    description?: string
}

export const adminService = {
    listUsers: (page = 1, pageSize = 20) =>
        apiClient.get<UserItem[]>('/admin/users', {
            params: { page, page_size: pageSize },
        }),

    listRoles: () => apiClient.get<RoleDetailItem[]>('/admin/roles'),

    listPermissions: () =>
        apiClient.get<PermissionItem[]>('/admin/permissions'),

    createRole: (data: CreateRoleRequest) =>
        apiClient.post<RoleDetailItem>('/admin/roles', data),

    updateRole: (roleId: string, data: UpdateRoleRequest) =>
        apiClient.patch<RoleDetailItem>(`/admin/roles/${roleId}`, data),

    updateRolePermissions: (roleId: string, permissionIds: string[]) =>
        apiClient.put<RoleDetailItem>(`/admin/roles/${roleId}/permissions`, {
            permission_ids: permissionIds,
        }),

    deleteRole: (roleId: string) => apiClient.delete(`/admin/roles/${roleId}`),

    createUser: (data: CreateUserRequest) =>
        apiClient.post<UserItem>('/admin/users', data),

    updateUser: (
        id: string,
        data: Partial<{ email: string; full_name: string; is_active: boolean }>,
    ) => apiClient.put<UserItem>(`/admin/users/${id}`, data),

    assignRoles: (userId: string, roleCodes: string[]) =>
        apiClient.post(`/admin/users/${userId}/roles`, {
            role_codes: roleCodes,
        }),

    unlockUser: (userId: string) =>
        apiClient.post(`/admin/users/${userId}/unlock`),

    resetPassword: (userId: string, newPassword: string) =>
        apiClient.post(`/admin/users/${userId}/reset-password`, {
            new_password: newPassword,
        }),

    deleteUser: (userId: string) => apiClient.delete(`/admin/users/${userId}`),
}
