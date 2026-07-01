import { useState } from 'react'
import {
    Table,
    Button,
    Tag,
    Modal,
    Select,
    message,
    Card,
    Input,
    Space,
} from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import projectService, {
    type ProjectMember,
    type ProjectMemberCandidate,
} from '@/services/projects'
import { useProjectStore } from '@/stores/projectStore'
import { useAuthStore } from '@/stores/authStore'
import { getErrorMessage } from '@/services/apiClient'
import { useDictItems } from '@/hooks/useDictItems'

export default function MembersPage() {
    const currentProject = useProjectStore((s) => s.currentProject)
    const currentUser = useAuthStore((s) => s.user)
    const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
    const { items: roleItems, options: roleOptions } =
        useDictItems('project_role')
    const { items: systemRoleItems } = useDictItems('system_role')
    const canManage =
        currentProject?.current_user_permissions.includes(
            'project.members.manage',
        ) ?? false

    const defaultRoleCode =
        roleItems.find((item) => item.permission_profile === 'member')?.code ??
        roleOptions[0]?.value ??
        'member'

    const [addModalOpen, setAddModalOpen] = useState(false)
    const [candidateUsers, setCandidateUsers] = useState<
        ProjectMemberCandidate[]
    >([])
    const [candidateLoading, setCandidateLoading] = useState(false)
    const [candidateTotal, setCandidateTotal] = useState(0)
    const [candidateKeyword, setCandidateKeyword] = useState('')
    const [candidatePage, setCandidatePage] = useState(1)
    const [candidatePageSize, setCandidatePageSize] = useState(10)
    const [selectedUserId, setSelectedUserId] = useState<string>()
    const [selectedRole, setSelectedRole] = useState<string>('member')
    const [adding, setAdding] = useState(false)

    const members = currentProject?.members ?? []

    const refreshProject = async () => {
        if (!currentProject) return
        try {
            const detail = await projectService.get(currentProject.id)
            setCurrentProject(detail)
        } catch {
            /* ignore */
        }
    }

    const fetchCandidateUsers = async (overrides?: {
        keyword?: string
        page?: number
        pageSize?: number
    }) => {
        if (!currentProject) return

        const nextKeyword = overrides?.keyword ?? candidateKeyword
        const nextPage = overrides?.page ?? candidatePage
        const nextPageSize = overrides?.pageSize ?? candidatePageSize

        setCandidateKeyword(nextKeyword)
        setCandidatePage(nextPage)
        setCandidatePageSize(nextPageSize)
        setCandidateLoading(true)

        try {
            const data = await projectService.listMemberCandidates(
                currentProject.id,
                {
                    keyword: nextKeyword || undefined,
                    page: nextPage,
                    page_size: nextPageSize,
                },
            )
            setCandidateUsers(data.items)
            setCandidateTotal(data.total)
            if (!data.items.some((user) => user.id === selectedUserId)) {
                setSelectedUserId(undefined)
            }
        } catch (err) {
            message.error(getErrorMessage(err, '获取候选用户失败'))
        } finally {
            setCandidateLoading(false)
        }
    }

    const handleAdd = async () => {
        if (!currentProject || !selectedUserId) return
        setAdding(true)
        try {
            await projectService.addMember(
                currentProject.id,
                selectedUserId,
                selectedRole,
            )
            message.success('成员添加成功')
            setAddModalOpen(false)
            setSelectedUserId(undefined)
            setSelectedRole('member')
            refreshProject()
        } catch (err) {
            message.error(getErrorMessage(err, '添加失败'))
        } finally {
            setAdding(false)
        }
    }

    const handleRemove = (member: ProjectMember) => {
        if (!currentProject) return
        Modal.confirm({
            title: '确认移除',
            content: `确认移除成员 ${member.full_name}？`,
            onOk: async () => {
                try {
                    await projectService.removeMember(
                        currentProject.id,
                        member.user_id,
                    )
                    message.success('已移除')
                    refreshProject()
                } catch (err) {
                    message.error(getErrorMessage(err, '移除失败'))
                }
            },
        })
    }

    const handleRoleChange = async (member: ProjectMember, newRole: string) => {
        if (!currentProject) return
        try {
            await projectService.updateMemberRole(
                currentProject.id,
                member.user_id,
                newRole,
            )
            message.success('角色已更新')
            refreshProject()
        } catch (err) {
            message.error(getErrorMessage(err, '更新失败'))
        }
    }

    const openAddModal = async () => {
        if (!currentProject) return
        setSelectedUserId(undefined)
        setSelectedRole(defaultRoleCode)
        setCandidateKeyword('')
        setCandidatePage(1)
        setCandidatePageSize(10)
        setAddModalOpen(true)
        await fetchCandidateUsers({
            keyword: '',
            page: 1,
            pageSize: 10,
        })
    }

    const columns = [
        { title: '用户名', dataIndex: 'username', width: 120 },
        { title: '姓名', dataIndex: 'full_name', width: 120 },
        {
            title: '角色',
            dataIndex: 'role',
            width: 150,
            render: (role: string, record: ProjectMember) =>
                canManage && record.user_id !== currentUser?.id ? (
                    <Select
                        size="small"
                        value={role}
                        style={{ width: 100 }}
                        onChange={(val) => handleRoleChange(record, val)}
                        options={roleOptions}
                    />
                ) : (
                    <Tag
                        color={
                            roleItems.find((r) => r.code === role)?.extra ||
                            'default'
                        }>
                        {roleItems.find((r) => r.code === role)?.label ?? role}
                    </Tag>
                ),
        },
        {
            title: '加入时间',
            dataIndex: 'joined_at',
            width: 170,
            render: (val: string) =>
                val ? new Date(val).toLocaleString('zh-CN') : '-',
        },
        ...(canManage
            ? [
                  {
                      title: '操作',
                      width: 80,
                      render: (_: unknown, record: ProjectMember) =>
                          record.user_id !== currentUser?.id ? (
                              <Button
                                  size="small"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={() => handleRemove(record)}
                              />
                          ) : null,
                  },
              ]
            : []),
    ]

    const candidateColumns = [
        { title: '用户名', dataIndex: 'username', width: 120, ellipsis: true },
        { title: '姓名', dataIndex: 'full_name', width: 140, ellipsis: true },
        { title: '邮箱', dataIndex: 'email', width: 180, ellipsis: true },
        {
            title: '系统角色',
            dataIndex: 'system_roles',
            width: 180,
            render: (roles: string[]) =>
                roles.length > 0 ? (
                    <Space size={[0, 4]} wrap>
                        {roles.map((role) => (
                            <Tag key={role} color="blue">
                                {systemRoleItems.find(
                                    (item) => item.code === role,
                                )?.label ?? role}
                            </Tag>
                        ))}
                    </Space>
                ) : (
                    '-'
                ),
        },
    ]

    return (
        <Card
            title="项目成员"
            extra={
                canManage && (
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openAddModal}>
                        添加成员
                    </Button>
                )
            }>
            <Table
                dataSource={members}
                columns={columns}
                rowKey="id"
                pagination={false}
            />

            <Modal
                title="添加成员"
                open={addModalOpen}
                width="min(90vw, 760px)"
                onOk={handleAdd}
                onCancel={() => {
                    setAddModalOpen(false)
                    setSelectedUserId(undefined)
                }}
                confirmLoading={adding}
                okText="添加"
                cancelText="取消"
                okButtonProps={{ disabled: !selectedUserId }}>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <Input.Search
                        placeholder="搜索用户名、姓名或邮箱"
                        allowClear
                        value={candidateKeyword}
                        onChange={(event) =>
                            setCandidateKeyword(event.target.value)
                        }
                        onSearch={(value) =>
                            fetchCandidateUsers({ keyword: value, page: 1 })
                        }
                    />
                    <Table
                        size="small"
                        rowKey="id"
                        columns={candidateColumns}
                        dataSource={candidateUsers}
                        loading={candidateLoading}
                        tableLayout="fixed"
                        scroll={{ x: 620 }}
                        rowSelection={{
                            type: 'radio',
                            selectedRowKeys: selectedUserId
                                ? [selectedUserId]
                                : [],
                            onChange: (selectedRowKeys) =>
                                setSelectedUserId(selectedRowKeys[0] as string),
                        }}
                        pagination={{
                            current: candidatePage,
                            pageSize: candidatePageSize,
                            total: candidateTotal,
                            size: 'small',
                            showSizeChanger: true,
                            showTotal: (total) => `共 ${total} 人`,
                            onChange: (page, pageSize) =>
                                fetchCandidateUsers({
                                    page,
                                    pageSize,
                                }),
                        }}
                    />
                    <div>
                        <label style={{ display: 'block', marginBottom: 4 }}>
                            项目角色
                        </label>
                        <Select
                            style={{ width: '100%' }}
                            value={selectedRole}
                            onChange={setSelectedRole}
                            options={roleOptions}
                        />
                    </div>
                </Space>
            </Modal>
        </Card>
    )
}
