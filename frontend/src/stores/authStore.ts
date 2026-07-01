import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
    id: string
    username: string
    email: string
    full_name: string
    is_active: boolean
    roles: string[]
    permissions: string[]
}

interface AuthState {
    accessToken: string | null
    refreshToken: string | null
    user: User | null
    isAuthenticated: boolean
    setTokens: (access: string, refresh: string) => void
    setUser: (user: User) => void
    logout: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            accessToken: null,
            refreshToken: null,
            user: null,
            isAuthenticated: false,
            setTokens: (access, refresh) =>
                set({
                    accessToken: access,
                    refreshToken: refresh,
                    isAuthenticated: true,
                }),
            setUser: (user) => set({ user }),
            logout: () =>
                set({
                    accessToken: null,
                    refreshToken: null,
                    user: null,
                    isAuthenticated: false,
                }),
        }),
        { name: 'csvs-auth' },
    ),
)
