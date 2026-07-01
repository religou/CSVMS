import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/authStore'
import { useProjectStore } from '@/stores/projectStore'

vi.mock('@/components/Layout', async () => {
    const router = await import('react-router-dom')

    return {
        AppLayout: () => (
            <div data-testid="app-layout">
                <router.Outlet />
            </div>
        ),
        ProjectLayout: () => (
            <div data-testid="project-layout">
                <router.Outlet />
            </div>
        ),
    }
})

vi.mock('@/pages/Login', () => ({ default: () => <div>登录页</div> }))
vi.mock('@/pages/Admin', () => ({ default: () => <div>用户管理页</div> }))
vi.mock('@/pages/Admin/Roles', () => ({
    default: () => <div>权限管理页</div>,
}))
vi.mock('@/pages/Admin/DictManagement', () => ({
    default: () => <div>字典管理页</div>,
}))
vi.mock('@/pages/Projects', () => ({ default: () => <div>项目列表页</div> }))
vi.mock('@/pages/Documents', () => ({ default: () => <div>项目文档页</div> }))
vi.mock('@/pages/Documents/Detail', () => ({
    default: () => <div>项目文档详情页</div>,
}))
vi.mock('@/pages/Workflows', () => ({ default: () => <div>项目审批页</div> }))
vi.mock('@/pages/AuditLog', () => ({
    default: () => <div>项目审计日志页</div>,
}))
vi.mock('@/pages/Traceability', () => ({
    default: () => <div>追溯矩阵页</div>,
}))
vi.mock('@/pages/Dashboard', () => ({ default: () => <div>项目概览页</div> }))
vi.mock('@/pages/Members', () => ({ default: () => <div>项目成员页</div> }))

import App from '@/App'

function buildUser(permissions: string[]) {
    return {
        id: 'user-1',
        username: 'tester',
        email: 'tester@example.com',
        full_name: 'Tester',
        is_active: true,
        roles: ['user'],
        permissions,
    }
}

function buildProjectDetail(permissionCodes: string[]) {
    return {
        id: 'project-1',
        name: '验证项目',
        code: 'VAL-202606-001',
        system_name: 'CSVS',
        description: null,
        status: 'active' as const,
        created_by: 'user-1',
        creator_name: 'Tester',
        member_count: 1,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
        members: [],
        current_user_permissions: permissionCodes,
    }
}

function renderAppAt(route: string) {
    return render(
        <MemoryRouter initialEntries={[route]}>
            <App />
        </MemoryRouter>,
    )
}

describe('App route guards', () => {
    beforeEach(() => {
        useAuthStore.setState({
            accessToken: null,
            refreshToken: null,
            user: null,
            isAuthenticated: false,
        })
        useProjectStore.setState({ currentProject: null })
        localStorage.clear()
    })

    it('renders a 403 page when visiting system admin routes without permission', async () => {
        useAuthStore.setState({
            accessToken: 'token',
            refreshToken: 'refresh',
            user: buildUser([]),
            isAuthenticated: true,
        })

        renderAppAt('/admin/users')

        expect(await screen.findByText('无权访问')).toBeInTheDocument()
        expect(
            screen.getByText('当前账号缺少用户管理页面访问权限。'),
        ).toBeInTheDocument()
        expect(screen.queryByText('用户管理页')).not.toBeInTheDocument()
    })

    it('renders a 403 page when visiting project routes without permission', async () => {
        useAuthStore.setState({
            accessToken: 'token',
            refreshToken: 'refresh',
            user: buildUser([]),
            isAuthenticated: true,
        })
        useProjectStore.setState({
            currentProject: buildProjectDetail([
                'project.dashboard.menu',
                'project.dashboard.view',
            ]),
        })

        renderAppAt('/projects/project-1/members')

        expect(await screen.findByText('无权访问')).toBeInTheDocument()
        expect(
            screen.getByText('当前账号缺少项目成员页面访问权限。'),
        ).toBeInTheDocument()
        expect(screen.queryByText('项目成员页')).not.toBeInTheDocument()
    })

    it('redirects the project root route to the first accessible project page', async () => {
        useAuthStore.setState({
            accessToken: 'token',
            refreshToken: 'refresh',
            user: buildUser([]),
            isAuthenticated: true,
        })
        useProjectStore.setState({
            currentProject: buildProjectDetail([
                'project.dashboard.menu',
                'project.dashboard.view',
            ]),
        })

        renderAppAt('/projects/project-1')

        expect(await screen.findByText('项目概览页')).toBeInTheDocument()
    })
})
