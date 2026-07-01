import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
    adminService,
    type PermissionItem,
    type RoleDetailItem,
} from '@/services/admin'
import dictService from '@/services/dictionary'
import type { DictCategory } from '@/services/dictionary'
import RoleManagementPage from '@/pages/Admin/Roles'
import { useAuthStore } from '@/stores/authStore'

vi.mock('@/services/admin', () => ({
    adminService: {
        listRoles: vi.fn(),
        listPermissions: vi.fn(),
        createRole: vi.fn(),
        updateRole: vi.fn(),
        updateRolePermissions: vi.fn(),
        deleteRole: vi.fn(),
    },
}))

vi.mock('@/services/dictionary', () => ({
    default: {
        listCategories: vi.fn(),
        listItems: vi.fn(),
        createCategory: vi.fn(),
        updateCategory: vi.fn(),
        deleteCategory: vi.fn(),
        createItem: vi.fn(),
        updateItem: vi.fn(),
        deleteItem: vi.fn(),
    },
}))

const ROLE_DETAILS: RoleDetailItem[] = [
    {
        id: 'role-admin',
        name: 'admin',
        display_name: '系统管理员',
        description: '系统内置管理员角色',
        is_system: true,
        permissions: [
            {
                id: 'permission-system-menu',
                code: 'system.admin.menu',
                resource_type: 'system_menu',
                action: 'access',
                display_name: '系统管理菜单',
            },
        ],
    },
]

const PERMISSIONS: PermissionItem[] = [
    {
        id: 'permission-system-menu',
        code: 'system.admin.menu',
        resource_type: 'system_menu',
        action: 'access',
        display_name: '系统管理菜单',
    },
    {
        id: 'permission-system-users-view',
        code: 'system.admin.users.view',
        resource_type: 'system_page',
        action: 'view',
        display_name: '查看用户管理页面',
    },
    {
        id: 'permission-project-members-menu',
        code: 'project.members.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '项目成员菜单',
    },
]

const ROLE_CATEGORIES: DictCategory[] = [
    {
        id: 'category-system-role',
        code: 'system_role',
        name: '系统角色',
        description: '系统级角色定义',
        is_system: true,
        created_at: '2026-06-01T00:00:00Z',
        items: [
            {
                id: 'dict-system-admin',
                category_id: 'category-system-role',
                code: 'admin',
                label: '系统管理员',
                description: '系统管理员',
                sort_order: 1,
                is_enabled: true,
                extra: null,
                permission_profile: null,
                permission_codes: null,
                created_at: '2026-06-01T00:00:00Z',
            },
        ],
    },
    {
        id: 'category-project-role',
        code: 'project_role',
        name: '项目角色',
        description: '项目成员角色定义',
        is_system: true,
        created_at: '2026-06-01T00:00:00Z',
        items: [
            {
                id: 'dict-project-manager',
                category_id: 'category-project-role',
                code: 'manager',
                label: '项目经理',
                description: '项目经理',
                sort_order: 1,
                is_enabled: true,
                extra: 'orange',
                permission_profile: 'manager',
                permission_codes: ['project.members.menu'],
                created_at: '2026-06-01T00:00:00Z',
            },
        ],
    },
]

