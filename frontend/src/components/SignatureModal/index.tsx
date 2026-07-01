import { useState } from 'react'
import { Modal, Form, Input, Select, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { signatureService } from '@/services/signatures'

const MEANING_OPTIONS = [
    { value: '我已起草此文档', label: '起草' },
    { value: '我已审核此文档，内容准确完整', label: '审核' },
    { value: '我已批准此文档，同意生效', label: '批准' },
]

interface SignatureModalProps {
    open: boolean
    documentId: string
    workflowId?: string
    workflowStepId?: string
    defaultMeaning?: string
    onSuccess?: () => void
    onCancel?: () => void
}

export default function SignatureModal({
    open,
    documentId,
    workflowId,
    workflowStepId,
    defaultMeaning,
    onSuccess,
    onCancel,
}: SignatureModalProps) {
    const [form] = Form.useForm()
    const [loading, setLoading] = useState(false)

    const handleSign = async () => {
        try {
            const values = await form.validateFields()
            setLoading(true)
            await signatureService.sign({
                username: values.username,
                password: values.password,
                document_id: documentId,
                meaning: values.meaning,
                workflow_id: workflowId,
                workflow_step_id: workflowStepId,
            })
            message.success('电子签名成功')
            form.resetFields()
            onSuccess?.()
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            message.error(detail || '签名失败')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal
            title="电子签名 (21 CFR Part 11)"
            open={open}
            onOk={handleSign}
            onCancel={() => {
                form.resetFields()
                onCancel?.()
            }}
            confirmLoading={loading}
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
                根据 21 CFR Part 11 要求，电子签名需重新验证您的身份。
                签名将绑定到当前文档版本，不可篡改。
            </div>
            <Form
                form={form}
                layout="vertical"
                initialValues={{
                    meaning: defaultMeaning || MEANING_OPTIONS[1]!.value,
                }}>
                <Form.Item
                    name="username"
                    label="用户名"
                    rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input
                        prefix={<UserOutlined />}
                        placeholder="请重新输入用户名"
                    />
                </Form.Item>
                <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="请重新输入密码"
                    />
                </Form.Item>
                <Form.Item
                    name="meaning"
                    label="签名含义"
                    rules={[{ required: true, message: '请选择签名含义' }]}>
                    <Select options={MEANING_OPTIONS} />
                </Form.Item>
            </Form>
        </Modal>
    )
}
