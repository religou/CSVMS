import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const apiClient = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
})

// 请求拦截：附加 token
apiClient.interceptors.request.use((config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// 响应拦截：处理 401 自动刷新
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        // Skip token refresh for auth endpoints (login/register/refresh)
        const isAuthRequest = originalRequest?.url?.startsWith('/auth/')

        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !isAuthRequest
        ) {
            originalRequest._retry = true
            const refreshToken = useAuthStore.getState().refreshToken

            if (refreshToken) {
                try {
                    const res = await axios.post('/api/v1/auth/refresh', {
                        refresh_token: refreshToken,
                    })
                    const { access_token, refresh_token } = res.data
                    useAuthStore
                        .getState()
                        .setTokens(access_token, refresh_token)
                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return apiClient(originalRequest)
                } catch {
                    useAuthStore.getState().logout()
                }
            } else {
                useAuthStore.getState().logout()
            }
        }

        return Promise.reject(error)
    },
)

/** Extract error message from API error response. */
export function getErrorMessage(err: unknown, fallback = '操作失败'): string {
    const error = err as {
        response?: {
            data?: { detail?: string | Array<{ msg: string; loc?: string[] }> }
        }
    }
    const detail = error?.response?.data?.detail
    if (!detail) return fallback
    if (typeof detail === 'string') return detail
    // FastAPI 422 validation error: detail is an array
    return detail.map((e) => e.msg).join('；')
}

export default apiClient
