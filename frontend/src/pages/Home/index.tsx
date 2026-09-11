import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Row,
    Col,
    Card,
    Statistic,
    List,
    Button,
    Tag,
    Typography,
    Space,
    Spin,
    Empty,
} from 'antd'
import {
    ProjectOutlined,
    ClockCircleOutlined,
    FileTextOutlined,
    RightOutlined,
} from '@ant-design/icons'
import { dashboardService, HomeSummary } from '@/services/traceability'
import { workflowService, WorkflowItem } from '@/services/workflows'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

const MAX_LIST = 5

export default function HomePage() {
    const navigate = useNavigate()
    const user = useAuthStore((state) => state.user)
    const [summary, setSummary] = useState<HomeSummary | null>(null)
    const [pending, setPending] = useState<WorkflowItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let active = true
        Promise.all([
            dashboardService.getHome(),
            workflowService.getMyPending(),
        ])
            .then(([homeRes, pendingRes]) => {
                if (!active) return
                setSummary(homeRes.data)
                setPending(pendingRes.data)
            })
            .finally(() => active && setLoading(false))
        return () => {
            active = false
        }
    }, [])

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: 80 }}>
                <Spin size="large" />
            </div>
        )
    }

    const pendingTop = pending.slice(0, MAX_LIST)
    const draftsTop = summary?.my_drafts ?? []

    const stepNameOf = (wf: WorkflowItem) =>
        wf.steps.find((s) => s.status === 'in_progress')?.name ??
        wf.steps.find((s) => s.step_order === wf.current_step_order)?.name ??
        '审批中'

    return (
        <div>
            <Title level={4} style={{ marginBottom: 4 }}>
                你好，{user?.full_name || user?.username}
            </Title>
            <Text type="secondary">这里是你的工作概览</Text>

            <Row gutter={16} style={{ marginTop: 16 }}>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="参与的项目"
                            value={summary?.project_count ?? 0}
                            prefix={<ProjectOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="待我审批"
                            value={pending.length}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{
                                color:
                                    pending.length > 0 ? '#ff4d4f' : undefined,
                            }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="我的草稿"
                            value={summary?.my_draft_count ?? 0}
                            prefix={<FileTextOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={16} style={{ marginTop: 16 }}>
                <Col xs={24} lg={12}>
                    <Card
                        title="待办事项 · 待我审批"
                        extra={
                            <Button
                                type="link"
                                onClick={() => navigate('/projects')}>
                                进入我的项目 <RightOutlined />
                            </Button>
                        }>
                        {pendingTop.length === 0 ? (
                            <Empty description="暂无待审批事项" />
                        ) : (
                            <List
                                dataSource={pendingTop}
                                renderItem={(wf) => (
                                    <List.Item
                                        style={{ cursor: 'pointer' }}
                                        onClick={() =>
                                            wf.project_id &&
                                            navigate(
                                                `/projects/${wf.project_id}/documents/${wf.document_id}`,
                                            )
                                        }>
                                        <List.Item.Meta
                                            title={
                                                wf.document_title ||
                                                wf.document_id
                                            }
                                            description={
                                                <Tag color="blue">
                                                    {stepNameOf(wf)}
                                                </Tag>
                                            }
                                        />
                                    </List.Item>
                                )}
                            />
                        )}
                        {pending.length > MAX_LIST && (
                            <Text type="secondary">
                                共 {pending.length} 项待审批
                            </Text>
                        )}
                    </Card>
                </Col>

                <Col xs={24} lg={12}>
                    <Card title="我的草稿">
                        {draftsTop.length === 0 ? (
                            <Empty description="暂无草稿" />
                        ) : (
                            <List
                                dataSource={draftsTop}
                                renderItem={(d) => (
                                    <List.Item
                                        style={{ cursor: 'pointer' }}
                                        onClick={() =>
                                            d.project_id &&
                                            navigate(
                                                `/projects/${d.project_id}/documents/${d.id}`,
                                            )
                                        }>
                                        <List.Item.Meta
                                            title={
                                                <Space>
                                                    <Tag>{d.doc_type}</Tag>
                                                    {d.title}
                                                </Space>
                                            }
                                            description={
                                                <Text type="secondary">
                                                    {d.doc_number} · v
                                                    {d.version} ·{' '}
                                                    {new Date(
                                                        d.updated_at,
                                                    ).toLocaleString('zh-CN')}
                                                </Text>
                                            }
                                        />
                                    </List.Item>
                                )}
                            />
                        )}
                        {summary && summary.my_draft_count > MAX_LIST && (
                            <Text type="secondary">
                                共 {summary.my_draft_count} 份草稿
                            </Text>
                        )}
                    </Card>
                </Col>
            </Row>
        </div>
    )
}
