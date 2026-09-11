import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
    documentService,
    listUrsReferences,
    type DocumentDetail,
} from '@/services/documents'
import { workflowService } from '@/services/workflows'
import { useProjectStore } from '@/stores/projectStore'
import DocumentDetailPage from './Detail'

vi.mock('@/services/documents', () => ({
    documentService: {
        list: vi.fn(),
        get: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
        getVersions: vi.fn(),
    },
    listUrsItems: vi.fn(),
    createUrsItem: vi.fn(),
    updateUrsItem: vi.fn(),
    deleteUrsItem: vi.fn(),
    listUrsReferences: vi.fn(),
    createUrsReference: vi.fn(),
    deleteUrsReference: vi.fn(),
}))

vi.mock('@/services/workflows', () => ({
    workflowService: {
        listTemplates: vi.fn(),
        getTemplate: vi.fn(),
        createTemplate: vi.fn(),
        updateTemplate: vi.fn(),
        submit: vi.fn(),
        approve: vi.fn(),
        reject: vi.fn(),
        return: vi.fn(),
        withdraw: vi.fn(),
        get: vi.fn(),
        getByDocument: vi.fn(),
        getMyPending: vi.fn(),
        getActions: vi.fn(),
    },
}))

const DOCUMENT_ID = 'doc-1'
const PROJECT_ID = 'project-1'

function buildFsDocument(): DocumentDetail {
    return {
        id: DOCUMENT_ID,
        title: '功能规格说明',
        doc_type: 'FS',
        doc_number: 'FS-001',
        status: 'draft',
        version: '1.0',
        summary: undefined,
        project_id: PROJECT_ID,
        author_id: 'user-1',
        author_name: '张三',
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
        content: '',
        versions: [],
    }
}

function renderDetailPage() {
    return render(
        <MemoryRouter
            initialEntries={[
                `/projects/${PROJECT_ID}/documents/${DOCUMENT_ID}`,
            ]}>
            <Routes>
                <Route
                    path="/projects/:projectId/documents/:id"
                    element={<DocumentDetailPage />}
                />
            </Routes>
        </MemoryRouter>,
    )
}

describe('DocumentDetailPage 关联的 URS 条目 Tab', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(workflowService.getByDocument).mockResolvedValue({
            data: null,
        } as Awaited<ReturnType<typeof workflowService.getByDocument>>)
    })

    it(// Requirements: 4.2
    '当文档尚未关联任何 URS_Item 时，展示统一的"未关联 URS 条目"提示', async () => {
        vi.mocked(documentService.get).mockResolvedValue({
            data: buildFsDocument(),
        } as Awaited<ReturnType<typeof documentService.get>>)
        vi.mocked(listUrsReferences).mockResolvedValue({
            data: [],
        } as unknown as Awaited<ReturnType<typeof listUrsReferences>>)

        renderDetailPage()

        // 等待文档加载完成，并切换到"关联的 URS 条目" Tab
        const tab = await screen.findByRole('tab', {
            name: '关联的 URS 条目',
        })
        tab.click()

        await waitFor(() => {
            expect(listUrsReferences).toHaveBeenCalledWith(DOCUMENT_ID)
        })

        expect(await screen.findByText('未关联 URS 条目')).toBeInTheDocument()
    })
})

describe('DocumentDetailPage 审批流程 Tab 状态门控', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(listUrsReferences).mockResolvedValue({
            data: [],
        } as unknown as Awaited<ReturnType<typeof listUrsReferences>>)
    })

    it('已批准文档发起变更回到草稿后，审批流程不再显示上一轮的"已通过"', async () => {
        vi.mocked(documentService.get).mockResolvedValue({
            data: { ...buildFsDocument(), status: 'draft', version: '1.1' },
        } as Awaited<ReturnType<typeof documentService.get>>)
        // 旧的已批准工作流仍存在（历史），但当前文档已是草稿
        vi.mocked(workflowService.getByDocument).mockResolvedValue({
            data: {
                id: 'wf-1',
                template_id: 'tpl-1',
                document_id: DOCUMENT_ID,
                status: 'approved',
                current_step_order: 2,
                initiated_by: 'user-1',
                initiated_at: '2026-06-01T00:00:00Z',
                steps: [
                    {
                        id: 's1',
                        step_order: 1,
                        name: 'QA审核',
                        step_type: 'review',
                        status: 'approved',
                    },
                    {
                        id: 's2',
                        step_order: 2,
                        name: 'QA批准',
                        step_type: 'approve',
                        status: 'approved',
                    },
                ],
            },
        } as Awaited<ReturnType<typeof workflowService.getByDocument>>)

        renderDetailPage()

        const tab = await screen.findByRole('tab', { name: '审批流程' })
        tab.click()

        expect(
            await screen.findByText('当前为草稿，待重新提交审批'),
        ).toBeInTheDocument()
        expect(screen.queryByText('已通过')).not.toBeInTheDocument()
    })
})