describe('RoleManagement permission allocation', () => {
    beforeEach(() => {
        vi.clearAllMocks()

        useAuthStore.setState({
            accessToken: 'token',
            refreshToken: 'refresh',
            user: {
                id: 'admin-1',
                username: 'admin',
                email: 'admin@example.com',
                full_name: 'Admin',
                is_active: true,
                roles: ['admin'],
                permissions: [
                    'system.admin.roles.view',
                    'system.admin.roles.manage',
                ],
            },
            isAuthenticated: true,
        })

        vi.mocked(adminService.listRoles).mockResolvedValue({
            data: ROLE_DETAILS,
            status: 200,
            statusText: 'OK',
            headers: {},
            config: { headers: {} },
        } as Awaited<ReturnType<typeof adminService.listRoles>>)

        vi.mocked(adminService.listPermissions).mockResolvedValue({
            data: PERMISSIONS,
            status: 200,
            statusText: 'OK',
            headers: {},
            config: { headers: {} },
        } as Awaited<ReturnType<typeof adminService.listPermissions>>)

        vi.mocked(dictService.listCategories).mockResolvedValue(ROLE_CATEGORIES)
    })

    it('does not show an edit action in the role table', async () => {
        render(
            <MemoryRouter>
                <RoleManagementPage />
            </MemoryRouter>,
        )

        expect(await screen.findByText('系统管理员')).toBeInTheDocument()
        expect(screen.queryByText('编辑')).not.toBeInTheDocument()
        expect(
            screen.getByRole('button', { name: /权限分配/i }),
        ).toBeInTheDocument()
    })

    it('uses dictionary roles as permission allocation source instead of free role-code input', async () => {
        render(
            <MemoryRouter>
                <RoleManagementPage />
            </MemoryRouter>,
        )

        expect(await screen.findByText('系统管理员')).toBeInTheDocument()

        fireEvent.click(screen.getByRole('button', { name: /权限分配/i }))

        await waitFor(() => {
            expect(screen.getByText('角色来源')).toBeInTheDocument()
            expect(screen.getByText('目标角色')).toBeInTheDocument()
        })

        expect(screen.queryByLabelText('角色编码')).not.toBeInTheDocument()
    })

    it('updates system role permissions after selecting a system role from dictionary', async () => {
        render(
            <MemoryRouter>
                <RoleManagementPage />
            </MemoryRouter>,
        )

        expect(await screen.findByText('系统管理员')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: /权限分配/i }))

        fireEvent.click(screen.getByRole('radio', { name: '系统角色' }))

        fireEvent.click(screen.getByRole('button', { name: 'OK' }))

        await waitFor(() => {
            expect(adminService.updateRolePermissions).toHaveBeenCalledWith(
                'role-admin',
                ['permission-system-menu'],
            )
        })
    })

    it('updates project role permissions after selecting a project role from dictionary', async () => {
        render(
            <MemoryRouter>
                <RoleManagementPage />
            </MemoryRouter>,
        )

        expect(await screen.findByText('系统管理员')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: /权限分配/i }))

        fireEvent.click(screen.getByRole('radio', { name: '项目角色' }))

        fireEvent.click(screen.getByRole('button', { name: 'OK' }))

        await waitFor(() => {
            expect(dictService.updateItem).toHaveBeenCalledWith(
                'dict-project-manager',
                expect.objectContaining({
                    permission_profile: 'manager',
                    permission_codes: ['project.members.menu'],
                }),
            )
        })
    })

    it('blocks saving when the selected system dictionary role has no matching system role entity', async () => {
        vi.mocked(adminService.listRoles).mockResolvedValue({
            data: [],
            status: 200,
            statusText: 'OK',
            headers: {},
            config: { headers: {} },
        } as unknown as Awaited<ReturnType<typeof adminService.listRoles>>)

        vi.mocked(dictService.listCategories).mockResolvedValue([
            {
                ...ROLE_CATEGORIES[0]!,
                items: [
                    {
                        id: 'dict-system-reviewer',
                        category_id: 'category-system-role',
                        code: 'reviewer',
                        label: '系统审查员',
                        description: '系统审查员',
                        sort_order: 1,
                        is_enabled: true,
                        extra: null,
                        permission_profile: null,
                        permission_codes: null,
                        created_at: '2026-06-01T00:00:00Z',
                    },
                ],
            },
            ROLE_CATEGORIES[1]!,
        ])

        render(
            <MemoryRouter>
                <RoleManagementPage />
            </MemoryRouter>,
        )

        expect(await screen.findByText('权限管理')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: /权限分配/i }))

        fireEvent.click(screen.getByRole('radio', { name: '系统角色' }))

        expect(
            await screen.findByText(
                '所选系统角色尚未同步到系统角色实体，请先在系统角色数据中补齐后再分配权限。',
            ),
        ).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'OK' })).toBeDisabled()
        expect(adminService.updateRolePermissions).not.toHaveBeenCalled()
    })
})
