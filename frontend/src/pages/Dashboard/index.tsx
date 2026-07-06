import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
    Card,
    Row,
    Col,
    Statistic,
    Tag,
    Space,
    Select,
    Button,
    Alert,
    message,
} from 'antd'
import {
    FileTextOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    EditOutlined,
    SafetyCertificateOutlined,
} from '@ant-design/icons'
import { dashboardService, DashboardStats } from '@/services/traceability'
import { useDictItems } from '@/hooks/useDictItems'
import { useProjectStore } from '@/stores/projectStore'
import projectService from '@/services/projects'
import { getErrorMessage } from '@/services/apiClient'
import { deriveEnabledStageOptions, resolveStageDisplay } from '@/utils/stageDisplay'

const WF_STATUS_LABELS: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    approved: '已完成',
    rejected: '已拒绝',
    cancelled: '已撤回',
}

function CurrentStageCard() {
    const currentProject = useProjectStore((s) => s.currentProject)
    const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
    const {
        items: stageItems,
        loading: stageLoading,
        error: stageError,
    } = useDictItems('project_stage', { enabledOnly: false })

    const savedStage = currentProject?.stage ?? null
    const [pendingStage, setPendingStage] = useState<string | null>(savedStage)
    const [saving, setSaving] = useState(false)

    // 项目切换或保存成功后，将本地待选值与已保存值同步
    useEffect(() => {
        setPendingStage(savedStage)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentProject?.id, savedStage])

    const canManageStage =
        currentProject?.current_user_permissions.includes(
            'project.stage.manage',
        ) ?? false

    const controlsDisabled = canManageStage === false || !!stageError

    const options = deriveEnabledStageOptions(stageError ? [] : stageItems)
    if (
        !stageError &&
        savedStage &&
        !options.some((opt) => opt.value === savedStage)
    ) {
        const savedDisplay = resolveStageDisplay(savedStage, stageItems)
        options.push({
            value: savedStage,
            label: savedDisplay.label,
        })
    }

    const handleSave = async () => {
        if (!currentProject || pendingStage === savedStage) return
        setSaving(true)
        try {
            const updated = await projectService.update(currentProject.id, {
                stage: pendingStage,
            })
            setCurrentProject({ ...currentProject, stage: updated.stage })
            message.success('阶段更新成功')
        } catch (err) {
            message.error(getErrorMessage(err, '阶段更新失败'))
            setPendingStage(savedStage)
        } finally {
            setSaving(false)
        }
    }

    return (
        <Card title="当前阶段" style={{ marginBottom: 24 }}>
            {!!stageError && (
                <Alert
                    type="error"
                    showIcon
                    message="获取项目阶段选项失败"
                    style={{ marginBottom: 12 }}
                />
            )}
            <Space>
                <Select
                    style={{ width: 200 }}
                    value={pendingStage ?? undefined}
                    placeholder="未设置"
                    allowClear
                    disabled={controlsDisabled}
                    loading={stageLoading}
                    options={options}
                    onChange={(value) => setPendingStage(value ?? null)}
                    onClear={() => setPendingStage(null)}
                />
                <Button
                    type="primary"
                    disabled={
                        controlsDisabled || pendingStage === savedStage
                    }
                    loading={saving}
                    onClick={handleSave}>
                    保存
                </Button>
            </Space>
        </Card>
    )
}

export default function DashboardPage() {
    const navigate = useNavigate()
    const { projectId } = useParams<{ projectId: string }>()
    const { items: statusDictItems } = useDictItems('doc_status')
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!projectId) return
        setLoading(true)
        ;(async () => {
            try {
                const res = await dashboardService.getStats(projectId)
                setStats(res.data)
            } catch {
                // ignore
            } finally {
                setLoading(false)
            }
        })()
    }, [projectId])

    if (loading || !stats) {
        return <Card loading />
    }

    return (
        <div>
            <CurrentStageCard />

            {/* 核心指标 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={4}>
                    <Card
                        hoverable
                        onClick={() =>
                            navigate(`/projects/${projectId}/documents`)
                        }>
                        <Statistic
                            title="文档总数"
                            value={stats.total_documents}
                            prefix={<FileTextOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card
                        hoverable
                        onClick={() =>
                            navigate(`/projects/${projectId}/workflows`)
                        }>
                        <Statistic
                            title="待我审批"
                            value={stats.pending_approvals}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{
                                color:
                                    stats.pending_approvals > 0
                                        ? '#ff4d4f'
                                        : undefined,
                            }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card
                        hoverable
                        onClick={() =>
                            navigate(`/projects/${projectId}/documents`)
                        }>
                        <Statistic
                            title="我的草稿"
                            value={stats.my_drafts}
                            prefix={<EditOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title="电子签名数"
                            value={stats.total_signatures}
                            prefix={<SafetyCertificateOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title="已批准文档"
                            value={
                                (stats.status_distribution['approved'] || 0) +
                                (stats.status_distribution['effective'] || 0)
                            }
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 文档状态分布 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={12}>
                    <Card title="文档状态分布">
                        <Space wrap>
                            {Object.entries(stats.status_distribution).map(
                                ([status, count]) => {
                                    const dictItem = statusDictItems.find(
                                        (s) => s.code === status,
                                    )
                                    return (
                                        <Tag
                                            key={status}
                                            color={dictItem?.extra || 'default'}
                                            style={{
                                                fontSize: 14,
                                                padding: '4px 12px',
                                            }}>
                                            {dictItem?.label || status}: {count}
                                        </Tag>
                                    )
                                },
                            )}
                            {Object.keys(stats.status_distribution).length ===
                                0 && (
                                <span style={{ color: '#999' }}>暂无数据</span>
                            )}
                        </Space>
                    </Card>
                </Col>
                <Col span={12}>
                    <Card title="文档类型分布">
                        <Space wrap>
                            {Object.entries(stats.type_distribution).map(
                                ([type, count]) => (
                                    <Tag
                                        key={type}
                                        style={{
                                            fontSize: 14,
                                            padding: '4px 12px',
                                        }}>
                                        {type}: {count}
                                    </Tag>
                                ),
                            )}
                            {Object.keys(stats.type_distribution).length ===
                                0 && (
                                <span style={{ color: '#999' }}>暂无数据</span>
                            )}
                        </Space>
                    </Card>
                </Col>
            </Row>

            {/* 工作流统计 */}
            <Row gutter={16}>
                <Col span={12}>
                    <Card title="审批工作流统计">
                        <Space wrap>
                            {Object.entries(stats.workflow_stats).map(
                                ([status, count]) => (
                                    <Tag
                                        key={status}
                                        style={{
                                            fontSize: 14,
                                            padding: '4px 12px',
                                        }}>
                                        {WF_STATUS_LABELS[status] || status}:{' '}
                                        {count}
                                    </Tag>
                                ),
                            )}
                            {Object.keys(stats.workflow_stats).length === 0 && (
                                <span style={{ color: '#999' }}>
                                    暂无审批记录
                                </span>
                            )}
                        </Space>
                    </Card>
                </Col>
            </Row>
        </div>
    )
}
