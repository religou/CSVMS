import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation, useParams } from 'react-router-dom'
import { Layout, Menu, Button } from 'antd'
import {
    FileTextOutlined,
    CheckCircleOutlined,
    NodeIndexOutlined,
    AuditOutlined,
    ArrowLeftOutlined,
    DashboardOutlined,
    TeamOutlined,
} from '@ant-design/icons'
import { useProjectStore } from '@/stores/projectStore'
import projectService from '@/services/projects'

const { Sider, Content } = Layout

export default function ProjectLayout() {
    const navigate = useNavigate()
    const location = useLocation()
    const { projectId } = useParams<{ projectId: string }>()
    const { currentProject, setCurrentProject } = useProjectStore()

    useEffect(() => {
        if (projectId && (!currentProject || currentProject.id !== projectId)) {
            projectService
                .get(projectId)
                .then(setCurrentProject)
                .catch(() => navigate('/'))
        }
    }, [projectId, currentProject, setCurrentProject, navigate])

    const basePath = `/projects/${projectId}`
    const currentUserPermissions =
        currentProject?.current_user_permissions ?? []

    const menuItems = [
        {
            key: `${basePath}/dashboard`,
            icon: <DashboardOutlined />,
            label: '概览',
            permissionCode: 'project.dashboard.menu',
        },
        {
            key: `${basePath}/documents`,
            icon: <FileTextOutlined />,
            label: '文档管理',
            permissionCode: 'project.documents.menu',
        },
        {
            key: `${basePath}/workflows`,
            icon: <CheckCircleOutlined />,
            label: '审批管理',
            permissionCode: 'project.workflows.menu',
        },
        {
            key: `${basePath}/traceability`,
            icon: <NodeIndexOutlined />,
            label: '追溯矩阵',
            permissionCode: 'project.traceability.menu',
        },
        {
            key: `${basePath}/audit-log`,
            icon: <AuditOutlined />,
            label: '审计日志',
            permissionCode: 'project.audit_log.menu',
        },
        {
            key: `${basePath}/members`,
            icon: <TeamOutlined />,
            label: '项目成员',
            permissionCode: 'project.members.menu',
        },
    ].filter((item) => currentUserPermissions.includes(item.permissionCode))

    const selectedKey = menuItems.find((item) =>
        location.pathname.startsWith(item.key),
    )?.key

    return (
        <Layout style={{ minHeight: '100%' }}>
            <Sider
                width={180}
                theme="light"
                style={{ borderRight: '1px solid #f0f0f0' }}>
                <div
                    style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid #f0f0f0',
                    }}>
                    <Button
                        type="text"
                        size="small"
                        icon={<ArrowLeftOutlined />}
                        onClick={() => navigate('/')}
                        style={{ marginBottom: 8 }}>
                        返回项目列表
                    </Button>
                    <div
                        style={{
                            fontWeight: 600,
                            fontSize: 14,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                        }}
                        title={currentProject?.name}>
                        {currentProject?.name ?? '加载中...'}
                    </div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                        {currentProject?.code}
                    </div>
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={selectedKey ? [selectedKey] : []}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    style={{ borderRight: 0 }}
                />
            </Sider>
            <Content style={{ padding: 24, minHeight: 400 }}>
                <Outlet />
            </Content>
        </Layout>
    )
}
