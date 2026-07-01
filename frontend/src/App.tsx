import type { ReactNode } from 'react'
import {
    Routes,
    Route,
    Navigate,
    useNavigate,
    useParams,
} from 'react-router-dom'
import { Button, Result, Spin } from 'antd'
import { useAuthStore } from '@/stores/authStore'
import { useProjectStore } from '@/stores/projectStore'
import { AppLayout, ProjectLayout } from '@/components/Layout'
import LoginPage from '@/pages/Login'
import AdminPage from '@/pages/Admin'
import RoleManagementPage from '@/pages/Admin/Roles'
import DictManagementPage from '@/pages/Admin/DictManagement'
import ProjectsPage from '@/pages/Projects'
import DocumentsPage from '@/pages/Documents'
import DocumentDetailPage from '@/pages/Documents/Detail'
import WorkflowsPage from '@/pages/Workflows'
import AuditLogPage from '@/pages/AuditLog'
import TraceabilityPage from '@/pages/Traceability'
import DashboardPage from '@/pages/Dashboard'
import MembersPage from '@/pages/Members'
import SystemsPage from '@/pages/Systems'

const ADMIN_ROUTE_TARGETS = [
    {
        path: '/admin/users',
        permissions: ['system.admin.users.menu', 'system.admin.users.view'],
    },
    {
        path: '/admin/roles',
        permissions: ['system.admin.roles.menu', 'system.admin.roles.view'],
    },
    {
        path: '/admin/dict',
        permissions: ['system.admin.dict.menu', 'system.admin.dict.view'],
    },
]

const PROJECT_ROUTE_TARGETS = [
    {
        path: 'dashboard',
        permissions: ['project.dashboard.menu', 'project.dashboard.view'],
    },
    {
        path: 'documents',
        permissions: ['project.documents.menu', 'project.documents.view'],
    },
    {
        path: 'workflows',
        permissions: ['project.workflows.menu', 'project.workflows.view'],
    },
    {
        path: 'traceability',
        permissions: ['project.traceability.menu', 'project.traceability.view'],
    },
    {
        path: 'audit-log',
        permissions: ['project.audit_log.menu', 'project.audit_log.view'],
    },
    {
        path: 'members',
        permissions: ['project.members.menu', 'project.members.view'],
    },
]

function PermissionDeniedPage({ description }: { description: string }) {
    const navigate = useNavigate()

    return (
        <Result
            status="403"
            title="无权访问"
            subTitle={description}
            extra={
                <Button type="primary" onClick={() => navigate('/')}>
                    返回首页
                </Button>
            }
        />
    )
}

function LoadingPage() {
    return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
            <Spin size="large" />
        </div>
    )
}

function hasAllPermissions(
    grantedPermissions: string[],
    requiredPermissions: string[],
) {
    return requiredPermissions.every((permission) =>
        grantedPermissions.includes(permission),
    )
}

function RequireSystemPermissions({
    requiredPermissions,
    description,
    children,
}: {
    requiredPermissions: string[]
    description: string
    children: ReactNode
}) {
    const permissions = useAuthStore((state) => state.user?.permissions ?? [])

    if (!hasAllPermissions(permissions, requiredPermissions)) {
        return <PermissionDeniedPage description={description} />
    }

    return <>{children}</>
}

function RequireProjectPermissions({
    requiredPermissions,
    description,
    children,
}: {
    requiredPermissions: string[]
    description: string
    children: ReactNode
}) {
    const { projectId } = useParams<{ projectId: string }>()
    const currentProject = useProjectStore((state) => state.currentProject)

    if (!projectId || !currentProject || currentProject.id !== projectId) {
        return <LoadingPage />
    }

    if (
        !hasAllPermissions(
            currentProject.current_user_permissions ?? [],
            requiredPermissions,
        )
    ) {
        return <PermissionDeniedPage description={description} />
    }

    return <>{children}</>
}

