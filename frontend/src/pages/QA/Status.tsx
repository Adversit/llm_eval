import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  Card,
  Steps,
  Progress,
  Typography,
  Space,
  Tag,
  Alert,
  Button,
  Statistic,
  Row,
  Col,
  List,
  Divider,
  message,
} from 'antd'
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { qaService } from '@/services/qaService'

const { Title, Text } = Typography
const { Step } = Steps

interface FileProgress {
  current_file: number
  total_files: number
  current_filename: string
  file_progress_percent: number
}

interface StepProgress {
  current_step: string
  step_progress_percent: number
  current_question: number
  total_questions: number
}

interface Timing {
  elapsed_seconds: number
  estimated_remaining_seconds: number | null
  estimated_total_seconds: number | null
}

interface ProgressData {
  status: string
  progress: number
  current_step: string
  message: string
  file_progress?: FileProgress
  step_progress?: StepProgress
  timing?: Timing
}

interface LogEntry {
  timestamp: string
  message: string
}

interface Artifact {
  type: string
  path: string
  filename: string
  size_bytes: number
}

interface Summary {
  total_time_seconds: number
  result_file: string
  total_files?: number
  success_count?: number
  fail_count?: number
  artifacts?: Artifact[]
}

const QAStatus = () => {
  const { taskId, taskType } = useParams<{ taskId: string; taskType: 'generate' | 'evaluate' }>()
  const navigate = useNavigate()
  const location = useLocation()

  const [progressData, setProgressData] = useState<ProgressData | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isProcessing, setIsProcessing] = useState(true)
  const [autoEvaluating, setAutoEvaluating] = useState(false)

  const eventSourceRef = useRef<EventSource | null>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)
  const autoEvalTriggeredRef = useRef(false)

  // 从路由state获取评估参数
  const evaluationParams = location.state as {
    minFactualScore?: number
    minOverallScore?: number
    samplePercentage?: number
  } || {}

  // 设置SSE连接
  useEffect(() => {
    if (!taskId) return

    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
    const url = `${apiBase}/qa/progress/${taskId}`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('progress', (e) => {
      try {
        const data = JSON.parse(e.data) as ProgressData
        setProgressData(data)
      } catch (error) {
        // console.error('Failed to parse progress data:', error)
      }
    })

    eventSource.addEventListener('log', (e) => {
      try {
        const log = JSON.parse(e.data) as LogEntry
        setLogs((prev) => [...prev, log])
      } catch (error) {
        // console.error('Failed to parse log data:', error)
      }
    })

    eventSource.addEventListener('complete', async (e) => {
      try {
        const data = JSON.parse(e.data)
        setIsProcessing(false)
        if (data.status === 'completed' && data.summary) {
          setSummary(data.summary)
          message.success(
            taskType === 'generate' ? '问答生成任务已完成！' : '问答评估任务已完成！'
          )
          // 注意：评估现在在后端完成，不再需要前端自动触发
        } else if (data.status === 'failed') {
          message.error(`任务失败: ${data.message}`)
        }
        eventSource.close()
      } catch (error) {
        // console.error('Failed to parse complete data:', error)
      }
    })

    eventSource.addEventListener('error', (e: any) => {
      try {
        if (e.data) {
          const errorData = JSON.parse(e.data)
          message.error(`错误: ${errorData.error}`)
        }
      } catch (error) {
        console.error('SSE error:', error)
      }
      setIsProcessing(false)
      eventSource.close()
    })

    eventSource.onerror = () => {
      console.error('SSE connection error')
      setIsProcessing(false)
      eventSource.close()
    }

    eventSourceRef.current = eventSource

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [taskId, taskType])

  // 自动滚动日志
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [logs])

  // 格式化时间
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs}秒`
  }

  // 下载结果
  const handleDownload = async () => {
    if (!taskId) return
    try {
      await qaService.downloadResult(taskId)
      message.success('下载成功')
    } catch (error) {
      message.error('下载失败')
    }
  }

  // 返回配置页面
  const handleBack = () => {
    navigate('/qa/process')
  }

  // 获取当前步骤
  const getCurrentStep = () => {
    if (!progressData) return 0

    const step = progressData.current_step?.toLowerCase() || ''

    if (taskType === 'generate') {
      // 步骤一: 文档处理
      if (step.includes('提取') || step.includes('extract')) return 0
      if (step.includes('评估') || step.includes('evaluate')) return 1
      if (step.includes('生成') || step.includes('问答') || step.includes('qa')) return 2
      return 0
    } else {
      // 步骤二: 问答质量评估
      return 0
    }
  }

  const currentStep = getCurrentStep()

  // 生成步骤配置
  const generateSteps = [
    { title: '提取文档内容', description: '从文档中提取结构化内容' },
    { title: '评估内容质量', description: '评估内容的信息密度和质量' },
    { title: '生成问答对', description: '基于高质量内容生成问答对' },
  ]

  const evaluateSteps = [{ title: '问答质量评估', description: '评估问答对的事实依据和整体质量' }]

  const steps = taskType === 'generate' ? generateSteps : evaluateSteps

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
            返回配置
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {taskType === 'generate' ? '步骤一：文档处理' : '步骤二：问答质量评估'}
          </Title>
        </Space>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          任务ID: {taskId}
        </Text>
      </div>

      {/* 步骤指示器 */}
      <Card style={{ borderRadius: 4, marginBottom: 24 }}>
        <Steps
          current={currentStep}
          status={
            progressData?.status === 'failed'
              ? 'error'
              : progressData?.status === 'completed'
              ? 'finish'
              : 'process'
          }
        >
          {steps.map((step, index) => (
            <Step key={index} title={step.title} description={step.description} />
          ))}
        </Steps>
      </Card>

      {/* 进度显示 */}
      {progressData && (
        <Card
          title={
            <Space>
              {isProcessing ? (
                <SyncOutlined spin style={{ color: '#0052D9' }} />
              ) : progressData.status === 'completed' ? (
                <CheckCircleOutlined style={{ color: '#00A870' }} />
              ) : (
                <CloseCircleOutlined style={{ color: '#D54941' }} />
              )}
              <Text strong>执行进度</Text>
            </Space>
          }
          style={{ borderRadius: 4, marginBottom: 24 }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 第一层: 总体文件进度 */}
            {progressData.file_progress && (
              <Card size="small" style={{ borderRadius: 4, background: '#f5f5f5' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>整体进度</Text>
                    <Tag color="blue">
                      文件 {progressData.file_progress.current_file}/
                      {progressData.file_progress.total_files}
                    </Tag>
                  </Space>
                  {progressData.file_progress.current_filename && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前文件: {progressData.file_progress.current_filename}
                    </Text>
                  )}
                  <Progress
                    percent={Math.round(progressData.progress)}
                    strokeColor="#0052D9"
                    strokeWidth={20}
                    status={isProcessing ? 'active' : 'normal'}
                  />
                  {progressData.timing && (
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="已用时间"
                          value={formatTime(progressData.timing.elapsed_seconds)}
                          valueStyle={{ fontSize: 14 }}
                          prefix={<ClockCircleOutlined />}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="预计剩余"
                          value={
                            progressData.timing.estimated_remaining_seconds
                              ? formatTime(progressData.timing.estimated_remaining_seconds)
                              : '-'
                          }
                          valueStyle={{ fontSize: 14 }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="预计总时间"
                          value={
                            progressData.timing.estimated_total_seconds
                              ? formatTime(progressData.timing.estimated_total_seconds)
                              : '-'
                          }
                          valueStyle={{ fontSize: 14 }}
                        />
                      </Col>
                    </Row>
                  )}
                </Space>
              </Card>
            )}

            {/* 第二层: 当前文件阶段进度 */}
            {progressData.step_progress && (
              <Card size="small" style={{ borderRadius: 4, background: '#f0f9ff' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>当前阶段</Text>
                    {progressData.file_progress && (
                      <Tag color="blue">
                        文件 {progressData.file_progress.current_file}/
                        {progressData.file_progress.total_files}
                      </Tag>
                    )}
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {progressData.step_progress.current_step}
                  </Text>
                  <Progress
                    percent={Math.round(progressData.step_progress.step_progress_percent)}
                    strokeColor="#00A870"
                    strokeWidth={16}
                    status="active"
                  />
                </Space>
              </Card>
            )}

            {/* 第三层: 问题处理进度 */}
            {progressData.step_progress && progressData.step_progress.total_questions > 0 && (
              <Card size="small" style={{ borderRadius: 4, background: '#fff7e6' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Text strong>问题处理进度</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {progressData.step_progress.current_question}/
                    {progressData.step_progress.total_questions} 问题
                  </Text>
                  <Progress
                    percent={Math.round(
                      (progressData.step_progress.current_question /
                        progressData.step_progress.total_questions) *
                        100
                    )}
                    strokeColor="#FF8800"
                    strokeWidth={12}
                    status="active"
                  />
                </Space>
              </Card>
            )}

            {/* 当前状态信息 */}
            {progressData.message && (
              <Alert
                message={progressData.message}
                type={
                  progressData.status === 'completed'
                    ? 'success'
                    : progressData.status === 'failed'
                    ? 'error'
                    : 'info'
                }
                showIcon
              />
            )}
          </Space>
        </Card>
      )}

      {/* 实时日志 */}
      {logs.length > 0 && (
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <Text strong>实时日志</Text>
              <Tag>{logs.length} 条</Tag>
            </Space>
          }
          style={{ borderRadius: 4, marginBottom: 24 }}
        >
          <div
            ref={logsContainerRef}
            style={{
              maxHeight: 400,
              overflowY: 'auto',
              background: '#fafafa',
              padding: 12,
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: 12,
            }}
          >
            {logs.map((log, index) => (
              <div key={index} style={{ marginBottom: 4 }}>
                <Text type="secondary">[{log.timestamp}]</Text> <Text>{log.message}</Text>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 完成汇总 */}
      {summary && (
        <Card
          title={
            <Space>
              <CheckCircleOutlined style={{ color: '#00A870' }} />
              <Text strong>任务完成汇总</Text>
            </Space>
          }
          style={{ borderRadius: 4 }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 统计信息 */}
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="总耗时"
                  value={formatTime(summary.total_time_seconds)}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
              {summary.total_files !== undefined && (
                <Col span={8}>
                  <Statistic title="处理文件" value={summary.total_files} suffix="个" />
                </Col>
              )}
              {summary.success_count !== undefined && (
                <Col span={8}>
                  <Statistic
                    title="成功"
                    value={summary.success_count}
                    suffix="个"
                    valueStyle={{ color: '#00A870' }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Col>
              )}
            </Row>

            {/* 生成文件列表 */}
            {summary.artifacts && summary.artifacts.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <div>
                  <Text strong>生成文件</Text>
                  <List
                    size="small"
                    dataSource={summary.artifacts}
                    renderItem={(artifact) => (
                      <List.Item>
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Space>
                            <FileTextOutlined />
                            <div>
                              <Text>{artifact.filename}</Text>
                              <br />
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {artifact.path}
                              </Text>
                            </div>
                          </Space>
                          <Text type="secondary">
                            {Math.round(artifact.size_bytes / 1024)} KB
                          </Text>
                        </Space>
                      </List.Item>
                    )}
                    style={{ marginTop: 8 }}
                  />
                </div>
              </>
            )}

            {/* 操作按钮 */}
            <Divider style={{ margin: '12px 0' }} />
            <Space>
              <Button
                type="primary"
                size="large"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                style={{ background: '#0052D9' }}
                disabled={autoEvaluating}
              >
                下载结果文件
              </Button>
              <Button
                size="large"
                onClick={() => navigate('/qa/results')}
                disabled={autoEvaluating}
              >
                查看所有结果
              </Button>
              <Button
                size="large"
                onClick={() => navigate('/qa/process')}
                disabled={autoEvaluating}
              >
                开始新任务
              </Button>
            </Space>
            {autoEvaluating && (
              <Alert
                message="正在自动启动质量评估..."
                description="问答生成已完成，系统正在自动创建质量评估任务"
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </Space>
        </Card>
      )}
    </div>
  )
}

export default QAStatus
