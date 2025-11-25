import { useState, useEffect, useMemo } from 'react'
import {
  Card,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
  Table,
  Tag,
  Space,
  Empty,
  Spin,
  Button,
  Divider,
  List,
  Alert,
} from 'antd'
import {
  BarChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TrophyOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  RedoOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { motion } from 'framer-motion'
import { evaluationService } from '../../services/evaluationService'
import { useWorkflow } from '@/hooks/useWorkflow'
import { useWorkflowGuard } from '@/hooks/useWorkflowGuard'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph, Text } = Typography
const { Option } = Select

const COLORS = ['#667eea', '#4caf50', '#ff9800', '#f44336']

const EvalAnalysis = () => {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [activeFileName, setActiveFileName] = useState<string | null>(null)
  const [historyModelFilter, setHistoryModelFilter] = useState<string | null>(null)

  const navigate = useNavigate()

  const { canAccessEvaluationAnalysis, resetEvaluation } = useWorkflow()
  useWorkflowGuard({
    canAccess: canAccessEvaluationAnalysis,
    title: '请先完成评估处理',
    content: '您需要先在"评估进程"页面完成评估处理，才能查看分析结果',
    redirectPath: '/eval/process',
    redirectLabel: '前往评估进程',
  })

  const { data: stats } = useQuery({
    queryKey: ['evaluationStats'],
    queryFn: () => evaluationService.getStats(),
  })

  const { data: taskList } = useQuery({
    queryKey: ['evaluationTaskList'],
    queryFn: () => evaluationService.listTasks(),
  })

  const taskOptions = taskList?.tasks ?? []

  useEffect(() => {
    if (!taskOptions.length) return
    if (!selectedTaskId) {
      setSelectedTaskId(taskOptions[0].task_id)
    }
  }, [taskOptions, selectedTaskId])

  const {
    data: results,
    isLoading: resultsLoading,
    error: resultsError,
  } = useQuery({
    queryKey: ['evaluationResults', selectedTaskId],
    queryFn: () => evaluationService.getResults(selectedTaskId!),
    enabled: !!selectedTaskId,
  })

  const { data: downloadLinks } = useQuery({
    queryKey: ['evaluationDownloads', selectedTaskId],
    queryFn: () => evaluationService.getDownloadLinks(selectedTaskId!),
    enabled: !!selectedTaskId,
  })

  const { data: historyResponse } = useQuery({
    queryKey: ['evaluationHistoryList'],
    queryFn: () => evaluationService.listHistory(),
  })

  useEffect(() => {
    if (!results?.results?.files || results.results.files.length === 0) {
      setActiveFileName(null)
      return
    }
    if (!activeFileName || !results.results.files.some(file => file.file_name === activeFileName)) {
      setActiveFileName(results.results.files[0].file_name)
    }
  }, [results, activeFileName])

  const files = results?.results?.files ?? []
  const activeFile = files.find(file => file.file_name === activeFileName) || files[0]
  const summary = results?.results?.summary
  const outcomeStats = activeFile?.final_analysis
  const outcomeData = outcomeStats
    ? [
        { name: '正确', value: outcomeStats.final_correct_answers || 0 },
        { name: '推理错误', value: outcomeStats.final_reasoning_errors || 0 },
        { name: '知识缺失', value: outcomeStats.final_knowledge_deficiency || 0 },
        { name: '能力不足', value: outcomeStats.final_capability_insufficient || 0 },
      ]
    : []

  const roundColumns = [
    { title: '轮次', dataIndex: 'round', key: 'round', width: 100 },
    { title: '需重测', dataIndex: 'needRetest', key: 'needRetest', width: 120 },
    {
      title: 'Stage2 执行',
      dataIndex: 'stage2Executed',
      key: 'stage2Executed',
      width: 140,
      render: (executed: boolean) => (
        <Tag icon={executed ? <CheckCircleOutlined /> : <CloseCircleOutlined />} color={executed ? 'success' : 'default'}>
          {executed ? '已执行' : '未执行'}
        </Tag>
      ),
    },
    { title: '知识缺失', dataIndex: 'knowledgeDeficiency', key: 'knowledgeDeficiency', width: 140 },
    { title: '推理错误', dataIndex: 'reasoningErrors', key: 'reasoningErrors', width: 140 },
    { title: '能力不足', dataIndex: 'capabilityInsufficient', key: 'capabilityInsufficient', width: 140 },
  ]

  const roundData =
    activeFile?.stage2_rounds?.map(round => ({
      key: round.round_number,
      round: `第${round.round_number}轮`,
      needRetest: round.need_retest ?? 0,
      stage2Executed: round.stage2_executed ?? false,
      knowledgeDeficiency: round.stage2_statistics?.knowledge_deficiency ?? 0,
      reasoningErrors: round.stage2_statistics?.reasoning_errors ?? 0,
      capabilityInsufficient: round.stage2_statistics?.capability_insufficient ?? 0,
    })) || []

  const fileColumns = [
    { title: '文件名', dataIndex: 'file_name', key: 'file_name' },
    { title: '总问题数', dataIndex: 'total_questions', key: 'total_questions', width: 120 },
    { title: '最终正确', dataIndex: 'final_correct_answers', key: 'final_correct_answers', width: 120 },
    { title: '推理错误', dataIndex: 'final_reasoning_errors', key: 'final_reasoning_errors', width: 120 },
    { title: '知识缺失', dataIndex: 'final_knowledge_deficiency', key: 'final_knowledge_deficiency', width: 120 },
    { title: '能力不足', dataIndex: 'final_capability_insufficient', key: 'final_capability_insufficient', width: 120 },
  ]

  const fileTableData = files.map(file => {
    const finalStats = file.final_analysis
    const stats = finalStats?.statistics || {}
    return {
      key: file.file_name,
      file_name: file.file_name,
      total_questions: stats.total_questions || 0,
      final_correct_answers: finalStats?.final_correct_answers || 0,
      final_reasoning_errors: finalStats?.final_reasoning_errors || 0,
      final_knowledge_deficiency: finalStats?.final_knowledge_deficiency || 0,
      final_capability_insufficient: finalStats?.final_capability_insufficient || 0,
    }
  })

  const multiFileChartData = files.map(file => ({
    name: file.file_name,
    正确: file.final_analysis?.final_correct_answers || 0,
    推理错误: file.final_analysis?.final_reasoning_errors || 0,
    知识缺失: file.final_analysis?.final_knowledge_deficiency || 0,
    能力不足: file.final_analysis?.final_capability_insufficient || 0,
  }))

  const buildDownloadUrl = (path?: string | null) => {
    if (!path) return ''
    return path.startsWith('http') ? path : `/api${path}`
  }

  const handleRestart = () => {
    resetEvaluation()
    navigate('/eval/process')
  }

  const downloadFiles = downloadLinks?.files || []
  const packageDownloadUrl = downloadLinks ? buildDownloadUrl(downloadLinks.package.url) : ''

  const historyEntries = historyResponse?.history || []
  const historyModelOptions = useMemo(() => {
    const models = Array.from(new Set(historyEntries.map(item => item.model_name).filter(Boolean))) as string[]
    return models
  }, [historyEntries])

  const filteredHistory = useMemo(() => {
    if (!historyModelFilter) return historyEntries
    return historyEntries.filter(item => item.model_name === historyModelFilter)
  }, [historyEntries, historyModelFilter])

  const historyDisplay = filteredHistory.slice(0, 8)

  const formatHistoryTime = (value?: string | null) => {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleString()
  }

  return (
    <div>
      
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          评估结果分析
        </Title>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          查看详细的评估结果、对比分析和可视化图表
        </Text>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Card style={{ marginBottom: 24, borderRadius: 4 }} title="下载与操作">
          <Space size="middle" wrap>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              href={packageDownloadUrl}
              target="_blank"
              rel="noreferrer"
              disabled={!downloadLinks}
            >
              {downloadLinks ? downloadLinks.package.label : '完整评估包'}
            </Button>
            <Button icon={<RedoOutlined />} onClick={handleRestart}>
              重新开始测评
            </Button>
          </Space>
          {downloadLinks ? (
            downloadFiles.length > 0 ? (
              <>
                <Divider />
                <List
                  itemLayout="vertical"
                  dataSource={downloadFiles}
                  renderItem={file => (
                    <List.Item
                      key={file.file_name}
                      actions={file.formats.map(format => (
                        <Button
                          key={`${file.file_name}-${format.format}`}
                          size="small"
                          icon={<DownloadOutlined />}
                          href={buildDownloadUrl(format.url)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {format.label}
                        </Button>
                      ))}
                    >
                      <List.Item.Meta
                        title={file.display_name || file.file_name}
                        description={`可下载 ${file.formats.length} 种格式`}
                      />
                    </List.Item>
                  )}
                />
              </>
            ) : (
              <Alert style={{ marginTop: 16 }} type="info" message="该任务暂无可下载的文件" showIcon />
            )
          ) : (
            <Alert style={{ marginTop: 16 }} type="info" message="请选择已完成的评估任务以获取下载链接" showIcon />
          )}
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Card style={{ marginBottom: 24, borderRadius: 4 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>选择评估任务</Text>
              <Select
                placeholder="请选择要查看的评估任务"
                style={{ width: '100%', marginTop: 8 }}
                value={selectedTaskId || undefined}
                onChange={value => setSelectedTaskId(value)}
                size="large"
              >
                {taskOptions.map(task => (
                  <Option key={task.task_id} value={task.task_id}>
                    {task.llm_name || task.task_id} ({task.status})
                  </Option>
                ))}
              </Select>
            </div>
            {files.length > 0 && (
              <div>
                <Text strong>选择文件</Text>
                <Select
                  placeholder="请选择文件"
                  style={{ width: '100%', marginTop: 8 }}
                  value={activeFile?.file_name}
                  onChange={value => setActiveFileName(value)}
                  size="large"
                >
                  {files.map(file => (
                    <Option key={file.file_name} value={file.file_name}>
                      {file.file_name}
                    </Option>
                  ))}
                </Select>
              </div>
            )}
          </Space>
        </Card>
      </motion.div>

      {stats && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card bordered={false} style={{ borderRadius: 4 }}>
                <Statistic title="总任务数" value={stats.total_tasks} prefix={<FileTextOutlined />} valueStyle={{ color: '#667eea' }} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card bordered={false} style={{ borderRadius: 4 }}>
                <Statistic title="已完成" value={stats.completed_tasks} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card bordered={false} style={{ borderRadius: 4 }}>
                <Statistic title="进行中" value={stats.processing_tasks} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#faad14' }} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card bordered={false} style={{ borderRadius: 4 }}>
                <Statistic
                  title="成功率"
                  value={stats.success_rate}
                  suffix="%"
                  prefix={<TrophyOutlined />}
                  valueStyle={{ color: '#13c2c2' }}
                  precision={1}
                />
              </Card>
            </Col>
          </Row>
        </motion.div>
      )}

      {!selectedTaskId ? (
        <Card style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
          <Empty description="请选择一个评估任务查看详细结果" />
        </Card>
      ) : resultsLoading ? (
        <Card style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" tip="加载评估结果中..." />
        </Card>
      ) : resultsError ? (
        <Card style={{ borderRadius: 4 }}>
          <Empty description="任务尚未完成或数据加载失败，请稍后再试" />
        </Card>
      ) : results ? (
        <>
          {summary && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ borderRadius: 4 }}>
                    <Statistic title="项目总问题数" value={summary.total_questions} prefix={<FileTextOutlined />} />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ borderRadius: 4 }}>
                    <Statistic title="最终正确率" value={summary.overall_accuracy_rate} suffix="%" valueStyle={{ color: '#52c41a' }} precision={2} />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ borderRadius: 4 }}>
                    <Statistic title="评估文件" value={summary.total_files} suffix="个" valueStyle={{ color: '#1890ff' }} />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ borderRadius: 4 }}>
                    <Statistic title="触发二次评估" value={summary.files_with_stage2 || 0} suffix="个" valueStyle={{ color: '#fa8c16' }} />
                  </Card>
                </Col>
              </Row>
            </motion.div>
          )}

          {files.length === 0 ? (
            <Card style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
              <Empty description="该任务暂无文件结果" />
            </Card>
          ) : (
            <>
              <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={12}>
                  <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>
                    <Card title="阶段表现" bordered={false} style={{ borderRadius: 4 }}>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={outcomeData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="value" fill="#667eea" radius={[8, 8, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={24} lg={12}>
                  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>
                    <Card title="结果分布" bordered={false} style={{ borderRadius: 4 }}>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={outcomeData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {outcomeData.map((_, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={24}>
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                    <Card title="文件对比" bordered={false} style={{ borderRadius: 4 }}>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={multiFileChartData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="正确" stackId="a" fill="#52c41a" />
                          <Bar dataKey="推理错误" stackId="a" fill="#fa8c16" />
                          <Bar dataKey="知识缺失" stackId="a" fill="#1890ff" />
                          <Bar dataKey="能力不足" stackId="a" fill="#ff4d4f" />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  </motion.div>
                </Col>
              </Row>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                <Card title="轮次详情" bordered={false} style={{ borderRadius: 4, marginBottom: 24 }}>
                  <Table columns={roundColumns} dataSource={roundData} pagination={false} scroll={{ x: 800 }} />
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                <Card title="文件概览" bordered={false} style={{ borderRadius: 4 }}>
                  <Table columns={fileColumns} dataSource={fileTableData} pagination={false} scroll={{ x: 800 }} />
                </Card>
              </motion.div>
            </>
          )}
        </>
      ) : null}

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15 }}>
        <Card title="历史评估记录" style={{ borderRadius: 4, marginTop: 24 }}>
          <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
            <Space>
              <span>按模型筛选：</span>
              <Select
                allowClear
                placeholder="全部模型"
                style={{ minWidth: 200 }}
                value={historyModelFilter || undefined}
                onChange={(value) => setHistoryModelFilter(value || null)}
              >
                {historyModelOptions.map(model => (
                  <Option key={model} value={model}>
                    {model}
                  </Option>
                ))}
              </Select>
            </Space>
            <Typography.Text type="secondary">{filteredHistory.length} 条记录</Typography.Text>
          </Space>
          {historyDisplay.length === 0 ? (
            <Empty description="暂无历史记录" style={{ margin: '24px 0' }} />
          ) : (
            <List
              itemLayout="vertical"
              dataSource={historyDisplay}
              renderItem={item => (
                <List.Item
                  key={`${item.model_name}-${item.timestamp}`}
                  actions={[
                    <Button
                      key="download"
                      size="small"
                      icon={<DownloadOutlined />}
                      href={buildDownloadUrl(`/eval/history/${item.model_name}/${item.timestamp}/package`)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      下载ZIP
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={`${item.display_name}`}
                    description={`文件 ${item.files.length} · ${formatHistoryTime(item.created_at)}`}
                  />
                  <Typography.Text type="secondary">目录：{item.result_dir}</Typography.Text>
                </List.Item>
              )}
            />
          )}
        </Card>
      </motion.div>
    </div>
  )
}

export default EvalAnalysis
