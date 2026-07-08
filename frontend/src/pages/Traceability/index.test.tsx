import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { traceabilityService, type TraceMatrixResponse } from '@/services/traceability'
import TraceabilityPage from './index'

vi.mock('@/services/traceability', () => ({
    traceabilityService: {
        getMatrix: vi.fn(),
        createLink: vi.fn(),
        deleteLink: vi.fn(),
        getDocumentTraces: vi.fn(),
    },
    dashboardService: {
        getStats: vi.fn(),
    },
}))

const PROJECT_ID = 'project-1'

function buildMatrixResponse(): TraceMatrixResponse {
    return {
        links: [],
        coverage: {
            FS: {
                total: 3,
                covered: 2,
                rate: 66.7,
                expected_targets: ['DS'],
            },
        },
        gaps: [],
        urs_coverage: {
            total: 5,
            covered: 3,
            uncovered: 2,
            rate: 60.0,
        },
        uncovered_urs_items: [
            {
                id: 'item-1',
                item_code: 'URS-001',
                description: '未覆盖的需求条目',
                document_id: 'doc-urs-1',
                doc_number: 'URS-DOC-001',
            },
        ],
    }
}

function renderTraceabilityPage() {
    return render(
        <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/traceability`]}>
            <Routes>
                <Route
                    path="/projects/:projectId/traceability"
                    element={<TraceabilityPage />}
                />
            </Routes>
        </MemoryRouter>,
    )
}

describe('TraceabilityPage URS 条目覆盖率卡片', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it(
        // Requirements: 6.3
        'URS 条目覆盖率卡片与既有文档级覆盖率卡片作为两个独立区块渲染',
        async () => {
            vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
                data: buildMatrixResponse(),
            } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

            renderTraceabilityPage()

            // 验证两张独立卡片都渲染在页面上
            const docCoverageCard = await screen.findByText('覆盖率统计')
            const ursCoverageCard = await screen.findByText('URS 条目覆盖率')

            expect(docCoverageCard).toBeInTheDocument()
            expect(ursCoverageCard).toBeInTheDocument()

            // 验证两者为不同的 DOM 元素（独立区块）
            expect(docCoverageCard).not.toBe(ursCoverageCard)

            // 验证两者不存在父子包含关系，即是兄弟级别的独立区块
            const docCard = docCoverageCard.closest('.ant-card')
            const ursCard = ursCoverageCard.closest('.ant-card')

            expect(docCard).not.toBeNull()
            expect(ursCard).not.toBeNull()
            expect(docCard).not.toBe(ursCard)
            expect(docCard!.contains(ursCard!)).toBe(false)
            expect(ursCard!.contains(docCard!)).toBe(false)
        },
    )
})
