import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { message } from 'antd'
import fc from 'fast-check'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import dictService, { type DictItem } from '@/services/dictionary'
import { dashboardService } from '@/services/traceability'
import projectService, { type ProjectDetail } from '@/services/projects'
import { useProjectStore } from '@/stores/projectStore'
import DashboardPage from './index'

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

vi.mock('@/services/traceability', () => ({
    dashboardService: {
        getStats: vi.fn(),
    },
    traceabilityService: {
        createLink: vi.fn(),
        deleteLink: vi.fn(),
        getDocumentTraces: vi.fn(),
        getMatrix: vi.fn(),
    },
}))

const PROJECT_ID = 'project-1'

function buildDictItem(
    code: string,
    label: string,
    isEnabled: boolean,
    sortOrder: number,
): DictItem {
    return {
        id: `item-${code}`,
        category_id: 'category-stage',
        code,
        label,
        description: null,
        sort_order: sortOrder,
        is_enabled: isEnabled,
        extra: null,
        permission_profile: null,
        permission_codes: null,
        created_at: '2026-06-01T00:00:00Z',
    }
}

function buildProjectDetail(
    stage: string | null,
    permissions: string[] = ['project.stage.manage'],
): ProjectDetail {
    return {
        id: PROJECT_ID,
        name: '示例项目',
        code: 'PRJ-001',
        system_name: '示例系统',
        system_id: 'system-1',
        description: null,
        status: 'active',
        stage,
        created_by: 'user-1',
        creator_name: '张三',
        member_count: 1,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
        members: [],
        current_user_permissions: permissions,
    }
}

// antd Button 会在两个汉字之间插入不可见空格，因此匹配"保存"按钮时需使用正则
const SAVE_BUTTON_NAME = /保\s*存/

