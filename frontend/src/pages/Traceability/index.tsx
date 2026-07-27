import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  Table,
  Tag,
  Alert,
  message,
} from 'antd';
import {
  traceabilityService,
  TraceMatrixResponse,
  UrsTraceRow,
  UrsTraceReference,
  UncoveredUrsItem,
} from '@/services/traceability';
import { isUncoveredHighlighted } from '@/utils/ursDisplay';

export default function TraceabilityPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<TraceMatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchMatrix = async () => {
    setLoading(true);
    try {
      const res = await traceabilityService.getMatrix(projectId);
      setData(res.data);
    } catch {
      message.error('加载追溯矩阵失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!projectId) return;
    fetchMatrix();
  }, [projectId]);

  const uncoveredUrsIds = (data?.uncovered_urs_items || []).map((item) => item.id);

  // URS 条目覆盖追溯矩阵：每行一个 URS 条目，展示引用（覆盖）它的下游文档。
  const matrixColumns = [
    {
      title: '条目编号',
      dataIndex: 'item_code',
      width: 160,
      render: (val: string, record: UrsTraceRow) => (
        <span style={{ color: isUncoveredHighlighted(record.urs_item_id, uncoveredUrsIds) ? '#ff4d4f' : undefined }}>
          {val}
        </span>
      ),
    },
    {
      title: '条目描述',
      dataIndex: 'description',
      ellipsis: true,
      render: (val: string, record: UrsTraceRow) => (
        <span style={{ color: isUncoveredHighlighted(record.urs_item_id, uncoveredUrsIds) ? '#ff4d4f' : undefined }}>
          {val}
        </span>
      ),
    },
    {
      title: '覆盖状态',
      dataIndex: 'covered',
      width: 100,
      render: (covered: boolean) =>
        covered ? <Tag color="green">已覆盖</Tag> : <Tag color="red">未覆盖</Tag>,
    },
    {
      title: '被引用文档 (下游追溯)',
      dataIndex: 'references',
      render: (references: UrsTraceReference[]) =>
        references.length > 0 ? (
          <span>
            {references.map((ref) => (
              <Tag color="blue" key={ref.document_id}>
                {ref.doc_type} {ref.doc_number}
              </Tag>
            ))}
          </span>
        ) : (
          <span style={{ color: '#999' }}>暂无</span>
        ),
    },
  ];

  const uncoveredUrsColumns = [
    {
      title: '条目编号',
      dataIndex: 'item_code',
      width: 160,
      render: (val: string, record: UncoveredUrsItem) => (
        <span style={{ color: isUncoveredHighlighted(record.id, uncoveredUrsIds) ? '#ff4d4f' : undefined }}>
          {val}
        </span>
      ),
    },
    {
      title: '条目描述',
      dataIndex: 'description',
      render: (val: string, record: UncoveredUrsItem) => (
        <span style={{ color: isUncoveredHighlighted(record.id, uncoveredUrsIds) ? '#ff4d4f' : undefined }}>
          {val}
        </span>
      ),
    },
  ];

  return (
    <div>
      {/* 未覆盖 URS 条目 */}
      {data && data.uncovered_urs_items.length > 0 && (
        <Card
          title={<span style={{ color: '#ff4d4f' }}>未覆盖 URS 条目 ({data.uncovered_urs_items.length})</span>}
          style={{ marginBottom: 16 }}
        >
          <Alert
            message="以下 URS 条目尚未被任何 FS/DS/IQ/OQ/PQ 文档引用，建议及时补充追溯关系"
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
          />
          <Table
            rowKey="id"
            columns={uncoveredUrsColumns}
            dataSource={data.uncovered_urs_items}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* URS 条目覆盖追溯矩阵 */}
      <Card title={`URS 条目追溯矩阵 (${data?.urs_matrix.length || 0})`}>
        <Table
          rowKey="urs_item_id"
          columns={matrixColumns}
          dataSource={data?.urs_matrix || []}
          loading={loading}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
          size="small"
          locale={{ emptyText: '暂无 URS 条目' }}
        />
      </Card>
    </div>
  );
}
