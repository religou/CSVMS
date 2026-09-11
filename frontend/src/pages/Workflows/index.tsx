import { useState, useEffect } from 'react'
import { Table, Tag, Button, Modal, Form, Input, Select, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { workflowService, WorkflowTemplate } from '@/services/workflows'
import { useDictItems } from '@/hooks/useDictItems'
import { useProjectStore } from '@/stores/projectStore'

const STEP_NAME_MAP: Record<string, string> = {
    review: '审核',
    approve: '批准',
}

export default function WorkflowsPage() {
    const { options: docTypeOptions } = useDictItems('doc_type')
    const { options: projectRoleOptions } = useDictItems('project_role')
    const currentProject = useProjectStore((state) => state.currentProject)
    const canManageWorkflows =
        currentProject?.current_user_permissions.includes(
            'project.workflows.manage',
        ) ?? false
    const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
    const [templateModalOpen, setTemplateModalOpen] = useState(false)
    const [editingTemplate, setEditingTemplate] =
        useState<WorkflowTemplate | null>(null)
    const [form] = Form.useForm()

    useEffect(() => {
        fetchTemplates()
    }, [])

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
            review_role: template.steps?.find((s) => s.step_type === 'review')
                ?.project_role,
            approve_role: template.steps?.find((s) => s.step_type === 'approve')
                ?.project_role,
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
                await workflowService.updateTemplate(
                    editingTemplate.id,
                    payload,
                )
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

    const roleLabel = (code?: string) =>
        code
            ? (projectRoleOptions.find((opt) => opt.value === code)?.label ??
              code)
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
            {canManageWorkflows && (
                <div style={{ marginBottom: 16, textAlign: 'right' }}>
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openCreateTemplate}>
                        新建模板
                    </Button>
                </div>
            )}
            <Table
                rowKey="id"
                columns={templateColumns}
                dataSource={templates}
                pagination={false}
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
                        <Input disabled placeholder="根据文档类型自动生成" />
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
