import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Upload,
  Button,
  Space,
  InputNumber,
  Switch,
  message,
  Divider,
  Typography,
  Alert,
  Row,
  Col,
  Slider,
  Steps,
  List,
  Tag,
  Statistic,
  Collapse,
  Progress,
} from 'antd'
import {
  RobotOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  DeleteOutlined,
  FileWordOutlined,
  ArrowRightOutlined,
  LeftOutlined,
  SettingOutlined,
  FilterOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { qaService } from '@/services/qaService'
import { useWorkflow } from '@/hooks/useWorkflow'

const { Title, Paragraph, Text } = Typography
const { Step } = Steps
const { Dragger } = Upload
const { Panel } = Collapse

// 定义进度数据类型
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

const QAProcess = () => {
  const navigate = useNavigate()
  // 工作流状态管理
  const {
    state: workflowState,
    saveQAParams,
    setQAStep,
  } = useWorkflow()

  const [currentStep, setCurrentStep] = useState(0)
  const paramsHydratedRef = useRef(false)

  // 文件上传
  const [fileList, setFileList] = useState<UploadFile[]>([])

  // 跳过步骤开关
  const [skipExtract, setSkipExtract] = useState(false)
  const [skipEvaluate, setSkipEvaluate] = useState(false)
  const [skipQA, setSkipQA] = useState(false)
  const [skipQAEvaluate, setSkipQAEvaluate] = useState(false)

  // 配置参数 - 生成
  const [numPairs, setNumPairs] = useState(5)
  const [useSuggested, setUseSuggested] = useState(false)
  const [includeReason, setIncludeReason] = useState(true)
  const [minDensityScore, setMinDensityScore] = useState(5)
  const [minQualityScore, setMinQualityScore] = useState(5)

  // 配置参数 - 评估（保存以便传递给Status页面）
  const [enableQAEvaluation, setEnableQAEvaluation] = useState(true) // 是否启用质量评估
  const [minFactualScore, setMinFactualScore] = useState(7)
  const [minOverallScore, setMinOverallScore] = useState(7)
  const [samplePercentage, setSamplePercentage] = useState(100)

  // 第三步：任务监控状态
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskType, setTaskType] = useState<'generate' | 'evaluate'>('generate')
  const [progressData, setProgressData] = useState<ProgressData | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // 多文件任务管理
  const [allTasks, setAllTasks] = useState<Array<{task_id: string, filename: string}>>([])
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)

  const eventSourceRef = useRef<EventSource | null>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  // 从持久化状态恢复参数
  useEffect(() => {
    if (paramsHydratedRef.current) return
    const params = workflowState.qa?.params
    if (params) {
      setNumPairs(params.numPairs)
      setUseSuggested(params.useSuggested)
      setIncludeReason(params.includeReason)
      setMinDensityScore(params.minDensityScore)
      setMinQualityScore(params.minQualityScore)
      setSkipExtract(params.skipExtract)
      setSkipEvaluate(params.skipEvaluate)
      setSkipQA(params.skipQA)
      setSkipQAEvaluate(params.skipQAEvaluate)
      setEnableQAEvaluation(params.enableQAEvaluation ?? true)
      setMinFactualScore(params.minFactualScore)
      setMinOverallScore(params.minOverallScore)
      setSamplePercentage(params.samplePercentage)
      paramsHydratedRef.current = true
    }
  }, [workflowState.qa?.params])

  // 保存参数到持久化存储
  useEffect(() => {
    if (!paramsHydratedRef.current) return
    saveQAParams({
      numPairs,
      useSuggested,
      includeReason,
      minDensityScore,
      minQualityScore,
      skipExtract,
      skipEvaluate,
      skipQA,
      skipQAEvaluate,
      enableQAEvaluation,
      minFactualScore,
      minOverallScore,
      samplePercentage,
    })
    setQAStep(currentStep)
  }, [
    numPairs,
    useSuggested,
    includeReason,
    minDensityScore,
    minQualityScore,
    skipExtract,
    skipEvaluate,
    skipQA,
    skipQAEvaluate,
    enableQAEvaluation,
    minFactualScore,
    minOverallScore,
    samplePercentage,
    saveQAParams,
    currentStep,
    setQAStep,
  ])

  const totalFileSize = useMemo(() => {
    const size = fileList.reduce((sum, file) => sum + (file.size || 0), 0)
    return ((size) / 1024 / 1024).toFixed(2)
  }, [fileList])

  // 上传配置
  const uploadProps: UploadProps = {
    multiple: true,
    accept: '.doc,.docx',
    fileList,
    showUploadList: false,
    beforeUpload: (file) => {
      if (startGenerateMutation.isPending) {
        return Upload.LIST_IGNORE
      }
      const uploadFile: UploadFile = {
        uid: file.uid,
        name: file.name,
        size: file.size,
        type: file.type,
        originFileObj: file,
      }
      setFileList((prev) => [...prev, uploadFile])
      return false
    },
    onRemove: (file) => {
      if (startGenerateMutation.isPending) {
        return false
      }
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
      return true
    },
  }

  // 启动生成任务
  const startGenerateMutation = useMutation({
    mutationFn: async (files: File[]) => {
      const params = {
        numPairs,
        useSuggested,
        includeReason,
        minDensityScore,
        minQualityScore,
        skipExtract,
        skipEvaluate,
        skipQA,
        skipQAEvaluate: !enableQAEvaluation, // 与启用评估相反
        minFactualScore,
        minOverallScore,
        samplePercentage,
      }
      console.log('[生成任务] 启动参数:', params)
      const response = await qaService.generateQA(files, params)
      console.log('[生成任务] 响应:', response)
      return response
    },
    onSuccess: (data) => {
      console.log('[生成任务] 成功, data:', data)
      if (data?.tasks && data.tasks.length > 0) {
        // 保存所有任务
        setAllTasks(data.tasks)
        setCurrentTaskIndex(0)

        // 设置第一个任务并进入第三步监控
        const firstTask = data.tasks[0]
        setTaskId(firstTask.task_id)
        setTaskType('generate')
        setIsProcessing(true)
        setCurrentStep(2) // 进入第三步

        message.success(`问答生成任务已创建 (共 ${data.tasks.length} 个文件)`)
        console.log('[生成任务] 保存所有任务:', data.tasks)
        console.log('[生成任务] 开始监控第1个任务:', firstTask)
      }
    },
    onError: (error: any) => {
      message.error(`启动失败: ${error.response?.data?.detail || error.message}`)
    },
  })

  // SSE 连接逻辑
  useEffect(() => {
    if (!taskId || currentStep !== 2) return

    console.log('[SSE] 开始连接进度监控, taskId:', taskId, 'currentStep:', currentStep)
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
    const url = `${apiBase}/qa/progress/${taskId}`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('progress', (e) => {
      try {
        const data = JSON.parse(e.data) as ProgressData
        console.log('[SSE Progress]', data)
        setProgressData(data)
      } catch (error) {
        console.error('Failed to parse progress data:', error)
      }
    })

    eventSource.addEventListener('log', (e) => {
      try {
        const log = JSON.parse(e.data) as LogEntry
        setLogs((prev) => [...prev, log])
      } catch (error) {
        console.error('Failed to parse log data:', error)
      }
    })

    eventSource.addEventListener('complete', async (e) => {
      try {
        const data = JSON.parse(e.data)
        console.log('[Complete Event] 收到完成事件:', data)

        if (data.status === 'completed') {
          // 检查当前阶段：只有阶段2（整体质量评估）完成才算真正完成
          const currentStage = getCurrentStage()
          const isStage2Complete = currentStage === 2 || (progressData?.progress ?? 0) >= 95

          console.log('[Complete Event] 当前阶段:', currentStage, '进度:', progressData?.progress)

          // 如果是阶段1完成（问答对生成完成），不显示任何完成消息，继续等待阶段2
          if (!isStage2Complete) {
            console.log('[Complete Event] 阶段1（问答对生成）完成，等待阶段2（质量评估）')
            // 不做任何操作，等待阶段2的进度更新
            return
          }

          // 阶段2完成，检查是否还有更多任务需要处理
          if (currentTaskIndex < allTasks.length - 1) {
            // 还有下一个文件，切换到下一个任务
            const nextIndex = currentTaskIndex + 1
            const nextTask = allTasks[nextIndex]

            console.log(`[Complete Event] 切换到下一个任务 (${nextIndex + 1}/${allTasks.length}):`, nextTask)

            // 关闭当前 SSE 连接
            eventSource.close()

            // 重置进度数据（这样进度条2和3会被重置）
            setProgressData(null)
            setLogs([])

            // 切换到下一个任务
            setCurrentTaskIndex(nextIndex)
            setTaskId(nextTask.task_id)

            message.info(`文件 ${currentTaskIndex + 1}/${allTasks.length} 处理完成，开始处理下一个文件: ${nextTask.filename}`)
          } else {
            // 所有任务都已完成
            setIsProcessing(false)
            if (data.summary) {
              setSummary(data.summary)
            }
            message.success(
              allTasks.length > 1
                ? `所有文件处理完成！(共 ${allTasks.length} 个文件)`
                : '所有任务已完成！'
            )
            eventSource.close()
          }
        } else if (data.status === 'failed') {
          console.log('[Complete Event] 任务失败:', data.message)
          setIsProcessing(false)
          message.error(`文件 ${currentTaskIndex + 1}/${allTasks.length} 处理失败: ${data.message}`)
          eventSource.close()
        } else {
          console.log('[Complete Event] 未知状态:', data.status)
          eventSource.close()
        }
      } catch (error) {
        console.error('Failed to parse complete data:', error)
      }
    })

    eventSource.addEventListener('error', (e: any) => {
      try {
        if (e.data) {
          const errorData = JSON.parse(e.data)
          console.error('[SSE Error Event]', errorData)
          message.error(`错误: ${errorData.error}`)
        }
      } catch (error) {
        console.error('[SSE] Error parsing error event:', error)
      }
      setIsProcessing(false)
      eventSource.close()
    })

    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error:', error)
      console.error('[SSE] EventSource readyState:', eventSource.readyState)

      // 如果是连接断开（readyState === 2），不要立即设置为未处理状态
      // 因为任务可能还在后台运行
      if (eventSource.readyState === EventSource.CLOSED) {
        console.warn('[SSE] 连接已关闭，但任务可能仍在运行')
        // 不立即设置 isProcessing = false，让用户可以刷新页面查看状态
      }
      eventSource.close()
    }

    eventSourceRef.current = eventSource

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [taskId, currentStep, taskType])

  // 自动滚动日志
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [logs])

  // 开始生成
  const handleStartGenerate = () => {
    const files = fileList
      .map((file) => file.originFileObj)
      .filter((file) => !!file) as File[]

    if (files.length === 0) {
      message.warning('请先上传文件')
      return
    }

    startGenerateMutation.mutate(files)
  }

  // 步骤验证
  const validateStep = (step: number): boolean => {
    if (step === 0) {
      if (fileList.length === 0) {
        message.warning('请至少上传一个文档')
        return false
      }
      return true
    }
    return true
  }

  // 下一步
  const handleNext = () => {
    if (validateStep(currentStep)) {
      // 如果是在步骤2（配置页），则启动任务
      if (currentStep === 1) {
        handleStartGenerate()
      } else {
        setCurrentStep(currentStep + 1)
      }
    }
  }

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

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

  // 获取当前阶段（1=问答对生成，2=整体质量评估）
  const getCurrentStage = () => {
    if (!progressData) return 1
    const step = progressData.current_step?.toLowerCase() || ''
    const message = progressData.message?.toLowerCase() || ''

    // 阶段2的明确标志：包含"问答质量评估"或"问答对质量"关键词
    // 注意：要区分"评估内容质量"（阶段1）和"问答质量评估"（阶段2）
    if (
      taskType === 'evaluate' ||
      step.includes('问答质量') ||
      step.includes('问答对质量') ||
      message.includes('问答质量') ||
      message.includes('问答对质量') ||
      step.includes('抽样') ||
      (step.includes('评估') && (step.includes('问答') || step.includes('qa')))
    ) {
      return 2
    }
    return 1
  }

  // 获取阶段1的当前步骤索引（提取=0, 评估内容质量=1, 生成问答对=2）
  const getStage1StepIndex = () => {
    if (!progressData) return -1
    const step = progressData.current_step?.toLowerCase() || ''
    const message = progressData.message?.toLowerCase() || ''

    if (step.includes('提取') || step.includes('extract') || message.includes('提取文档')) return 0
    // 注意：这里是"评估内容质量"，不是"问答质量评估"
    if ((step.includes('评估') && step.includes('内容')) || message.includes('评估内容质量')) return 1
    if (step.includes('生成') || step.includes('问答对') || message.includes('生成问答')) return 2
    return -1
  }

  // 获取阶段2的当前步骤索引
  const getStage2StepIndex = () => {
    if (!progressData) return -1
    const step = progressData.current_step?.toLowerCase() || ''
    const message = progressData.message?.toLowerCase() || ''

    if (step.includes('初始化') || step.includes('读取') || message.includes('读取问答')) return 0
    if (step.includes('抽样') || message.includes('抽样')) return 1
    if (step.includes('评估') || step.includes('质量') || message.includes('评估问答')) return 2
    if (step.includes('保存') || message.includes('保存结果')) return 3
    if (step.includes('完成') || message.includes('评估完成')) return 4
    return -1
  }

  // 渲染步骤1: 数据与上传
  const renderStep1 = () => (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          <span>数据上传</span>
        </Space>
      }
      style={{ borderRadius: 8 }}
    >
      <Alert
        message="第一步: 上传文档数据"
        description="上传 Word 文档(.doc/.docx),系统将从中提取内容并生成问答对"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #667eea' }}>
            <Statistic
              title="已选文件"
              value={fileList.length}
              suffix="个"
              valueStyle={{ color: '#667eea' }}
             
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #4caf50' }}>
            <Statistic
              title="总大小"
              value={totalFileSize}
              suffix="MB"
              valueStyle={{ color: '#4caf50' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #ff9800' }}>
            <Statistic
              title="准备状态"
              value={fileList.length > 0 ? '就绪' : '等待'}
              valueStyle={{
                color: fileList.length > 0 ? '#4caf50' : '#999',
                fontSize: 20,
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 文件上传区域 */}
      <Card
        title="拖拽或点击上传文件"
        style={{ borderRadius: 8, marginBottom: 24 }}
      >
        <Dragger {...uploadProps} style={{ padding: '20px 0' }}>
          <p className="ant-upload-drag-icon">
            <FileWordOutlined style={{ fontSize: 64, color: '#667eea' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持单个或批量上传。支持格式: .doc, .docx
          </p>
        </Dragger>
      </Card>

      {/* 文件列表 */}
      {fileList.length > 0 && (
        <Card title="已选择的文件" style={{ borderRadius: 8 }}>
          <List
            dataSource={fileList}
            renderItem={(file, index) => (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <List.Item
                  actions={[
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() =>
                        setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
                      }
                    >
                      删除
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileWordOutlined style={{ fontSize: 32, color: '#4caf50' }} />}
                    title={
                      <Space>
                        {file.name}
                        <Tag color="blue">
                          {((file.size || 0) / 1024).toFixed(2)} KB
                        </Tag>
                      </Space>
                    }
                    description={`文件类型: ${file.name.split('.').pop()?.toUpperCase()}`}
                  />
                </List.Item>
              </motion.div>
            )}
          />
        </Card>
      )}
    </Card>
  )

  // 渲染步骤2: 问答生成与评估配置
  const renderStep2 = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* 问答生成配置 */}
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>问答生成配置</span>
          </Space>
        }
        style={{ borderRadius: 8 }}
      >
        <Alert
          message="配置问答对生成参数"
          description="设置每段落的问答对数量以及质量筛选标准"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Row gutter={[24, 24]}>
          <Col span={24}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space>
                <Text strong>问答对数量:</Text>
                <Switch
                  checked={useSuggested}
                  onChange={setUseSuggested}
                  checkedChildren="模型建议"
                  unCheckedChildren="固定数量"
                  disabled={startGenerateMutation.isPending}
                />
                {!useSuggested && (
                  <InputNumber
                    min={1}
                    max={20}
                    value={numPairs}
                    onChange={(val) => setNumPairs(val || 5)}
                    disabled={startGenerateMutation.isPending}
                    style={{ width: 100 }}
                  />
                )}
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {useSuggested ? '由模型根据内容自动建议数量' : `每个段落生成 ${numPairs} 个问答对`}
              </Text>
            </Space>
          </Col>

          <Col span={24}>
            <Space>
              <Switch
                checked={includeReason}
                onChange={setIncludeReason}
                disabled={startGenerateMutation.isPending}
              />
              <Text strong>包含评估理由</Text>
            </Space>
          </Col>
        </Row>

        <Divider />

        <Card
          title={
            <Space>
              <FilterOutlined />
              <span>质量筛选阈值</span>
            </Space>
          }
          size="small"
          type="inner"
          style={{ borderRadius: 6 }}
        >
          <Row gutter={[24, 24]}>
            <Col xs={24} md={12}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Text strong>最低信息密度分数: {minDensityScore}</Text>
                <Slider
                  min={1}
                  max={10}
                  value={minDensityScore}
                  onChange={setMinDensityScore}
                  disabled={startGenerateMutation.isPending}
                  marks={{ 1: '1', 5: '5', 10: '10' }}
                  tooltip={{ formatter: value => `${value} 分` }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  筛选信息密度 ≥ {minDensityScore} 的内容段落
                </Text>
              </Space>
            </Col>
            <Col xs={24} md={12}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Text strong>最低信息质量分数: {minQualityScore}</Text>
                <Slider
                  min={1}
                  max={10}
                  value={minQualityScore}
                  onChange={setMinQualityScore}
                  disabled={startGenerateMutation.isPending}
                  marks={{ 1: '1', 5: '5', 10: '10' }}
                  tooltip={{ formatter: value => `${value} 分` }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  筛选信息质量 ≥ {minQualityScore} 的内容段落
                </Text>
              </Space>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* 高级选项 - 跳过步骤 */}
        <Collapse bordered={false} ghost>
          <Panel header="高级选项: 跳过步骤设置" key="skip">
            <Alert
              message="跳过步骤功能"
              description="如果已存在中间结果文件,可以跳过相应步骤以节省时间。请确保对应的结果文件存在。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Space>
                  <Switch
                    checked={skipExtract}
                    onChange={setSkipExtract}
                    disabled={startGenerateMutation.isPending}
                  />
                  <Text>跳过内容提取</Text>
                </Space>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Space>
                  <Switch
                    checked={skipEvaluate}
                    onChange={setSkipEvaluate}
                    disabled={startGenerateMutation.isPending}
                  />
                  <Text>跳过内容评估</Text>
                </Space>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Space>
                  <Switch
                    checked={skipQA}
                    onChange={setSkipQA}
                    disabled={startGenerateMutation.isPending}
                  />
                  <Text>跳过问答生成</Text>
                </Space>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Space>
                  <Switch
                    checked={skipQAEvaluate}
                    onChange={setSkipQAEvaluate}
                    disabled={startGenerateMutation.isPending}
                  />
                  <Text>跳过问答评估</Text>
                </Space>
              </Col>
            </Row>
          </Panel>
        </Collapse>
      </Card>

      {/* 质量评估配置 */}
      <Card
        title={
          <Space>
            <CheckCircleOutlined />
            <span>质量评估配置</span>
          </Space>
        }
        style={{ borderRadius: 8 }}
      >
        <Alert
          message="配置问答对质量评估参数"
          description="对生成的问答对进行质量评估,筛选出符合标准的高质量问答对"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        {/* 质量评估总开关 */}
        <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Card
              size="small"
              style={{
                borderRadius: 6,
                background: enableQAEvaluation ? '#f6ffed' : '#fafafa',
                borderColor: enableQAEvaluation ? '#b7eb8f' : '#d9d9d9'
              }}
            >
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Space>
                  <Switch
                    checked={enableQAEvaluation}
                    onChange={setEnableQAEvaluation}
                    disabled={startGenerateMutation.isPending}
                    checkedChildren="已启用"
                    unCheckedChildren="已禁用"
                  />
                  <Text strong style={{ fontSize: 15 }}>启用问答质量评估</Text>
                  <Tag color={enableQAEvaluation ? 'success' : 'default'}>
                    {enableQAEvaluation ? '生成后将自动评估' : '仅生成问答对'}
                  </Tag>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {enableQAEvaluation
                   }
                </Text>
              </Space>
            </Card>
          </Col>
        </Row>

        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong style={{ color: enableQAEvaluation ? undefined : '#d9d9d9' }}>
                最低事实依据分数: {minFactualScore}
              </Text>
              <Slider
                min={0}
                max={10}
                value={minFactualScore}
                onChange={setMinFactualScore}
                disabled={!enableQAEvaluation}
                marks={{ 0: '0', 5: '5', 7: '7', 10: '10' }}
                tooltip={{ formatter: value => `${value} 分` }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                只保留事实依据分数 ≥ {minFactualScore} 的问答对
              </Text>
            </Space>
          </Col>
          <Col xs={24} md={12}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong style={{ color: enableQAEvaluation ? undefined : '#d9d9d9' }}>
                最低总体质量分数: {minOverallScore}
              </Text>
              <Slider
                min={0}
                max={10}
                value={minOverallScore}
                onChange={setMinOverallScore}
                disabled={!enableQAEvaluation}
                marks={{ 0: '0', 5: '5', 7: '7', 10: '10' }}
                tooltip={{ formatter: value => `${value} 分` }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                只保留总体质量分数 ≥ {minOverallScore} 的问答对
              </Text>
            </Space>
          </Col>
          <Col xs={24}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Text strong style={{ color: enableQAEvaluation ? undefined : '#d9d9d9' }}>
                抽查百分比: {samplePercentage}%
              </Text>
              <Slider
                min={1}
                max={100}
                value={samplePercentage}
                onChange={setSamplePercentage}
                disabled={!enableQAEvaluation}
                marks={{ 1: '1%', 25: '25%', 50: '50%', 75: '75%', 100: '100%' }}
                tooltip={{ formatter: value => `${value}%` }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {samplePercentage === 100
                  ? '将评估所有问答对(推荐用于重要数据)'
                  : `将随机抽查 ${samplePercentage}% 的问答对(可节省API成本)`}
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>
    </Space>
  )

  // 渲染步骤3: 处理状态监控
  const renderStep3 = () => {
    const currentStage = getCurrentStage()
    const stage1StepIndex = getStage1StepIndex()
    const stage2StepIndex = getStage2StepIndex()

    // 阶段1的步骤
    const stage1Steps = ['提取文档内容', '评估内容质量', '生成问答对']
    // 阶段2的步骤
    const stage2Steps = ['初始化/读取问答Excel', '抽样问答对', '质量评估', '保存结果', '完成']

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 进度显示 */}
        <Card
          title={
            <Space>
              {isProcessing ? (
                <SyncOutlined spin style={{ color: '#1890ff' }} />
              ) : progressData?.status === 'completed' ? (
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
              ) : progressData?.status === 'failed' ? (
                <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
              ) : (
                <SyncOutlined spin style={{ color: '#1890ff' }} />
              )}
              <Text strong>执行进度</Text>
            </Space>
          }
          style={{ borderRadius: 8 }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 如果没有进度数据,显示处理中状态 */}
            {!progressData && isProcessing && (
              <Alert
                message="正在处理中..."
                description="任务已启动,等待后端返回进度信息"
                type="info"
                showIcon
                icon={<SyncOutlined spin />}
              />
            )}

            {/* 进度条1: 文件处理进度（蓝色） */}
            {progressData && (
              <Card size="small" style={{ borderRadius: 8, background: '#e6f7ff', border: '1px solid #91d5ff' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Space>
                        <FileTextOutlined style={{ fontSize: 16, color: '#1890ff' }} />
                        <Text strong style={{ fontSize: 15 }}>文件处理进度</Text>
                      </Space>
                    </Col>
                    <Col>
                      {allTasks.length > 0 ? (
                        <Text strong style={{ color: '#1890ff' }}>
                          文件 {currentTaskIndex + 1} / {allTasks.length}
                        </Text>
                      ) : progressData.file_progress ? (
                        <Text strong style={{ color: '#1890ff' }}>
                          {progressData.file_progress.current_file} / {progressData.file_progress.total_files} 文件
                        </Text>
                      ) : (
                        <Tag color={
                          progressData.status === 'completed' ? 'success' :
                          progressData.status === 'failed' ? 'error' :
                          'processing'
                        }>
                          {progressData.status === 'completed' ? '已完成' :
                           progressData.status === 'failed' ? '处理失败' :
                           '处理中...'}
                        </Tag>
                      )}
                    </Col>
                  </Row>
                  <Progress
                    percent={Math.round(
                      allTasks.length > 1
                        ? (
                            // 已完成的文件占比 + 当前文件的进度条2占比
                            (currentTaskIndex / allTasks.length) * 100 +
                            (progressData.progress ?? 0) / allTasks.length
                          )
                        : (progressData.progress ?? 0)  // 单文件时，进度条1 = 进度条2
                    )}
                    strokeColor="#1890ff"
                    strokeWidth={20}
                    status={
                      // 只有当所有文件都完成（最后一个文件且进度条2满了）时才显示success
                      (progressData.status === 'completed' &&
                       progressData.progress >= 100 &&
                       currentTaskIndex === allTasks.length - 1) ? 'success' :
                      progressData.status === 'failed' ? 'exception' :
                      isProcessing ? 'active' : 'normal'
                    }
                  />
                  {allTasks.length > 0 && allTasks[currentTaskIndex] && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前文件: {allTasks[currentTaskIndex].filename}
                    </Text>
                  )}
                  {!allTasks.length && progressData.file_progress?.current_filename && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {progressData.file_progress.current_filename}
                    </Text>
                  )}
                </Space>
              </Card>
            )}

            {/* 进度条2: 阶段进度（绿色） */}
            {progressData && (
              <Card size="small" style={{ borderRadius: 8, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Space>
                        <SyncOutlined spin={isProcessing} style={{ fontSize: 16, color: '#52c41a' }} />
                        <Text strong style={{ fontSize: 15 }}>阶段进度</Text>
                      </Space>
                    </Col>
                    <Col>
                      <Tag color={currentStage === 1 ? 'processing' : 'success'}>
                        阶段 {currentStage}/2
                      </Tag>
                    </Col>
                  </Row>
                  <Progress
                    percent={Math.round(progressData.progress || 0)}
                    strokeColor="#52c41a"
                    strokeWidth={16}
                    status={isProcessing ? 'active' : 'normal'}
                  />
                  {/* 阶段标签 */}
                  <Row gutter={8} style={{ marginTop: 8 }}>
                    <Col span={12}>
                      <Tag
                        color={
                          // 任务完成或阶段1已完成 -> success
                          (!isProcessing && progressData.status === 'completed') || currentStage > 1
                            ? 'success'
                            : currentStage === 1 && isProcessing
                            ? 'processing'
                            : 'default'
                        }
                        style={{ width: '100%', textAlign: 'center', padding: '4px 0' }}
                      >
                        {(!isProcessing && progressData.status === 'completed') || currentStage > 1 ? (
                          <CheckCircleOutlined />
                        ) : currentStage === 1 && isProcessing ? (
                          <SyncOutlined spin />
                        ) : (
                          ''
                        )}{' '}
                        问答对生成
                      </Tag>
                    </Col>
                    <Col span={12}>
                      <Tag
                        color={
                          // 任务完成 -> success
                          !isProcessing && progressData.status === 'completed'
                            ? 'success'
                            : currentStage === 2 && isProcessing
                            ? 'processing'
                            : currentStage > 2
                            ? 'success'
                            : 'default'
                        }
                        style={{ width: '100%', textAlign: 'center', padding: '4px 0' }}
                      >
                        {!isProcessing && progressData.status === 'completed' ? (
                          <CheckCircleOutlined />
                        ) : currentStage === 2 && isProcessing ? (
                          <SyncOutlined spin />
                        ) : currentStage > 2 ? (
                          <CheckCircleOutlined />
                        ) : (
                          ''
                        )}{' '}
                        整体质量评估
                      </Tag>
                    </Col>
                  </Row>
                </Space>
              </Card>
            )}

            {/* 进度条3: 当前阶段小步骤（橙色） */}
            {progressData && (
              <Card size="small" style={{ borderRadius: 8, background: '#fff7e6', border: '1px solid #ffd591' }}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Space>
                        <ClockCircleOutlined style={{ fontSize: 16, color: '#fa8c16' }} />
                        <Text strong style={{ fontSize: 15 }}>当前步骤</Text>
                      </Space>
                    </Col>
                    <Col>
                      <Text strong style={{ color: '#fa8c16' }}>
                        {(progressData.step_progress?.current_question ?? 0) > 0 && (progressData.step_progress?.total_questions ?? 0) > 0
                          ? `${progressData.step_progress?.current_question} / ${progressData.step_progress?.total_questions}`
                          : (progressData.step_progress?.current_step || progressData.current_step || '执行中')}
                      </Text>
                    </Col>
                  </Row>
                  <Progress
                    percent={Math.round(
                      (progressData.step_progress?.total_questions ?? 0) > 0
                        ? ((progressData.step_progress?.current_question ?? 0) / (progressData.step_progress?.total_questions ?? 1)) * 100
                        : progressData.step_progress?.step_progress_percent ?? progressData.progress ?? 0
                    )}
                    strokeColor="#fa8c16"
                    strokeWidth={12}
                    status={isProcessing ? 'active' : 'normal'}
                    showInfo={true}  // 显示百分比数值
                  />
                  {/* 步骤列表 */}
                  <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                    {(currentStage === 1 ? stage1Steps : stage2Steps).map((stepName, index) => {
                      const currentIndex = currentStage === 1 ? stage1StepIndex : stage2StepIndex
                      let color = 'default'
                      let icon = null

                      if (progressData.status === 'failed' && index === currentIndex) {
                        color = 'error'
                        icon = <CloseCircleOutlined />
                      } else if (index < currentIndex) {
                        color = 'success'
                        icon = <CheckCircleOutlined />
                      } else if (index === currentIndex) {
                        color = 'warning'
                        icon = <SyncOutlined spin />
                      }

                      return (
                        <Col key={index} span={currentStage === 1 ? 8 : 24 / stage2Steps.length}>
                          <Tag
                            color={color}
                            style={{
                              width: '100%',
                              textAlign: 'center',
                              padding: '4px 8px',
                              fontSize: 12
                            }}
                          >
                            {icon} {stepName}
                          </Tag>
                        </Col>
                      )
                    })}
                  </Row>
                  {/* 当前步骤消息 */}
                  {progressData.message && (
                    <Space align="center" style={{ marginTop: 4 }}>
                      <div style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: '#fa8c16'
                      }} />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {progressData.message}
                      </Text>
                    </Space>
                  )}
                </Space>
              </Card>
            )}
          </Space>
        </Card>

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
            style={{ borderRadius: 8 }}
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
            style={{ borderRadius: 8 }}
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
                >
                  下载结果文件
                </Button>
                <Button
                  size="large"
                  onClick={() => navigate('/qa/results')}
                >
                  查看所有结果
                </Button>
                <Button
                  size="large"
                  icon={<LeftOutlined />}
                  onClick={() => {
                    setCurrentStep(1)
                    setTaskId(null)
                    setProgressData(null)
                    setLogs([])
                    setSummary(null)
                  }}
                >
                  返回配置页面
                </Button>
              </Space>
            </Space>
          </Card>
        )}
      </Space>
    )
  }

  const steps = [
    { title: '数据上传', content: renderStep1() },
    { title: '参数配置', content: renderStep2() },
    { title: '处理状态', content: renderStep3() },
  ]

  return (
    <div>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            marginBottom: 24,
            borderRadius: 8,
          }}
        >
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Title level={2} style={{ color: 'white', margin: 0 }}>
              <RobotOutlined /> 数据集生成系统 
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.9)', margin: 0 }}>
            
            </Paragraph>
          </Space>
        </Card>
      </motion.div>

      {/* Steps */}
      <Card style={{ marginBottom: 24, borderRadius: 8 }}>
        <Steps current={currentStep}>
          {steps.map((item) => (
            <Step key={item.title} title={item.title} />
          ))}
        </Steps>
      </Card>

      {/* Content */}
      <motion.div
        key={currentStep}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {steps[currentStep].content}
      </motion.div>

      {/* Navigation */}
      <Card style={{ marginTop: 24, borderRadius: 8 }}>
        <Space size="large">
          {/* 步骤1和2可以返回上一步 */}
          {currentStep > 0 && currentStep < steps.length - 1 && (
            <Button size="large" icon={<LeftOutlined />} onClick={handlePrev}>
              上一步
            </Button>
          )}
          {/* 步骤1显示"下一步"，步骤2显示"启动任务" */}
          {currentStep < steps.length - 1 && (
            <Button
              type="primary"
              size="large"
              onClick={handleNext}
              icon={currentStep === 1 ? <PlayCircleOutlined /> : <ArrowRightOutlined />}
              loading={currentStep === 1 && startGenerateMutation.isPending}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
              }}
            >
              {currentStep === 1
                ? (startGenerateMutation.isPending ? '正在启动任务...' : '启动任务')
                : '下一步'}
            </Button>
          )}
          {/* 步骤3（监控中）显示返回配置按钮 */}
          {currentStep === steps.length - 1 && !isProcessing && (
            <Button
              size="large"
              icon={<LeftOutlined />}
              onClick={() => {
                setCurrentStep(1)
                setTaskId(null)
                setProgressData(null)
                setLogs([])
                setSummary(null)
              }}
            >
              返回配置
            </Button>
          )}
          {/* 步骤1显示清空按钮 */}
          {currentStep === 0 && fileList.length > 0 && (
            <Button size="large" onClick={() => setFileList([])}>
              清空列表
            </Button>
          )}
        </Space>
      </Card>
    </div>
  )
}

export default QAProcess
