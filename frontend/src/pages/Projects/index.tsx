import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Tag, Modal, Form, Input, Select, message, Table } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import projectService, {
    type Project,
    type CreateProjectData,
} from '@/services/projects'
import { getErrorMessage } from '@/services/apiClient'
import { useDictItems } from '@/hooks/useDictItems'
import systemService, { type SystemItem } from '@/services/systems'
import { resolveStageDisplay } from '@/utils/stageDisplay'

export default function ProjectsPage() {
    const navigate = useNavigate()
    const { items: stageItems } = useDictItems('project_stage', {
        enabledOnly: false,
    })
    const [projects, setProjects] = useState<Project[]>([])
    const [loading, setLoading] = useState(false)
    const [modalOpen, setModalOpen] = useState(false)
    const [form] = Form.useForm<CreateProjectData>()
    const [creating, setCreating] = useState(false)
    const [keyword, setKeyword] = useState('')
    const [systems, setSystems] = useState<SystemItem[]>([])

    const fetchProjects = useCallback(async (kw?: string) => {
        setLoading(true)
        try {
            const params = kw ? { keyword: kw } : undefined
            const data = await projectService.list(params)
            setProjects(data)
        } catch (err) {
            message.error(getErrorMessage(err, '获取项目列表失败'))
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchProjects()
    }, [fetchProjects])

    useEffect(() => {
        systemService
            .list({ active_only: true, page_size: 100 })
            .then((data) => {
                setSystems(data.items)
            })
    }, [])

    const handleSearch = (value: string) => {
        setKeyword(value)
        fetchProjects(value.trim() || undefined)
    }

    const handleCreate = async () => {
        try {
            const values = await form.validateFields()
            setCreating(true)
            await projectService.create(values)
            message.success('项目创建成功')
            setModalOpen(false)
            form.resetFields()
            fetchProjects()
        } catch (err) {
            if (err && typeof err === 'object' && 'response' in err) {
                message.error(getErrorMessage(err, '创建失败'))
            }
        } finally {
            setCreating(false)
        }
    }

    const columns: ColumnsType<Project> = [
        {
            title: '项目编号',
            dataIndex: 'code',
            width: 160,
        },
        {
            title: '项目名称',
            dataIndex: 'name',
            ellipsis: true,
        },
        {
            title: '被验证系统',
            dataIndex: 'system_name',
            width: 200,
            ellipsis: true,
        },
        {
            title: '阶段',
            dataIndex: 'stage',
            width: 100,
            render: (stage: string | null) => {
                const display = resolveStageDisplay(stage, stageItems)
                return display.matched && display.color ? (
                    <Tag color={display.color}>{display.label}</Tag>
                ) : (
                    <Tag>{display.label}</Tag>
                )
            },
        },
        {
            title: '成员',
            dataIndex: 'member_count',
            width: 80,
            render: (count: number) => `${count} 人`,
        },
        {
            title: '更新时间',
            dataIndex: 'updated_at',
            width: 170,
            render: (val: string) =>
                val ? new Date(val).toLocaleString('zh-CN') : '-',
        },
    ]

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 16,
                }}>
                <h2 style={{ margin: 0 }}>验证项目</h2>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setModalOpen(true)}>
                    新建项目
                </Button>
            </div>

            <Input.Search
                placeholder="搜索项目名称、编号或系统"
                allowClear
                enterButton
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onSearch={handleSearch}
                style={{ marginBottom: 16, maxWidth: 400 }}
            />

            <Table<Project>
                columns={columns}
                dataSource={projects}
                rowKey="id"
                loading={loading}
                pagination={{
                    defaultPageSize: 20,
                    pageSizeOptions: ['20', '50', '100'],
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 个项目`,
                }}
                onRow={(record) => ({
                    onClick: () => navigate(`/projects/${record.id}`),
                    style: { cursor: 'pointer' },
                })}
            />

            <Modal
                title="新建验证项目"
                open={modalOpen}
                onOk={handleCreate}
                onCancel={() => setModalOpen(false)}
                confirmLoading={creating}
                okText="创建"
                cancelText="取消">
                <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                    <Form.Item
                        name="name"
                        label="项目名称"
                        rules={[{ required: true, message: '请输入项目名称' }]}>
                        <Input placeholder="如：XX系统验证" />
                    </Form.Item>
                    <Form.Item
                        name="system_id"
                        label="被验证系统"
                        rules={[
                            { required: true, message: '请选择被验证系统' },
                        ]}>
                        <Select
                            placeholder="选择被验证系统"
                            showSearch
                            optionFilterProp="label"
                            options={systems.map((s) => ({
                                value: s.id,
                                label: `${s.name} (${s.code})`,
                            }))}
                        />
                    </Form.Item>
                    <Form.Item name="description" label="项目描述">
                        <Input.TextArea rows={3} placeholder="可选" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
