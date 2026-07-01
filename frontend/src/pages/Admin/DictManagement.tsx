import { useEffect, useMemo, useState } from 'react'
import {
    Card,
    Table,
    Button,
    Modal,
    Form,
    Input,
    InputNumber,
    Switch,
    Space,
    Tag,
    Typography,
    message,
    Tabs,
    Select,
} from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { adminService, type PermissionItem } from '@/services/admin'
import dictService, {
    type DictCategory,
    type DictItem,
} from '@/services/dictionary'
import { getErrorMessage } from '@/services/apiClient'
import { useAuthStore } from '@/stores/authStore'

const PROJECT_PERMISSION_GROUP_LABELS: Record<string, string> = {
    project_menu: '项目菜单',
    project_page: '项目页面',
    project_button: '项目按钮',
}

const PROJECT_PERMISSION_GROUP_ORDER = [
    'project_menu',
    'project_page',
    'project_button',
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

    if (permissionProfile === 'viewer') {
        return baseCodes
    }

    return []
}

export default function DictManagementPage() {
    const PROJECT_ROLE_PERMISSION_OPTIONS = [
        { value: 'owner', label: '负责人权限' },
        { value: 'manager', label: '项目经理权限' },
        { value: 'member', label: '成员权限' },
        { value: 'viewer', label: '只读权限' },
    ]

    const [categories, setCategories] = useState<DictCategory[]>([])
    const [loading, setLoading] = useState(false)
    const [activeCategory, setActiveCategory] = useState<string>()
    const [itemModalOpen, setItemModalOpen] = useState(false)
    const [editingItem, setEditingItem] = useState<DictItem | null>(null)
    const [catModalOpen, setCatModalOpen] = useState(false)
    const [editingCategory, setEditingCategory] = useState<DictCategory | null>(
        null,
    )
    const [projectPermissions, setProjectPermissions] = useState<
        PermissionItem[]
    >([])
    const [itemForm] = Form.useForm()
    const [catForm] = Form.useForm()
    const currentUser = useAuthStore((state) => state.user)
    const canManageDict =
        currentUser?.permissions?.includes('system.admin.dict.manage') ?? false
    const watchedPermissionProfile = Form.useWatch(
        'permission_profile',
        itemForm,
    )

    const projectPermissionMap = useMemo(
        () =>
            new Map(
                projectPermissions.map((permission) => [
                    permission.code,
                    permission,
                ]),
            ),
        [projectPermissions],
    )

    const groupedProjectPermissionOptions = useMemo(() => {
        const groups = new Map<string, PermissionItem[]>()
        projectPermissions.forEach((permission) => {
            const items = groups.get(permission.resource_type) ?? []
            items.push(permission)
            groups.set(permission.resource_type, items)
        })

        return PROJECT_PERMISSION_GROUP_ORDER.map((resourceType) => ({
            label:
                PROJECT_PERMISSION_GROUP_LABELS[resourceType] ?? resourceType,
            options: (groups.get(resourceType) ?? [])
                .sort((left, right) =>
                    left.display_name.localeCompare(
                        right.display_name,
                        'zh-CN',
                    ),
                )
                .map((permission) => ({
                    value: permission.code,
                    label: `${permission.display_name} (${permission.code})`,
                })),
        })).filter((group) => group.options.length > 0)
    }, [projectPermissions])

    const fetchCategories = async () => {
        setLoading(true)
        try {
            const data = await dictService.listCategories()
            setCategories(data)
            if (!activeCategory && data.length > 0) {
                setActiveCategory(data[0]!.id)
            }
        } catch (err) {
            message.error(getErrorMessage(err, '获取字典失败'))
        } finally {
            setLoading(false)
        }
    }

    const fetchProjectPermissions = async () => {
        try {
            const { data } = await adminService.listPermissions()
            setProjectPermissions(
                data.filter((permission) =>
                    permission.code.startsWith('project.'),
                ),
            )
        } catch (err) {
            message.error(getErrorMessage(err, '获取项目权限目录失败'))
        }
    }

    useEffect(() => {
        fetchCategories()
        if (canManageDict) {
            fetchProjectPermissions()
        }
    }, [canManageDict])

    const currentCategory = categories.find((c) => c.id === activeCategory)
    const items = currentCategory?.items ?? []
    const isProjectRoleCategory = currentCategory?.code === 'project_role'

    useEffect(() => {
        if (
            !itemModalOpen ||
            !isProjectRoleCategory ||
            !watchedPermissionProfile
        ) {
            return
        }

        const currentPermissionCodes = itemForm.getFieldValue(
            'permission_codes',
        ) as string[] | undefined

        if (!currentPermissionCodes || currentPermissionCodes.length === 0) {
            itemForm.setFieldValue(
                'permission_codes',
                defaultProjectRolePermissionCodes(watchedPermissionProfile),
            )
        }
    }, [
        isProjectRoleCategory,
        itemForm,
        itemModalOpen,
        watchedPermissionProfile,
    ])

    const handleCreateCategory = async () => {
        try {
            const values = await catForm.validateFields()
            if (editingCategory) {
                await dictService.updateCategory(editingCategory.id, {
                    name: values.name,
                    description: values.description,
                })
                message.success('类别更新成功')
            } else {
                await dictService.createCategory(values)
                message.success('类别创建成功')
            }
            setCatModalOpen(false)
            setEditingCategory(null)
            catForm.resetFields()
            fetchCategories()
        } catch (err) {
            if (err && typeof err === 'object' && 'response' in err) {
                message.error(
                    getErrorMessage(
                        err,
                        editingCategory ? '更新失败' : '创建失败',
                    ),
                )
            }
        }
    }

    const openEditCategory = (cat: DictCategory) => {
        setEditingCategory(cat)
        catForm.setFieldsValue({
            code: cat.code,
            name: cat.name,
            description: cat.description,
        })
        setCatModalOpen(true)
    }

    const handleDeleteCategory = (cat: DictCategory) => {
        if (cat.is_system) {
            message.warning('系统内置类别不可删除')
            return
        }
        Modal.confirm({
            title: '确认删除',
            content: `删除类别「${cat.name}」及其所有选项？`,
            onOk: async () => {
                try {
                    await dictService.deleteCategory(cat.id)
                    message.success('已删除')
                    setActiveCategory(undefined)
                    fetchCategories()
                } catch (err) {
                    message.error(getErrorMessage(err, '删除失败'))
                }
            },
        })
    }

    const openItemModal = (item?: DictItem) => {
        setEditingItem(item ?? null)
        if (item) {
            itemForm.setFieldsValue({
                ...item,
                permission_codes:
                    item.permission_codes ??
                    defaultProjectRolePermissionCodes(item.permission_profile),
            })
        } else {
            itemForm.resetFields()
            itemForm.setFieldsValue({
                is_enabled: true,
                sort_order: 0,
                permission_codes: [],
            })
        }
        setItemModalOpen(true)
    }

    const applyDefaultProjectPermissions = () => {
        const permissionProfile = itemForm.getFieldValue(
            'permission_profile',
        ) as string | undefined

        if (!permissionProfile) {
            message.warning('请先选择权限档位')
            return
        }

        itemForm.setFieldValue(
            'permission_codes',
            defaultProjectRolePermissionCodes(permissionProfile),
        )
    }

    const handleSaveItem = async () => {
        try {
            const values = await itemForm.validateFields()
            if (editingItem) {
                await dictService.updateItem(editingItem.id, values)
                message.success('已更新')
            } else {
                await dictService.createItem(activeCategory!, values)
                message.success('已添加')
            }
            setItemModalOpen(false)
            itemForm.resetFields()
            fetchCategories()
        } catch (err) {
            if (err && typeof err === 'object' && 'response' in err) {
                message.error(getErrorMessage(err, '操作失败'))
            }
        }
    }

    const handleDeleteItem = (item: DictItem) => {
        Modal.confirm({
            title: '确认删除',
            content: `删除选项「${item.label}」？`,
            onOk: async () => {
                try {
                    await dictService.deleteItem(item.id)
                    message.success('已删除')
                    fetchCategories()
                } catch (err) {
                    message.error(getErrorMessage(err, '删除失败'))
                }
            },
        })
    }

    const handleToggleEnabled = async (item: DictItem) => {
        try {
            await dictService.updateItem(item.id, {
                is_enabled: !item.is_enabled,
            })
            fetchCategories()
        } catch (err) {
            message.error(getErrorMessage(err, '操作失败'))
        }
    }

    const columns = [
        { title: '编码', dataIndex: 'code', width: 120 },
        { title: '显示名称', dataIndex: 'label', ellipsis: true },
        { title: '描述', dataIndex: 'description', ellipsis: true },
        {
            title: '附加信息',
            dataIndex: 'extra',
            width: 120,
            render: (val: string | null) => (val ? <Tag>{val}</Tag> : '-'),
        },
        ...(isProjectRoleCategory
            ? [
                  {
                      title: '权限档位',
                      dataIndex: 'permission_profile',
                      width: 140,
                      render: (val: string | null) => {
                          const option = PROJECT_ROLE_PERMISSION_OPTIONS.find(
                              (item) => item.value === val,
                          )
                          return option ? (
                              <Tag color="geekblue">{option.label}</Tag>
                          ) : (
                              '-'
                          )
                      },
                  },
                  {
                      title: '权限配置',
                      dataIndex: 'permission_codes',
                      width: 280,
                      render: (
                          permissionCodes: string[] | null,
                          record: DictItem,
                      ) => {
                          const effectiveCodes =
                              permissionCodes ??
                              defaultProjectRolePermissionCodes(
                                  record.permission_profile,
                              )

                          if (!effectiveCodes.length) {
                              return (
                                  <Typography.Text type="secondary">
                                      未配置
                                  </Typography.Text>
                              )
                          }

                          return (
                              <Space size={[0, 4]} wrap>
                                  {effectiveCodes
                                      .slice(0, 2)
                                      .map((permissionCode) => (
                                          <Tag key={permissionCode}>
                                              {projectPermissionMap.get(
                                                  permissionCode,
                                              )?.display_name ?? permissionCode}
                                          </Tag>
                                      ))}
                                  {effectiveCodes.length > 2 ? (
                                      <Tag>+{effectiveCodes.length - 2}</Tag>
                                  ) : null}
                              </Space>
                          )
                      },
                  },
              ]
            : []),
        { title: '排序', dataIndex: 'sort_order', width: 70 },
        {
            title: '状态',
            dataIndex: 'is_enabled',
            width: 80,
            render: (val: boolean, record: DictItem) => (
                <Switch
                    size="small"
                    checked={val}
                    onChange={() => handleToggleEnabled(record)}
                    disabled={!canManageDict}
                />
            ),
        },
        ...(canManageDict
            ? [
                  {
                      title: '操作',
                      width: 100,
                      render: (_: unknown, record: DictItem) => (
                          <Space size="small">
                              <Button
                                  size="small"
                                  type="link"
                                  icon={<EditOutlined />}
                                  onClick={() => openItemModal(record)}
                              />
                              <Button
                                  size="small"
                                  type="link"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={() => handleDeleteItem(record)}
                              />
                          </Space>
                      ),
                  },
              ]
            : []),
    ]

    const tabItems = categories.map((cat) => ({
        key: cat.id,
        label: (
            <span>
                {cat.name}
                {cat.is_system && (
                    <Tag color="blue" style={{ marginLeft: 4, fontSize: 10 }}>
                        系统
                    </Tag>
                )}
            </span>
        ),
    }))

    return (
        <div style={{ padding: 24 }}>
            <Card
                title="字典管理"
                extra={
                    canManageDict ? (
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={() => setCatModalOpen(true)}>
                            新增类别
                        </Button>
                    ) : null
                }>
                <Tabs
                    activeKey={activeCategory}
                    onChange={setActiveCategory}
                    items={tabItems}
                    tabBarExtraContent={
                        canManageDict && currentCategory ? (
                            <Space size="small">
                                <Button
                                    size="small"
                                    icon={<EditOutlined />}
                                    onClick={() =>
                                        openEditCategory(currentCategory)
                                    }>
                                    编辑类别
                                </Button>
                                {!currentCategory.is_system && (
                                    <Button
                                        size="small"
                                        danger
                                        onClick={() =>
                                            handleDeleteCategory(
                                                currentCategory,
                                            )
                                        }>
                                        删除类别
                                    </Button>
                                )}
                            </Space>
                        ) : undefined
                    }
                />

                {currentCategory && (
                    <>
                        <div
                            style={{
                                marginBottom: 12,
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                            }}>
                            <span style={{ color: '#666' }}>
                                类别编码：{currentCategory.code}
                                {currentCategory.description &&
                                    ` | ${currentCategory.description}`}
                            </span>
                            {canManageDict ? (
                                <Button
                                    type="primary"
                                    size="small"
                                    icon={<PlusOutlined />}
                                    onClick={() => openItemModal()}>
                                    新增选项
                                </Button>
                            ) : null}
                        </div>
                        <Table
                            columns={columns}
                            dataSource={items}
                            rowKey="id"
                            pagination={{
                                defaultPageSize: 20,
                                pageSizeOptions: ['20', '50', '100'],
                                showSizeChanger: true,
                                showQuickJumper: true,
                                showTotal: (total) => `共 ${total} 条`,
                            }}
                            size="small"
                            loading={loading}
                        />
                    </>
                )}
            </Card>

            {/* 新增/编辑类别 Modal */}
            <Modal
                title={editingCategory ? '编辑字典类别' : '新增字典类别'}
                open={catModalOpen}
                onOk={handleCreateCategory}
                onCancel={() => {
                    setCatModalOpen(false)
                    setEditingCategory(null)
                    catForm.resetFields()
                }}
                okText={editingCategory ? '保存' : '创建'}
                cancelText="取消">
                <Form form={catForm} layout="vertical">
                    <Form.Item
                        name="code"
                        label="类别编码"
                        rules={[{ required: true, message: '请输入编码' }]}>
                        <Input
                            placeholder="如：doc_type"
                            disabled={!!editingCategory}
                        />
                    </Form.Item>
                    <Form.Item
                        name="name"
                        label="类别名称"
                        rules={[{ required: true, message: '请输入名称' }]}>
                        <Input placeholder="如：文档类型" />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 新增/编辑选项 Modal */}
            <Modal
                title={editingItem ? '编辑选项' : '新增选项'}
                open={itemModalOpen}
                onOk={handleSaveItem}
                onCancel={() => setItemModalOpen(false)}
                okText="保存"
                cancelText="取消">
                <Form form={itemForm} layout="vertical">
                    <Form.Item
                        name="code"
                        label="选项编码"
                        rules={[{ required: true, message: '请输入编码' }]}>
                        <Input placeholder="如：VP" disabled={!!editingItem} />
                    </Form.Item>
                    <Form.Item
                        name="label"
                        label="显示名称"
                        rules={[{ required: true, message: '请输入名称' }]}>
                        <Input placeholder="如：VP（Validation Plan）" />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input />
                    </Form.Item>
                    <Form.Item name="extra" label="附加信息">
                        <Input placeholder="如颜色标签：green、blue" />
                    </Form.Item>
                    {isProjectRoleCategory && (
                        <>
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
                                    placeholder="选择该角色继承的权限档位"
                                    options={PROJECT_ROLE_PERMISSION_OPTIONS}
                                />
                            </Form.Item>
                            <div style={{ marginBottom: 8 }}>
                                <Space>
                                    <Typography.Text>
                                        菜单与按钮权限
                                    </Typography.Text>
                                    <Button
                                        size="small"
                                        type="link"
                                        onClick={
                                            applyDefaultProjectPermissions
                                        }>
                                        按档位填充默认权限
                                    </Button>
                                </Space>
                            </div>
                            <Form.Item name="permission_codes">
                                <Select
                                    mode="multiple"
                                    placeholder="选择该项目角色允许访问的菜单、页面和按钮权限"
                                    options={groupedProjectPermissionOptions}
                                />
                            </Form.Item>
                        </>
                    )}
                    <Form.Item name="sort_order" label="排序" initialValue={0}>
                        <InputNumber min={0} />
                    </Form.Item>
                    <Form.Item
                        name="is_enabled"
                        label="启用"
                        valuePropName="checked"
                        initialValue={true}>
                        <Switch />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
