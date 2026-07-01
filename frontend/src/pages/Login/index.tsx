import { useState } from 'react'
import { Form, Input, Button, Card, Typography, message, Tabs } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authService } from '@/services/auth'
import { getErrorMessage } from '@/services/apiClient'

const { Title } = Typography

export default function LoginPage() {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const { setTokens, setUser } = useAuthStore()
    const [loading, setLoading] = useState(false)

    const handleLogin = async (values: {
        username: string
        password: string
    }) => {
        setLoading(true)
        try {
            const { data } = await authService.login(values)
            setTokens(data.access_token, data.refresh_token)
            const { data: user } = await authService.getMe()
            setUser(user)
            message.success(t('auth.loginSuccess'))
            navigate('/')
        } catch (err: unknown) {
            message.error(getErrorMessage(err, t('auth.loginFailed')))
        } finally {
            setLoading(false)
        }
    }

    const handleRegister = async (values: {
        username: string
        email: string
        full_name: string
        password: string
    }) => {
        setLoading(true)
        try {
            await authService.register(values)
            message.success('注册成功，请登录')
        } catch (err: unknown) {
            message.error(getErrorMessage(err, '注册失败'))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div
            style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                background: '#f0f2f5',
            }}>
            <Card
                style={{ width: 420, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
                <Title
                    level={3}
                    style={{ textAlign: 'center', marginBottom: 24 }}>
                    {t('app.title')}
                </Title>

                <Tabs
                    defaultActiveKey="login"
                    centered
                    items={[
                        {
                            key: 'login',
                            label: t('auth.login'),
                            children: (
                                <Form onFinish={handleLogin} size="large">
                                    <Form.Item
                                        name="username"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入用户名',
                                            },
                                        ]}>
                                        <Input
                                            prefix={<UserOutlined />}
                                            placeholder={t('auth.username')}
                                        />
                                    </Form.Item>
                                    <Form.Item
                                        name="password"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入密码',
                                            },
                                        ]}>
                                        <Input.Password
                                            prefix={<LockOutlined />}
                                            placeholder={t('auth.password')}
                                        />
                                    </Form.Item>
                                    <Form.Item>
                                        <Button
                                            type="primary"
                                            htmlType="submit"
                                            block
                                            loading={loading}>
                                            {t('auth.login')}
                                        </Button>
                                    </Form.Item>
                                </Form>
                            ),
                        },
                        {
                            key: 'register',
                            label: t('auth.register'),
                            children: (
                                <Form onFinish={handleRegister} size="large">
                                    <Form.Item
                                        name="username"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入用户名',
                                            },
                                            {
                                                min: 3,
                                                max: 50,
                                                message:
                                                    '用户名长度必须在3-50字符之间',
                                            },
                                            {
                                                pattern: /^[a-zA-Z0-9_]+$/,
                                                message:
                                                    '用户名只能包含字母、数字和下划线',
                                            },
                                        ]}>
                                        <Input
                                            prefix={<UserOutlined />}
                                            placeholder={t('auth.username')}
                                        />
                                    </Form.Item>
                                    <Form.Item
                                        name="email"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入邮箱',
                                            },
                                            {
                                                type: 'email',
                                                message: '邮箱格式不正确',
                                            },
                                        ]}>
                                        <Input
                                            prefix={<MailOutlined />}
                                            placeholder={t('auth.email')}
                                        />
                                    </Form.Item>
                                    <Form.Item
                                        name="full_name"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入姓名',
                                            },
                                        ]}>
                                        <Input
                                            prefix={<UserOutlined />}
                                            placeholder={t('auth.fullName')}
                                        />
                                    </Form.Item>
                                    <Form.Item
                                        name="password"
                                        rules={[
                                            {
                                                required: true,
                                                message: '请输入密码',
                                            },
                                            {
                                                min: 8,
                                                message: '密码长度不能少于8位',
                                            },
                                            {
                                                pattern: /[A-Z]/,
                                                message:
                                                    '密码必须包含至少一个大写字母',
                                            },
                                            {
                                                pattern: /[a-z]/,
                                                message:
                                                    '密码必须包含至少一个小写字母',
                                            },
                                            {
                                                pattern: /\d/,
                                                message:
                                                    '密码必须包含至少一个数字',
                                            },
                                            {
                                                pattern:
                                                    /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]/,
                                                message:
                                                    '密码必须包含至少一个特殊字符',
                                            },
                                        ]}>
                                        <Input.Password
                                            prefix={<LockOutlined />}
                                            placeholder={t('auth.password')}
                                        />
                                    </Form.Item>
                                    <Form.Item>
                                        <Button
                                            type="primary"
                                            htmlType="submit"
                                            block
                                            loading={loading}>
                                            {t('auth.register')}
                                        </Button>
                                    </Form.Item>
                                </Form>
                            ),
                        },
                    ]}
                />
            </Card>
        </div>
    )
}
