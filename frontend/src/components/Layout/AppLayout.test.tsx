import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AppLayout from './AppLayout'
import { useAuthStore } from '@/stores/authStore'

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: string) => key,
        i18n: {
            language: 'zh-CN',
            changeLanguage: vi.fn(),
        },
    }),
}))

function buildUser(permissions: string[]) {
    return {
        id: 'user-1',
        username: 'tester',
        email: 'tester@example.com',
        full_name: 'Tester',
        is_active: true,
        roles: ['admin'],
        permissions,
    }
}

function renderLayout(route = '/admin/users') {
    return render(
        <MemoryRouter initialEntries={[route]}>
            <Routes>
                <Route path="/" element={<AppLayout />}>
                    <Route path="admin/users" element={<div>当前页</div>} />
                    <Route path="admin/dict" element={<div>当前页</div>} />
                    <Route path="admin/roles" element={<div>当前页</div>} />
                </Route>
            </Routes>
        </MemoryRouter>,
    )
}

function expectBefore(left: HTMLElement, right: HTMLElement) {
    expect(
        Boolean(
            left.compareDocumentPosition(right) &
            Node.DOCUMENT_POSITION_FOLLOWING,
        ),
    ).toBe(true)
}

describe('AppLayout admin menu order', () => {
    beforeEach(() => {
        localStorage.clear()
        useAuthStore.setState({
            accessToken: 'token',
            refreshToken: 'refresh',
            user: buildUser([
                'system.admin.menu',
                'system.admin.users.menu',
                'system.admin.dict.menu',
                'system.admin.roles.menu',
            ]),
            isAuthenticated: true,
        })
    })

    it('renders dictionary management before permission management in the admin menu', async () => {
        renderLayout()

        const userMenuItem = (await screen.findByText('用户管理')).closest('li')
        const dictMenuItem = screen.getByText('字典管理').closest('li')
        const rolesMenuItem = screen.getByText('权限管理').closest('li')

        expect(userMenuItem).not.toBeNull()
        expect(dictMenuItem).not.toBeNull()
        expect(rolesMenuItem).not.toBeNull()

        expectBefore(userMenuItem as HTMLElement, dictMenuItem as HTMLElement)
        expectBefore(dictMenuItem as HTMLElement, rolesMenuItem as HTMLElement)
    })
})
