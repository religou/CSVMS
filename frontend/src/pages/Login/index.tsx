import { useState } from 'react'
import { Form, Input, Button, Card, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
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

    return (
        <div
            style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                background:
                    'linear-gradient(135deg, #1677ff 0%, #4096ff 45%, #7cb9ff 100%)',
                backgroundSize: 'cover',
            }}>
            <Card
                style={{
                    width: 420,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                }}>
                <Title
                    level={3}
                    style={{ textAlign: 'center', marginBottom: 24 }}>
                    {t('app.title')}
                </Title>

                <Form onFinish={handleLogin} size="large">
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: '请输入用户名' }]}>
                        <Input
                            prefix={<UserOutlined />}
                            placeholder={t('auth.username')}
                        />
                    </Form.Item>
                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入密码' }]}>
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
            </Card>
        </div>
    )
}
