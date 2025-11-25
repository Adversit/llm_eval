import { useState } from 'react'
import { useWorkflow } from '../../hooks/useWorkflow'
import {
  Card,
  Typography,
  Form,
  Input,
  Button,
  Space,
  Steps,
  message,
  Row,
  Col,
  Tree,
  Checkbox,
  Modal,
  Spin,
  Alert,
  Divider,
  Tag,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  RightOutlined,
  LeftOutlined,
  FolderOutlined,
  FileOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  flmmService,
  FunctionModule,
  SelectedItem,
  ProjectCreateRequest,
} from '../../services/flmmService'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Step } = Steps

interface TreeNodeData {
  key: string
  title: string
  children?: TreeNodeData[]
  isLeaf?: boolean
  questionCount?: number
  questions?: string[]
  domain?: string
  subdomain1?: string
  subdomain2?: string
  item?: string
}

const FLMMCreate = () => {
  const { setFLMMProcessCompleted } = useWorkflow()
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()

  // 步骤1: 基本信息
  const [companyName, setCompanyName] = useState('')
  const [scenarioName, setScenarioName] = useState('')
  const [scenarioDescription, setScenarioDescription] = useState('')
  const [functionsList, setFunctionsList] = useState<FunctionModule[]>([])

  // 步骤2: 问卷筛选
  const [selectedQuestionnaireKeys, setSelectedQuestionnaireKeys] = useState<string[]>([])
  const [selectedQuestionnaireItems, setSelectedQuestionnaireItems] = useState<SelectedItem[]>([])

  // 步骤3: 证明材料筛选
  const [selectedEvidenceKeys, setSelectedEvidenceKeys] = useState<string[]>([])
  const [selectedEvidenceItems, setSelectedEvidenceItems] = useState<SelectedItem[]>([])
  const [enableEvidence, setEnableEvidence] = useState(false)

  // 步骤4: 项目设置
  const [autoGenerateAccount, setAutoGenerateAccount] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  // 获取FLMM调研表结构
  const { data: questionnaireStructure, isLoading: loadingQuestionnaire } = useQuery({
    queryKey: ['flmm-questionnaire-structure'],
    queryFn: () => flmmService.getQuestionnaireStructure(),
  })

  // 获取FLMM自评表结构
  const { data: evidenceStructure, isLoading: loadingEvidence } = useQuery({
    queryKey: ['flmm-evidence-structure'],
    queryFn: () => flmmService.getEvidenceStructure(),
    enabled: enableEvidence,
  })

  // 创建项目
  const createProjectMutation = useMutation({
    mutationFn: (data: ProjectCreateRequest) => flmmService.createProject(data),
    retry: false, // 禁用重试，防止重复创建
    onSuccess: (data) => {
      // 记录完成状态
      setFLMMProcessCompleted(data.project_id)

      Modal.success({
        title: '项目创建成功！',
        content: (
          <div>
            <p><strong>项目信息：</strong></p>
            <p>• 项目ID: <Text code>{data.project_id}</Text></p>
            <p>• 项目文件夹: <Text code>{data.folder_name}</Text></p>

            <Divider />

            <div style={{ background: '#f6ffed', padding: '12px', borderRadius: '4px', border: '1px solid #b7eb8f' }}>
              <p><strong>登录账号信息（请保存）：</strong></p>
              <p>• 用户名: <Text copyable strong code>{data.account.username}</Text></p>
              <p>• 密码: <Text copyable strong code>{data.account.password}</Text></p>
              {data.account.login_url && data.account.login_url !== '待部署' && (
                <p>
                  • 访问链接: <Text copyable code>{data.account.login_url}</Text>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => window.open(data.account.login_url, '_blank')}
                  >
                    立即打开
                  </Button>
                </p>
              )}
            </div>

            <Divider />

            <p><strong>生成的文件：</strong></p>
            {data.generated_files.map((file, i) => (
              <p key={i}>• {file}</p>
            ))}

            <Divider />

            <p style={{ color: '#1890ff' }}>提示：</p>
            <p>• 账号密码可在 <strong>"项目管理"</strong> 页面随时查看</p>
            <p>• 访问链接已自动启动，请等待5-10秒后访问</p>
            <p>• 评估完成后可在 <strong>"结果分析"</strong> 查看数据</p>
          </div>
        ),
        width: 650,
        okText: '我知道了',
        onOk: () => {
          // 重置表单
          resetAllSteps()
        },
      })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '项目创建失败')
    },
  })

  // 重置所有步骤
  const resetAllSteps = () => {
    setCurrentStep(0)
    setCompanyName('')
    setScenarioName('')
    setScenarioDescription('')
    setFunctionsList([])
    setSelectedQuestionnaireKeys([])
    setSelectedQuestionnaireItems([])
    setSelectedEvidenceKeys([])
    setSelectedEvidenceItems([])
    setEnableEvidence(false)
    setAutoGenerateAccount(true)
    setUsername('')
    setPassword('')
    form.resetFields()
  }

  // 添加功能模块
  const addFunction = () => {
    const newFunc: FunctionModule = {
      name: '',
      description: '',
    }
    setFunctionsList([...functionsList, newFunc])
  }

  // 删除功能模块
  const removeFunction = (index: number) => {
    const newList = functionsList.filter((_, i) => i !== index)
    setFunctionsList(newList)
  }

  // 更新功能模块
  const updateFunction = (index: number, field: keyof FunctionModule, value: string) => {
    const newList = [...functionsList]
    newList[index] = { ...newList[index], [field]: value }
    setFunctionsList(newList)
  }

  // 构建问卷树形数据
  const buildQuestionnaireTree = (): TreeNodeData[] => {
    if (!questionnaireStructure?.structure) return []

    const tree: TreeNodeData[] = []
    const structure = questionnaireStructure.structure

    Object.keys(structure).forEach((domain) => {
      const domainNode: TreeNodeData = {
        key: `domain-${domain}`,
        title: `${domain} (能力域)`,
        children: [],
      }

      Object.keys(structure[domain]).forEach((subdomain1) => {
        const subdomain1Node: TreeNodeData = {
          key: `subdomain1-${domain}-${subdomain1}`,
          title: `${subdomain1} (子域1)`,
          children: [],
        }

        Object.keys(structure[domain][subdomain1]).forEach((subdomain2) => {
          const items = structure[domain][subdomain1][subdomain2]

          if (subdomain2 && subdomain2 !== 'undefined') {
            // 有子域2
            const subdomain2Node: TreeNodeData = {
              key: `subdomain2-${domain}-${subdomain1}-${subdomain2}`,
              title: `${subdomain2} (子域2)`,
              children: [],
            }

            Object.keys(items).forEach((item) => {
              const questions = items[item]
              subdomain2Node.children!.push({
                key: `item-${domain}-${subdomain1}-${subdomain2}-${item}`,
                title: `${item} (${questions.length}题)`,
                isLeaf: true,
                questionCount: questions.length,
                questions: questions,
                domain,
                subdomain1,
                subdomain2,
                item,
              })
            })

            subdomain1Node.children!.push(subdomain2Node)
          } else {
            // 无子域2，直接添加能力项
            Object.keys(items).forEach((item) => {
              const questions = items[item]
              subdomain1Node.children!.push({
                key: `item-${domain}-${subdomain1}--${item}`,
                title: `${item} (${questions.length}题)`,
                isLeaf: true,
                questionCount: questions.length,
                questions: questions,
                domain,
                subdomain1,
                subdomain2: '',
                item,
              })
            })
          }
        })

        domainNode.children!.push(subdomain1Node)
      })

      tree.push(domainNode)
    })

    return tree
  }

  // 构建证明材料树形数据
  const buildEvidenceTree = (): TreeNodeData[] => {
    if (!evidenceStructure?.structure) return []

    const tree: TreeNodeData[] = []
    const structure = evidenceStructure.structure

    Object.keys(structure).forEach((domain) => {
      const domainNode: TreeNodeData = {
        key: `ev-domain-${domain}`,
        title: `${domain} (能力域)`,
        children: [],
      }

      Object.keys(structure[domain]).forEach((subdomain1) => {
        const subdomain1Node: TreeNodeData = {
          key: `ev-subdomain1-${domain}-${subdomain1}`,
          title: `${subdomain1} (子域1)`,
          children: [],
        }

        Object.keys(structure[domain][subdomain1]).forEach((subdomain2) => {
          const items = structure[domain][subdomain1][subdomain2]

          if (subdomain2 && subdomain2 !== 'undefined') {
            const subdomain2Node: TreeNodeData = {
              key: `ev-subdomain2-${domain}-${subdomain1}-${subdomain2}`,
              title: `${subdomain2} (子域2)`,
              children: [],
            }

            items.forEach((item: string) => {
              subdomain2Node.children!.push({
                key: `ev-item-${domain}-${subdomain1}-${subdomain2}-${item}`,
                title: item,
                isLeaf: true,
                domain,
                subdomain1,
                subdomain2,
                item,
              })
            })

            subdomain1Node.children!.push(subdomain2Node)
          } else {
            items.forEach((item: string) => {
              subdomain1Node.children!.push({
                key: `ev-item-${domain}-${subdomain1}--${item}`,
                title: item,
                isLeaf: true,
                domain,
                subdomain1,
                subdomain2: '',
                item,
              })
            })
          }
        })

        domainNode.children!.push(subdomain1Node)
      })

      tree.push(domainNode)
    })

    return tree
  }

  // 处理问卷树选择
  const handleQuestionnaireCheck = (checkedKeys: any) => {
    setSelectedQuestionnaireKeys(checkedKeys)

    // 收集所有叶子节点（能力项）
    const leafNodes: TreeNodeData[] = []
    const collectLeafNodes = (nodes: TreeNodeData[]) => {
      nodes.forEach((node) => {
        if (node.isLeaf && checkedKeys.includes(node.key)) {
          leafNodes.push(node)
        }
        if (node.children) {
          collectLeafNodes(node.children)
        }
      })
    }
    collectLeafNodes(buildQuestionnaireTree())

    // 转换为SelectedItem格式
    const items: SelectedItem[] = leafNodes.map((node) => ({
      domain: node.domain!,
      subdomain1: node.subdomain1!,
      subdomain2: node.subdomain2,
      item: node.item!,
      questions: node.questions,
      question_count: node.questionCount,
    }))

    setSelectedQuestionnaireItems(items)
  }

  // 处理证明材料树选择
  const handleEvidenceCheck = (checkedKeys: any) => {
    setSelectedEvidenceKeys(checkedKeys)

    const leafNodes: TreeNodeData[] = []
    const collectLeafNodes = (nodes: TreeNodeData[]) => {
      nodes.forEach((node) => {
        if (node.isLeaf && checkedKeys.includes(node.key)) {
          leafNodes.push(node)
        }
        if (node.children) {
          collectLeafNodes(node.children)
        }
      })
    }
    collectLeafNodes(buildEvidenceTree())

    const items: SelectedItem[] = leafNodes.map((node) => ({
      domain: node.domain!,
      subdomain1: node.subdomain1!,
      subdomain2: node.subdomain2,
      item: node.item!,
    }))

    setSelectedEvidenceItems(items)
  }

  // 步骤验证
  const validateStep = (step: number): boolean => {
    switch (step) {
      case 0:
        if (!companyName.trim()) {
          message.warning('请输入公司名称')
          return false
        }
        if (!scenarioName.trim()) {
          message.warning('请输入评估场景名称')
          return false
        }

        return true
      case 1:
        if (selectedQuestionnaireItems.length === 0) {
          message.warning('请至少选择一个问卷能力项')
          return false
        }
        return true
      case 2:
        // 证明材料是可选的
        return true
      case 3:
        if (!autoGenerateAccount) {
          if (!username.trim()) {
            message.warning('请输入用户名')
            return false
          }
          if (!password.trim()) {
            message.warning('请输入密码')
            return false
          }
        }
        return true
      default:
        return true
    }
  }

  // 下一步
  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(currentStep + 1)
    }
  }

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

  // 提交项目
  const handleSubmit = () => {
    if (!validateStep(currentStep)) return

    // 防止重复提交
    if (createProjectMutation.isPending) {
      message.warning('项目正在创建中，请稍候...')
      return
    }

    const data: ProjectCreateRequest = {
      company_name: companyName,
      scenario_name: scenarioName,
      scenario_description: scenarioDescription,
      functions_list: functionsList,
      selected_questionnaire_items: selectedQuestionnaireItems,
      selected_evidence_items: enableEvidence ? selectedEvidenceItems : [],
      enable_questionnaire: true,
      enable_evidence: enableEvidence,
      auto_generate_account: autoGenerateAccount,
      username: autoGenerateAccount ? undefined : username,
      password: autoGenerateAccount ? undefined : password,
    }

    createProjectMutation.mutate(data)
  }

  // 渲染步骤1: 基本信息
  const renderStep1 = () => (
    <Card title="被评估方信息" style={{ borderRadius: 4 }}>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Text strong>公司名称 <Text type="danger">*</Text></Text>
          <Input
            placeholder="请输入被评估方公司全称"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            size="large"
            style={{ marginTop: 8 }}
          />
        </Col>
        <Col span={12}>
          <Text strong>评估大模型名称 <Text type="danger">*</Text></Text>
          <Input
            placeholder="请输入具体的大模型名称"
            value={scenarioName}
            onChange={(e) => setScenarioName(e.target.value)}
            size="large"
            style={{ marginTop: 8 }}
          />
        </Col>
        <Col span={24}>
          <Text strong>评估业务场景描述 <Text type="secondary">(可选)</Text></Text>
          <TextArea
            placeholder="请详细描述该业务场景的具体内容、应用范围和预期目标..."
            value={scenarioDescription}
            onChange={(e) => setScenarioDescription(e.target.value)}
            rows={4}
            style={{ marginTop: 8 }}
          />
        </Col>
      </Row>

      <Divider />

      <div>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong>功能模块管理</Text>
          <Button type="dashed" icon={<PlusOutlined />} onClick={addFunction}>
            添加功能
          </Button>
        </div>

        {functionsList.length === 0 ? (
          <Alert message='暂无功能模块，点击"添加功能"开始添加' type="info" showIcon />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {functionsList.map((func, index) => (
              <Card key={index} size="small" style={{ backgroundColor: '#f5f5f5' }}>
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Input
                      placeholder="功能名称"
                      value={func.name}
                      onChange={(e) => updateFunction(index, 'name', e.target.value)}
                    />
                  </Col>
                  <Col span={14}>
                    <Input
                      placeholder="功能描述"
                      value={func.description}
                      onChange={(e) => updateFunction(index, 'description', e.target.value)}
                    />
                  </Col>
                  <Col span={2}>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => removeFunction(index)}
                      block
                    />
                  </Col>
                </Row>
              </Card>
            ))}
          </Space>
        )}
      </div>
    </Card>
  )

  // 渲染步骤2: 问卷筛选
  const renderStep2 = () => (
    <Row gutter={24}>
      <Col span={14}>
        <Card title="问卷内容选择" style={{ borderRadius: 4, height: 600, overflow: 'auto' }}>
          {loadingQuestionnaire ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
              <p style={{ marginTop: 16 }}>加载FLMM调研表数据...</p>
            </div>
          ) : (
            <>
              <Alert
                message="请选择需要评估的能力项。您可以按能力域、子域或具体能力项进行选择。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Tree
                checkable
                defaultExpandAll
                checkedKeys={selectedQuestionnaireKeys}
                onCheck={handleQuestionnaireCheck}
                treeData={buildQuestionnaireTree()}
                showIcon
                icon={<FolderOutlined />}
              />
            </>
          )}
        </Card>
      </Col>
      <Col span={10}>
        <Card title="筛选结果" style={{ borderRadius: 4, height: 600, overflow: 'auto' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Row gutter={16}>
                <Col span={12}>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <Text type="secondary">选中能力项</Text>
                      <Title level={3} style={{ margin: '8px 0' }}>
                        {selectedQuestionnaireItems.length}
                      </Title>
                    </div>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <Text type="secondary">总问题数</Text>
                      <Title level={3} style={{ margin: '8px 0' }}>
                        {selectedQuestionnaireItems.reduce((sum, item) => sum + (item.question_count || 0), 0)}
                      </Title>
                    </div>
                  </Card>
                </Col>
              </Row>
            </div>

            <Divider />

            {selectedQuestionnaireItems.length > 0 ? (
              <div>
                <Text strong>已选择的能力项：</Text>
                <div style={{ marginTop: 12 }}>
                  {selectedQuestionnaireItems.map((item, index) => (
                    <div key={index} style={{ marginBottom: 12 }}>
                      <Tag color="blue" style={{ marginBottom: 4 }}>
                        {index + 1}. {item.item}
                      </Tag>
                      <div style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                        {item.domain} → {item.subdomain1} {item.subdomain2 ? `→ ${item.subdomain2}` : ''}
                      </div>
                      <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                        包含 {item.question_count} 个问题
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Alert message="请在左侧选择需要评估的能力项" type="warning" showIcon />
            )}
          </Space>
        </Card>
      </Col>
    </Row>
  )

  // 渲染步骤3: 证明材料筛选
  const renderStep3 = () => (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Checkbox
          checked={enableEvidence}
          onChange={(e) => setEnableEvidence(e.target.checked)}
        >
          <Text strong>启用证明材料收集功能</Text>
        </Checkbox>
      </div>

      {enableEvidence ? (
        <Row gutter={24}>
          <Col span={14}>
            <Card title="证明材料能力项选择" style={{ borderRadius: 4, height: 600, overflow: 'auto' }}>
              {loadingEvidence ? (
                <div style={{ textAlign: 'center', padding: 60 }}>
                  <Spin size="large" />
                  <p style={{ marginTop: 16 }}>加载FLMM自评表数据...</p>
                </div>
              ) : (
                <>
                  <Alert
                    message="请选择需要收集证明材料的能力项"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Tree
                    checkable
                    defaultExpandAll
                    checkedKeys={selectedEvidenceKeys}
                    onCheck={handleEvidenceCheck}
                    treeData={buildEvidenceTree()}
                    showIcon
                    icon={<FileOutlined />}
                  />
                </>
              )}
            </Card>
          </Col>
          <Col span={10}>
            <Card title="筛选结果" style={{ borderRadius: 4, height: 600, overflow: 'auto' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary">选中能力项</Text>
                    <Title level={3} style={{ margin: '8px 0' }}>
                      {selectedEvidenceItems.length}
                    </Title>
                  </div>
                </Card>

                <Divider />

                {selectedEvidenceItems.length > 0 ? (
                  <div>
                    <Text strong>已选择的能力项：</Text>
                    <div style={{ marginTop: 12 }}>
                      {selectedEvidenceItems.map((item, index) => (
                        <div key={index} style={{ marginBottom: 8 }}>
                          <Tag color="green">{index + 1}. {item.item}</Tag>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <Alert message="请在左侧选择需要收集证明材料的能力项" type="warning" showIcon />
                )}
              </Space>
            </Card>
          </Col>
        </Row>
      ) : (
        <Alert
          message="证明材料收集功能未启用"
          description="如需收集证明材料，请勾选上方的启用选项"
          type="info"
          showIcon
        />
      )}
    </div>
  )

  // 渲染步骤4: 预览确认
  const renderStep4 = () => (
    <Row gutter={24}>
      <Col span={16}>
        <Card title="项目信息预览" style={{ borderRadius: 4, marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>被评估方信息</Text>
              <div style={{ marginTop: 12, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 8 }}>
                <p><Text type="secondary">公司名称：</Text>{companyName}</p>
                <p><Text type="secondary">场景名称：</Text>{scenarioName}</p>
                <p><Text type="secondary">场景描述：</Text>{scenarioDescription}</p>
                {functionsList.length > 0 && (
                  <div>
                    <Text type="secondary">功能模块：</Text>
                    {functionsList.map((func, i) => (
                      <Tag key={i} color="blue" style={{ marginTop: 4 }}>{func.name}</Tag>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <Text strong>问卷选择</Text>
              <div style={{ marginTop: 12, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 8 }}>
                <p>
                  <Text type="secondary">已选择能力项：</Text>
                  <Text strong>{selectedQuestionnaireItems.length}</Text> 项
                </p>
                <p>
                  <Text type="secondary">总问题数：</Text>
                  <Text strong>
                    {selectedQuestionnaireItems.reduce((sum, item) => sum + (item.question_count || 0), 0)}
                  </Text> 题
                </p>
              </div>
            </div>

            {enableEvidence && (
              <div>
                <Text strong>证明材料选择</Text>
                <div style={{ marginTop: 12, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 8 }}>
                  <p>
                    <Text type="secondary">已选择能力项：</Text>
                    <Text strong>{selectedEvidenceItems.length}</Text> 项
                  </p>
                </div>
              </div>
            )}
          </Space>
        </Card>
      </Col>

      <Col span={8}>
        <Card title="项目设置" style={{ borderRadius: 4 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>账号生成设置</Text>
              <div style={{ marginTop: 12 }}>
                <Checkbox
                  checked={autoGenerateAccount}
                  onChange={(e) => setAutoGenerateAccount(e.target.checked)}
                >
                  自动生成登录账号
                </Checkbox>
              </div>

              {!autoGenerateAccount && (
                <div style={{ marginTop: 16 }}>
                  <Input
                    placeholder="自定义用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    style={{ marginBottom: 12 }}
                  />
                  <Input.Password
                    placeholder="自定义密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              )}
            </div>

            <Divider />

            <div>
              <Text strong>将生成的内容</Text>
              <div style={{ marginTop: 12 }}>
                <p>• 项目信息JSON</p>
                <p>• 问卷Excel文件</p>
                {enableEvidence && <p>• 证明材料文件夹</p>}
              </div>
            </div>
          </Space>
        </Card>
      </Col>
    </Row>
  )

  const steps = [
    { title: '基本信息', content: renderStep1() },
    { title: '问卷筛选', content: renderStep2() },
    { title: '证明材料', content: renderStep3() },
    { title: '预览确认', content: renderStep4() },
  ]

  return (
    <div>
      {/* 页面标题 */}
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
              <BarChartOutlined /> 测试指标评估执行流程
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.9)', margin: 0 }}>
              
            </Paragraph>
          </Space>
        </Card>
      </motion.div>

      {/* Steps */}
      <Card bordered={false} style={{ marginBottom: 24, borderRadius: 4 }}>
        <Steps current={currentStep}>
          {steps.map((item) => (
            <Step key={item.title} title={item.title} />
          ))}
        </Steps>
      </Card>

      {/* Content */}
      <div>
        {steps[currentStep].content}
      </div>

      {/* Navigation */}
      <Card bordered={false} style={{ marginTop: 24, borderRadius: 4 }}>
        <Space size="large">
          {currentStep > 0 && (
            <Button size="large" icon={<LeftOutlined />} onClick={handlePrev}>
              上一步
            </Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button type="primary" size="large" onClick={handleNext} icon={<RightOutlined />}>
              下一步
            </Button>
          )}
          {currentStep === steps.length - 1 && (
            <Button
              type="primary"
              size="large"
              icon={<CheckCircleOutlined />}
              onClick={handleSubmit}
              loading={createProjectMutation.isPending}
            >
              确认生成项目
            </Button>
          )}
          <Button size="large" onClick={resetAllSteps}>
            重置
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default FLMMCreate