function renderDashboard() {
    return render(
        <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/dashboard`]}>
            <Routes>
                <Route
                    path="/projects/:projectId/dashboard"
                    element={<DashboardPage />}
                />
            </Routes>
        </MemoryRouter>,
    )
}

async function openStageSelect(container: HTMLElement) {
    const selector = container.querySelector('.ant-select-selector')
    await act(async () => {
        fireEvent.mouseDown(selector as HTMLElement)
    })
}

async function chooseStageOption(label: string) {
    // rc-select 的可见选项使用 `.ant-select-item-option` 渲染（`role="option"`
    // 命中的是仅用于无障碍读屏的隐藏副本，不含点击处理），需在此定位真实可点击节点。
    // 当所选标签恰好与当前选择器展示值相同时，页面中会同时存在选择器内的展示文本
    // 与下拉选项文本，因此使用 findAllByText 等待并从所有匹配节点中筛选出属于
    // 下拉选项的那一个。
    const optionNode = await screen.findAllByText(label).then((nodes) => {
        const match = nodes
            .map((el) => el.closest('.ant-select-item-option'))
            .find((el): el is HTMLElement => el !== null)
        if (!match) {
            throw new Error(`未找到下拉选项: ${label}`)
        }
        return match
    })
    await act(async () => {
        fireEvent.click(optionNode)
    })
}

const scenarioArbitrary = fc.integer({ min: 1, max: 5 }).chain((n) =>
    fc.record({
        n: fc.constant(n),
        enabledFlags: fc.array(fc.boolean(), { minLength: n, maxLength: n }),
        savedIndex: fc.integer({ min: -1, max: n - 1 }),
        chosenLocalRaw: fc.nat(),
    }),
)

describe('Dashboard CurrentStageCard property tests', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(dashboardService.getStats).mockResolvedValue({
            data: {
                total_documents: 0,
                status_distribution: {},
                type_distribution: {},
                workflow_stats: {},
                pending_approvals: 0,
                my_drafts: 0,
                total_signatures: 0,
            },
        } as Awaited<ReturnType<typeof dashboardService.getStats>>)
    })

    it(
        // Feature: project-stage-management, Property 10: 仅在确认且值发生变化时才提交阶段更新
        // Validates: Requirements 5.4, 5.5, 6.4
        'submits an update exactly once when confirmed with a changed value, and never on mere selection or unchanged confirmation',
        async () => {
            await fc.assert(
                fc.asyncProperty(
                    scenarioArbitrary,
                    async ({ n, enabledFlags, savedIndex, chosenLocalRaw }) => {
                        const enabledIndices: number[] = []
                        enabledFlags.forEach((enabled, idx) => {
                            if (enabled) enabledIndices.push(idx)
                        })
                        // 需要至少一个已启用的可选项才能驱动"选择新值"这一交互
                        fc.pre(enabledIndices.length > 0)

                        vi.clearAllMocks()
                        useProjectStore.setState({ currentProject: null })
                        vi.mocked(dashboardService.getStats).mockResolvedValue({
                            data: {
                                total_documents: 0,
                                status_distribution: {},
                                type_distribution: {},
                                workflow_stats: {},
                                pending_approvals: 0,
                                my_drafts: 0,
                                total_signatures: 0,
                            },
                        } as Awaited<ReturnType<typeof dashboardService.getStats>>)

                        const codes = Array.from({ length: n }, (_, i) => `stage-${i}`)
                        const labels = codes.map((_, i) => `Stage ${i}`)
                        const items = codes.map((code, i) =>
                            buildDictItem(code, labels[i], enabledFlags[i], i),
                        )
                        const savedStage = savedIndex === -1 ? null : codes[savedIndex]
                        const chosenIndex =
                            enabledIndices[chosenLocalRaw % enabledIndices.length]
                        const chosenCode = codes[chosenIndex]
                        const chosenLabel = labels[chosenIndex]

                        vi.mocked(dictService.listItems).mockImplementation(
                            (categoryCode: string) => {
                                if (categoryCode === 'project_stage') {
                                    return Promise.resolve(items)
                                }
                                return Promise.resolve([])
                            },
                        )
                        vi.mocked(projectService.update).mockResolvedValue(
                            buildProjectDetail(chosenCode),
                        )

                        useProjectStore.setState({
                            currentProject: buildProjectDetail(savedStage),
                        })

                        try {
                            const { container } = renderDashboard()

                            // 等待字典项与统计数据加载完成
                            await screen.findByText('当前阶段')
                            await screen.findByRole('button', {
                                name: SAVE_BUTTON_NAME,
                            })

                            // 步骤一：未变更选择值即直接确认保存——不应提交请求
                            // （同时覆盖"已保存值对应一个已禁用字典项且用户未变更该值"的场景，Requirement 6.4）
                            await act(async () => {
                                fireEvent.click(
                                    screen.getByRole('button', {
                                        name: SAVE_BUTTON_NAME,
                                    }),
                                )
                            })
                            expect(projectService.update).not.toHaveBeenCalled()

                            // 步骤二：仅选择新值但未确认保存——不应提交任何请求
                            await openStageSelect(container)
                            await chooseStageOption(chosenLabel)
                            expect(projectService.update).not.toHaveBeenCalled()

                            // 步骤三：确认保存——当且仅当所选值与已保存值不同时，触发恰好一次带所选编码的请求
                            await act(async () => {
                                fireEvent.click(
                                    screen.getByRole('button', {
                                        name: SAVE_BUTTON_NAME,
                                    }),
                                )
                            })

                            if (chosenCode === savedStage) {
                                expect(
                                    projectService.update,
                                ).not.toHaveBeenCalled()
                            } else {
                                expect(
                                    projectService.update,
                                ).toHaveBeenCalledTimes(1)
                                expect(projectService.update).toHaveBeenCalledWith(
                                    PROJECT_ID,
                                    { stage: chosenCode },
                                )
                            }
                        } finally {
                            cleanup()
                        }
                    },
                ),
                { numRuns: 100 },
            )
        },
        300000,
    )
})

// 用于定位当前 Select 展示的文本：已选中值展示为 `.ant-select-selection-item`，
// 未选中（值为空）时展示占位文本 `.ant-select-selection-placeholder`。
function getSelectDisplayText(container: HTMLElement): string | null {
    const selectedItem = container.querySelector('.ant-select-selection-item')
    if (selectedItem) {
        return selectedItem.textContent
    }
    const placeholder = container.querySelector(
        '.ant-select-selection-placeholder',
    )
    return placeholder ? placeholder.textContent : null
}

const property11ScenarioArbitrary = fc.integer({ min: 2, max: 5 }).chain((n) =>
    fc.record({
        n: fc.constant(n),
        enabledFlags: fc.array(fc.boolean(), { minLength: n, maxLength: n }),
        savedIndex: fc.integer({ min: -1, max: n - 1 }),
        chosenLocalRaw: fc.nat(),
    }),
)

describe('Dashboard CurrentStageCard property 11 test', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(dashboardService.getStats).mockResolvedValue({
            data: {
                total_documents: 0,
                status_distribution: {},
                type_distribution: {},
                workflow_stats: {},
                pending_approvals: 0,
                my_drafts: 0,
                total_signatures: 0,
            },
        } as Awaited<ReturnType<typeof dashboardService.getStats>>)
    })

    it(
        // Feature: project-stage-management, Property 11: 更新失败时展示值回退
        // Validates: Requirements 5.7
        'rolls back the displayed value to the pre-update value and leaves persisted stage unchanged when the update request fails',
        async () => {
            await fc.assert(
                fc.asyncProperty(
                    property11ScenarioArbitrary,
                    async ({ n, enabledFlags, savedIndex, chosenLocalRaw }) => {
                        const enabledIndices: number[] = []
                        enabledFlags.forEach((enabled, idx) => {
                            if (enabled) enabledIndices.push(idx)
                        })
                        // 需要至少一个"与已保存值不同"的已启用可选项，才能驱动一次
                        // 会实际提交请求的阶段变更
                        const changeableIndices = enabledIndices.filter(
                            (idx) => idx !== savedIndex,
                        )
                        fc.pre(changeableIndices.length > 0)

                        vi.clearAllMocks()
                        useProjectStore.setState({ currentProject: null })
                        vi.mocked(dashboardService.getStats).mockResolvedValue({
                            data: {
                                total_documents: 0,
                                status_distribution: {},
                                type_distribution: {},
                                workflow_stats: {},
                                pending_approvals: 0,
                                my_drafts: 0,
                                total_signatures: 0,
                            },
                        } as Awaited<ReturnType<typeof dashboardService.getStats>>)

                        const codes = Array.from({ length: n }, (_, i) => `stage-${i}`)
                        const labels = codes.map((_, i) => `Stage ${i}`)
                        const items = codes.map((code, i) =>
                            buildDictItem(code, labels[i], enabledFlags[i], i),
                        )
                        const savedStage = savedIndex === -1 ? null : codes[savedIndex]
                        const savedLabel =
                            savedIndex === -1 ? '未设置' : labels[savedIndex]
                        const chosenIndex =
                            changeableIndices[
                                chosenLocalRaw % changeableIndices.length
                            ]
                        const chosenCode = codes[chosenIndex]
                        const chosenLabel = labels[chosenIndex]

                        vi.mocked(dictService.listItems).mockImplementation(
                            (categoryCode: string) => {
                                if (categoryCode === 'project_stage') {
                                    return Promise.resolve(items)
                                }
                                return Promise.resolve([])
                            },
                        )
                        vi.mocked(projectService.update).mockRejectedValue(
                            new Error('network error'),
                        )

                        useProjectStore.setState({
                            currentProject: buildProjectDetail(savedStage),
                        })

                        try {
                            const { container } = renderDashboard()

                            // 等待字典项与统计数据加载完成
                            await screen.findByText('当前阶段')
                            await screen.findByRole('button', {
                                name: SAVE_BUTTON_NAME,
                            })

                            // 选择一个与已保存值不同的新阶段
                            await openStageSelect(container)
                            await chooseStageOption(chosenLabel)
                            expect(getSelectDisplayText(container)).toBe(
                                chosenLabel,
                            )

                            // 确认保存，触发失败的更新请求
                            await act(async () => {
                                fireEvent.click(
                                    screen.getByRole('button', {
                                        name: SAVE_BUTTON_NAME,
                                    }),
                                )
                            })

                            await waitFor(() => {
                                expect(
                                    projectService.update,
                                ).toHaveBeenCalledWith(PROJECT_ID, {
                                    stage: chosenCode,
                                })
                            })

                            // 展示值精确回退为更新前的已保存值，而非用户尝试提交的新值
                            await waitFor(() => {
                                expect(getSelectDisplayText(container)).toBe(
                                    savedLabel,
                                )
                            })
                            expect(getSelectDisplayText(container)).not.toBe(
                                chosenLabel,
                            )

                            // 实际持久化的阶段值保持不变（更新失败时不调用 setCurrentProject）
                            expect(
                                useProjectStore.getState().currentProject
                                    ?.stage,
                            ).toBe(savedStage)
                        } finally {
                            cleanup()
                        }
                    },
                ),
                { numRuns: 100 },
            )
        },
        300000,
    )
})

describe('Dashboard CurrentStageCard dictionary load failure', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(dashboardService.getStats).mockResolvedValue({
            data: {
                total_documents: 0,
                status_distribution: {},
                type_distribution: {},
                workflow_stats: {},
                pending_approvals: 0,
                my_drafts: 0,
                total_signatures: 0,
            },
        } as Awaited<ReturnType<typeof dashboardService.getStats>>)
    })

    it(
        // Requirements: 5.2
        '当获取字典项失败时展示错误提示、禁用控件且不提供任何可选项',
        async () => {
            vi.mocked(dictService.listItems).mockImplementation(
                (categoryCode: string) => {
                    if (categoryCode === 'project_stage') {
                        return Promise.reject(new Error('network error'))
                    }
                    return Promise.resolve([])
                },
            )

            useProjectStore.setState({
                currentProject: buildProjectDetail('stage-0'),
            })

            const { container } = renderDashboard()

            // 等待错误提示展示
            await screen.findByText('获取项目阶段选项失败')

            const saveButton = await screen.findByRole('button', {
                name: SAVE_BUTTON_NAME,
            })

            // Select 控件应处于禁用态
            expect(
                container.querySelector('.ant-select-disabled'),
            ).not.toBeNull()
            // 保存按钮应处于禁用态
            expect(saveButton).toBeDisabled()

            // 禁用态下尝试打开下拉也不应展示任何可选项
            const selector = container.querySelector('.ant-select-selector')
            await act(async () => {
                fireEvent.mouseDown(selector as HTMLElement)
            })
            const openedOption = container
                .querySelector('.ant-select-dropdown')
                ?.querySelector('.ant-select-item-option')
            expect(openedOption ?? null).toBeNull()

            cleanup()
        },
    )
})

const property12ScenarioArbitrary = fc.integer({ min: 1, max: 5 }).chain((n) =>
    fc.record({
        n: fc.constant(n),
        enabledFlags: fc.array(fc.boolean(), { minLength: n, maxLength: n }),
        savedIndex: fc.integer({ min: -1, max: n - 1 }),
        attemptLocalRaw: fc.nat(),
    }),
)

describe('Dashboard CurrentStageCard property 12 test', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(dashboardService.getStats).mockResolvedValue({
            data: {
                total_documents: 0,
                status_distribution: {},
                type_distribution: {},
                workflow_stats: {},
                pending_approvals: 0,
                my_drafts: 0,
                total_signatures: 0,
            },
        } as Awaited<ReturnType<typeof dashboardService.getStats>>)
    })

    it(
        // Feature: project-stage-management, Property 12: 无权限用户不会触发任何阶段更新提交
        // Validates: Requirements 5.8, 6.5
        'never submits a stage update request for a user lacking project.stage.manage, regardless of the displayed value or attempted interaction',
        async () => {
            await fc.assert(
                fc.asyncProperty(
                    property12ScenarioArbitrary,
                    async ({ n, enabledFlags, savedIndex, attemptLocalRaw }) => {
                        vi.clearAllMocks()
                        useProjectStore.setState({ currentProject: null })
                        vi.mocked(dashboardService.getStats).mockResolvedValue({
                            data: {
                                total_documents: 0,
                                status_distribution: {},
                                type_distribution: {},
                                workflow_stats: {},
                                pending_approvals: 0,
                                my_drafts: 0,
                                total_signatures: 0,
                            },
                        } as Awaited<ReturnType<typeof dashboardService.getStats>>)

                        const codes = Array.from({ length: n }, (_, i) => `stage-${i}`)
                        const labels = codes.map((_, i) => `Stage ${i}`)
                        const items = codes.map((code, i) =>
                            buildDictItem(code, labels[i], enabledFlags[i], i),
                        )
                        // savedIndex 可能指向一个已被禁用的字典项，覆盖"值对应
                        // 一个禁用字典项"这一场景
                        const savedStage = savedIndex === -1 ? null : codes[savedIndex]

                        vi.mocked(dictService.listItems).mockImplementation(
                            (categoryCode: string) => {
                                if (categoryCode === 'project_stage') {
                                    return Promise.resolve(items)
                                }
                                return Promise.resolve([])
                            },
                        )
                        vi.mocked(projectService.update).mockResolvedValue(
                            buildProjectDetail(savedStage, []),
                        )

                        // 用户在项目中既非 Owner 也非 Manager：权限列表中不包含
                        // `project.stage.manage`
                        useProjectStore.setState({
                            currentProject: buildProjectDetail(savedStage, []),
                        })

                        try {
                            const { container } = renderDashboard()

                            // 等待字典项与统计数据加载完成
                            await screen.findByText('当前阶段')
                            const saveButton = await screen.findByRole('button', {
                                name: SAVE_BUTTON_NAME,
                            })

                            // 控件应处于禁用态
                            const selector = container.querySelector(
                                '.ant-select-selector',
                            )
                            expect(
                                container.querySelector('.ant-select-disabled'),
                            ).not.toBeNull()
                            expect(saveButton).toBeDisabled()

                            // 尝试交互一：打开 Select 并尝试选择一个选项
                            await act(async () => {
                                fireEvent.mouseDown(selector as HTMLElement)
                            })
                            // 禁用态下下拉不应展开，任何字典项标签均不应作为
                            // 可点击的下拉选项出现
                            const openedOption = container
                                .querySelector('.ant-select-dropdown')
                                ?.querySelector('.ant-select-item-option')
                            expect(openedOption ?? null).toBeNull()

                            // 尝试交互二：点击禁用态的保存按钮
                            await act(async () => {
                                fireEvent.click(saveButton)
                            })

                            // 尝试交互三：根据随机数决定是否额外尝试点击 Select 选择器本身
                            if (attemptLocalRaw % 2 === 0) {
                                await act(async () => {
                                    fireEvent.click(selector as HTMLElement)
                                })
                            }

                            expect(projectService.update).not.toHaveBeenCalled()
                        } finally {
                            cleanup()
                        }
                    },
                ),
                { numRuns: 100 },
            )
        },
        300000,
    )
})

describe('Dashboard CurrentStageCard save success feedback', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        useProjectStore.setState({ currentProject: null })
        vi.mocked(dashboardService.getStats).mockResolvedValue({
            data: {
                total_documents: 0,
                status_distribution: {},
                type_distribution: {},
                workflow_stats: {},
                pending_approvals: 0,
                my_drafts: 0,
                total_signatures: 0,
            },
        } as Awaited<ReturnType<typeof dashboardService.getStats>>)
    })

    it(
        // Requirements: 5.6
        '保存成功后展示成功提示，且展示值刷新为更新后阶段编码对应的名称',
        async () => {
            const successSpy = vi.spyOn(message, 'success')

            const savedCode = 'stage-0'
            const savedLabel = '立项'
            const targetCode = 'stage-1'
            const targetLabel = '实施'
            const items = [
                buildDictItem(savedCode, savedLabel, true, 0),
                buildDictItem(targetCode, targetLabel, true, 1),
            ]

            vi.mocked(dictService.listItems).mockImplementation(
                (categoryCode: string) => {
                    if (categoryCode === 'project_stage') {
                        return Promise.resolve(items)
                    }
                    return Promise.resolve([])
                },
            )
            vi.mocked(projectService.update).mockResolvedValue(
                buildProjectDetail(targetCode),
            )

            useProjectStore.setState({
                currentProject: buildProjectDetail(savedCode),
            })

            const { container } = renderDashboard()

            // 等待字典项与统计数据加载完成
            await screen.findByText('当前阶段')
            const saveButton = await screen.findByRole('button', {
                name: SAVE_BUTTON_NAME,
            })

            // 选择一个与已保存值不同的新阶段
            await openStageSelect(container)
            await chooseStageOption(targetLabel)
            expect(getSelectDisplayText(container)).toBe(targetLabel)

            // 确认保存
            await act(async () => {
                fireEvent.click(saveButton)
            })

            await waitFor(() => {
                expect(projectService.update).toHaveBeenCalledWith(
                    PROJECT_ID,
                    { stage: targetCode },
                )
            })

            // 展示成功提示
            await waitFor(() => {
                expect(successSpy).toHaveBeenCalledWith('阶段更新成功')
            })

            // 展示值刷新为更新后阶段编码对应的名称
            await waitFor(() => {
                expect(getSelectDisplayText(container)).toBe(targetLabel)
            })

            // 持久化的阶段值同步为更新后的阶段编码
            expect(
                useProjectStore.getState().currentProject?.stage,
            ).toBe(targetCode)

            cleanup()
        },
    )
})
