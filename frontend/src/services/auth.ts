import apiClient from './apiClient'

export interface LoginRequest {
    username: string
    password: string
}

export interface TokenResponse {
    access_token: string
    refresh_token: string
    token_type: string
}

export interface UserResponse {
    id: string
    username: string
    email: string
    full_name: string
    is_active: boolean
    roles: string[]
    permissions: string[]
}

export const authService = {
    login: (data: LoginRequest) =>
        apiClient.post<TokenResponse>('/auth/login', data),

    getMe: () => apiClient.get<UserResponse>('/auth/me'),

    refresh: (refreshToken: string) =>
        apiClient.post<TokenResponse>('/auth/refresh', {
            refresh_token: refreshToken,
        }),
}
