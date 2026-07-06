import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Card,
    Descriptions,
    Tag,
    Button,
    Space,
    Input,
    Form,
    message,
    Spin,
    Timeline,
    Modal,
    Tabs,
    Row,
    Col,
    Anchor,
} from 'antd'
import {
    EditOutlined,
    SaveOutlined,
    SendOutlined,
    RollbackOutlined,
    ArrowLeftOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSlug from 'rehype-slug'
import GithubSlugger from 'github-slugger'
import RichTextEditor from '@/components/RichTextEditor'
import { documentService, DocumentDetail } from '@/services/documents'
import { workflowService, WorkflowItem } from '@/services/workflows'
import { useDictItems } from '@/hooks/useDictItems'
import { useProjectStore } from '@/stores/projectStore'

interface HeadingItem {
    id: string
    text: string
    level: number
}

function extractHeadings(markdown: string): HeadingItem[] {
    const slugger = new GithubSlugger()
    const headings: HeadingItem[] = []
    const lines = markdown.split('\n')
    for (const line of lines) {
        const match = /^(#{1,6})\s+(.+?)\s*$/.exec(line)
        if (match && match[1] && match[2]) {
            const level = match[1].length
            const text = match[2].trim()
            headings.push({ id: slugger.slug(text), text, level })
        }
    }
    return headings
}

export default function DocumentDetailPage() {
    const { id, projectId } = useParams<{ id: string; projectId: string }>()
    const navigate = useNavigate()
    const { items: statusDictItems } = useDictItems('doc_status')
    const currentProject = useProjectStore((state) => state.currentProject)
    const [doc, setDoc] = useState<DocumentDetail | null>(null)
    const [workflow, setWorkflow] = useState<WorkflowItem | null>(null)
    const [loading, setLoading] = useState(true)
    const [editing, setEditing] = useState(false)
    const [saving, setSaving] = useState(false)
    const [form] = Form.useForm()

    const fetchData = async () => {
        if (!id) return
        setLoading(true)
        try {
            const [docRes, wfRes] = await Promise.all([
                documentService.get(id),
                workflowService.getByDocument(id),
            ])
            setDoc(docRes.data)
            setWorkflow(wfRes.data)
            form.setFieldsValue({
                title: docRes.data.title,
                content: docRes.data.content || '',
                summary: docRes.data.summary || '',
            })
        } catch {
            message.error('加载文档失败')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
    }, [id])

    const handleSave = async () => {
        if (!id || !doc) return
        setSaving(true)
        try {
            const values = form.getFieldsValue()
            await documentService.update(id, values)
            message.success('保存成功')
            setEditing(false)
            fetchData()
        } catch {
            message.error('保存失败')
        } finally {
            setSaving(false)
        }
    }

    const handleSubmit = async () => {
        if (!id) return
        Modal.confirm({
            title: '提交审批',
            content: '提交后文档将进入审核流程，确认提交？',
            onOk: async () => {
                try {
                    await workflowService.submit(id)
                    message.success('已提交审批')
                    fetchData()
                } catch (err: any) {
                    message.error(err?.response?.data?.detail || '提交失败')
                }
            },
        })
    }

    const handleApprove = async () => {
        if (!workflow) return
        try {
            await workflowService.approve(workflow.id, '同意')
            message.success('审批通过')
            fetchData()
        } catch (err: any) {
            message.error(err?.response?.data?.detail || '操作失败')
        }
    }

    const handleReject = () => {
        if (!workflow) return
        Modal.confirm({
            title: '拒绝审批',
            content: (
                <Input.TextArea
                    id="reject-reason"
                    placeholder="请输入拒绝原因"
                    rows={3}
                />
            ),
            onOk: async () => {
                const reason =
                    (
                        document.getElementById(
                            'reject-reason',
                        ) as HTMLTextAreaElement
                    )?.value || '不通过'
                await workflowService.reject(workflow.id, reason)
                message.success('已拒绝')
                fetchData()
            },
        })
    }

    const handleWithdraw = async () => {
        if (!workflow) return
        Modal.confirm({
            title: '撤回审批',
            content: '撤回后文档将回到草稿状态',
            onOk: async () => {
                await workflowService.withdraw(workflow.id)
                message.success('已撤回')
                fetchData()
            },
        })
    }

    const headings = useMemo(
        () => extractHeadings(doc?.content || ''),
        [doc?.content],
    )

    if (loading)
        return (
            <Spin
                size="large"
                style={{ display: 'block', margin: '100px auto' }}
            />
        )
    if (!doc) return <div>文档不存在</div>

    const isDraft = doc.status === 'draft'
    const isUnderReview = doc.status === 'under_review'
    const canManageDocuments =
        currentProject?.current_user_permissions.includes(
            'project.documents.manage',
        ) ?? false
    const canManageWorkflows =
        currentProject?.current_user_permissions.includes(
            'project.workflows.manage',
        ) ?? false
    const statusDictItem = statusDictItems.find((s) => s.code === doc.status)
    const statusInfo = {
        label: statusDictItem?.label || doc.status,
        color: statusDictItem?.extra || 'default',
    }

    return (
        <div>
            <Space style={{ marginBottom: 16 }}>
                <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() =>
                        navigate(`/projects/${projectId}/documents`)
                    }>
                    返回列表
                </Button>
            </Space>

            <Card
                title={
                    <Space>
                        <Tag>{doc.doc_type}</Tag>
                        <span>{doc.doc_number}</span>
                        <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
                    </Space>
                }
                extra={
                    <Space>
                        {isDraft && !editing && canManageDocuments && (
                            <Button
                                icon={<EditOutlined />}
                                onClick={() => setEditing(true)}>
                                编辑
                            </Button>
                        )}
                        {editing && canManageDocuments && (
                            <>
                                <Button
                                    icon={<SaveOutlined />}
                                    type="primary"
                                    loading={saving}
                                    onClick={handleSave}>
                                    保存
                                </Button>
                                <Button onClick={() => setEditing(false)}>
                                    取消
                                </Button>
                            </>
                        )}
                        {isDraft && !editing && canManageDocuments && (
                            <Button
                                type="primary"
                                icon={<SendOutlined />}
                                onClick={handleSubmit}>
                                提交审批
                            </Button>
                        )}
                        {isUnderReview &&
                            canManageWorkflows &&
                            workflow &&
                            workflow.status === 'in_progress' && (
                                <>
                                    <Button
                                        type="primary"
                                        onClick={handleApprove}>
                                        通过
                                    </Button>
                                    <Button danger onClick={handleReject}>
                                        拒绝
                                    </Button>
                                    <Button
                                        icon={<RollbackOutlined />}
                                        onClick={handleWithdraw}>
                                        撤回
                                    </Button>
                                </>
                            )}
                    </Space>
                }>
                <Tabs
                    items={[
                        {
                            key: 'content',
                            label: '文档内容',
                            children: editing ? (
                                <Form form={form} layout="vertical">
                                    <Form.Item name="title" label="标题">
                                        <Input />
                                    </Form.Item>
                                    <Form.Item name="summary" label="摘要">
                                        <Input.TextArea rows={2} />
                                    </Form.Item>
                                    <Form.Item name="content" label="正文内容">
                                        <RichTextEditor />
                                    </Form.Item>
                                </Form>
                            ) : (
                                <div>
                                    <Descriptions
                                        column={2}
                                        bordered
                                        size="small"
                                        style={{ marginBottom: 16 }}>
                                        <Descriptions.Item label="标题">
                                            {doc.title}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="版本">
                                            {doc.version}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="作者">
                                            {doc.author_name}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="创建时间">
                                            {new Date(
                                                doc.created_at,
                                            ).toLocaleString('zh-CN')}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="更新时间">
                                            {new Date(
                                                doc.updated_at,
                                            ).toLocaleString('zh-CN')}
                                        </Descriptions.Item>
                                        {doc.summary && (
                                            <Descriptions.Item
                                                label="摘要"
                                                span={2}>
                                                {doc.summary}
                                            </Descriptions.Item>
                                        )}
                                    </Descriptions>
                                    <Row gutter={16}>
                                        {headings.length > 0 && (
                                            <Col
                                                span={5}
                                                style={{
                                                    maxHeight: 600,
                                                    overflow: 'auto',
                                                }}>
                                                <Card
                                                    type="inner"
                                                    title="目录"
                                                    size="small">
                                                    <Anchor
                                                        affix={false}
                                                        items={headings.map(
                                                            (h) => ({
                                                                key: h.id,
                                                                href: `#${h.id}`,
                                                                title: h.text,
                                                                style: {
                                                                    paddingLeft:
                                                                        (h.level -
                                                                            1) *
                                                                        12,
                                                                },
                                                            }),
                                                        )}
                                                    />
                                                </Card>
                                            </Col>
                                        )}
                                        <Col span={headings.length > 0 ? 19 : 24}>
                                            <Card
                                                type="inner"
                                                title="正文"
                                                style={{ minHeight: 200 }}>
                                                {doc.content ? (
                                                    <div className="markdown-body">
                                                        <ReactMarkdown
                                                            remarkPlugins={[
                                                                remarkGfm,
                                                            ]}
                                                            rehypePlugins={[
                                                                rehypeSlug,
                                                            ]}>
                                                            {doc.content}
                                                        </ReactMarkdown>
                                                    </div>
                                                ) : (
                                                    <span
                                                        style={{
                                                            color: '#999',
                                                        }}>
                                                        暂无内容
                                                    </span>
                                                )}
                                            </Card>
                                        </Col>
                                    </Row>
                                </div>
                            ),
                        },
                        {
                            key: 'workflow',
                            label: '审批流程',
                            children: workflow ? (
                                <Timeline
                                    items={workflow.steps.map((step) => ({
                                        color:
                                            step.status === 'approved'
                                                ? 'green'
                                                : step.status === 'rejected'
                                                  ? 'red'
                                                  : step.status ===
                                                      'in_progress'
                                                    ? 'blue'
                                                    : 'gray',
                                        children: (
                                            <div>
                                                <strong>{step.name}</strong>
                                                <span style={{ marginLeft: 8 }}>
                                                    <Tag
                                                        color={
                                                            step.status ===
                                                            'approved'
                                                                ? 'green'
                                                                : step.status ===
                                                                    'rejected'
                                                                  ? 'red'
                                                                  : step.status ===
                                                                      'in_progress'
                                                                    ? 'blue'
                                                                    : 'default'
                                                        }>
                                                        {step.status ===
                                                        'approved'
                                                            ? '已通过'
                                                            : step.status ===
                                                                'rejected'
                                                              ? '已拒绝'
                                                              : step.status ===
                                                                  'in_progress'
                                                                ? '进行中'
                                                                : '待处理'}
                                                    </Tag>
                                                </span>
                                                {step.actor_name && (
                                                    <div
                                                        style={{
                                                            fontSize: 12,
                                                            color: '#666',
                                                        }}>
                                                        操作人:{' '}
                                                        {step.actor_name} |{' '}
                                                        {step.acted_at
                                                            ? new Date(
                                                                  step.acted_at,
                                                              ).toLocaleString(
                                                                  'zh-CN',
                                                              )
                                                            : ''}
                                                    </div>
                                                )}
                                                {step.comment && (
                                                    <div
                                                        style={{
                                                            fontSize: 12,
                                                            color: '#888',
                                                        }}>
                                                        意见: {step.comment}
                                                    </div>
                                                )}
                                            </div>
                                        ),
                                    }))}
                                />
                            ) : (
                                <div style={{ color: '#999' }}>
                                    尚未进入审批流程
                                </div>
                            ),
                        },
                        {
                            key: 'versions',
                            label: '版本历史',
                            children:
                                doc.versions && doc.versions.length > 0 ? (
                                    <Timeline
                                        items={doc.versions.map((v) => ({
                                            children: (
                                                <div>
                                                    <strong>
                                                        v{v.version_label}
                                                    </strong>
                                                    <span
                                                        style={{
                                                            marginLeft: 8,
                                                            color: '#666',
                                                            fontSize: 12,
                                                        }}>
                                                        {new Date(
                                                            v.created_at,
                                                        ).toLocaleString(
                                                            'zh-CN',
                                                        )}
                                                    </span>
                                                    {v.change_reason && (
                                                        <div
                                                            style={{
                                                                fontSize: 12,
                                                                color: '#888',
                                                            }}>
                                                            {v.change_reason}
                                                        </div>
                                                    )}
                                                </div>
                                            ),
                                        }))}
                                    />
                                ) : (
                                    <div style={{ color: '#999' }}>
                                        暂无版本历史
                                    </div>
                                ),
                        },
                    ]}
                />
            </Card>
        </div>
    )
}
