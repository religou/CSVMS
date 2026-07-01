import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Statistic, Tag, Space } from 'antd'
import {
    FileTextOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    EditOutlined,
    SafetyCertificateOutlined,
} from '@ant-design/icons'
import { dashboardService, DashboardStats } from '@/services/traceability'
import { useDictItems } from '@/hooks/useDictItems'

const WF_STATUS_LABELS: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    approved: '已完成',
    rejected: '已拒绝',
    cancelled: '已撤回',
}

export default function DashboardPage() {
    const navigate = useNavigate()
    const { items: statusDictItems } = useDictItems('doc_status')
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        ;(async () => {
            try {
                const res = await dashboardService.getStats()
                setStats(res.data)
            } catch {
                // ignore
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    if (loading || !stats) {
        return <Card loading />
    }

    return (
        <div>
            {/* 核心指标 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={4}>
                    <Card hoverable onClick={() => navigate('/documents')}>
                        <Statistic
                            title="文档总数"
                            value={stats.total_documents}
                            prefix={<FileTextOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card hoverable onClick={() => navigate('/workflows')}>
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
                    <Card hoverable onClick={() => navigate('/documents')}>
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
