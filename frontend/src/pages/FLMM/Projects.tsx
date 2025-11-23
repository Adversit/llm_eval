import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Descriptions,
  Spin,
} from 'antd'
import {
  EyeOutlined,
  CopyOutlined,
  LinkOutlined,
  FolderOpenOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const { Title, Text, Paragraph } = Typography

interface Project {
  folder_name: string
  project_id: string
  company_name: string
  scenario_name: string
  created_time: string
  status: string
  questionnaire_enabled: boolean
  evidence_enabled: boolean
  has_questionnaire_file?: boolean
  has_evidence_file?: boolean
}

interface ProjectDetails {
  evaluation_info: {
    project_id: string
    company_name: string
    scenario_name: string
    scenario_description: string
    functions_list: { name: string; description: string }[]
    created_time: string
    status: string
    questionnaire_enabled: boolean
    evidence_enabled: boolean
  }
  account_info: {
    username: string
    password: string
    company_name: string
    scenario_name: string
    created_time: string
    login_url?: string
    status: string
  }
}

const FLMMProjects = () => {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [detailsVisible, setDetailsVisible] = useState(false)
  const [projectDetails, setProjectDetails] = useState<ProjectDetails | null>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)

  // 获取项目列表
  const { data: projectsData, isLoading, refetch } = useQuery({
    queryKey: ['flmm-projects'],
    queryFn: async () => {
      const response = await axios.get('http://localhost:8000/api/flmm/projects')
      return response.data
    },
  })

  // 查看项目详情
  const viewProjectDetails = async (project: Project) => {
    setSelectedProject(project)
    setDetailsVisible(true)
    setLoadingDetails(true)

    try {
      // 读取项目JSON文件获取账号密码
      const response = await axios.get(
        `http://localhost:8000/api/flmm/project/${project.folder_name}/details`
      )
      setProjectDetails(response.data)
    } catch (error: any) {
      // 如果后端没有这个接口,使用本地读取
      message.error('获取项目详情失败')
    } finally {
      setLoadingDetails(false)
    }
  }

  // 启动问卷
  const launchQuestionnaire = async (project: Project) => {
    const loadingMsg = message.loading('正在启动问卷服务...', 0)

    try {
      // 调用按需启动API
      const response = await axios.post(
        `http://localhost:8000/api/flmm/project/${project.folder_name}/launch-questionnaire`
      )

      loadingMsg()

      if (response.data.success && response.data.url) {
        // 打开Streamlit链接
        window.open(response.data.url, '_blank')
        message.success(response.data.message || '问卷页面已在新标签页打开')
      } else {
        message.error('启动失败')
      }
    } catch (error: any) {
      loadingMsg()
      const errorMsg = error.response?.data?.detail || '启动问卷失败'
      message.error(errorMsg)
    }
  }

  // 启动证明材料
  const launchEvidence = async (project: Project) => {
    const loadingMsg = message.loading('正在启动证明材料服务...', 0)

    try {
      // 调用按需启动API
      const response = await axios.post(
        `http://localhost:8000/api/flmm/project/${project.folder_name}/launch-evidence`
      )

      loadingMsg()

      if (response.data.success && response.data.url) {
        // 打开Streamlit链接
        window.open(response.data.url, '_blank')
        message.success(response.data.message || '证明材料页面已在新标签页打开')
      } else {
        message.error('启动失败')
      }
    } catch (error: any) {
      loadingMsg()
      const errorMsg = error.response?.data?.detail || '启动证明材料失败'
      message.error(errorMsg)
    }
  }

  // 复制到剪贴板
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    message.success(`${label}已复制到剪贴板`)
  }

  const columns = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 150,
    },
    {
      title: '场景名称',
      dataIndex: 'scenario_name',
      key: 'scenario_name',
      width: 150,
    },
    {
      title: '项目ID',
      dataIndex: 'project_id',
      key: 'project_id',
      width: 120,
      render: (text: string) => (
        <Text code copyable>
          {text}
        </Text>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      key: 'created_time',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString('zh-CN'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          待评估: 'blue',
          评估中: 'processing',
          已完成: 'success',
        }
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
      },
    },
    {
      title: '功能模块',
      key: 'modules',
      width: 150,
      render: (_: any, record: Project) => (
        <Space>
          {record.questionnaire_enabled && <Tag color="green">问卷</Tag>}
          {record.evidence_enabled && <Tag color="blue">证明材料</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      fixed: 'right' as const,
      render: (_: any, record: Project) => (
        <Space size="small" wrap>
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => viewProjectDetails(record)}
            style={{ minWidth: 90 }}
          >
            查看详情
          </Button>
          {record.questionnaire_enabled && (
            <Button
              type="default"
              size="small"
              icon={<LinkOutlined />}
              onClick={() => launchQuestionnaire(record)}
              disabled={!record.has_questionnaire_file}
              title={!record.has_questionnaire_file ? '该项目缺少问卷文件，请重新创建项目' : '启动问卷服务'}
              style={{ minWidth: 90 }}
            >
              启动问卷
            </Button>
          )}
          {record.evidence_enabled && (
            <Button
              type="default"
              size="small"
              icon={<UploadOutlined />}
              onClick={() => launchEvidence(record)}
              disabled={!record.has_evidence_file}
              title={!record.has_evidence_file ? '该项目缺少证明材料文件，请重新创建项目' : '启动证明材料上传服务'}
              style={{ minWidth: 110 }}
            >
              启动证明材料
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title={
          <Space>
            <FolderOpenOutlined />
            <span>FLMM 项目管理</span>
          </Space>
        }
        extra={
          <Button onClick={() => refetch()}>刷新</Button>
        }
      >
        <Paragraph>
          查看所有已创建的FLMM评估项目，获取登录账号和访问链接。
        </Paragraph>

        <Table
          columns={columns}
          dataSource={projectsData?.projects || []}
          rowKey="folder_name"
          loading={isLoading}
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 个项目`,
          }}
        />
      </Card>

      {/* 项目详情弹窗 */}
      <Modal
        title={
          <Space>
            <EyeOutlined />
            项目详情 - {selectedProject?.company_name} / {selectedProject?.scenario_name}
          </Space>
        }
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {loadingDetails ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
          </div>
        ) : projectDetails ? (
          <div>
            {/* 登录信息 */}
            <Card
              title="登录信息"
              size="small"
              style={{ marginBottom: 16 }}
              extra={
                <Tag color={projectDetails.account_info.status === '激活' ? 'success' : 'default'}>
                  {projectDetails.account_info.status}
                </Tag>
              }
            >
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="用户名">
                  <Space>
                    <Text code>{projectDetails.account_info.username}</Text>
                    <Button
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() =>
                        copyToClipboard(projectDetails.account_info.username, '用户名')
                      }
                    >
                      复制
                    </Button>
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="密码">
                  <Space>
                    <Text code>{projectDetails.account_info.password}</Text>
                    <Button
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() =>
                        copyToClipboard(projectDetails.account_info.password, '密码')
                      }
                    >
                      复制
                    </Button>
                  </Space>
                </Descriptions.Item>
                {projectDetails.account_info.login_url &&
                  projectDetails.account_info.login_url !== '待部署' && (
                    <Descriptions.Item label="访问链接">
                      <Space>
                        <Text code>{projectDetails.account_info.login_url}</Text>
                        <Button
                          size="small"
                          type="primary"
                          icon={<LinkOutlined />}
                          onClick={() =>
                            window.open(projectDetails.account_info.login_url, '_blank')
                          }
                        >
                          打开链接
                        </Button>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={() =>
                            copyToClipboard(
                              projectDetails.account_info.login_url!,
                              '访问链接'
                            )
                          }
                        >
                          复制
                        </Button>
                      </Space>
                    </Descriptions.Item>
                  )}
              </Descriptions>
            </Card>

            {/* 项目信息 */}
            <Card title="项目信息" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="项目ID">
                  {projectDetails.evaluation_info.project_id}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color="blue">{projectDetails.evaluation_info.status}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="公司名称" span={2}>
                  {projectDetails.evaluation_info.company_name}
                </Descriptions.Item>
                <Descriptions.Item label="场景名称" span={2}>
                  {projectDetails.evaluation_info.scenario_name}
                </Descriptions.Item>
                <Descriptions.Item label="场景描述" span={2}>
                  {projectDetails.evaluation_info.scenario_description}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间" span={2}>
                  {new Date(projectDetails.evaluation_info.created_time).toLocaleString(
                    'zh-CN'
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="启用模块" span={2}>
                  <Space>
                    {projectDetails.evaluation_info.questionnaire_enabled && (
                      <Tag color="green">问卷收集</Tag>
                    )}
                    {projectDetails.evaluation_info.evidence_enabled && (
                      <Tag color="blue">证明材料</Tag>
                    )}
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 功能模块 */}
            {projectDetails.evaluation_info.functions_list &&
              projectDetails.evaluation_info.functions_list.length > 0 && (
                <Card title="功能模块" size="small">
                  {projectDetails.evaluation_info.functions_list.map((func, index) => (
                    <Card.Grid key={index} style={{ width: '50%' }}>
                      <Text strong>{func.name}</Text>
                      <br />
                      <Text type="secondary">{func.description}</Text>
                    </Card.Grid>
                  ))}
                </Card>
              )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text type="secondary">暂无详细信息</Text>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default FLMMProjects
