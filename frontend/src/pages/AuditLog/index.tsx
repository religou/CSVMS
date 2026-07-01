import { useState, useEffect, useCallback } from 'react'
import {
    Table,
    Card,
    Tag,
    Select,
    DatePicker,
    Row,
    Col,
    Button,
    Descriptions,
    Modal,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { auditService, AuditLogItem } from '@/services/signatures'

const ACTION_OPTIONS = [
    { value: 'CREATE', label: '创建' },
    { value: 'UPDATE', label: '修改' },
    { value: 'DELETE', label: '删除' },
    { value: 'LOGIN', label: '登录' },
    { value: 'LOGOUT', label: '登出' },
    { value: 'SIGN', label: '电子签名' },
    { value: 'APPROVE', label: '审批通过' },
    { value: 'REJECT', label: '审批拒绝' },
]

const RESOURCE_TYPES = [
    { value: 'document', label: '文档' },
    { value: 'user', label: '用户' },
    { value: 'workflow', label: '工作流' },
    { value: 'signature', label: '签名' },
    { value: 'system', label: '系统' },
]

const ACTION_COLORS: Record<string, string> = {
    CREATE: 'green',
    UPDATE: 'blue',
    DELETE: 'red',
    LOGIN: 'cyan',
    LOGOUT: 'default',
    SIGN: 'purple',
    APPROVE: 'green',
    REJECT: 'red',
}

export default function AuditLogPage() {
    const [data, setData] = useState<AuditLogItem[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(50)
    const [loading, setLoading] = useState(false)
    const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null)
    const [filters, setFilters] = useState<{
        resource_type?: string
        action?: string
        start_time?: string
        end_time?: string
    }>({})

    const fetchLogs = useCallback(async () => {
        setLoading(true)
        try {
            const res = await auditService.list({
                ...filters,
                page,
                page_size: pageSize,
            })
            setData(res.data.items)
            setTotal(res.data.total)
        } catch {
            // ignore
        } finally {
            setLoading(false)
        }
    }, [filters, page, pageSize])

    useEffect(() => {
        fetchLogs()
    }, [fetchLogs])

    const columns = [
        {
            title: '时间',
            dataIndex: 'timestamp',
            width: 170,
            render: (val: string) => new Date(val).toLocaleString('zh-CN'),
        },
        {
            title: '操作人',
            dataIndex: 'username',
            width: 100,
        },
        {
            title: '操作',
            dataIndex: 'action',
            width: 100,
            render: (val: string) => (
                <Tag color={ACTION_COLORS[val] || 'default'}>{val}</Tag>
            ),
        },
        {
            title: '资源类型',
            dataIndex: 'resource_type',
            width: 80,
            render: (val: string) => {
                const opt = RESOURCE_TYPES.find((r) => r.value === val)
                return opt?.label || val
            },
        },
        {
            title: '资源',
            dataIndex: 'resource_name',
            ellipsis: true,
            render: (val: string | undefined, record: AuditLogItem) =>
                val || record.resource_id?.slice(0, 8) || '-',
        },
        {
            title: '变更字段',
            dataIndex: 'field_changed',
            width: 100,
            render: (val: string | undefined) => val || '-',
        },
        {
            title: '修改前',
            dataIndex: 'old_value',
            width: 220,
            ellipsis: true,
            render: (val: string | undefined) => val || '-',
        },
        {
            title: '修改后',
            dataIndex: 'new_value',
            width: 220,
            ellipsis: true,
            render: (val: string | undefined) => val || '-',
        },
        {
            title: '原因',
            dataIndex: 'reason',
            width: 180,
            ellipsis: true,
            render: (val: string | undefined) => val || '-',
        },
    ]

    return (
        <div>
            <Card style={{ marginBottom: 16 }}>
                <Row gutter={16} align="middle">
                    <Col>
                        <Select
                            placeholder="资源类型"
                            allowClear
                            style={{ width: 120 }}
                            options={RESOURCE_TYPES}
                            onChange={(val) =>
                                setFilters((f) => ({
                                    ...f,
                                    resource_type: val,
                                }))
                            }
                        />
                    </Col>
                    <Col>
                        <Select
                            placeholder="操作类型"
                            allowClear
                            style={{ width: 120 }}
                            options={ACTION_OPTIONS}
                            onChange={(val) =>
                                setFilters((f) => ({ ...f, action: val }))
                            }
                        />
                    </Col>
                    <Col>
                        <DatePicker.RangePicker
                            onChange={(dates) => {
                                if (dates && dates[0] && dates[1]) {
                                    setFilters((f) => ({
                                        ...f,
                                        start_time: dates[0]!.toISOString(),
                                        end_time: dates[1]!.toISOString(),
                                    }))
                                } else {
                                    setFilters((f) => ({
                                        ...f,
                                        start_time: undefined,
                                        end_time: undefined,
                                    }))
                                }
                            }}
                        />
                    </Col>
                    <Col>
                        <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
                            刷新
                        </Button>
                    </Col>
                </Row>
            </Card>

            <Table
                rowKey="id"
                columns={columns}
                dataSource={data}
                loading={loading}
                onRow={(record) => ({
                    onClick: () => setSelectedLog(record),
                    style: { cursor: 'pointer' },
                })}
                pagination={{
                    current: page,
                    pageSize,
                    total,
                    showSizeChanger: true,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: (p, ps) => {
                        setPage(p)
                        setPageSize(ps)
                    },
                }}
                scroll={{ x: 1400 }}
                size="small"
            />

            <Modal
                title="审计日志详情"
                open={Boolean(selectedLog)}
                onCancel={() => setSelectedLog(null)}
                footer={null}
                width={900}
                destroyOnClose>
                {selectedLog ? (
                    <Descriptions column={1} size="small" bordered>
                        <Descriptions.Item label="时间">
                            {new Date(selectedLog.timestamp).toLocaleString(
                                'zh-CN',
                            )}
                        </Descriptions.Item>
                        <Descriptions.Item label="操作人">
                            {selectedLog.username}
                        </Descriptions.Item>
                        <Descriptions.Item label="操作">
                            {selectedLog.action}
                        </Descriptions.Item>
                        <Descriptions.Item label="资源类型">
                            {RESOURCE_TYPES.find(
                                (resourceType) =>
                                    resourceType.value ===
                                    selectedLog.resource_type,
                            )?.label || selectedLog.resource_type}
                        </Descriptions.Item>
                        <Descriptions.Item label="资源">
                            {selectedLog.resource_name ||
                                selectedLog.resource_id?.slice(0, 8) ||
                                '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="变更字段">
                            {selectedLog.field_changed || '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="修改前">
                            <pre
                                style={{
                                    margin: 0,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                }}>
                                {selectedLog.old_value || '-'}
                            </pre>
                        </Descriptions.Item>
                        <Descriptions.Item label="修改后">
                            <pre
                                style={{
                                    margin: 0,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                }}>
                                {selectedLog.new_value || '-'}
                            </pre>
                        </Descriptions.Item>
                        <Descriptions.Item label="原因">
                            <pre
                                style={{
                                    margin: 0,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                }}>
                                {selectedLog.reason || '-'}
                            </pre>
                        </Descriptions.Item>
                    </Descriptions>
                ) : null}
            </Modal>
        </div>
    )
}