function AdminIndexRedirect() {
    const permissions = useAuthStore((state) => state.user?.permissions ?? [])
    const firstAccessibleTarget = ADMIN_ROUTE_TARGETS.find((target) =>
        hasAllPermissions(permissions, target.permissions),
    )

    if (!firstAccessibleTarget) {
        return (
            <PermissionDeniedPage description="当前账号缺少系统设置页面访问权限。" />
        )
    }

    return <Navigate to={firstAccessibleTarget.path} replace />
}

function ProjectIndexRedirect() {
    const { projectId } = useParams<{ projectId: string }>()
    const currentProject = useProjectStore((state) => state.currentProject)

    if (!projectId || !currentProject || currentProject.id !== projectId) {
        return <LoadingPage />
    }

    const firstAccessibleTarget = PROJECT_ROUTE_TARGETS.find((target) =>
        hasAllPermissions(
            currentProject.current_user_permissions ?? [],
            target.permissions,
        ),
    )

    if (!firstAccessibleTarget) {
        return (
            <PermissionDeniedPage description="当前账号缺少该项目的页面访问权限。" />
        )
    }

    return (
        <Navigate
            to={`/projects/${projectId}/${firstAccessibleTarget.path}`}
            replace
        />
    )
}

function App() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

    if (!isAuthenticated) {
        return (
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        )
    }

    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route path="/" element={<ProjectsPage />} />
                <Route path="/systems" element={<SystemsPage />} />
                <Route path="/admin" element={<AdminIndexRedirect />} />
                <Route
                    path="/admin/users"
                    element={
                        <RequireSystemPermissions
                            requiredPermissions={[
                                'system.admin.users.menu',
                                'system.admin.users.view',
                            ]}
                            description="当前账号缺少用户管理页面访问权限。">
                            <AdminPage />
                        </RequireSystemPermissions>
                    }
                />
                <Route
                    path="/admin/roles"
                    element={
                        <RequireSystemPermissions
                            requiredPermissions={[
                                'system.admin.roles.menu',
                                'system.admin.roles.view',
                            ]}
                            description="当前账号缺少权限管理页面访问权限。">
                            <RoleManagementPage />
                        </RequireSystemPermissions>
                    }
                />
                <Route
                    path="/admin/dict"
                    element={
                        <RequireSystemPermissions
                            requiredPermissions={[
                                'system.admin.dict.menu',
                                'system.admin.dict.view',
                            ]}
                            description="当前账号缺少字典管理页面访问权限。">
                            <DictManagementPage />
                        </RequireSystemPermissions>
                    }
                />
                <Route path="/projects/:projectId" element={<ProjectLayout />}>
                    <Route index element={<ProjectIndexRedirect />} />
                    <Route
                        path="dashboard"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.dashboard.menu',
                                    'project.dashboard.view',
                                ]}
                                description="当前账号缺少项目概览页面访问权限。">
                                <DashboardPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="documents"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.documents.menu',
                                    'project.documents.view',
                                ]}
                                description="当前账号缺少项目文档页面访问权限。">
                                <DocumentsPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="documents/:id"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.documents.menu',
                                    'project.documents.view',
                                ]}
                                description="当前账号缺少项目文档页面访问权限。">
                                <DocumentDetailPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="workflows"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.workflows.menu',
                                    'project.workflows.view',
                                ]}
                                description="当前账号缺少项目审批页面访问权限。">
                                <WorkflowsPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="traceability"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.traceability.menu',
                                    'project.traceability.view',
                                ]}
                                description="当前账号缺少追溯矩阵页面访问权限。">
                                <TraceabilityPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="audit-log"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.audit_log.menu',
                                    'project.audit_log.view',
                                ]}
                                description="当前账号缺少项目审计日志页面访问权限。">
                                <AuditLogPage />
                            </RequireProjectPermissions>
                        }
                    />
                    <Route
                        path="members"
                        element={
                            <RequireProjectPermissions
                                requiredPermissions={[
                                    'project.members.menu',
                                    'project.members.view',
                                ]}
                                description="当前账号缺少项目成员页面访问权限。">
                                <MembersPage />
                            </RequireProjectPermissions>
                        }
                    />
                </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}

export default App
