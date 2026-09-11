import { useState } from 'react'
import { Modal, Form, Input } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'

interface SignatureModalProps {
    open: boolean
    /** 当前登录用户名（只读展示，不可修改，防止冒签） */
    username: string
    /** 本次签名的法律含义（只读展示，由调用方按动作/步骤生成） */
    meaning: string
    confirmLoading?: boolean
    /** 确认后回调，返回重新输入的密码由调用方去执行批准/拒绝 */
    onConfirm: (password: string) => void
    onCancel?: () => void
}

export default function SignatureModal({
    open,
    username,
    meaning,
    confirmLoading,
    onConfirm,
    onCancel,
}: SignatureModalProps) {
    const [form] = Form.useForm()
    const [submitting, setSubmitting] = useState(false)

    const handleOk = async () => {
        try {
            setSubmitting(true)
            const values = await form.validateFields()
            onConfirm(values.password)
        } catch {
            // 校验失败，保持弹窗打开
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Modal
            title="电子签名 (21 CFR Part 11)"
            open={open}
            onOk={handleOk}
            onCancel={() => {
                form.resetFields()
                onCancel?.()
            }}
            confirmLoading={confirmLoading || submitting}
            okText="确认签名"
            cancelText="取消"
            destroyOnClose>
            <div
                style={{
                    marginBottom: 16,
                    padding: 12,
                    background: '#fffbe6',
                    borderRadius: 4,
                    fontSize: 12,
                }}>
                根据 21 CFR Part 11 要求，此操作需重新输入密码进行电子签名。
                签名将绑定到当前文档版本，不可篡改。
            </div>
            <Form form={form} layout="vertical">
                <Form.Item label="签名人">
                    <Input
                        prefix={<UserOutlined />}
                        value={username}
                        disabled
                    />
                </Form.Item>
                <Form.Item label="签名含义">
                    <Input value={meaning} disabled />
                </Form.Item>
                <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="请重新输入登录密码"
                        autoFocus
                    />
                </Form.Item>
            </Form>
        </Modal>
    )
}
