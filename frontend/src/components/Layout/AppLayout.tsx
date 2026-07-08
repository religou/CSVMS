import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Dropdown, Avatar, Space } from 'antd'
import {
    DashboardOutlined,
    SettingOutlined,
    UserOutlined,
    LogoutOutlined,
    TeamOutlined,
    BookOutlined,
    SafetyCertificateOutlined,
    ClusterOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'

const { Header, Sider, Content } = Layout

export default function AppLayout() {
    const { t, i18n } = useTranslation()
    const navigate = useNavigate()
    const location = useLocation()
    const { user, logout } = useAuthStore()
    const [collapsed, setCollapsed] = useState(false)

    const permissions = user?.permissions ?? []

    const adminChildren = [
        permissions.includes('system.admin.users.menu')
            ? {
                  key: '/admin/users',
                  icon: <TeamOutlined />,
                  label: '用户管理',
              }
            : null,
        permissions.includes('system.admin.dict.menu')
            ? {
                  key: '/admin/dict',
                  icon: <BookOutlined />,
                  label: '字典管理',
              }
            : null,
        permissions.includes('system.admin.roles.menu')
            ? {
                  key: '/admin/roles',
                  icon: <SafetyCertificateOutlined />,
                  label: '权限管理',
              }
            : null,
    ].filter((item): item is NonNullable<typeof item> => item !== null)

    const canAccessAdminMenu =
        permissions.includes('system.admin.menu') && adminChildren.length > 0

    const menuItems = [
        {
            key: '/systems',
            icon: <ClusterOutlined />,
            label: '系统管理',
        },
        {
            key: '/',
            icon: <DashboardOutlined />,
            label: '验证项目',
        },
        ...(canAccessAdminMenu
            ? [
                  {
                      key: '/admin',
                      icon: <SettingOutlined />,
                      label: '系统设置',
                      children: adminChildren,
                  },
              ]
            : []),
    ]

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    const toggleLanguage = () => {
        const next = i18n.language === 'zh-CN' ? 'en-US' : 'zh-CN'
        i18n.changeLanguage(next)
    }

    const userMenu = {
        items: [
            {
                key: 'lang',
                label: i18n.language === 'zh-CN' ? 'English' : '中文',
                onClick: toggleLanguage,
            },
            {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: t('auth.logout'),
                onClick: handleLogout,
            },
        ],
    }

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
                <div
                    style={{
                        height: 32,
                        margin: 16,
                        color: '#fff',
                        textAlign: 'center',
                        fontSize: collapsed ? 14 : 18,
                        fontWeight: 'bold',
                    }}>
                    {collapsed ? 'CS' : 'CSVS'}
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    defaultOpenKeys={[]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                />
            </Sider>
            <Layout>
                <Header
                    style={{
                        padding: '0 24px',
                        background: '#fff',
                        display: 'flex',
                        justifyContent: 'flex-end',
                        alignItems: 'center',
                    }}>
                    <Dropdown menu={userMenu} placement="bottomRight">
                        <Space style={{ cursor: 'pointer' }}>
                            <Avatar icon={<UserOutlined />} />
                            <span>{user?.full_name || user?.username}</span>
                        </Space>
                    </Dropdown>
                </Header>
                <Content
                    style={{
                        margin: 24,
                        padding: 24,
                        background: '#fff',
                        borderRadius: 8,
                    }}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    )
}
