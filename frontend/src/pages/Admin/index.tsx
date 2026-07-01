import { useEffect, useState } from 'react'
import {
    Table,
    Button,
    Tag,
    Space,
    Modal,
    Form,
    Input,
    Switch,
    Select,
    message,
    Card,
    Popconfirm,
} from 'antd'
import {
    PlusOutlined,
    UnlockOutlined,
    EditOutlined,
    DeleteOutlined,
    KeyOutlined,
    TeamOutlined,
} from '@ant-design/icons'
import { adminService, RoleItem, UserItem } from '@/services/admin'
import { useAuthStore } from '@/stores/authStore'

export default function AdminPage() {
    const [users, setUsers] = useState<UserItem[]>([])
    const [roles, setRoles] = useState<RoleItem[]>([])
    const [loading, setLoading] = useState(false)
    const [createModalOpen, setCreateModalOpen] = useState(false)
    const [editModalOpen, setEditModalOpen] = useState(false)
    const [rolesModalOpen, setRolesModalOpen] = useState(false)
    const [resetPwdModalOpen, setResetPwdModalOpen] = useState(false)
    const [editingUser, setEditingUser] = useState<UserItem | null>(null)
    const [form] = Form.useForm()
    const [editForm] = Form.useForm()
    const [rolesForm] = Form.useForm()
    const [resetPwdForm] = Form.useForm()

    const currentUser = useAuthStore((s) => s.user)
    const canManageUsers =
        currentUser?.permissions?.includes('system.admin.users.manage') ?? false
    const roleOptions = roles.map((role) => ({
        label: role.display_name,
        value: role.name,
    }))

    const fetchUsers = async () => {
        setLoading(true)
        try {
            const { data } = await adminService.listUsers()
            setUsers(data)
        } catch {
            message.error('获取用户列表失败')
        } finally {
            setLoading(false)
        }
    }

    const fetchRoles = async () => {
        try {
            const { data } = await adminService.listRoles()
            setRoles(data)
        } catch {
            message.error('获取角色列表失败')
        }
    }

    useEffect(() => {
        fetchUsers()
        if (canManageUsers) {
            fetchRoles()
        }
    }, [canManageUsers])

    const handleCreate = async (values: {
        username: string
        email: string
        full_name: string
        password: string
        role_codes?: string[]
    }) => {
        try {
            await adminService.createUser({
                ...values,
                role_codes: values.role_codes ?? [],
            })
            message.success('用户创建成功')
            setCreateModalOpen(false)
            form.resetFields()
            fetchUsers()
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '创建失败')
        }
    }

    const handleToggleActive = async (user: UserItem) => {
        try {
            await adminService.updateUser(user.id, {
                is_active: !user.is_active,
            })
            message.success('状态更新成功')
            fetchUsers()
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '更新失败')
        }
    }

    const handleUnlock = async (userId: string) => {
        try {
            await adminService.unlockUser(userId)
            message.success('用户已解锁')
            fetchUsers()
        } catch {
            message.error('解锁失败')
        }
    }

    const openEditModal = (user: UserItem) => {
        setEditingUser(user)
        editForm.setFieldsValue({
            email: user.email,
            full_name: user.full_name,
        })
        setEditModalOpen(true)
    }

    const handleEdit = async (values: { email: string; full_name: string }) => {
        if (!editingUser) return
        try {
            await adminService.updateUser(editingUser.id, values)
            message.success('用户信息已更新')
            setEditModalOpen(false)
            setEditingUser(null)
            fetchUsers()
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '更新失败')
        }
    }

    const openRolesModal = (user: UserItem) => {
        setEditingUser(user)
        rolesForm.setFieldsValue({
            role_codes: user.roles.map((r) => r.name),
        })
        setRolesModalOpen(true)
    }

    const handleAssignRoles = async (values: { role_codes: string[] }) => {
        if (!editingUser) return
        try {
            await adminService.assignRoles(editingUser.id, values.role_codes)
            message.success('角色分配成功')
            setRolesModalOpen(false)
            setEditingUser(null)
            fetchUsers()
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '角色分配失败')
        }
    }

    const openResetPwdModal = (user: UserItem) => {
        setEditingUser(user)
        resetPwdForm.resetFields()
        setResetPwdModalOpen(true)
    }

    const handleResetPassword = async (values: { new_password: string }) => {
        if (!editingUser) return
        try {
            await adminService.resetPassword(
                editingUser.id,
                values.new_password,
            )
            message.success('密码已重置')
            setResetPwdModalOpen(false)
            setEditingUser(null)
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '密码重置失败')
        }
    }

    const handleDelete = async (userId: string) => {
        try {
            await adminService.deleteUser(userId)
            message.success('用户已删除')
            fetchUsers()
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } }
            message.error(error.response?.data?.detail || '删除失败')
        }
    }

    const isSelf = (user: UserItem) => currentUser?.id === user.id

    const columns = [
        { title: '用户名', dataIndex: 'username', key: 'username' },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
        { title: '邮箱', dataIndex: 'email', key: 'email' },
        {
            title: '角色',
            dataIndex: 'roles',
            key: 'roles',
            render: (roles: UserItem['roles']) =>
                roles.map((r) => <Tag key={r.id}>{r.display_name}</Tag>),
        },
        {
            title: '状态',
            key: 'status',
            render: (_: unknown, record: UserItem) => (
                <Space>
                    <Switch
                        checked={record.is_active}
                        onChange={() => handleToggleActive(record)}
                        checkedChildren="启用"
                        unCheckedChildren="禁用"
                        disabled={!canManageUsers || isSelf(record)}
                    />
                    {record.is_locked && <Tag color="red">锁定</Tag>}
                </Space>
            ),
        },
        ...(canManageUsers
            ? [
                  {
                      title: '操作',
                      key: 'actions',
                      render: (_: unknown, record: UserItem) => (
                          <Space>
                              <Button
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={() => openEditModal(record)}>
                                  编辑
                              </Button>
                              <Button
                                  size="small"
                                  icon={<TeamOutlined />}
                                  onClick={() => openRolesModal(record)}>
                                  角色
                              </Button>
                              <Button
                                  size="small"
                                  icon={<KeyOutlined />}
                                  onClick={() => openResetPwdModal(record)}>
                                  重置密码
                              </Button>
                              {record.is_locked && (
                                  <Button
                                      size="small"
                                      icon={<UnlockOutlined />}
                                      onClick={() => handleUnlock(record.id)}>
                                      解锁
                                  </Button>
                              )}
                              {!isSelf(record) && (
                                  <Popconfirm
                                      title="确认删除"
                                      description={`确定要删除用户「${record.username}」吗？此操作不可恢复。`}
                                      onConfirm={() => handleDelete(record.id)}
                                      okText="删除"
                                      cancelText="取消"
                                      okButtonProps={{ danger: true }}>
                                      <Button
                                          size="small"
                                          danger
                                          icon={<DeleteOutlined />}>
                                          删除
                                      </Button>
                                  </Popconfirm>
                              )}
                          </Space>
                      ),
                  },
              ]
            : []),
    ]

    return (
        <Card
            title="用户管理"
            extra={
                canManageUsers ? (
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setCreateModalOpen(true)}>
                        新建用户
                    </Button>
                ) : null
            }>
            <Table
                dataSource={users}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={{
                    defaultPageSize: 20,
                    pageSizeOptions: ['20', '50', '100'],
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条`,
                }}
            />

            {/* 新建用户弹窗 */}
            <Modal
                title="新建用户"
                open={createModalOpen}
                onCancel={() => setCreateModalOpen(false)}
                onOk={() => form.submit()}>
                <Form form={form} layout="vertical" onFinish={handleCreate}>
                    <Form.Item
                        name="username"
                        label="用户名"
                        rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="email"
                        label="邮箱"
                        rules={[{ required: true }, { type: 'email' }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="full_name"
                        label="姓名"
                        rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="password"
                        label="密码"
                        rules={[{ required: true }, { min: 8 }]}>
                        <Input.Password />
                    </Form.Item>
                    <Form.Item name="role_codes" label="角色">
                        <Select
                            mode="multiple"
                            placeholder="可选，后续再分配"
                            options={roleOptions}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 编辑用户弹窗 */}
            <Modal
                title={`编辑用户 - ${editingUser?.username}`}
                open={editModalOpen}
                onCancel={() => {
                    setEditModalOpen(false)
                    setEditingUser(null)
                }}
                onOk={() => editForm.submit()}>
                <Form form={editForm} layout="vertical" onFinish={handleEdit}>
                    <Form.Item
                        name="full_name"
                        label="姓名"
                        rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="email"
                        label="邮箱"
                        rules={[{ required: true }, { type: 'email' }]}>
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 角色分配弹窗 */}
            <Modal
                title={`角色分配 - ${editingUser?.username}`}
                open={rolesModalOpen}
                onCancel={() => {
                    setRolesModalOpen(false)
                    setEditingUser(null)
                }}
                onOk={() => rolesForm.submit()}>
                <Form
                    form={rolesForm}
                    layout="vertical"
                    onFinish={handleAssignRoles}>
                    <Form.Item
                        name="role_codes"
                        label="角色"
                        rules={[
                            { required: true, message: '请至少选择一个角色' },
                        ]}>
                        <Select
                            mode="multiple"
                            placeholder="选择角色"
                            options={roleOptions}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 重置密码弹窗 */}
            <Modal
                title={`重置密码 - ${editingUser?.username}`}
                open={resetPwdModalOpen}
                onCancel={() => {
                    setResetPwdModalOpen(false)
                    setEditingUser(null)
                }}
                onOk={() => resetPwdForm.submit()}>
                <Form
                    form={resetPwdForm}
                    layout="vertical"
                    onFinish={handleResetPassword}>
                    <Form.Item
                        name="new_password"
                        label="新密码"
                        rules={[
                            { required: true },
                            { min: 8, message: '密码至少8位' },
                        ]}>
                        <Input.Password />
                    </Form.Item>
                    <Form.Item
                        name="confirm_password"
                        label="确认密码"
                        dependencies={['new_password']}
                        rules={[
                            { required: true },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (
                                        !value ||
                                        getFieldValue('new_password') === value
                                    ) {
                                        return Promise.resolve()
                                    }
                                    return Promise.reject(
                                        new Error('两次输入的密码不一致'),
                                    )
                                },
                            }),
                        ]}>
                        <Input.Password />
                    </Form.Item>
                </Form>
            </Modal>
        </Card>
    )
}
