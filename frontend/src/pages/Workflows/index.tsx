import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Table,
    Tag,
    Tabs,
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

const STEP_NAME_MAP: Record<string, string> = {
    review: '审核',
    approve: '批准',
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
    pending: { label: '待处理', color: 'default' },
    in_progress: { label: '进行中', color: 'processing' },
    approved: { label: '已批准', color: 'success' },
    rejected: { label: '已拒绝', color: 'error' },
    cancelled: { label: '已撤回', color: 'warning' },
}

export default function WorkflowsPage() {
    const { options: docTypeOptions } = useDictItems('doc_type')
    const { options: projectRoleOptions } = useDictItems('project_role')
    const navigate = useNavigate()
    const currentProject = useProjectStore((state) => state.currentProject)
    const canManageWorkflows =
        currentProject?.current_user_permissions.includes(
            'project.workflows.manage',
        ) ?? false
    const [activeTab, setActiveTab] = useState('pending')
    const [pendingList, setPendingList] = useState<WorkflowItem[]>([])
    const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
    const [loading, setLoading] = useState(false)
    const [templateModalOpen, setTemplateModalOpen] = useState(false)
    const [editingTemplate, setEditingTemplate] =
        useState<WorkflowTemplate | null>(null)
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

    const openCreateTemplate = () => {
        setEditingTemplate(null)
        form.resetFields()
        setTemplateModalOpen(true)
    }

    const openEditTemplate = (template: WorkflowTemplate) => {
        setEditingTemplate(template)
        form.setFieldsValue({
            doc_type: template.doc_type,
            name: template.name,
            review_role: template.steps?.find(
                (s) => s.step_type === 'review',
            )?.project_role,
            approve_role: template.steps?.find(
                (s) => s.step_type === 'approve',
            )?.project_role,
        })
        setTemplateModalOpen(true)
    }

    const closeTemplateModal = () => {
        setTemplateModalOpen(false)
        setEditingTemplate(null)
        form.resetFields()
    }

    const handleSubmitTemplate = async (values: any) => {
        const payload = {
            name: values.name,
            doc_type: values.doc_type,
            steps: [
                {
                    name: STEP_NAME_MAP.review,
                    step_type: 'review' as const,
                    project_role: values.review_role,
                },
                {
                    name: STEP_NAME_MAP.approve,
                    step_type: 'approve' as const,
                    project_role: values.approve_role,
                },
            ],
        }
        try {
            if (editingTemplate) {
                await workflowService.updateTemplate(editingTemplate.id, payload)
                message.success('模板更新成功')
            } else {
                await workflowService.createTemplate(payload)
                message.success('模板创建成功')
            }
            closeTemplateModal()
            fetchTemplates()
        } catch {
            message.error(editingTemplate ? '更新失败' : '创建失败')
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

    const roleLabel = (code?: string) =>
        code
            ? projectRoleOptions.find((opt) => opt.value === code)?.label ?? code
            : '-'

    const stepRole = (
        steps: WorkflowTemplate['steps'],
        stepType: 'review' | 'approve',
    ) => roleLabel(steps?.find((s) => s.step_type === stepType)?.project_role)

    const templateColumns = [
        {
            title: '适用文档类型',
            dataIndex: 'doc_type',
            width: 140,
            render: (val: string) => (
                <Tag>
                    {docTypeOptions.find((opt) => opt.value === val)?.label ??
                        val}
                </Tag>
            ),
        },
        { title: '模板名称', dataIndex: 'name' },
        {
            title: '审核',
            key: 'review_role',
            width: 120,
            render: (_: unknown, record: WorkflowTemplate) =>
                stepRole(record.steps, 'review'),
        },
        {
            title: '批准',
            key: 'approve_role',
            width: 120,
            render: (_: unknown, record: WorkflowTemplate) =>
                stepRole(record.steps, 'approve'),
        },
        ...(canManageWorkflows
            ? [
                  {
                      title: '操作',
                      key: 'action',
                      width: 80,
                      render: (_: unknown, record: WorkflowTemplate) => (
                          <a onClick={() => openEditTemplate(record)}>编辑</a>
                      ),
                  },
              ]
            : []),
    ]

    return (
        <div>
            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                tabBarExtraContent={
                    activeTab === 'templates' && canManageWorkflows ? (
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={openCreateTemplate}>
                            新建模板
                        </Button>
                    ) : null
                }
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
                            <Table
                                rowKey="id"
                                columns={templateColumns}
                                dataSource={templates}
                                pagination={false}
                            />
                        ),
                    },
                ]}
            />

            <Modal
                title={editingTemplate ? '编辑审批模板' : '新建审批模板'}
                open={templateModalOpen}
                onCancel={closeTemplateModal}
                onOk={() => form.submit()}>
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmitTemplate}>
                    <Form.Item
                        name="doc_type"
                        label="适用文档类型"
                        rules={[{ required: true }]}>
                        <Select
                            placeholder="选择文档类型"
                            options={docTypeOptions}
                            onChange={(val) => {
                                const label =
                                    docTypeOptions.find(
                                        (opt) => opt.value === val,
                                    )?.label ?? val
                                form.setFieldsValue({
                                    name: `${label}审批流程`,
                                })
                            }}
                        />
                    </Form.Item>
                    <Form.Item
                        name="name"
                        label="模板名称"
                        rules={[{ required: true }]}>
                        <Input
                            disabled
                            placeholder="根据文档类型自动生成"
                        />
                    </Form.Item>
                    <Form.Item
                        name="review_role"
                        label="审核"
                        rules={[{ required: true }]}>
                        <Select
                            placeholder="选择审核角色"
                            options={projectRoleOptions}
                        />
                    </Form.Item>
                    <Form.Item
                        name="approve_role"
                        label="批准"
                        rules={[{ required: true }]}>
                        <Select
                            placeholder="选择批准角色"
                            options={projectRoleOptions}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
