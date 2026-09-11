import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { dashboardService } from '@/services/traceability'
import { workflowService } from '@/services/workflows'
import { useAuthStore } from '@/stores/authStore'
import HomePage from './index'

vi.mock('@/services/traceability', () => ({
    dashboardService: { getHome: vi.fn(), getStats: vi.fn() },
}))

vi.mock('@/services/workflows', () => ({
    workflowService: { getMyPending: vi.fn() },
}))

function renderHome() {
    return render(
        <MemoryRouter>
            <HomePage />
        </MemoryRouter>,
    )
}

describe('HomePage', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useAuthStore.setState({
            user: {
                id: 'u1',
                username: 'alice',
                email: 'a@x.com',
                full_name: '爱丽丝',
                is_active: true,
                roles: [],
                permissions: [],
            },
        } as Partial<ReturnType<typeof useAuthStore.getState>> as never)
    })

    it('展示参与项目数、待我审批与我的草稿', async () => {
        vi.mocked(dashboardService.getHome).mockResolvedValue({
            data: {
                project_count: 3,
                my_draft_count: 1,
                my_drafts: [
                    {
                        id: 'd1',
                        title: '草稿甲',
                        doc_type: 'URS',
                        doc_number: 'URS-1',
                        version: '0.1',
                        project_id: 'p1',
                        updated_at: '2026-06-01T00:00:00Z',
                    },
                ],
            },
        } as Awaited<ReturnType<typeof dashboardService.getHome>>)
        vi.mocked(workflowService.getMyPending).mockResolvedValue({
            data: [
                {
                    id: 'w1',
                    template_id: 't1',
                    document_id: 'doc9',
                    document_title: '待审文档',
                    project_id: 'p1',
                    status: 'in_progress',
                    current_step_order: 1,
                    initiated_by: 'u2',
                    initiated_at: '2026-06-01T00:00:00Z',
                    steps: [
                        {
                            id: 's1',
                            step_order: 1,
                            name: 'QA审核',
                            step_type: 'review',
                            status: 'in_progress',
                        },
                    ],
                },
            ],
        } as Awaited<ReturnType<typeof workflowService.getMyPending>>)

        renderHome()

        expect(await screen.findByText('待审文档')).toBeInTheDocument()
        expect(screen.getByText('QA审核')).toBeInTheDocument()
        expect(screen.getByText('草稿甲')).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('无待办与草稿时展示空态', async () => {
        vi.mocked(dashboardService.getHome).mockResolvedValue({
            data: { project_count: 0, my_draft_count: 0, my_drafts: [] },
        } as Awaited<ReturnType<typeof dashboardService.getHome>>)
        vi.mocked(workflowService.getMyPending).mockResolvedValue({
            data: [],
        } as Awaited<ReturnType<typeof workflowService.getMyPending>>)

        renderHome()

        expect(await screen.findByText('暂无待审批事项')).toBeInTheDocument()
        expect(screen.getByText('暂无草稿')).toBeInTheDocument()
    })
})
