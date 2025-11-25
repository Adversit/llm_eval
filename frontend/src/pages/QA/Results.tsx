import { useState, useMemo } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  Typography,
  Space,
  Button,
  Empty,
  Spin,
  message,
  Modal,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { qaService } from '@/services/qaService'

const { Title, Text } = Typography

// 企业级配色
const CHART_COLORS = ['#0052D9', '#00A870', '#FF8800', '#D54941']

const QAResults = () => {
  const [previewModalVisible, setPreviewModalVisible] = useState(false)
  const [previewData, setPreviewData] = useState<any>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // 获取所有任务数据
  const { data: tasksData, isLoading, refetch } = useQuery({
    queryKey: ['allQATasks'],
    queryFn: qaService.getAllTasks,
    refetchInterval: 5000,
  })

  // 计算统计数据
  const stats = useMemo(() => {
    if (!tasksData?.tasks) {
      return {
        total: 0,
        completed: 0,
        processing: 0,
        failed: 0,
        completionRate: 0,
      }
    }

    const tasks = tasksData.tasks
    const completed = tasks.filter((t: any) => t.status === 'completed').length
    const processing = tasks.filter((t: any) => t.status === 'processing').length
    const failed = tasks.filter((t: any) => t.status === 'failed').length

    return {
      total: tasks.length,
      completed,
      processing,
      failed,
      completionRate: tasks.length > 0 ? ((completed / tasks.length) * 100).toFixed(1) : 0,
    }
  }, [tasksData])

  // 图表数据
  const chartData = [
    { name: '已完成', value: stats.completed },
    { name: '进行中', value: stats.processing },
    { name: '失败', value: stats.failed },
  ].filter(item => item.value > 0)

  // 格式化任务数据
  const tableData = useMemo(() => {
    if (!tasksData?.tasks) return []

    return tasksData.tasks.map((task: any) => ({
      key: task.task_id,
      taskId: task.task_id,
      file: task.filename,
      taskType: task.task_type === 'generation' ? '问答生成' : 
                task.task_type === 'evaluation' ? '质量评估' : 
                '未知类型',
      status: task.status,
      progress: task.progress || 0,
      time: task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-',
      message: task.message,
    }))
  }, [tasksData])

  const handleDownload = async (taskId: string) => {
    try {
      await qaService.downloadResult(taskId)
      message.success('下载成功')
    } catch (error) {
      message.error('下载失败')
    }
  }

  const handlePreview = async (taskId: string) => {
    try {
      setPreviewLoading(true)
      setPreviewModalVisible(true)
      const data = await qaService.previewResult(taskId, 100)
      setPreviewData(data)
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '预览失败')
      setPreviewModalVisible(false)
    } finally {
      setPreviewLoading(false)
    }
  }

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'taskId',
      key: 'taskId',
      width: 120,
      render: (text: string) => (
        <Text code style={{ fontSize: 12 }}>
          {text.slice(0, 8)}...
        </Text>
      ),
    },
    {
      title: '任务类型',
      dataIndex: 'taskType',
      key: 'taskType',
      width: 100,
      render: (type: string) => (
        <Tag color={type === '问答生成' ? 'blue' : 'green'}>
          {type}
        </Tag>
      ),
      filters: [
        { text: '问答生成', value: '问答生成' },
        { text: '质量评估', value: '质量评估' },
      ],
      onFilter: (value: any, record: any) => record.taskType === value,
    },
    {
      title: '文件名',
      dataIndex: 'file',
      key: 'file',
      ellipsis: true,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number, record: any) => (
        <Progress
          percent={progress}
          size="small"
          status={
            record.status === 'failed' ? 'exception' :
            record.status === 'completed' ? 'success' :
            'active'
          }
          strokeColor={
            record.status === 'completed' ? '#00A870' :
            record.status === 'failed' ? '#D54941' :
            '#0052D9'
          }
        />
      ),
      sorter: (a: any, b: any) => a.progress - b.progress,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = {
          completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
          processing: { color: 'processing', icon: <SyncOutlined spin />, text: '处理中' },
          failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
          pending: { color: 'default', icon: <SyncOutlined />, text: '等待中' },
        }[status] || { color: 'default', icon: null, text: status }

        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        )
      },
      filters: [
        { text: '已完成', value: 'completed' },
        { text: '处理中', value: 'processing' },
        { text: '失败', value: 'failed' },
      ],
      onFilter: (value: any, record: any) => record.status === value,
    },
    {
      title: '创建时间',
      dataIndex: 'time',
      key: 'time',
      width: 180,
      sorter: (a: any, b: any) => new Date(a.time).getTime() - new Date(b.time).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            size="small"
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.taskId)}
            disabled={record.status !== 'completed'}
          >
            预览
          </Button>
          <Button
            size="small"
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.taskId)}
            disabled={record.status !== 'completed'}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ]

  // 动态生成预览表格列
  const previewColumns = useMemo(() => {
    if (!previewData?.columns) {
      return []
    }

    return previewData.columns.map((col: string, index: number) => ({
      title: col,
      dataIndex: col,
      key: col,
      ellipsis: { showTitle: true },
      width: index === 0 ? 200 : undefined,
    }))
  }, [previewData])

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载数据中..." />
      </div>
    )
  }

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 8 }}>
        <Space size="small">
          <Title level={4} style={{ margin: 0, fontSize: 16 }}>
            数据集生成结果
          </Title>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            size="small"
            style={{ fontSize: 11 }}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={6} style={{ marginBottom: 8 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '8px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 10 }}>总任务数</Text>}
              value={stats.total}
              valueStyle={{ color: '#252B3A', fontWeight: 600, fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '8px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 10 }}>已完成</Text>}
              value={stats.completed}
              valueStyle={{ color: '#00A870', fontWeight: 600, fontSize: 16 }}
              prefix={<CheckCircleOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '8px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 10 }}>进行中</Text>}
              value={stats.processing}
              valueStyle={{ color: '#0052D9', fontWeight: 600, fontSize: 16 }}
              prefix={<SyncOutlined spin={stats.processing > 0} style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '8px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 10 }}>失败</Text>}
              value={stats.failed}
              valueStyle={{ color: '#D54941', fontWeight: 600, fontSize: 16 }}
              prefix={<CloseCircleOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      {chartData.length > 0 && (
        <Card
          bordered={false}
          style={{ marginBottom: 8, borderRadius: 4 }}
          styles={{ body: { padding: '8px' } }}
          title={<Text strong style={{ fontSize: 12 }}>任务状态分布</Text>}
        >
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={60}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* 任务列表 */}
      <Card
        bordered={false}
        style={{ borderRadius: 4 }}
        styles={{ body: { padding: '8px' } }}
        title={<Text strong style={{ fontSize: 12 }}>任务列表</Text>}
      >
        {tableData.length > 0 ? (
          <Table
            columns={columns}
            dataSource={tableData}
            pagination={{
              pageSize: 10,
              showTotal: (total) => `共 ${total} 条记录`,
              showSizeChanger: true,
              showQuickJumper: true,
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        ) : (
          <Empty description="暂无任务记录" />
        )}
      </Card>

      {/* 预览弹窗 */}
      <Modal
        title={`结果预览${previewData?.filename ? ` - ${previewData.filename}` : ''}`}
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        width={1200}
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" />
          </div>
        ) : previewData ? (
          <>
            {previewData.total_rows && (
              <div style={{ marginBottom: 12, color: '#666' }}>
                显示 {previewData.preview_rows} / {previewData.total_rows} 条记录
              </div>
            )}
            <Table
              columns={previewColumns}
              dataSource={previewData.data || []}
              pagination={{
                pageSize: 10,
                showTotal: (total) => `共 ${total} 条`,
              }}
              size="small"
              scroll={{ x: 'max-content', y: 400 }}
              rowKey={(_, index) => (index !== undefined ? index.toString() : '0')}
            />
          </>
        ) : (
          <Empty description="暂无数据" />
        )}
      </Modal>
    </div>
  )
}

export default QAResults
