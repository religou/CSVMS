import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Alert,
  Space,
  Input,
  Button,
  Row,
  Col,
  message,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { traceabilityService, TraceMatrixResponse, TraceLinkItem } from '@/services/traceability';

export default function TraceabilityPage() {
  const [data, setData] = useState<TraceMatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [systemName, setSystemName] = useState<string>('');

  const fetchMatrix = async () => {
    setLoading(true);
    try {
      const res = await traceabilityService.getMatrix(systemName || undefined);
      setData(res.data);
    } catch {
      message.error('加载追溯矩阵失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatrix();
  }, []);

  const linkColumns = [
    {
      title: '源文档',
      render: (_: unknown, record: TraceLinkItem) => (
        <span>
          <Tag>{record.source_doc_type}</Tag>
          {record.source_doc_number} - {record.source_title}
          {record.source_section && <span style={{ color: '#888' }}> §{record.source_section}</span>}
        </span>
      ),
    },
    {
      title: '关系',
      dataIndex: 'link_type',
      width: 100,
      render: (val: string) => <Tag color="blue">{val === 'traces_to' ? '追溯到' : val}</Tag>,
    },
    {
      title: '目标文档',
      render: (_: unknown, record: TraceLinkItem) => (
        <span>
          <Tag>{record.target_doc_type}</Tag>
          {record.target_doc_number} - {record.target_title}
          {record.target_section && <span style={{ color: '#888' }}> §{record.target_section}</span>}
        </span>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      width: 150,
    },
  ];

  const gapColumns = [
    { title: '文档编号', dataIndex: 'doc_number', width: 140 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'doc_type', width: 80, render: (val: string) => <Tag>{val}</Tag> },
    {
      title: '缺失目标',
      dataIndex: 'missing_targets',
      render: (targets: string[]) => targets.map((t) => <Tag color="red" key={t}>{t}</Tag>),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="按系统名称筛选"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
            style={{ width: 200 }}
            onPressEnter={fetchMatrix}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchMatrix} loading={loading}>
            刷新
          </Button>
        </Space>
      </Card>

      {/* 覆盖率统计 */}
      {data && Object.keys(data.coverage).length > 0 && (
        <Card title="覆盖率统计" style={{ marginBottom: 16 }}>
          <Row gutter={24}>
            {Object.entries(data.coverage).map(([docType, info]) => (
              <Col span={6} key={docType} style={{ marginBottom: 16 }}>
                <Card size="small" title={`${docType} → ${info.expected_targets.join('/')}`}>
                  <Progress
                    percent={info.rate}
                    status={info.rate === 100 ? 'success' : info.rate > 50 ? 'normal' : 'exception'}
                    format={(p) => `${p}%`}
                  />
                  <div style={{ fontSize: 12, color: '#666' }}>
                    {info.covered}/{info.total} 已覆盖
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Gap 分析 */}
      {data && data.gaps.length > 0 && (
        <Card
          title={<span style={{ color: '#ff4d4f' }}>Gap 分析 - 未覆盖文档 ({data.gaps.length})</span>}
          style={{ marginBottom: 16 }}
        >
          <Alert
            message="以下文档缺少下游追溯关系，建议补充"
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
          />
          <Table
            rowKey="document_id"
            columns={gapColumns}
            dataSource={data.gaps}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* 追溯关系列表 */}
      <Card title={`追溯关系 (${data?.links.length || 0})`}>
        <Table
          rowKey="id"
          columns={linkColumns}
          dataSource={data?.links || []}
          loading={loading}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
          size="small"
          locale={{ emptyText: '暂无追溯关系' }}
        />
      </Card>
    </div>
  );
}
