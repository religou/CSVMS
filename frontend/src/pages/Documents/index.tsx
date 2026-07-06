import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
    Table,
    Button,
    Space,
    Tag,
    Input,
    Select,
    Card,
    Modal,
    Form,
    message,
    Row,
    Col,
} from 'antd'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { documentService, DocumentItem } from '@/services/documents'
import { useDictItems } from '@/hooks/useDictItems'
import { useProjectStore } from '@/stores/projectStore'

export default function DocumentsPage() {
    const navigate = useNavigate()
    const { projectId } = useParams<{ projectId: string }>()
    const currentProject = useProjectStore((s) => s.currentProject)
    const canManageDocuments =
        currentProject?.current_user_permissions.includes(
            'project.documents.manage',
        ) ?? false
    const { options: docTypeOptions } = useDictItems('doc_type')
    const { items: statusItems } = useDictItems('doc_status')
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<DocumentItem[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [filters, setFilters] = useState<{
        doc_type?: string
        status?: string
        keyword?: string
    }>({})
    const [createModalOpen, setCreateModalOpen] = useState(false)
    const [form] = Form.useForm()

    const fetchDocuments = useCallback(async () => {
        setLoading(true)
        try {
            const res = await documentService.list({
                ...filters,
                project_id: projectId,
                page,
                page_size: pageSize,
            })
            setData(res.data.items)
            setTotal(res.data.total)
        } catch {
            message.error('加载文档列表失败')
        } finally {
            setLoading(false)
        }
    }, [filters, page, pageSize, projectId])

    useEffect(() => {
        fetchDocuments()
    }, [fetchDocuments])

    const handleCreate = async (values: {
        title: string
        doc_type: string
        summary?: string
    }) => {
        try {
            const res = await documentService.create({
                ...values,
                project_id: projectId,
            })
            message.success('文档创建成功')
            setCreateModalOpen(false)
            form.resetFields()
            navigate(`/projects/${projectId}/documents/${res.data.id}`)
        } catch {
            message.error('创建失败')
        }
    }

    const handleDelete = (id: string) => {
        Modal.confirm({
            title: '确认删除',
            content: '删除后不可恢复，确认删除此文档？',
            onOk: async () => {
                await documentService.delete(id)
                message.success('已删除')
                fetchDocuments()
            },
        })
    }

    const getStatusTag = (status: string) => {
        const opt = statusItems.find((s) => s.code === status)
        return <Tag color={opt?.extra || 'default'}>{opt?.label || status}</Tag>
    }

    const columns = [
        {
            title: '文档编号',
            dataIndex: 'doc_number',
            width: 160,
            render: (text: string, record: DocumentItem) => (
                <a
                    onClick={() =>
                        navigate(
                            `/projects/${projectId}/documents/${record.id}`,
                        )
                    }>
                    {text}
                </a>
            ),
        },
        { title: '标题', dataIndex: 'title', ellipsis: true },
        {
            title: '类型',
            dataIndex: 'doc_type',
            width: 80,
            render: (val: string) => <Tag>{val}</Tag>,
        },
        {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (val: string) => getStatusTag(val),
        },
        { title: '版本', dataIndex: 'version', width: 70 },
        { title: '作者', dataIndex: 'author_name', width: 100 },
        {
            title: '更新时间',
            dataIndex: 'updated_at',
            width: 170,
            render: (val: string) =>
                val ? new Date(val).toLocaleString('zh-CN') : '-',
        },
        {
            title: '操作',
            width: 120,
            render: (_: unknown, record: DocumentItem) => (
                <Space size="small">
                    <a
                        onClick={() =>
                            navigate(
                                `/projects/${projectId}/documents/${record.id}`,
                            )
                        }>
                        查看
                    </a>
                    {canManageDocuments && record.status === 'draft' && (
                        <a
                            style={{ color: '#ff4d4f' }}
                            onClick={() => handleDelete(record.id)}>
                            删除
                        </a>
                    )}
                </Space>
            ),
        },
    ]

    return (
        <div>
            <Card style={{ marginBottom: 16 }}>
                <Row gutter={16} align="middle">
                    <Col>
                        <Select
                            placeholder="文档类型"
                            allowClear
                            style={{ width: 120 }}
                            options={docTypeOptions}
                            onChange={(val) =>
                                setFilters((f) => ({ ...f, doc_type: val }))
                            }
                        />
                    </Col>
                    <Col>
                        <Select
                            placeholder="状态"
                            allowClear
                            style={{ width: 120 }}
                            options={statusItems.map((s) => ({
                                value: s.code,
                                label: s.label,
                            }))}
                            onChange={(val) =>
                                setFilters((f) => ({ ...f, status: val }))
                            }
                        />
                    </Col>
                    <Col>
                        <Input
                            placeholder="搜索标题/编号"
                            prefix={<SearchOutlined />}
                            allowClear
                            style={{ width: 200 }}
                            onPressEnter={(e) =>
                                setFilters((f) => ({
                                    ...f,
                                    keyword: (e.target as HTMLInputElement)
                                        .value,
                                }))
                            }
                        />
                    </Col>
                    <Col>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={fetchDocuments}>
                            刷新
                        </Button>
                    </Col>
                    <Col flex="auto" style={{ textAlign: 'right' }}>
                        {canManageDocuments && (
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={() => setCreateModalOpen(true)}>
                                新建文档
                            </Button>
                        )}
                    </Col>
                </Row>
            </Card>

            <Table
                rowKey="id"
                columns={columns}
                dataSource={data}
                loading={loading}
                pagination={{
                    current: page,
                    pageSize,
                    total,
                    showSizeChanger: true,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: (p, ps) => {
                        setPage(p)
                        setPageSize(ps)
                    },
                }}
            />

            <Modal
                title="新建文档"
                open={createModalOpen}
                onCancel={() => {
                    setCreateModalOpen(false)
                    form.resetFields()
                }}
                onOk={() => form.submit()}>
                <Form form={form} layout="vertical" onFinish={handleCreate}>
                    <Form.Item
                        name="doc_type"
                        label="文档类型"
                        rules={[{ required: true, message: '请选择类型' }]}>
                        <Select
                            placeholder="选择文档类型"
                            options={docTypeOptions}
                        />
                    </Form.Item>
                    <Form.Item
                        name="title"
                        label="文档标题"
                        rules={[{ required: true, message: '请输入标题' }]}>
                        <Input placeholder="输入文档标题" />
                    </Form.Item>
                    <Form.Item name="summary" label="摘要">
                        <Input.TextArea rows={3} placeholder="文档简要说明" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
