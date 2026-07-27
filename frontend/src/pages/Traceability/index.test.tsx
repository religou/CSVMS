import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { traceabilityService, type TraceMatrixResponse } from '@/services/traceability'
import TraceabilityPage from './index'

vi.mock('@/services/traceability', () => ({
    traceabilityService: {
        getMatrix: vi.fn(),
    },
    dashboardService: {
        getStats: vi.fn(),
    },
}))

const PROJECT_ID = 'project-1'

function buildMatrixResponse(): TraceMatrixResponse {
    return {
        urs_matrix: [
            {
                urs_item_id: 'item-1',
                item_code: 'URS-DOC-001-001',
                description: '未覆盖的需求条目',
                source_document_id: 'doc-urs-1',
                source_doc_number: 'URS-DOC-001',
                covered: false,
                references: [],
            },
            {
                urs_item_id: 'item-2',
                item_code: 'URS-DOC-001-002',
                description: '已覆盖的需求条目',
                source_document_id: 'doc-urs-1',
                source_doc_number: 'URS-DOC-001',
                covered: true,
                references: [
                    {
                        document_id: 'doc-fs-1',
                        doc_number: 'FS-DOC-001',
                        title: 'FS 文档',
                        doc_type: 'FS',
                    },
                ],
            },
        ],
        uncovered_urs_items: [
            {
                id: 'item-1',
                item_code: 'URS-DOC-001-001',
                description: '未覆盖的需求条目',
            },
        ],
    }
}

async function getMatrixCard(): Promise<HTMLElement> {
    const matrixTitle = await screen.findByText(/^URS 条目追溯矩阵 \(/)
    const matrixCard = matrixTitle.closest('.ant-card') as HTMLElement
    expect(matrixCard).not.toBeNull()
    return matrixCard
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

describe('TraceabilityPage URS 条目覆盖追溯矩阵', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('渲染以条目为核心的覆盖追溯矩阵与未覆盖 URS 条目区块', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        // 以 URS 条目为核心的追溯矩阵（标题含条目总数）
        const matrixCard = await screen.findByText('URS 条目追溯矩阵 (2)')
        expect(matrixCard).toBeInTheDocument()

        // 矩阵展示条目及其下游引用文档（覆盖关系）
        expect(await screen.findByText('URS-DOC-001-002')).toBeInTheDocument()
        expect(screen.getByText('FS FS-DOC-001')).toBeInTheDocument()

        // 不再展示文档级覆盖率统计区块
        expect(screen.queryByText('覆盖率统计')).not.toBeInTheDocument()
    })

    // 2.1 (Req 1.1, 1.3): 主矩阵不再渲染"所属 URS 文档"表头
    it('主追溯矩阵不再渲染"所属 URS 文档"表头', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        const matrixCard = await getMatrixCard()
        const withinMatrix = within(matrixCard)

        // 已移除的列标题不应出现在矩阵卡片内
        expect(withinMatrix.queryByText('所属 URS 文档')).toBeNull()
    })

    // 2.2 (Req 1.2): 主矩阵保留其余四列表头
    it('主追溯矩阵保留条目编号、条目描述、覆盖状态、被引用文档 (下游追溯) 四列表头', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        const matrixCard = await getMatrixCard()
        const columnHeader = within(matrixCard).getAllByRole('columnheader')
        const headerTexts = columnHeader.map((th) => th.textContent)

        expect(headerTexts).toContain('条目编号')
        expect(headerTexts).toContain('条目描述')
        expect(headerTexts).toContain('覆盖状态')
        expect(headerTexts).toContain('被引用文档 (下游追溯)')
    })

    // 2.3 (Req 2.1): 载荷含 source_doc_number 字段时仍正常渲染条目与下游引用
    it('载荷包含 source_doc_number 字段时主矩阵仍正常渲染条目与下游引用', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        const matrixCard = await getMatrixCard()
        const withinMatrix = within(matrixCard)

        // 忽略 source_doc_number 字段但仍渲染条目行与下游引用（不抛错）
        expect(withinMatrix.getByText('URS-DOC-001-002')).toBeInTheDocument()
        expect(withinMatrix.getByText('FS FS-DOC-001')).toBeInTheDocument()
    })

    it('未覆盖 URS 条目表格不包含来源文档列，仅展示条目编号与描述', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        // 等待未覆盖 URS 条目区块出现，并定位到该卡片
        const uncoveredTitle = await screen.findByText('未覆盖 URS 条目 (1)')
        const uncoveredCard = uncoveredTitle.closest('.ant-card') as HTMLElement
        expect(uncoveredCard).not.toBeNull()

        const withinUncovered = within(uncoveredCard)

        // 不再包含来源文档列（已移除的列标题）
        expect(withinUncovered.queryByText('所属 URS 文档编号')).toBeNull()

        // 仅展示条目编号与描述
        expect(withinUncovered.getByText('URS-DOC-001-001')).toBeInTheDocument()
        expect(withinUncovered.getByText('未覆盖的需求条目')).toBeInTheDocument()
    })

    // 2.4 (Req 3.1, 3.2): 未覆盖卡片渲染与未覆盖高亮回归
    it('未覆盖 URS 条目卡片渲染，且主矩阵对未覆盖条目以红色高亮编号与描述', async () => {
        vi.mocked(traceabilityService.getMatrix).mockResolvedValue({
            data: buildMatrixResponse(),
        } as Awaited<ReturnType<typeof traceabilityService.getMatrix>>)

        renderTraceabilityPage()

        // 未覆盖 URS 条目卡片仍然渲染（Req 3.2）
        const uncoveredTitle = await screen.findByText('未覆盖 URS 条目 (1)')
        expect(uncoveredTitle).toBeInTheDocument()

        // 主矩阵对未覆盖条目（item-1 / URS-DOC-001-001）以红色文本高亮（Req 3.1）
        const matrixCard = await getMatrixCard()
        const highlightedCode = within(matrixCard).getByText('URS-DOC-001-001')
        expect(highlightedCode).toHaveStyle({ color: '#ff4d4f' })
    })
})
