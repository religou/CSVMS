import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import projectService, { type Project } from '@/services/projects'
import systemService from '@/services/systems'
import dictService from '@/services/dictionary'
import ProjectsPage from './index'

vi.mock('@/services/projects', () => ({
    default: {
        list: vi.fn(),
        get: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        addMember: vi.fn(),
        listMemberCandidates: vi.fn(),
        updateMemberRole: vi.fn(),
        removeMember: vi.fn(),
    },
}))

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

const PROJECTS: Project[] = [
    {
        id: 'project-1',
        name: '示例项目',
        code: 'PRJ-001',
        system_name: '示例系统',
        system_id: 'system-1',
        description: null,
        status: 'active',
        stage: 'iq',
        created_by: 'user-1',
        creator_name: '张三',
        member_count: 3,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-02T00:00:00Z',
    },
]

const STAGE_ITEMS = [
    {
        id: 'stage-item-1',
        category_id: 'category-stage',
        code: 'iq',
        label: '安装确认',
        description: null,
        sort_order: 1,
        is_enabled: true,
        extra: 'blue',
        permission_profile: null,
        permission_codes: null,
        created_at: '2026-06-01T00:00:00Z',
    },
]

const STATUS_ITEMS = [
    {
        id: 'status-item-1',
        category_id: 'category-status',
        code: 'active',
        label: '进行中',
        description: null,
        sort_order: 1,
        is_enabled: true,
        extra: 'green',
        permission_profile: null,
        permission_codes: null,
        created_at: '2026-06-01T00:00:00Z',
    },
]

function renderProjectsPage() {
    return render(
        <MemoryRouter>
            <ProjectsPage />
        </MemoryRouter>,
    )
}

describe('ProjectsPage column structure', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(projectService.list).mockResolvedValue(PROJECTS)
        vi.mocked(systemService.list).mockResolvedValue({
            items: [],
            total: 0,
            page: 1,
            page_size: 100,
        })
        vi.mocked(dictService.listItems).mockImplementation(
            (categoryCode: string) => {
                if (categoryCode === 'project_stage') {
                    return Promise.resolve(STAGE_ITEMS)
                }
                if (categoryCode === 'project_status') {
                    return Promise.resolve(STATUS_ITEMS)
                }
                return Promise.resolve([])
            },
        )
    })

    it('renders "阶段" column but not "状态" column', async () => {
        renderProjectsPage()

        // 等待数据加载完成
        await screen.findByText('示例项目')

        const table = document.querySelector('.ant-table') as HTMLElement
        expect(table).toBeInTheDocument()

        const stageHeaderRow = within(table).getByRole('columnheader', {
            name: '阶段',
        })
        expect(stageHeaderRow).toBeInTheDocument()

        // “状态”列已移除
        expect(
            within(table).queryByRole('columnheader', { name: '状态' }),
        ).not.toBeInTheDocument()

        // 阶段列仍然渲染各自的 Tag
        expect(await screen.findByText('安装确认')).toBeInTheDocument()
        // 状态标签不应出现
        expect(screen.queryByText('进行中')).not.toBeInTheDocument()
    })
})
