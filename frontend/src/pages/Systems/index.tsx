import { useEffect, useState, useCallback } from 'react'
import {
    Card,
    Table,
    Button,
    Modal,
    Form,
    Input,
    Select,
    Switch,
    Space,
    Tag,
    Row,
    Col,
    message,
} from 'antd'
import {
    PlusOutlined,
    DeleteOutlined,
    EditOutlined,
    SearchOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import systemService, {
    type SystemItem,
    type CreateSystemData,
    type UpdateSystemData,
} from '@/services/systems'
import { getErrorMessage } from '@/services/apiClient'
import { useAuthStore } from '@/stores/authStore'
import { adminService, type UserItem } from '@/services/admin'

const GXP_CATEGORY_OPTIONS = [
    { value: 'GMP', label: 'GMP（良好生产规范）' },
    { value: 'GLP', label: 'GLP（良好实验室规范）' },
    { value: 'GCP', label: 'GCP（良好临床规范）' },
    { value: 'GDP', label: 'GDP（良好分销规范）' },
    { value: 'GVP', label: 'GVP（良好药物警戒规范）' },
]

const GAMP5_CATEGORY_OPTIONS = [
    { value: 'category_1', label: 'Category 1：基础设施软件' },
    { value: 'category_3', label: 'Category 3：非配置型产品' },
    { value: 'category_4', label: 'Category 4：配置型产品' },
    { value: 'category_5', label: 'Category 5：定制应用软件' },
]

export default function SystemsPage() {
    const [systems, setSystems] = useState<SystemItem[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [search, setSearch] = useState('')
    const [modalOpen, setModalOpen] = useState(false)
    const [editingSystem, setEditingSystem] = useState<SystemItem | null>(null)
    const [users, setUsers] = useState<UserItem[]>([])
    const [form] = Form.useForm()
    const currentUser = useAuthStore((state) => state.user)
    const isAdmin = currentUser?.roles?.includes('admin') ?? false

    const fetchSystems = useCallback(async () => {
        setLoading(true)
        try {
            const data = await systemService.list({
                page,
                page_size: pageSize,
                search: search || undefined,
            })
            setSystems(data.items)
            setTotal(data.total)
        } catch (err) {
            message.error(getErrorMessage(err, '获取系统列表失败'))
        } finally {
            setLoading(false)
        }
    }, [page, pageSize, search])

    useEffect(() => {
        fetchSystems()
    }, [fetchSystems])

    const fetchUsers = useCallback(async () => {
        try {
            const res = await adminService.listUsers(1, 100)
            setUsers(Array.isArray(res.data) ? res.data : [])
        } catch {
            // 非管理员可能无权限，静默处理
        }
    }, [])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    const handleSearch = (value: string) => {
        setSearch(value)
        setPage(1)
    }

    const openModal = (system?: SystemItem) => {
        setEditingSystem(system ?? null)
        if (system) {
            form.setFieldsValue(system)
        } else {
            form.resetFields()
        }
        setModalOpen(true)
    }

    const handleSave = async () => {
        try {
            const values = await form.validateFields()
            if (editingSystem) {
                const updateData: UpdateSystemData = { ...values }
                delete (updateData as Record<string, unknown>).code
                await systemService.update(editingSystem.id, updateData)
                message.success('系统更新成功')
            } else {
                await systemService.create(values as CreateSystemData)
                message.success('系统创建成功')
            }
            setModalOpen(false)
            setEditingSystem(null)
            form.resetFields()
            fetchSystems()
        } catch (err) {
            if (err && typeof err === 'object' && 'response' in err) {
                message.error(
                    getErrorMessage(
                        err,
                        editingSystem ? '更新失败' : '创建失败',
                    ),
                )
            }
        }
    }

    const handleDelete = (system: SystemItem) => {
        Modal.confirm({
            title: '确认删除',
            content: `确定删除系统「${system.name}」？有关联项目的系统无法删除。`,
            onOk: async () => {
                try {
                    await systemService.delete(system.id)
                    message.success('已删除')
                    fetchSystems()
                } catch (err) {
                    message.error(getErrorMessage(err, '删除失败'))
                }
            },
        })
    }

    const handleToggleActive = async (system: SystemItem) => {
        try {
            await systemService.update(system.id, {
                is_active: !system.is_active,
            })
            fetchSystems()
        } catch (err) {
            message.error(getErrorMessage(err, '操作失败'))
        }
    }

    const columns: ColumnsType<SystemItem> = [
        { title: '系统编号', dataIndex: 'code', width: 120 },
        { title: '系统名称', dataIndex: 'name', width: 180, ellipsis: true },
        { title: '供应商', dataIndex: 'vendor', width: 160, ellipsis: true },
        { title: '版本号', dataIndex: 'version', width: 100 },
        {
            title: 'GxP 类别',
            dataIndex: 'gxp_category',
            width: 130,
            render: (val: string | null) => {
                const opt = GXP_CATEGORY_OPTIONS.find((o) => o.value === val)
                return opt ? <Tag>{val}</Tag> : '-'
            },
        },
        {
            title: 'GAMP5 类别',
            dataIndex: 'gamp5_category',
            width: 160,
            render: (val: string | null) => {
                const opt = GAMP5_CATEGORY_OPTIONS.find((o) => o.value === val)
                return opt ? <Tag color="blue">{opt.label}</Tag> : '-'
            },
        },
        {
            title: '负责人',
            dataIndex: 'owner_name',
            width: 100,
            render: (val: string | null) => val || '-',
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            width: 80,
            render: (val: boolean, record: SystemItem) => (
                <Switch
                    size="small"
                    checked={val}
                    onChange={() => handleToggleActive(record)}
                    disabled={!isAdmin}
                />
            ),
        },
        ...(isAdmin
            ? [
                  {
                      title: '操作',
                      width: 100,
                      render: (_: unknown, record: SystemItem) => (
                          <Space size="small">
                              <Button
                                  size="small"
                                  type="link"
                                  icon={<EditOutlined />}
                                  onClick={() => openModal(record)}
                              />
                              <Button
                                  size="small"
                                  type="link"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={() => handleDelete(record)}
                              />
                          </Space>
                      ),
                  },
              ]
            : []),
    ]

    return (
        <div style={{ padding: 24 }}>
            <Card
                title="系统管理"
                extra={
                    <Space>
                        <Input.Search
                            placeholder="搜索系统名称或编号"
                            allowClear
                            onSearch={handleSearch}
                            style={{ width: 240 }}
                            prefix={<SearchOutlined />}
                        />
                        {isAdmin && (
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={() => openModal()}>
                                新增系统
                            </Button>
                        )}
                    </Space>
                }>
                <Table
                    columns={columns}
                    dataSource={systems}
                    rowKey="id"
                    loading={loading}
                    size="small"
                    pagination={{
                        current: page,
                        pageSize,
                        total,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        pageSizeOptions: ['20', '50', '100'],
                        showTotal: (t) => `共 ${t} 条`,
                        onChange: (p, ps) => {
                            setPage(p)
                            setPageSize(ps)
                        },
                    }}
                />
            </Card>

            <Modal
                title={editingSystem ? '编辑系统' : '新增系统'}
                open={modalOpen}
                onOk={handleSave}
                onCancel={() => {
                    setModalOpen(false)
                    setEditingSystem(null)
                    form.resetFields()
                }}
                okText="保存"
                cancelText="取消"
                width={560}>
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="code"
                        label="系统编号"
                        rules={[{ required: true, message: '请输入系统编号' }]}>
                        <Input
                            placeholder="如：ERP-001"
                            disabled={!!editingSystem}
                        />
                    </Form.Item>
                    <Form.Item
                        name="name"
                        label="系统名称"
                        rules={[{ required: true, message: '请输入系统名称' }]}>
                        <Input placeholder="如：SAP ERP 系统" />
                    </Form.Item>
                    <Form.Item name="vendor" label="供应商">
                        <Input placeholder="如：SAP" />
                    </Form.Item>
                    <Form.Item name="version" label="版本号">
                        <Input placeholder="如：v4.2.1" />
                    </Form.Item>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name="gxp_category" label="GxP 类别">
                                <Select
                                    placeholder="选择 GxP 类别"
                                    options={GXP_CATEGORY_OPTIONS}
                                    allowClear
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="gamp5_category" label="GAMP5 类别">
                                <Select
                                    placeholder="选择 GAMP5 软件类别"
                                    options={GAMP5_CATEGORY_OPTIONS}
                                    allowClear
                                />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name="description" label="系统描述">
                        <Input.TextArea rows={3} />
                    </Form.Item>
                    <Form.Item name="owner_id" label="系统负责人">
                        <Select
                            placeholder="选择负责人"
                            showSearch
                            optionFilterProp="label"
                            allowClear
                            options={users.map((u) => ({
                                value: u.id,
                                label: `${u.full_name} (${u.username})`,
                            }))}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
