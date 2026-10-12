import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { adminService } from '@/services/admin'
import dictService, { type DictItem } from '@/services/dictionary'
import systemService, { type SystemItem } from '@/services/systems'
import SystemsPage from '@/pages/Systems'
import { useAuthStore } from '@/stores/authStore'

vi.mock('@/services/systems', () => ({
    default: {
        list: vi.fn(),
        get: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
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

vi.mock('@/services/admin', () => ({
    adminService: {
        listUsers: vi.fn(),
    },
}))

const SYSTEM: SystemItem = {
    id: 'system-1',
    code: 'ERP-001',
    name: 'SAP ERP 系统',
    vendor: 'SAP',
    version: 'v1',
    description: null,
    gxp_category: 'GMP',
    gamp5_category: 'category_4',
    regulations: ['fda_21cfr_part11'],
    owner_id: null,
    owner_name: null,
    is_active: true,
    created_at: '2026-10-12T00:00:00Z',
    updated_at: '2026-10-12T00:00:00Z',
}

function regulationItem(code: string, label: string, sortOrder: number): DictItem {
    return {
        id: `item-${code}`,
        category_id: 'category-regulation',
        code,
        label,
        description: null,
        sort_order: sortOrder,
        is_enabled: true,
        extra: null,
        permission_profile: null,
        permission_codes: null,
        created_at: '2026-10-12T00:00:00Z',
    }
}

const REGULATION_ITEMS = [
    regulationItem('fda_21cfr_part11', 'FDA 21 CFR Part 11', 10),
    regulationItem('eu_gmp_annex11', 'EU GMP Annex 11', 70),
]

describe('SystemsPage 符合法规 field', () => {
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
                permissions: [],
            },
            isAuthenticated: true,
        })
        vi.mocked(systemService.list).mockResolvedValue({
            items: [SYSTEM],
            total: 1,
            page: 1,
            page_size: 20,
        })
        vi.mocked(systemService.update).mockResolvedValue(SYSTEM)
        vi.mocked(dictService.listItems).mockImplementation(async (code) =>
            code === 'regulation' ? REGULATION_ITEMS : [],
        )
        vi.mocked(adminService.listUsers).mockResolvedValue({
            data: [],
        } as unknown as Awaited<ReturnType<typeof adminService.listUsers>>)
    })

    it('loads options from the regulation dictionary', async () => {
        render(<SystemsPage />)

        await waitFor(() =>
            expect(dictService.listItems).toHaveBeenCalledWith('regulation', true),
        )
    })

    it('shows 符合法规 between GAMP5 类别 and 系统描述 and saves the array', async () => {
        render(<SystemsPage />)

        expect(await screen.findByText('ERP-001')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: 'edit' }))

        expect(await screen.findByText('符合法规')).toBeInTheDocument()
        const labels = Array.from(
            document.querySelectorAll('.ant-modal .ant-form-item-label label'),
        ).map((label) => label.textContent)
        const regulationsIndex = labels.indexOf('符合法规')
        expect(regulationsIndex).toBeGreaterThan(labels.indexOf('GAMP5 类别'))
        expect(regulationsIndex).toBeLessThan(labels.indexOf('系统描述'))

        // 编辑模式回填已有法规（以选项 label 展示）
        expect(await screen.findByTitle('FDA 21 CFR Part 11')).toBeInTheDocument()

        fireEvent.click(screen.getByRole('button', { name: /保\s*存/ }))

        await waitFor(() =>
            expect(systemService.update).toHaveBeenCalledWith(
                'system-1',
                expect.objectContaining({ regulations: ['fda_21cfr_part11'] }),
            ),
        )
    })
})
