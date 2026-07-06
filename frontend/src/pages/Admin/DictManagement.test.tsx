import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { adminService } from '@/services/admin'
import dictService from '@/services/dictionary'
import DictManagementPage from '@/pages/Admin/DictManagement'
import { useAuthStore } from '@/stores/authStore'

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

vi.mock('@/services/admin', () => ({
    adminService: {
        listPermissions: vi.fn(),
    },
}))

const PROJECT_ROLE_CATEGORY = [
    {
        id: 'category-1',
        code: 'project_role',
        name: '项目角色',
        description: '项目成员角色配置',
        is_system: true,
        created_at: '2026-06-01T00:00:00Z',
        items: [
            {
                id: 'item-1',
                category_id: 'category-1',
                code: 'coordinator',
                label: '协调人',
                description: null,
                sort_order: 1,
                is_enabled: true,
                extra: 'orange',
                permission_profile: 'manager',
                permission_codes: null,
                created_at: '2026-06-01T00:00:00Z',
            },
        ],
    },
]

const PROJECT_PERMISSIONS = [
    {
        id: 'permission-1',
        code: 'project.dashboard.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '项目概览菜单',
    },
    {
        id: 'permission-2',
        code: 'project.dashboard.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看项目概览',
    },
    {
        id: 'permission-3',
        code: 'project.documents.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '文档管理菜单',
    },
    {
        id: 'permission-4',
        code: 'project.documents.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看项目文档',
    },
    {
        id: 'permission-5',
        code: 'project.workflows.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '审批管理菜单',
    },
    {
        id: 'permission-6',
        code: 'project.workflows.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看项目审批',
    },
    {
        id: 'permission-7',
        code: 'project.traceability.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '追溯矩阵菜单',
    },
    {
        id: 'permission-8',
        code: 'project.traceability.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看追溯矩阵',
    },
    {
        id: 'permission-9',
        code: 'project.audit_log.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '审计日志菜单',
    },
    {
        id: 'permission-10',
        code: 'project.audit_log.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看项目审计日志',
    },
    {
        id: 'permission-11',
        code: 'project.members.menu',
        resource_type: 'project_menu',
        action: 'access',
        display_name: '项目成员菜单',
    },
    {
        id: 'permission-12',
        code: 'project.members.view',
        resource_type: 'project_page',
        action: 'view',
        display_name: '查看项目成员',
    },
    {
        id: 'permission-13',
        code: 'project.documents.manage',
        resource_type: 'project_button',
        action: 'manage',
        display_name: '管理项目文档',
    },
    {
        id: 'permission-14',
        code: 'project.workflows.manage',
        resource_type: 'project_button',
        action: 'manage',
        display_name: '管理项目审批',
    },
    {
        id: 'permission-15',
        code: 'project.members.manage',
        resource_type: 'project_button',
        action: 'manage',
        display_name: '管理项目成员',
    },
]

describe('DictManagement project role permission configuration', () => {
    beforeEach(() => {
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
                    'system.admin.dict.view',
                    'system.admin.dict.manage',
                ],
            },
            isAuthenticated: true,
        })
        vi.mocked(dictService.listCategories).mockResolvedValue(
            PROJECT_ROLE_CATEGORY,
        )
        vi.mocked(dictService.updateItem).mockResolvedValue({
            id: 'item-1',
            category_id: 'category-1',
            code: 'coordinator',
            label: '协调人',
            description: null,
            sort_order: 1,
            is_enabled: true,
            extra: 'orange',
            permission_profile: 'manager',
            permission_codes: [
                'project.dashboard.menu',
                'project.dashboard.view',
                'project.documents.menu',
                'project.documents.view',
                'project.workflows.menu',
                'project.workflows.view',
                'project.traceability.menu',
                'project.traceability.view',
                'project.audit_log.menu',
                'project.audit_log.view',
                'project.members.menu',
                'project.members.view',
                'project.documents.manage',
                'project.workflows.manage',
                'project.members.manage',
            ],
            created_at: '2026-06-01T00:00:00Z',
        })
        vi.mocked(adminService.listPermissions).mockResolvedValue({
            data: PROJECT_PERMISSIONS,
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {
                headers: {},
            },
        } as Awaited<ReturnType<typeof adminService.listPermissions>>)
    })

    it('fills default project permissions from permission_profile and submits permission_codes', async () => {
        render(<DictManagementPage />)

        expect(await screen.findByText('协调人')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: 'edit' }))
        fireEvent.click(
            screen.getByRole('button', { name: '按档位填充默认权限' }),
        )
        fireEvent.click(screen.getByRole('button', { name: /保\s*存/ }))

        await waitFor(() => {
            expect(dictService.updateItem).toHaveBeenCalledWith(
                'item-1',
                expect.objectContaining({
                    permission_profile: 'manager',
                    permission_codes: [
                        'project.dashboard.menu',
                        'project.dashboard.view',
                        'project.documents.menu',
                        'project.documents.view',
                        'project.workflows.menu',
                        'project.workflows.view',
                        'project.traceability.menu',
                        'project.traceability.view',
                        'project.audit_log.menu',
                        'project.audit_log.view',
                        'project.members.menu',
                        'project.members.view',
                        'project.documents.manage',
                        'project.workflows.manage',
                        'project.members.manage',
                    ],
                }),
            )
        })
    })
})
