import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Table,
    Tag,
    Tabs,
    Space,
    Button,
    Modal,
    Form,
    Input,
    Select,
    message,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import {
    workflowService,
    WorkflowItem,
    WorkflowTemplate,
} from '@/services/workflows'
import { useDictItems } from '@/hooks/useDictItems'
import { useProjectStore } from '@/stores/projectStore'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
    pending: { label: '待处理', color: 'default' },
    in_progress: { label: '进行中', color: 'processing' },
    approved: { label: '已批准', color: 'success' },
    rejected: { label: '已拒绝', color: 'error' },
    cancelled: { label: '已撤回', color: 'warning' },
}

export default function WorkflowsPage() {
    const { options: docTypeOptions } = useDictItems('doc_type')
    const navigate = useNavigate()
    const currentProject = useProjectStore((state) => state.currentProject)
    const canManageWorkflows =
        currentProject?.current_user_permissions.includes(
            'project.workflows.manage',
        ) ?? false
    const [pendingList, setPendingList] = useState<WorkflowItem[]>([])
    const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
    const [loading, setLoading] = useState(false)
    const [templateModalOpen, setTemplateModalOpen] = useState(false)
    const [form] = Form.useForm()

    useEffect(() => {
        fetchPending()
        fetchTemplates()
    }, [])

    const fetchPending = async () => {
        setLoading(true)
        try {
            const res = await workflowService.getMyPending()
            setPendingList(res.data)
        } catch {
            // ignore
        } finally {
            setLoading(false)
        }
    }

    const fetchTemplates = async () => {
        try {
            const res = await workflowService.listTemplates()
            setTemplates(res.data)
        } catch {
            // ignore
        }
    }

    const handleCreateTemplate = async (values: any) => {
        try {
            await workflowService.createTemplate({
                name: values.name,
                doc_type: values.doc_type,
                description: values.description,
                steps: values.steps || [
                    { name: '审核', step_type: 'review' as const },
                    { name: '批准', step_type: 'approve' as const },
                ],
            })
            message.success('模板创建成功')
            setTemplateModalOpen(false)
            form.resetFields()
            fetchTemplates()
        } catch {
            message.error('创建失败')
        }
    }

    const pendingColumns = [
        {
            title: '文档',
            dataIndex: 'document_id',
            render: (val: string) => (
                <a onClick={() => navigate(`/documents/${val}`)}>
                    {val.slice(0, 8)}...
                </a>
            ),
        },
        {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (val: string) => {
                const info = STATUS_MAP[val] || { label: val, color: 'default' }
                return <Tag color={info.color}>{info.label}</Tag>
            },
        },
        {
            title: '当前步骤',
            render: (_: unknown, record: WorkflowItem) => {
                const step = record.steps.find(
                    (s) => s.step_order === record.current_step_order,
                )
                return step ? step.name : '-'
            },
        },
        { title: '发起人', dataIndex: 'initiator_name' },
        {
            title: '发起时间',
            dataIndex: 'initiated_at',
            render: (val: string) => new Date(val).toLocaleString('zh-CN'),
        },
        {
            title: '操作',
            render: (_: unknown, record: WorkflowItem) => (
                <a onClick={() => navigate(`/documents/${record.document_id}`)}>
                    查看
                </a>
            ),
        },
    ]

    const templateColumns = [
        { title: '模板名称', dataIndex: 'name' },
        {
            title: '文档类型',
            dataIndex: 'doc_type',
            width: 100,
            render: (val: string) => <Tag>{val}</Tag>,
        },
        { title: '描述', dataIndex: 'description', ellipsis: true },
        {
            title: '步骤',
            dataIndex: 'steps',
            render: (steps: any[]) =>
                steps?.map((s) => s.name).join(' → ') || '-',
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            width: 80,
            render: (val: boolean) => (
                <Tag color={val ? 'green' : 'default'}>
                    {val ? '启用' : '停用'}
                </Tag>
            ),
        },
    ]

    return (
        <div>
            <Tabs
                defaultActiveKey="pending"
                items={[
                    {
                        key: 'pending',
                        label: `待我审批 (${pendingList.length})`,
                        children: (
                            <Table
                                rowKey="id"
                                columns={pendingColumns}
                                dataSource={pendingList}
                                loading={loading}
                                pagination={false}
                                locale={{ emptyText: '暂无待审批事项' }}
                            />
                        ),
                    },
                    {
                        key: 'templates',
                        label: '流程模板',
                        children: (
                            <div>
                                <Space style={{ marginBottom: 16 }}>
                                    {canManageWorkflows ? (
                                        <Button
                                            type="primary"
                                            icon={<PlusOutlined />}
                                            onClick={() =>
                                                setTemplateModalOpen(true)
                                            }>
                                            新建模板
                                        </Button>
                                    ) : null}
                                </Space>
                                <Table
                                    rowKey="id"
                                    columns={templateColumns}
                                    dataSource={templates}
                                    pagination={false}
                                />
                            </div>
                        ),
                    },
                ]}
            />

            <Modal
                title="新建审批模板"
                open={templateModalOpen}
                onCancel={() => {
                    setTemplateModalOpen(false)
                    form.resetFields()
                }}
                onOk={() => form.submit()}>
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleCreateTemplate}>
                    <Form.Item
                        name="name"
                        label="模板名称"
                        rules={[{ required: true }]}>
                        <Input placeholder="如：URS审批流程" />
                    </Form.Item>
                    <Form.Item
                        name="doc_type"
                        label="适用文档类型"
                        rules={[{ required: true }]}>
                        <Select
                            placeholder="选择文档类型"
                            options={docTypeOptions}
                        />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                    <Form.Item label="审批步骤">
                        <div style={{ color: '#666', fontSize: 12 }}>
                            默认: 审核 → 批准（两步流程）
                        </div>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
