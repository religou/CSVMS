import { useEffect, useMemo, useState } from 'react'
import {
    Alert,
    Button,
    Card,
    Checkbox,
    Form,
    Input,
    Modal,
    Popconfirm,
    Radio,
    Result,
    Select,
    Space,
    Table,
    Tag,
    Tooltip,
    Typography,
    message,
} from 'antd'
import {
    DeleteOutlined,
    PlusOutlined,
    SafetyCertificateOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { adminService, PermissionItem, RoleDetailItem } from '@/services/admin'
import dictService, { DictCategory } from '@/services/dictionary'
import { useAuthStore } from '@/stores/authStore'

const RESOURCE_TYPE_LABELS: Record<string, string> = {
    system_menu: '系统菜单',
    system_page: '系统页面',
    system_button: '系统按钮',
    project_menu: '项目菜单',
    project_page: '项目页面',
    project_button: '项目按钮',
}

const RESOURCE_TYPE_ORDER = [
    'system_menu',
    'system_page',
    'system_button',
    'project_menu',
    'project_page',
    'project_button',
]

type RoleFormValues = {
    name?: string
    display_name: string
    description?: string
}

type RoleSourceType = 'system_role' | 'project_role'

type AssignmentFormValues = {
    source_type: RoleSourceType
    role_code: string
    permission_profile?: string
}

const PROJECT_ROLE_PERMISSION_OPTIONS = [
    { value: 'owner', label: '负责人权限' },
    { value: 'manager', label: '项目经理权限' },
    { value: 'member', label: '成员权限' },
    { value: 'viewer', label: '只读权限' },
]

function defaultProjectRolePermissionCodes(permissionProfile?: string | null) {
    const baseCodes = [
        'project.dashboard.menu',
        'project.dashboard.view',
        'project.documents.menu',
        'project.documents.view',
        'project.workflows.menu',
        'project.workflows.view',
        'project.traceability.menu',
        'project.traceability.view',
        'project.audit_log.menu',
        'project.audit_log.view',
        'project.members.menu',
        'project.members.view',
    ]

    if (permissionProfile === 'owner' || permissionProfile === 'manager') {
        return [
            ...baseCodes,
            'project.documents.manage',
            'project.workflows.manage',
            'project.members.manage',
        ]
    }

    if (permissionProfile === 'member') {
        return [...baseCodes, 'project.documents.manage']
    }

    return baseCodes
}

function getErrorMessage(error: unknown, fallback: string) {
    const responseError = error as { response?: { data?: { detail?: string } } }
    return responseError.response?.data?.detail || fallback
}

export default function RoleManagementPage() {
    const navigate = useNavigate()
    const currentUser = useAuthStore((state) => state.user)
    const [roles, setRoles] = useState<RoleDetailItem[]>([])
    const [permissions, setPermissions] = useState<PermissionItem[]>([])
    const [categories, setCategories] = useState<DictCategory[]>([])
    const [loading, setLoading] = useState(false)
    const [assignmentModalOpen, setAssignmentModalOpen] = useState(false)
    const [roleModalOpen, setRoleModalOpen] = useState(false)
    const [permissionsModalOpen, setPermissionsModalOpen] = useState(false)
    const [roleModalMode, setRoleModalMode] = useState<'create' | 'edit'>(
        'create',
    )
    const [editingRole, setEditingRole] = useState<RoleDetailItem | null>(null)
    const [permissionsRole, setPermissionsRole] =
        useState<RoleDetailItem | null>(null)
    const [selectedPermissionIds, setSelectedPermissionIds] = useState<
        string[]
    >([])
    const [assignmentPermissionValues, setAssignmentPermissionValues] =
        useState<string[]>([])
    const [submitting, setSubmitting] = useState(false)
    const [assignmentForm] = Form.useForm<AssignmentFormValues>()
    const [roleForm] = Form.useForm<RoleFormValues>()
    const watchedRoleSource = Form.useWatch('source_type', assignmentForm)
    const watchedRoleCode = Form.useWatch('role_code', assignmentForm)

    const currentPermissions = currentUser?.permissions ?? []
    const canViewRoles = currentPermissions.includes('system.admin.roles.view')
    const canManageRoles = currentPermissions.includes(
        'system.admin.roles.manage',
    )
    const assignmentDisabledReason = canManageRoles
        ? null
        : '当前账号只能查看角色，不允许分配权限'

    const groupedPermissions = useMemo(() => {
        const groups = new Map<string, PermissionItem[]>()
        permissions.forEach((permission) => {
            const items = groups.get(permission.resource_type) ?? []
            items.push(permission)
            groups.set(permission.resource_type, items)
        })

        return RESOURCE_TYPE_ORDER.map((resourceType) => ({
            resourceType,
            label: RESOURCE_TYPE_LABELS[resourceType] ?? resourceType,
            items: (groups.get(resourceType) ?? []).sort((left, right) =>
                left.display_name.localeCompare(right.display_name, 'zh-CN'),
            ),
        })).filter((group) => group.items.length > 0)
    }, [permissions])

    const systemRoleItems = useMemo(
        () =>
            categories.find((category) => category.code === 'system_role')
                ?.items ?? [],
        [categories],
    )

    const projectRoleItems = useMemo(
        () =>
            categories.find((category) => category.code === 'project_role')
                ?.items ?? [],
        [categories],
    )

    const groupedAssignableRoleOptions = useMemo(
        () => [
            {
                label: '系统角色',
                options: systemRoleItems.map((item) => ({
                    value: item.code,
                    label: item.label,
                })),
            },
            {
                label: '项目角色',
                options: projectRoleItems.map((item) => ({
                    value: item.code,
                    label: item.label,
                })),
            },
        ],
        [projectRoleItems, systemRoleItems],
    )

    const assignableRoleOptions = useMemo(() => {
        if (watchedRoleSource === 'system_role') {
            return groupedAssignableRoleOptions[0]?.options ?? []
        }

        if (watchedRoleSource === 'project_role') {
            return groupedAssignableRoleOptions[1]?.options ?? []
        }

        return []
    }, [groupedAssignableRoleOptions, watchedRoleSource])

    const selectedSystemRole = useMemo(
        () =>
            watchedRoleSource === 'system_role'
                ? (roles.find((role) => role.name === watchedRoleCode) ?? null)
                : null,
        [roles, watchedRoleCode, watchedRoleSource],
    )

    const selectedProjectRole = useMemo(
        () =>
            watchedRoleSource === 'project_role'
                ? (projectRoleItems.find(
                      (item) => item.code === watchedRoleCode,
                  ) ?? null)
                : null,
        [projectRoleItems, watchedRoleCode, watchedRoleSource],
    )

    const systemRoleSyncError =
        watchedRoleSource === 'system_role' &&
        watchedRoleCode &&
        !selectedSystemRole
            ? '所选系统角色尚未同步到系统角色实体，请先在系统角色数据中补齐后再分配权限。'
            : null

    const assignmentPermissionGroups = useMemo(() => {
        if (!watchedRoleSource) {
            return []
        }

        const codePrefix =
            watchedRoleSource === 'system_role' ? 'system.' : 'project.'
        const filteredPermissions = permissions.filter((permission) =>
            permission.code.startsWith(codePrefix),
        )

        const groups = new Map<string, PermissionItem[]>()
        filteredPermissions.forEach((permission) => {
            const items = groups.get(permission.resource_type) ?? []
            items.push(permission)
            groups.set(permission.resource_type, items)
        })

        return RESOURCE_TYPE_ORDER.map((resourceType) => ({
            resourceType,
            label: RESOURCE_TYPE_LABELS[resourceType] ?? resourceType,
            items: (groups.get(resourceType) ?? []).sort((left, right) =>
                left.display_name.localeCompare(right.display_name, 'zh-CN'),
            ),
        })).filter((group) => group.items.length > 0)
    }, [permissions, watchedRoleSource])

    const fetchRoles = async () => {
        setLoading(true)
        try {
            const { data } = await adminService.listRoles()
            setRoles(data)
        } catch {
            message.error('获取角色列表失败')
        } finally {
            setLoading(false)
        }
    }

    const fetchPermissions = async () => {
        try {
            const { data } = await adminService.listPermissions()
            setPermissions(data)
        } catch {
            message.error('获取权限目录失败')
        }
    }

    const fetchRoleCategories = async () => {
        try {
            const data = await dictService.listCategories()
            setCategories(
                data.filter(
                    (category) =>
                        category.code === 'system_role' ||
                        category.code === 'project_role',
                ),
            )
        } catch {
            message.error('获取角色字典失败')
        }
    }

    useEffect(() => {
        if (!canViewRoles) {
            return
        }

        fetchRoles()
        if (canManageRoles) {
            fetchPermissions()
            fetchRoleCategories()
        }
    }, [canManageRoles, canViewRoles])

    useEffect(() => {
        if (!assignmentModalOpen || !watchedRoleSource || !watchedRoleCode) {
            return
        }

        if (watchedRoleSource === 'system_role') {
            setAssignmentPermissionValues(
                selectedSystemRole?.permissions
                    .filter((permission) =>
                        permission.code.startsWith('system.'),
                    )
                    .map((permission) => permission.id) ?? [],
            )
            assignmentForm.setFieldValue('permission_profile', undefined)
            return
        }

        if (selectedProjectRole) {
            assignmentForm.setFieldValue(
                'permission_profile',
                selectedProjectRole.permission_profile ?? undefined,
            )
            setAssignmentPermissionValues(
                selectedProjectRole.permission_codes ??
                    defaultProjectRolePermissionCodes(
                        selectedProjectRole.permission_profile,
                    ),
            )
        }
    }, [
        assignmentForm,
        assignmentModalOpen,
        selectedProjectRole,
        selectedSystemRole,
        watchedRoleCode,
        watchedRoleSource,
    ])

    useEffect(() => {
        if (
            !assignmentModalOpen ||
            !watchedRoleSource ||
            assignmentForm.getFieldValue('role_code') ||
            assignableRoleOptions.length !== 1
        ) {
            return
        }

        assignmentForm.setFieldValue(
            'role_code',
            assignableRoleOptions[0]?.value,
        )
    }, [
        assignmentForm,
        assignmentModalOpen,
        assignableRoleOptions,
        watchedRoleSource,
    ])

    const openAssignmentModal = () => {
        assignmentForm.resetFields()
        setAssignmentPermissionValues([])
        setAssignmentModalOpen(true)
    }

    const closeAssignmentModal = () => {
        assignmentForm.resetFields()
        setAssignmentPermissionValues([])
        setAssignmentModalOpen(false)
    }

    const handleAssignmentValuesChange = (
        changedValues: Partial<AssignmentFormValues>,
    ) => {
        if ('source_type' in changedValues) {
            assignmentForm.setFieldsValue({
                role_code: undefined,
                permission_profile: undefined,
            })
            setAssignmentPermissionValues([])
        }
    }

    const handleAssignmentSubmit = async (values: AssignmentFormValues) => {
        setSubmitting(true)
        try {
            if (values.source_type === 'system_role') {
                if (!selectedSystemRole) {
                    message.error(systemRoleSyncError || '系统角色不存在')
                    return
                }

                await adminService.updateRolePermissions(
                    selectedSystemRole.id,
                    assignmentPermissionValues,
                )
                message.success('系统角色权限已更新')
                closeAssignmentModal()
                await fetchRoles()
                return
            }

            if (!selectedProjectRole) {
                message.error('项目角色不存在')
                return
            }

            await dictService.updateItem(selectedProjectRole.id, {
                permission_profile:
                    values.permission_profile ??
                    selectedProjectRole.permission_profile ??
                    undefined,
                permission_codes: assignmentPermissionValues,
            })
            message.success('项目角色权限已更新')
            closeAssignmentModal()
            await fetchRoleCategories()
        } catch (error: unknown) {
            message.error(getErrorMessage(error, '权限分配失败'))
        } finally {
            setSubmitting(false)
        }
    }

    const openEditRoleModal = (role: RoleDetailItem) => {
        setRoleModalMode('edit')
        setEditingRole(role)
        roleForm.setFieldsValue({
            display_name: role.display_name,
            description: role.description,
        })
        setRoleModalOpen(true)
    }
    void openEditRoleModal

    const openPermissionsModal = (role: RoleDetailItem) => {
        setPermissionsRole(role)
        setSelectedPermissionIds(
            role.permissions.map((permission) => permission.id),
        )
        setPermissionsModalOpen(true)
    }

    const closeRoleModal = () => {
        setRoleModalOpen(false)
        setEditingRole(null)
        roleForm.resetFields()
    }

    const closePermissionsModal = () => {
        setPermissionsModalOpen(false)
        setPermissionsRole(null)
        setSelectedPermissionIds([])
    }

    const handleSubmitRole = async (values: RoleFormValues) => {
        setSubmitting(true)
        try {
            if (roleModalMode === 'create') {
                await adminService.createRole({
                    name: values.name?.trim() ?? '',
                    display_name: values.display_name.trim(),
                    description: values.description?.trim() || undefined,
                })
                message.success('角色已创建')
            } else if (editingRole) {
                await adminService.updateRole(editingRole.id, {
                    display_name: values.display_name.trim(),
                    description: values.description?.trim() || undefined,
                })
                message.success('角色信息已更新')
            }
            closeRoleModal()
            fetchRoles()
        } catch (error: unknown) {
            message.error(getErrorMessage(error, '角色保存失败'))
        } finally {
            setSubmitting(false)
        }
    }

    const handleSavePermissions = async () => {
        if (!permissionsRole) {
            return
        }

        setSubmitting(true)
        try {
            await adminService.updateRolePermissions(
                permissionsRole.id,
                selectedPermissionIds,
            )
            message.success('权限已更新')
            closePermissionsModal()
            fetchRoles()
        } catch (error: unknown) {
            message.error(getErrorMessage(error, '权限更新失败'))
        } finally {
            setSubmitting(false)
        }
    }

    const handleDeleteRole = async (role: RoleDetailItem) => {
        try {
            await adminService.deleteRole(role.id)
            message.success('角色已删除')
            fetchRoles()
        } catch (error: unknown) {
            message.error(getErrorMessage(error, '删除失败'))
        }
    }

    const updatePermissionSelection = (
        groupPermissionIds: string[],
        nextCheckedIds: string[],
    ) => {
        setSelectedPermissionIds((previous) => {
            const remainingIds = previous.filter(
                (permissionId) => !groupPermissionIds.includes(permissionId),
            )
            return [...remainingIds, ...nextCheckedIds]
        })
    }

    if (!canViewRoles) {
        return (
            <Result
                status="403"
                title="无权访问"
                subTitle="当前账号缺少权限管理页面访问权限。"
                extra={
                    <Button type="primary" onClick={() => navigate('/')}>
                        返回首页
                    </Button>
                }
            />
        )
    }

    const columns = [
        {
            title: '角色名称',
            key: 'display_name',
            render: (_: unknown, record: RoleDetailItem) => (
                <Space direction="vertical" size={2}>
                    <Space>
                        <Typography.Text strong>
                            {record.display_name}
                        </Typography.Text>
                        {record.is_system ? (
                            <Tag color="blue">内置</Tag>
                        ) : (
                            <Tag>自定义</Tag>
                        )}
                        {record.name === 'validation_admin' ? (
                            <Tag color="orange">受限</Tag>
                        ) : null}
                    </Space>
                    <Typography.Text type="secondary">
                        {record.name}
                    </Typography.Text>
                </Space>
            ),
        },
        {
            title: '说明',
            dataIndex: 'description',
            key: 'description',
            render: (value?: string) => value || '-',
        },
        {
            title: '权限',
            key: 'permissions',
            render: (_: unknown, record: RoleDetailItem) => {
                if (!record.permissions.length) {
                    return (
                        <Typography.Text type="secondary">
                            未分配
                        </Typography.Text>
                    )
                }

                return (
                    <Space size={[0, 8]} wrap>
                        {record.permissions.slice(0, 3).map((permission) => (
                            <Tag key={permission.id} color="processing">
                                {permission.display_name}
                            </Tag>
                        ))}
                        {record.permissions.length > 3 ? (
                            <Tag>+{record.permissions.length - 3}</Tag>
                        ) : null}
                    </Space>
                )
            },
        },
        {
            title: '操作',
            key: 'actions',
            render: (_: unknown, record: RoleDetailItem) => {
                const manageDisabledReason = !canManageRoles
                    ? '当前账号只能查看角色，不允许分配权限或删除'
                    : null
                const permissionsDisabledReason =
                    record.name === 'validation_admin'
                        ? '验证管理员角色不允许修改权限'
                        : manageDisabledReason
                const deleteDisabledReason =
                    record.name === 'validation_admin'
                        ? '验证管理员角色不允许删除'
                        : manageDisabledReason

                return (
                    <Space>
                        <Tooltip title={permissionsDisabledReason || ''}>
                            <span>
                                <Button
                                    size="small"
                                    icon={<SafetyCertificateOutlined />}
                                    disabled={Boolean(
                                        permissionsDisabledReason,
                                    )}
                                    onClick={() =>
                                        openPermissionsModal(record)
                                    }>
                                    权限
                                </Button>
                            </span>
                        </Tooltip>
                        <Tooltip title={deleteDisabledReason || ''}>
                            <span>
                                <Popconfirm
                                    title="确认删除角色"
                                    description={`确定要删除角色「${record.display_name}」吗？`}
                                    onConfirm={() => handleDeleteRole(record)}
                                    okText="删除"
                                    cancelText="取消"
                                    okButtonProps={{ danger: true }}
                                    disabled={Boolean(deleteDisabledReason)}>
                                    <Button
                                        size="small"
                                        danger
                                        icon={<DeleteOutlined />}
                                        disabled={Boolean(
                                            deleteDisabledReason,
                                        )}>
                                        删除
                                    </Button>
                                </Popconfirm>
                            </span>
                        </Tooltip>
                    </Space>
                )
            },
        },
    ]

    return (
        <Card
            title="权限管理"
            extra={
                <Tooltip title={assignmentDisabledReason || ''}>
                    <span>
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={openAssignmentModal}
                            disabled={!canManageRoles}>
                            权限分配
                        </Button>
                    </span>
                </Tooltip>
            }>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Alert
                    type="info"
                    showIcon
                    message="内置角色约束"
                    description="validation_admin 不允许配置权限或删除；具备角色管理权限的账号可对其他角色执行权限分配和删除。"
                />
                <Table
                    dataSource={roles}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        defaultPageSize: 10,
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50'],
                        showTotal: (total) => `共 ${total} 条`,
                    }}
                />
            </Space>

            <Modal
                title="权限分配"
                open={assignmentModalOpen}
                onCancel={closeAssignmentModal}
                onOk={() => assignmentForm.submit()}
                confirmLoading={submitting}
                okButtonProps={{ disabled: Boolean(systemRoleSyncError) }}>
                <Form
                    form={assignmentForm}
                    layout="vertical"
                    onValuesChange={handleAssignmentValuesChange}
                    onFinish={handleAssignmentSubmit}>
                    <Form.Item
                        name="source_type"
                        label="角色来源"
                        rules={[{ required: true, message: '请选择角色来源' }]}>
                        <Radio.Group
                            options={[
                                { value: 'system_role', label: '系统角色' },
                                { value: 'project_role', label: '项目角色' },
                            ]}
                            optionType="button"
                            buttonStyle="solid"
                        />
                    </Form.Item>
                    <Form.Item
                        name="role_code"
                        label="目标角色"
                        rules={[{ required: true, message: '请选择目标角色' }]}>
                        <Select
                            placeholder="从字典管理中的角色里选择"
                            options={assignableRoleOptions}
                            disabled={!watchedRoleSource}
                        />
                    </Form.Item>
                    {systemRoleSyncError ? (
                        <Alert
                            type="error"
                            showIcon
                            message="系统角色未同步"
                            description={systemRoleSyncError}
                            style={{ marginBottom: 16 }}
                        />
                    ) : null}
                    {watchedRoleSource === 'project_role' &&
                    selectedProjectRole ? (
                        <Form.Item
                            name="permission_profile"
                            label="权限档位"
                            rules={[
                                {
                                    required: true,
                                    message: '请选择权限档位',
                                },
                            ]}>
                            <Select
                                placeholder="选择该项目角色的权限档位"
                                options={PROJECT_ROLE_PERMISSION_OPTIONS}
                            />
                        </Form.Item>
                    ) : null}
                    {watchedRoleCode ? (
                        <Space
                            direction="vertical"
                            size={16}
                            style={{ width: '100%' }}>
                            {assignmentPermissionGroups.map((group) => {
                                const groupValues = group.items.map((item) =>
                                    watchedRoleSource === 'system_role'
                                        ? item.id
                                        : item.code,
                                )

                                return (
                                    <Card
                                        key={group.resourceType}
                                        size="small"
                                        title={group.label}>
                                        <Checkbox.Group
                                            style={{ width: '100%' }}
                                            value={assignmentPermissionValues.filter(
                                                (permissionValue) =>
                                                    groupValues.includes(
                                                        permissionValue,
                                                    ),
                                            )}
                                            onChange={(checkedValues) => {
                                                const remainingValues =
                                                    assignmentPermissionValues.filter(
                                                        (permissionValue) =>
                                                            !groupValues.includes(
                                                                permissionValue,
                                                            ),
                                                    )
                                                setAssignmentPermissionValues([
                                                    ...remainingValues,
                                                    ...(checkedValues as string[]),
                                                ])
                                            }}>
                                            <Space
                                                direction="vertical"
                                                style={{ width: '100%' }}>
                                                {group.items.map(
                                                    (permission) => {
                                                        const checkboxValue =
                                                            watchedRoleSource ===
                                                            'system_role'
                                                                ? permission.id
                                                                : permission.code

                                                        return (
                                                            <Checkbox
                                                                key={
                                                                    permission.id
                                                                }
                                                                value={
                                                                    checkboxValue
                                                                }>
                                                                <Space
                                                                    direction="vertical"
                                                                    size={0}>
                                                                    <Typography.Text>
                                                                        {
                                                                            permission.display_name
                                                                        }
                                                                    </Typography.Text>
                                                                    <Typography.Text type="secondary">
                                                                        {
                                                                            permission.code
                                                                        }
                                                                    </Typography.Text>
                                                                </Space>
                                                            </Checkbox>
                                                        )
                                                    },
                                                )}
                                            </Space>
                                        </Checkbox.Group>
                                    </Card>
                                )
                            })}
                        </Space>
                    ) : (
                        <Alert
                            type="info"
                            showIcon
                            message="后续步骤"
                            description="选择角色后，将直接加载并配置该角色当前权限。"
                        />
                    )}
                </Form>
            </Modal>

            <Modal
                title={roleModalMode === 'create' ? '权限分配' : '编辑角色'}
                open={roleModalOpen}
                onCancel={closeRoleModal}
                onOk={() => roleForm.submit()}
                confirmLoading={submitting}>
                <Form
                    form={roleForm}
                    layout="vertical"
                    onFinish={handleSubmitRole}>
                    {roleModalMode === 'create' ? (
                        <Form.Item
                            name="name"
                            label="角色编码"
                            rules={[
                                { required: true, message: '请输入角色编码' },
                                {
                                    pattern: /^[a-z0-9_]+$/,
                                    message: '仅支持小写字母、数字和下划线',
                                },
                            ]}>
                            <Input placeholder="例如：qa_manager" />
                        </Form.Item>
                    ) : (
                        <Form.Item label="角色编码">
                            <Input value={editingRole?.name} disabled />
                        </Form.Item>
                    )}
                    <Form.Item
                        name="display_name"
                        label="显示名称"
                        rules={[{ required: true, message: '请输入显示名称' }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="description" label="说明">
                        <Input.TextArea rows={4} />
                    </Form.Item>
                </Form>
            </Modal>

            <Modal
                title={`配置权限 - ${permissionsRole?.display_name || ''}`}
                open={permissionsModalOpen}
                onCancel={closePermissionsModal}
                onOk={handleSavePermissions}
                confirmLoading={submitting}
                width={720}>
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                    {groupedPermissions.map((group) => {
                        const groupPermissionIds = group.items.map(
                            (item) => item.id,
                        )

                        return (
                            <Card
                                key={group.resourceType}
                                size="small"
                                title={group.label}>
                                <Checkbox.Group
                                    style={{ width: '100%' }}
                                    value={selectedPermissionIds.filter(
                                        (permissionId) =>
                                            groupPermissionIds.includes(
                                                permissionId,
                                            ),
                                    )}
                                    onChange={(checkedValues) =>
                                        updatePermissionSelection(
                                            groupPermissionIds,
                                            checkedValues as string[],
                                        )
                                    }>
                                    <Space
                                        direction="vertical"
                                        style={{ width: '100%' }}>
                                        {group.items.map((permission) => (
                                            <Checkbox
                                                key={permission.id}
                                                value={permission.id}>
                                                <Space
                                                    direction="vertical"
                                                    size={0}>
                                                    <Typography.Text>
                                                        {
                                                            permission.display_name
                                                        }
                                                    </Typography.Text>
                                                    <Typography.Text type="secondary">
                                                        {permission.code}
                                                    </Typography.Text>
                                                </Space>
                                            </Checkbox>
                                        ))}
                                    </Space>
                                </Checkbox.Group>
                            </Card>
                        )
                    })}
                </Space>
            </Modal>
        </Card>
    )
}
