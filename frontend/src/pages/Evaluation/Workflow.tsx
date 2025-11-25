import { useState, useEffect, useRef, useMemo } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Alert,
  message,
  Steps,
  Upload,
  List,
  Tag,
  Row,
  Col,
  Statistic,
  Progress,
  InputNumber,
  Divider,
  Empty,
  Checkbox,
  Slider,
  Spin,
  Tooltip,
  Collapse,
} from 'antd'
import {
  FormOutlined,
  FileTextOutlined,
  FundProjectionScreenOutlined,
  DeleteOutlined,
  FileExcelOutlined,
  ArrowRightOutlined,
  LeftOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  AimOutlined,
} from '@ant-design/icons'
import type { UploadFile, UploadProps, RcFile } from 'antd/es/upload/interface'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useWorkflow } from '@/hooks/useWorkflow'
import {
  evaluationService,
  type EvaluationTaskStatus,
  type EvaluationUploadResponse,
  type ServerFileMeta,
  type ServerHistoryGroup,
} from '@/services/evaluationService'
import type { EvaluationStageKey, WorkflowStageSnapshot } from '@/store/workflowStore'

const { Title, Paragraph } = Typography
const { Step } = Steps
const { Dragger } = Upload
const { Panel } = Collapse

const EvaluationWorkflow = () => {
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()

  // 步骤1: 信息填写
  const [llmName, setLlmName] = useState('')
  const [llmInputMode, setLlmInputMode] = useState<'select' | 'custom'>('select')
  const [evalModelName, setEvalModelName] = useState('')
  const [description, setDescription] = useState('')

  // 步骤2: 文件上传与配置
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [evaluationType, setEvaluationType] = useState('both')
  const [stage1AnswerThreshold, setStage1AnswerThreshold] = useState(60)
  const [stage1ReasoningThreshold, setStage1ReasoningThreshold] = useState(60)
  const [stage2AnswerThreshold, setStage2AnswerThreshold] = useState(60)
  const [stage2ReasoningThreshold, setStage2ReasoningThreshold] = useState(60)
  const [evaluationRounds, setEvaluationRounds] = useState(1)
  const [uploadedServerFiles, setUploadedServerFiles] = useState<EvaluationUploadResponse['files']>([])
  const [selectedServerFilePaths, setSelectedServerFilePaths] = useState<string[]>([])

  // 步骤3: 评估进程
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<EvaluationTaskStatus | null>(null)
  const [creatingTask, setCreatingTask] = useState(false)
  const [workflowNotified, setWorkflowNotified] = useState(false)
  const pollingRef = useRef<number | null>(null)
  const paramsHydratedRef = useRef(false)

  // 工作流状态管理
  const {
    state: workflowState,
    setEvaluationWorkflowCompleted,
    saveEvaluationParams,
    bulkUpdateEvaluationStages,
    resetEvaluationStages,
  } = useWorkflow()

  // 获取可用模型列表
  const { data: modelsData, isLoading: loadingModels } = useQuery({
    queryKey: ['availableModels'],
    queryFn: () => evaluationService.getAvailableModels(),
    staleTime: 1000 * 60 * 5, // 5分钟缓存
  })

  const { data: serverFileInventory, isFetching: loadingServerFiles, refetch: refetchServerFiles } = useQuery({
    queryKey: ['serverFileInventory', llmName],
    queryFn: () => evaluationService.listServerFiles(llmName || undefined),
    enabled: !!llmName,
    staleTime: 1000 * 30,
  })

  const availableServerFiles = useMemo(() => {
    if (!serverFileInventory) return []
    const uploads = (serverFileInventory.uploads || []).map(file => ({ ...file, groupLabel: '上传缓存' }))
    const history = (serverFileInventory.history || []).flatMap(group =>
      (group.files || []).map(file => ({
        ...file,
        groupLabel: group.display_name,
        model_name: file.model_name || group.model_name,
        timestamp: file.timestamp || group.timestamp,
      }))
    )
    return [...uploads, ...history]
  }, [serverFileInventory])

  const selectedServerFiles = useMemo(() => {
    if (!selectedServerFilePaths.length) return []
    return availableServerFiles.filter(file => selectedServerFilePaths.includes(file.file_path))
  }, [availableServerFiles, selectedServerFilePaths])

  const totalSelectedFiles = fileList.length + selectedServerFilePaths.length
  const totalSelectedSize = useMemo(() => {
    const localSize = fileList.reduce((sum, file) => sum + (file.size || 0), 0)
    const serverSize = selectedServerFiles.reduce((sum, file) => sum + (file.size || 0), 0)
    return ((localSize + serverSize) / 1024 / 1024).toFixed(2)
  }, [fileList, selectedServerFiles])

  useEffect(() => {
    if (paramsHydratedRef.current) return
    const params = workflowState.evaluation?.params
    if (params) {
      setStage1AnswerThreshold(params.stage1_answer_threshold)
      setStage1ReasoningThreshold(params.stage1_reasoning_threshold)
      setStage2AnswerThreshold(params.stage2_answer_threshold)
      setStage2ReasoningThreshold(params.stage2_reasoning_threshold)
      setEvaluationRounds(params.evaluation_rounds)
      paramsHydratedRef.current = true
    }
  }, [workflowState.evaluation?.params])

  useEffect(() => {
    if (!paramsHydratedRef.current) return
    saveEvaluationParams({
      stage1_answer_threshold: stage1AnswerThreshold,
      stage1_reasoning_threshold: stage1ReasoningThreshold,
      stage2_answer_threshold: stage2AnswerThreshold,
      stage2_reasoning_threshold: stage2ReasoningThreshold,
      evaluation_rounds: evaluationRounds,
    })
  }, [
    stage1AnswerThreshold,
    stage1ReasoningThreshold,
    stage2AnswerThreshold,
    stage2ReasoningThreshold,
    evaluationRounds,
    saveEvaluationParams,
  ])

  useEffect(() => {
    setSelectedServerFilePaths([])
  }, [llmName])



  const formatFileSize = (size: number) => {
    if (!size) return '0KB'
    if (size >= 1024 * 1024) {
      return `${(size / 1024 / 1024).toFixed(2)} MB`
    }
    return `${(size / 1024).toFixed(2)} KB`
  }

  const toggleServerFileSelection = (path: string, checked: boolean) => {
    setSelectedServerFilePaths(prev => {
      if (checked) {
        return Array.from(new Set([...prev, path]))
      }
      return prev.filter(item => item !== path)
    })
  }

  const startEvaluation = async () => {
    if (!llmName.trim()) {
      message.warning('请先填写模型名称')
      setCurrentStep(0)
      return
    }

    // 允许仅选服务器文件或仅选本地文件，二者都空才提示
    if ((fileList.length + selectedServerFilePaths.length) === 0) {
      message.warning('请至少选择一个本地或服务器文件')
      return
    }

    const files = fileList
      .map(file => file.originFileObj)
      .filter((file): file is RcFile => file !== undefined)

    // 检查：如果用户选择了本地文件但读取失败，才报错
    if (fileList.length > 0 && files.length === 0) {
      message.warning('文件读取异常，请重新选择后再试')
      return
    }

    // 检查：必须至少有一个有效文件（本地或服务器）
    if (files.length === 0 && selectedServerFilePaths.length === 0) {
      message.warning('请至少选择一个本地或服务器文件')
      return
    }

    setCreatingTask(true)
    setWorkflowNotified(false)
    resetEvaluationStages()

    try {
      const uploadResp = files.length > 0 ? await evaluationService.uploadFiles(files) : null
      const uploadedPaths = uploadResp?.files?.map(file => file.file_path) ?? []
      const serverPaths = [...selectedServerFilePaths]
      const allFilePaths = [...serverPaths, ...uploadedPaths]

      if (allFilePaths.length === 0) {
        message.warning('文件路径解析失败，请重试')
        return
      }

      const response = await evaluationService.createTask({
        llm_name: llmName,
        evaluation_type: evaluationType,
        description,
        file_paths: allFilePaths,
        stage1_answer_threshold: stage1AnswerThreshold,
        stage1_reasoning_threshold: stage1ReasoningThreshold,
        stage2_answer_threshold: stage2AnswerThreshold,
        stage2_reasoning_threshold: stage2ReasoningThreshold,
        evaluation_rounds: evaluationRounds,
        eval_model_name: evalModelName || undefined,
      })

      const serverDisplay = selectedServerFilePaths.map(path => {
        const meta = availableServerFiles.find(file => file.file_path === path)
        const fallbackName = path.split(/[/\\]/).pop() || path
        return {
          filename: meta?.file_name || fallbackName,
          file_path: path,
          size: meta?.size || 0,
        }
      }) as EvaluationUploadResponse['files']

      setUploadedServerFiles([...(serverDisplay || []), ...(uploadResp?.files ?? [])])
      setTaskId(response.task_id)
      setTaskStatus(null)
      setCurrentStep(2)
      setSelectedServerFilePaths([])
      setFileList([])
      message.success('评估任务已创建，正在排队执行')
    } catch (error) {
      console.error('创建评估任务失败', error)
      message.error('创建评估任务失败，请稍后重试')
    } finally {
      setCreatingTask(false)
    }
  }

  useEffect(() => {
    const fetchStatus = async () => {
      if (!taskId) return
      try {
        const status = await evaluationService.getTaskStatus(taskId)
        setTaskStatus(status)

        if (status.stage_progress) {
          const stagePayload: Record<string, Partial<WorkflowStageSnapshot>> = {}
          Object.entries(status.stage_progress).forEach(([key, value]) => {
            const typedKey = key as EvaluationStageKey
            stagePayload[typedKey] = {
              key: (value.key as EvaluationStageKey) || typedKey,
              label: value.label,
              progress: value.progress ?? 0,
              status: (value.status as WorkflowStageSnapshot['status']) || 'pending',
              enabled: value.enabled ?? true,
              message: value.message ?? null,
              updatedAt: (value.updated_at || (value as any).updatedAt) ?? null,
            }
          })
          bulkUpdateEvaluationStages(stagePayload)
        }

        if (status.status === 'completed' && !workflowNotified) {
          setEvaluationWorkflowCompleted(taskId)
          setWorkflowNotified(true)
          message.success('评估任务已完成')
        }

        if (status.status === 'failed' && !workflowNotified) {
          message.error(status.message || '评估任务失败')
          setWorkflowNotified(true)
        }

        if (['completed', 'failed'].includes(status.status) && pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        } else if (!['completed', 'failed'].includes(status.status) && pollingRef.current) {
          // 根据任务状态动态调整轮询间隔
          // processing: 1秒刷新（有进度条显示）
          // pending: 4秒刷新（等待状态）
          const currentInterval = status.status === 'processing' ? 1000 : 4000
          clearInterval(pollingRef.current)
          pollingRef.current = setInterval(fetchStatus, currentInterval)
        }
      } catch (error) {
        console.error('拉取评估任务状态失败', error)
      }
    }

    if (taskId) {
      fetchStatus()
      // 初始轮询间隔设为4秒，后续根据状态动态调整
      pollingRef.current = setInterval(fetchStatus, 4000)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [taskId, workflowNotified, setEvaluationWorkflowCompleted, bulkUpdateEvaluationStages])

  const uploadProps: UploadProps = {
    multiple: true,
    accept: '.xlsx,.xls,.csv,.json',
    beforeUpload: (file) => {
      if (creatingTask) {
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
    disabled: creatingTask,
    fileList,
    onRemove: (file) => {
      if (creatingTask) {
        return false
      }
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
      return true
    },
  }

  // 步骤验证
  const validateStep = (step: number): boolean => {
    if (step === 0) {
      if (!llmName.trim()) {
        message.warning('请输入被评估模型名称')
        return false
      }
      if (!evalModelName.trim()) {
        message.warning('请选择评估模型')
        return false
      }
      return true
    }
    if (step === 1) {
      if (fileList.length === 0 && selectedServerFilePaths.length === 0) {
        message.warning('请至少上传或选择服务器文件')
        return false
      }
      return true
    }
    return true
  }

  // 下一步
  const handleNext = () => {
    if (validateStep(currentStep)) {
      if (currentStep === 1) {
        startEvaluation()
      } else {
        setCurrentStep(currentStep + 1)
      }
    }
  }

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

  // 渲染步骤1: 信息填写
  const renderStep1 = () => (
    <Card
      title={
        <Space>
          <FormOutlined />
          <span>评估信息填写</span>
        </Space>
      }
      style={{ borderRadius: 4 }}
    >
      <Alert
        message="第一步：填写评估基本信息"
        description="请填写被评估模型和评估模型信息，这些信息将用于后续的评估流程"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form
        form={form}
        layout="vertical"
      >
        {/* 被评估模型 */}
        <Divider orientation="left"></Divider>
        
        <Form.Item label="选择输入方式">
          <Select
            value={llmInputMode}
            onChange={setLlmInputMode}
            size="large"
          >
            <Select.Option value="select">从列表选择</Select.Option>
            <Select.Option value="custom">自定义输入</Select.Option>
          </Select>
        </Form.Item>

        {llmInputMode === 'select' ? (
          <Form.Item
            label="选择被评估模型"
            name="llm_name"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select
              placeholder="选择要评估的模型"
              size="large"
              value={llmName}
              onChange={setLlmName}
              loading={loadingModels}
              showSearch
              optionFilterProp="children"
            >
              {modelsData?.test_models.map(model => (
                <Select.Option key={model.key} value={model.key}>
                  {model.display_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Form.Item
            label="自定义模型名称"
            name="llm_name_custom"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input
              placeholder="例如: my-custom-model"
              size="large"
              value={llmName}
              onChange={(e) => setLlmName(e.target.value)}
            />
          </Form.Item>
        )}

        {/* 评估模型 */}
        <Divider orientation="left"></Divider>
        
        <Form.Item
          label="选择裁判模型"
          name="eval_model_name"
          rules={[{ required: true, message: '请选择评估模型' }]}
        >
          <Select
            placeholder="选择用于评估的模型"
            size="large"
            value={evalModelName}
            onChange={setEvalModelName}
            loading={loadingModels}
            showSearch
            optionFilterProp="children"
          >
            {modelsData?.eval_models.map(model => (
              <Select.Option key={model.key} value={model.key}>
                {model.display_name}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {/* 备注信息 */}
        <Divider orientation="left"></Divider>
        
        <Form.Item label="备注" name="description">
          <Input.TextArea
            placeholder="请输入任何相关的备注信息（可选）"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Form.Item>
      </Form>
    </Card>
  )

  // 渲染步骤2: 文件上传
  const renderStep2 = () => (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          <span>文件上传</span>
        </Space>
      }
      style={{ borderRadius: 4 }}
    >
      <Alert
        message="第二步：上传评估文件"
        description="支持批量上传Excel、CSV、JSON格式的评估数据文件，系统将自动解析并进行质量检查"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #667eea' }}>
            <Statistic
              title="本地待上传"
              value={fileList.length}
              suffix="个"
              valueStyle={{ color: '#667eea' }}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #4caf50' }}>
            <Statistic
              title="总大小"
              value={totalSelectedSize}
              suffix="MB"
              valueStyle={{ color: '#4caf50' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #ff9800' }}>
            <Statistic
              title="准备状态"
              value={totalSelectedFiles > 0 ? '就绪' : '等待'}
              valueStyle={{
                color: totalSelectedFiles > 0 ? '#4caf50' : '#999',
                fontSize: 20,
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card style={{ borderRadius: 8, borderTop: '3px solid #1890ff' }}>
            <Statistic
              title="服务器已选"
              value={selectedServerFilePaths.length}
              suffix="个"
              valueStyle={{ color: '#1890ff' }}
              prefix={<CloudServerOutlined />}
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
            <FileExcelOutlined style={{ fontSize: 64, color: '#667eea' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持单个或批量上传。支持格式: .xlsx, .xls, .csv, .json
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
                    avatar={<FileExcelOutlined style={{ fontSize: 32, color: '#4caf50' }} />}
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
                  {creatingTask && (
                    <Progress
                      percent={100}
                      status="active"
                      strokeColor="#667eea"
                      style={{ width: 200 }}
                    />
                  )}
                </List.Item>
              </motion.div>
            )}
          />
        </Card>
      )}

      <Card
        title={
          <Space>
            <CloudServerOutlined />
            <span>服务器已有文件</span>
          </Space>
        }
        style={{ borderRadius: 8, marginTop: 24 }}
      >
        {!llmName ? (
          <Alert message="请先填写模型名称以加载对应的服务器文件" type="info" showIcon />
        ) : loadingServerFiles ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="正在加载服务器文件..." />
          </div>
        ) : !serverFileInventory || ((serverFileInventory.uploads || []).length === 0 && (serverFileInventory.history || []).length === 0) ? (
          <Empty description="暂无服务器文件" />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Typography.Text>已勾选 {selectedServerFilePaths.length} 个服务器文件</Typography.Text>
              <Space>
                <Button size="small" icon={<ReloadOutlined />} onClick={() => refetchServerFiles()} disabled={loadingServerFiles}>
                  刷新
                </Button>
                {selectedServerFilePaths.length > 0 && (
                  <Button size="small" type="link" onClick={() => setSelectedServerFilePaths([])}>
                    清空选择
                  </Button>
                )}
              </Space>
            </Space>

            {(serverFileInventory.uploads || []).length > 0 && (
              <Card size="small" type="inner" title="上传缓存" style={{ borderRadius: 6 }}>
                <List
                  dataSource={serverFileInventory.uploads}
                  renderItem={file => (
                    <List.Item key={file.file_path}>
                      <Checkbox
                        checked={selectedServerFilePaths.includes(file.file_path)}
                        onChange={(e) => toggleServerFileSelection(file.file_path, e.target.checked)}
                        disabled={creatingTask}
                      >
                        <Space direction="vertical" size={0}>
                          <Typography.Text strong>{file.file_name}</Typography.Text>
                          <Typography.Text type="secondary">{formatFileSize(file.size)}</Typography.Text>
                        </Space>
                      </Checkbox>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {(serverFileInventory.history || []).length > 0 && (
              <Collapse bordered={false} accordion>
                {(serverFileInventory.history || []).map((group: ServerHistoryGroup) => (
                  <Panel header={`${group.display_name}（${group.files.length} 个文件）`} key={`${group.model_name}-${group.timestamp}`}>
                    <List
                      dataSource={group.files}
                      renderItem={(file: ServerFileMeta) => {
                        const checked = selectedServerFilePaths.includes(file.file_path)
                        return (
                          <List.Item key={file.file_path}>
                            <Checkbox
                              checked={checked}
                              onChange={(e) => toggleServerFileSelection(file.file_path, e.target.checked)}
                              disabled={creatingTask}
                            >
                              <Space direction="vertical" size={0}>
                                <Typography.Text strong>{file.file_name}</Typography.Text>
                                <Typography.Text type="secondary">
                                  {group.model_name} · {formatFileSize(file.size)}
                                </Typography.Text>
                                <Tooltip title={file.file_path}>
                                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                                    {file.timestamp ? `时间戳 ${file.timestamp}` : '系统文件'}
                                  </Typography.Text>
                                </Tooltip>
                              </Space>
                            </Checkbox>
                          </List.Item>
                        )
                      }}
                    />
                  </Panel>
                ))}
              </Collapse>
            )}
          </Space>
        )}
      </Card>

      <Card title="评估类型" style={{ borderRadius: 8, marginTop: 24 }}>
        <Form.Item
          label="选择评估类型"
          style={{ marginBottom: 0 }}
        >
          <Select
            size="large"
            value={evaluationType}
            onChange={setEvaluationType}
            disabled={creatingTask}
          >
            <Select.Option value="stage1">第一阶段评估</Select.Option>
            <Select.Option value="stage2">第二阶段评估</Select.Option>
            <Select.Option value="both">双阶段评估</Select.Option>
          </Select>
        </Form.Item>
      </Card>

      <Card title="阈值与轮次配置" style={{ borderRadius: 8, marginTop: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12} lg={6}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Typography.Text>Stage1 答案阈值</Typography.Text>
              <Slider
                min={0}
                max={100}
                step={1}
                value={stage1AnswerThreshold}
                tooltip={{ formatter: value => `${value} 分` }}
                onChange={(val) => setStage1AnswerThreshold(Number(val))}
                disabled={creatingTask}
              />
              <InputNumber
                min={0}
                max={100}
                value={stage1AnswerThreshold}
                onChange={(val) => setStage1AnswerThreshold(val ?? 0)}
                style={{ width: '100%' }}
                disabled={creatingTask}
              />
            </Space>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Typography.Text>Stage1 推理阈值</Typography.Text>
              <Slider
                min={0}
                max={100}
                step={1}
                value={stage1ReasoningThreshold}
                tooltip={{ formatter: value => `${value} 分` }}
                onChange={(val) => setStage1ReasoningThreshold(Number(val))}
                disabled={creatingTask}
              />
              <InputNumber
                min={0}
                max={100}
                value={stage1ReasoningThreshold}
                onChange={(val) => setStage1ReasoningThreshold(val ?? 0)}
                style={{ width: '100%' }}
                disabled={creatingTask}
              />
            </Space>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Typography.Text>Stage2 答案阈值</Typography.Text>
              <Slider
                min={0}
                max={100}
                step={1}
                value={stage2AnswerThreshold}
                tooltip={{ formatter: value => `${value} 分` }}
                onChange={(val) => setStage2AnswerThreshold(Number(val))}
                disabled={creatingTask}
              />
              <InputNumber
                min={0}
                max={100}
                value={stage2AnswerThreshold}
                onChange={(val) => setStage2AnswerThreshold(val ?? 0)}
                style={{ width: '100%' }}
                disabled={creatingTask}
              />
            </Space>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Typography.Text>Stage2 推理阈值</Typography.Text>
              <Slider
                min={0}
                max={100}
                step={1}
                value={stage2ReasoningThreshold}
                tooltip={{ formatter: value => `${value} 分` }}
                onChange={(val) => setStage2ReasoningThreshold(Number(val))}
                disabled={creatingTask}
              />
              <InputNumber
                min={0}
                max={100}
                value={stage2ReasoningThreshold}
                onChange={(val) => setStage2ReasoningThreshold(val ?? 0)}
                style={{ width: '100%' }}
                disabled={creatingTask}
              />
            </Space>
          </Col>
        </Row>
        <Divider />
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12} lg={6}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Typography.Text>评估轮次</Typography.Text>
              <Slider
                min={1}
                max={5}
                value={evaluationRounds}
                step={1}
                onChange={(val) => setEvaluationRounds(Number(val))}
                disabled={creatingTask}
              />
              <InputNumber
                min={1}
                max={5}
                value={evaluationRounds}
                onChange={(val) => setEvaluationRounds(val ?? 1)}
                style={{ width: '100%' }}
                disabled={creatingTask}
              />
            </Space>
          </Col>
        </Row>
      </Card>
    </Card>
  )

  // 渲染步骤3: 评估进程
  const renderStep3 = () => {
    const status = taskStatus?.status || 'pending'
    const statusTextMap: Record<string, { label: string; color: string }> = {
      pending: { label: '等待开始', color: '#faad14' },
      processing: { label: '进行中', color: '#1890ff' },
      completed: { label: '已完成', color: '#52c41a' },
      failed: { label: '已失败', color: '#ff4d4f' },
    }

    const statusInfo = statusTextMap[status] || statusTextMap.pending
    const progressValue = taskStatus?.progress ?? 0
    const filesCount = taskStatus?.files?.length || uploadedServerFiles.length || fileList.length

    return (
      <Card
        title={
          <Space>
            <FundProjectionScreenOutlined />
            <span>评估进程</span>
          </Space>
        }
        style={{ borderRadius: 4 }}
      >
        {!taskId ? (
          <Empty description="请先创建评估任务" style={{ padding: '40px 0' }} />
        ) : (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} sm={6}>
                <Card style={{ borderRadius: 8, borderTop: '3px solid #667eea' }}>
                  <Statistic
                    title="当前阶段"
                    value={taskStatus?.current_stage || '等待中'}
                    valueStyle={{ color: '#667eea', fontSize: 18 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card style={{ borderRadius: 8, borderTop: '3px solid #4caf50' }}>
                  <Statistic
                    title="进度"
                    value={progressValue}
                    suffix="%"
                    valueStyle={{ color: '#4caf50' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card style={{ borderRadius: 8, borderTop: '3px solid #ff9800' }}>
                  <Statistic
                    title="任务状态"
                    value={statusInfo.label}
                    valueStyle={{ color: statusInfo.color, fontSize: 18 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card style={{ borderRadius: 8, borderTop: '3px solid #2196f3' }}>
                  <Statistic
                    title="处理文件"
                    value={filesCount}
                    suffix="个"
                    valueStyle={{ color: '#2196f3' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 进度显示 */}
            {taskStatus && (taskStatus.file_progress || taskStatus.step_progress) && (
              <Card
                title={
                  <Space>
                    {status === 'processing' ? (
                      <SyncOutlined spin style={{ color: '#0052D9' }} />
                    ) : status === 'completed' ? (
                      <CheckCircleOutlined style={{ color: '#00A870' }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#D54941' }} />
                    )}
                    <Typography.Text strong>执行进度</Typography.Text>
                  </Space>
                }
                style={{ borderRadius: 12, marginTop: 12 }}
              >
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {/* 文件处理进度 */}
                  {taskStatus.file_progress && taskStatus.step_progress && (() => {
                    const stageMap: Record<string, number> = {
                      'stage1_infer': 1,
                      'stage1_eval': 2,
                      'stage2_infer': 3,
                      'stage2_eval': 4,
                      'analysis': 5,
                    }
                    const currentStageNum = stageMap[taskStatus.step_progress.current_step] || 1
                    const currentFileIndex = taskStatus.file_progress.current_file || 1
                    const totalFiles = taskStatus.file_progress.total_files || 1
                    
                    // 计算当前文件的阶段完成度（0-1）
                    const completedStagesInCurrentFile = currentStageNum - 1
                    const currentStageProgressInFile = taskStatus.step_progress.step_progress_percent / 100
                    const currentFileProgress = (completedStagesInCurrentFile + currentStageProgressInFile) / 5
                    
                    // 计算整体文件处理进度
                    // (已完成的文件数 + 当前文件的完成度) / 总文件数 * 100
                    const completedFiles = currentFileIndex - 1
                    const overallFileProgress = ((completedFiles + currentFileProgress) / totalFiles) * 100
                    
                    return (
                      <Card size="small" style={{ borderRadius: 10, background: '#e6f4ff' }}>
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                            <Typography.Text strong>
                              <FileTextOutlined /> 文件处理进度
                            </Typography.Text>
                            <Tag color="blue">
                              文件 {currentFileIndex}/{totalFiles}
                            </Tag>
                          </Space>
                          {taskStatus.file_progress.current_filename && (
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              当前文件：{taskStatus.file_progress.current_filename}
                            </Typography.Text>
                          )}
                          <Progress
                            percent={Math.round(overallFileProgress)}
                            strokeColor="#1677ff"
                            strokeWidth={18}
                            status={status === 'processing' ? 'active' : 'normal'}
                          />
                        </Space>
                      </Card>
                    )
                  })()}

                  {/* 阶段进度 */}
                  {taskStatus.step_progress && (() => {
                    const stageMap: Record<string, number> = {
                      'stage1_infer': 1,
                      'stage1_eval': 2,
                      'stage2_infer': 3,
                      'stage2_eval': 4,
                      'analysis': 5,
                    }
                    const currentStageNum = stageMap[taskStatus.step_progress.current_step] || 1
                    const isProcessing = status === 'processing'
                    const isCompleted = status === 'completed'
                    
                    const stages = [
                      { num: 1, label: 'Stage1推理' },
                      { num: 2, label: 'Stage1评估' },
                      { num: 3, label: 'Stage2推理' },
                      { num: 4, label: 'Stage2评估' },
                      { num: 5, label: '结果分析' },
                    ]
                    
                    // 计算整体阶段进度：已完成的阶段数 / 总阶段数 * 100
                    // 当前阶段正在进行时，加上当前阶段内的进度比例
                    const completedStages = currentStageNum - 1 // 已完成的阶段数
                    const currentStageProgress = taskStatus.step_progress.step_progress_percent / 100 // 当前阶段内的进度 (0-1)
                    const overallProgress = ((completedStages + currentStageProgress) / 5) * 100
                    
                    const getStageColor = (stageNum: number) => {
                      if (isCompleted || currentStageNum > stageNum) return 'success'
                      if (currentStageNum === stageNum && isProcessing) return 'processing'
                      return 'default'
                    }
                    
                    const getStageIcon = (stageNum: number) => {
                      if (isCompleted || currentStageNum > stageNum) return <CheckCircleOutlined />
                      if (currentStageNum === stageNum && isProcessing) return <SyncOutlined spin />
                      return null
                    }
                    
                    return (
                      <Card size="small" style={{ borderRadius: 8, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Row justify="space-between" align="middle">
                            <Col>
                              <Space>
                                <SyncOutlined 
                                  spin={isProcessing} 
                                  style={{ fontSize: 16, color: '#52c41a' }} 
                                />
                                <Typography.Text strong style={{ fontSize: 15 }}>
                                  阶段进度
                                </Typography.Text>
                              </Space>
                            </Col>
                            <Col>
                              <Tag color={currentStageNum < 5 ? 'processing' : 'success'}>
                                阶段 {currentStageNum}/5
                              </Tag>
                            </Col>
                          </Row>
                          <Progress
                            percent={Math.round(overallProgress)}
                            strokeColor="#52c41a"
                            strokeWidth={16}
                            status={isProcessing ? 'active' : 'normal'}
                          />
                          {/* 阶段标签 */}
                          <Row gutter={[4, 8]} style={{ marginTop: 8 }}>
                            {stages.map((stage) => (
                              <Col key={stage.num} flex="1">
                                <Tag
                                  color={getStageColor(stage.num)}
                                  style={{ 
                                    width: '100%', 
                                    textAlign: 'center', 
                                    padding: '4px 2px',
                                    margin: 0,
                                    fontSize: '12px',
                                  }}
                                >
                                  {getStageIcon(stage.num)} {stage.label}
                                </Tag>
                              </Col>
                            ))}
                          </Row>
                        </Space>
                      </Card>
                    )
                  })()}

                  {/* 当前步骤 - 始终显示 */}
                  {taskStatus.step_progress && (
                    <Card size="small" style={{ borderRadius: 10, background: '#fff7e6' }}>
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                          <Typography.Text strong>
                            <AimOutlined /> 当前步骤
                          </Typography.Text>
                          {(taskStatus.step_progress.total_questions ?? 0) > 0 ? (
                            <Tag color="orange">
                              {taskStatus.step_progress.current_question || 0}/{taskStatus.step_progress.total_questions} 问题
                            </Tag>
                          ) : (
                            <Tag color="orange">处理中</Tag>
                          )}
                        </Space>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {(taskStatus.step_progress.total_questions ?? 0) > 0
                            ? `正在处理问题 ${taskStatus.step_progress.current_question || 0}/${taskStatus.step_progress.total_questions}`
                            : (() => {
                                const stepLabels: Record<string, string> = {
                                  stage1_infer: 'Stage1 推理',
                                  stage1_eval: 'Stage1 评估',
                                  stage2_infer: 'Stage2 推理',
                                  stage2_eval: 'Stage2 评估',
                                  analysis: '结果分析',
                                }
                                return stepLabels[taskStatus.step_progress.current_step] || '处理中'
                              })()
                          }
                        </Typography.Text>
                        <Progress
                          percent={
                            (taskStatus.step_progress.total_questions ?? 0) > 0
                              ? Math.round(
                                  ((taskStatus.step_progress.current_question || 0) /
                                    (taskStatus.step_progress.total_questions ?? 1)) *
                                    100
                                )
                              : Math.round(taskStatus.step_progress.step_progress_percent)
                          }
                          strokeColor="#fa8c16"
                          strokeWidth={14}
                          status={status === 'processing' ? 'active' : 'normal'}
                        />
                      </Space>
                    </Card>
                  )}

                  {/* 当前状态信息 */}
                  {taskStatus.message && (
                    <Alert
                      message={taskStatus.message}
                      type={
                        status === 'completed'
                          ? 'success'
                          : status === 'failed'
                          ? 'error'
                          : 'info'
                      }
                      showIcon
                    />
                  )}
                </Space>
              </Card>
            )}

            {(uploadedServerFiles.length > 0 || taskStatus?.files?.length) && (
              <Card title="任务文件" style={{ borderRadius: 8, marginBottom: 24 }}>
                <List
                  dataSource={taskStatus?.files || uploadedServerFiles.map(item => item.file_path)}
                  renderItem={(item) => (
                    <List.Item>
                      <FileTextOutlined style={{ color: '#667eea', marginRight: 8 }} />
                      <Typography.Text>
                        {(() => {
                          const path = typeof item === 'string' ? item : ''
                          const name = path.split(/[/\\]/).pop() || path
                          return name || '未命名文件'
                        })()}
                      </Typography.Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {status === 'completed' && (
              <Alert
                message="评估完成"
                description="所有评估任务已完成，您可以前往「结果分析」查看详细的评估报告和数据分析"
                type="success"
                showIcon
                style={{ marginTop: 24 }}
              />
            )}

            {status === 'failed' && (
              <Alert
                message="评估失败"
                description={taskStatus?.message || '请稍后重试或联系管理员'}
                type="error"
                showIcon
                style={{ marginTop: 24 }}
              />
            )}
          </>
        )}
      </Card>
    )
  }

  const steps = [
    { title: '信息填写', content: renderStep1() },
    { title: '文件上传', content: renderStep2() },
    { title: '评估进程', content: renderStep3() },
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
            borderRadius: 4,
          }}
        >
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Title level={2} style={{ color: 'white', margin: 0 }}>
              <FundProjectionScreenOutlined /> 智能评估与报告生成系统
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.9)', margin: 0 }}>
              
            </Paragraph>
          </Space>
        </Card>
      </motion.div>

      {/* Steps */}
      <Card style={{ marginBottom: 24, borderRadius: 4 }}>
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
      <Card style={{ marginTop: 24, borderRadius: 4 }}>
        <Space size="large">
          {currentStep > 0 && currentStep < 2 && (
            <Button size="large" icon={<LeftOutlined />} onClick={handlePrev}>
              上一步
            </Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button
              type="primary"
              size="large"
              onClick={handleNext}
              icon={<ArrowRightOutlined />}
              loading={creatingTask}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
              }}
            >
              {currentStep === 1 ? '开始评估' : '下一步'}
            </Button>
          )}
          {currentStep === 1 && fileList.length > 0 && (
            <Button size="large" onClick={() => setFileList([])} disabled={creatingTask}>
              清空列表
            </Button>
          )}
        </Space>
      </Card>
    </div>
  )
}

export default EvaluationWorkflow
