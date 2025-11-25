import { Card, Row, Col, Typography, Space, Button, Table, Statistic, Tag, Spin, Empty } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useState, useMemo, useEffect } from 'react'
import {
  RobotOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { qaService } from '@/services/qaService'
import { flmmService } from '@/services/flmmService'
import { evaluationService } from '@/services/evaluationService'

const { Title, Text } = Typography

interface Task {
  key: string
  name: string
  type: string
  status: string
  time: string
  module: string
}

const Home = () => {
  const navigate = useNavigate()
  const [showAllTasks, setShowAllTasks] = useState(false)

  // 获取QA任务数据
  const { data: qaTasksData, isLoading: qaLoading, refetch: refetchQA } = useQuery({
    queryKey: ['qaTasksForDashboard'],
    queryFn: qaService.getAllTasks,
    staleTime: 30000,
  })

  // 获取FLMM项目数据
  const { data: flmmProjectsData, isLoading: flmmLoading, refetch: refetchFLMM } = useQuery({
    queryKey: ['flmmProjectsForDashboard'],
    queryFn: flmmService.getAnalysisProjects,
    staleTime: 30000,
  })

  // 获取评估任务数据
  const { data: evalTasksData, isLoading: evalLoading, refetch: refetchEval } = useQuery({
    queryKey: ['evalTasksForDashboard'],
    queryFn: evaluationService.getAllTasks,
    staleTime: 30000,
  })

  const isLoading = qaLoading || flmmLoading || evalLoading

  // 使用 useMemo 优化统计数据和任务列表计算
  const { stats, sortedTasks } = useMemo(() => {
    const statsData = {
      total: 0,
      completed: 0,
      processing: 0,
      failed: 0,
    }

    const allTasks: Task[] = []

    // 处理QA任务
    if (qaTasksData?.tasks) {
      qaTasksData.tasks.forEach((task: any) => {
        statsData.total++
        if (task.status === 'completed') statsData.completed++
        else if (task.status === 'processing') statsData.processing++
        else if (task.status === 'failed') statsData.failed++

        allTasks.push({
          key: `qa-${task.task_id}`,
          name: task.filename || '问答生成任务',
          type: task.task_type === 'generation' ? '问答生成' : '质量评估',
          status: task.status,
          time: task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-',
          module: '数据集生成',
        })
      })
    }

    // 处理FLMM项目
    if (flmmProjectsData?.projects) {
      flmmProjectsData.projects.forEach((project: any) => {
        statsData.total++
        if (project.status === '已完成') statsData.completed++
        else if (project.status === '评估中') statsData.processing++

        allTasks.push({
          key: `flmm-${project.folder_name}`,
          name: `${project.company_name} - ${project.scenario_name}`,
          type: '测试指标评估',
          status: project.status === '已完成' ? 'completed' : project.status === '评估中' ? 'processing' : 'pending',
          time: project.created_time ? new Date(project.created_time).toLocaleString('zh-CN') : '-',
          module: '测试指标',
        })
      })
    }

    // 处理评估任务
    if (evalTasksData?.tasks) {
      evalTasksData.tasks.forEach((task: any) => {
        statsData.total++
        if (task.status === 'completed') statsData.completed++
        else if (task.status === 'processing') statsData.processing++
        else if (task.status === 'failed') statsData.failed++

        allTasks.push({
          key: `eval-${task.task_id}`,
          name: `${task.llm_name} 评估`,
          type: task.evaluation_type === 'stage1' ? '第一阶段' : task.evaluation_type === 'stage2' ? '第二阶段' : '双阶段',
          status: task.status,
          time: task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-',
          module: '智能评估',
        })
      })
    }

    // 按时间倒序排序,修复 Invalid Date 问题
    const sorted = allTasks.sort((a, b) => {
      // 处理 '-' 的情况,将其视为最旧的时间
      if (a.time === '-' && b.time === '-') return 0
      if (a.time === '-') return 1
      if (b.time === '-') return -1

      const timeA = new Date(a.time).getTime()
      const timeB = new Date(b.time).getTime()

      // 处理 Invalid Date 的情况
      if (isNaN(timeA) && isNaN(timeB)) return 0
      if (isNaN(timeA)) return 1
      if (isNaN(timeB)) return -1

      return timeB - timeA
    })

    return { stats: statsData, sortedTasks: sorted }
  }, [qaTasksData, flmmProjectsData, evalTasksData])

  // 根据展开状态决定显示多少条
  const displayTasks = showAllTasks ? sortedTasks : sortedTasks.slice(0, 12)

  // 当有进行中的任务时,启动自动刷新
  useEffect(() => {
    if (stats.processing > 0) {
      const interval = setInterval(() => {
        refetchQA()
        refetchFLMM()
        refetchEval()
      }, 5000) // 每5秒刷新一次

      return () => clearInterval(interval)
    }
  }, [stats.processing, refetchQA, refetchFLMM, refetchEval])

  // 表格列定义
  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: '32%',
    },
    {
      title: '所属模块',
      dataIndex: 'module',
      key: 'module',
      width: '13%',
      render: (module: string) => {
        const colorMap: Record<string, string> = {
          '数据集生成': 'blue',
          '测试指标': 'orange',
          '智能评估': 'green',
        }
        return <Tag color={colorMap[module]} style={{ fontSize: 12 }}>{module}</Tag>
      },
    },
    {
      title: '任务类型',
      dataIndex: 'type',
      key: 'type',
      width: '15%',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '12%',
      render: (status: string) => {
        const config: Record<string, any> = {
          completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
          processing: { color: 'processing', icon: <SyncOutlined spin />, text: '进行中' },
          failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
          pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待处理' },
        }
        const cfg = config[status] || { color: 'default', icon: null, text: status }
        return (
          <Tag color={cfg.color} icon={cfg.icon} style={{ fontSize: 12 }}>
            {cfg.text}
          </Tag>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'time',
      key: 'time',
      width: '18%',
    },
  ]

  // 快速操作按钮
  const quickActions = [
    {
      title: '生成数据集',
      icon: <DatabaseOutlined />,
      path: '/qa/process',
      description: '从文档生成问答对',
      color: '#0052D9',
    },
    {
      title: '创建测试指标',
      icon: <BarChartOutlined />,
      path: '/flmm/create',
      description: '创建评估项目',
      color: '#00A870',
    },
    {
      title: '开始智能评估',
      icon: <RobotOutlined />,
      path: '/eval/workflow',
      description: '启动模型评估',
      color: '#FF8800',
    },
  ]

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column',
      gap: '12px'
    }}>
      {/* 快速操作 */}
      <div>
        <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
          快速操作
        </Text>
        <Row gutter={12}>
          {quickActions.map((action, index) => (
            <Col xs={24} sm={12} lg={8} key={index}>
              <Card
                bordered={false}
                hoverable
                style={{ borderRadius: 4, cursor: 'pointer' }}
                styles={{ body: { padding: '10px' } }}
                onClick={() => navigate(action.path)}
              >
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 4,
                      background: `${action.color}15`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 14,
                      color: action.color,
                    }}
                  >
                    {action.icon}
                  </div>
                  <Title level={5} style={{ margin: '4px 0 2px 0', fontSize: 12 }}>
                    {action.title}
                  </Title>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {action.description}
                  </Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      {/* 统计卡片 */}
      <Row gutter={12}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '10px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 11 }}>总任务数</Text>}
              value={stats.total}
              valueStyle={{ color: '#252B3A', fontSize: 18, fontWeight: 600 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '10px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 11 }}>已完成</Text>}
              value={stats.completed}
              valueStyle={{ color: '#00A870', fontSize: 18, fontWeight: 600 }}
              prefix={<CheckCircleOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '10px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 11 }}>进行中</Text>}
              value={stats.processing}
              valueStyle={{ color: '#0052D9', fontSize: 18, fontWeight: 600 }}
              prefix={<SyncOutlined spin={stats.processing > 0} style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} style={{ borderRadius: 4 }} styles={{ body: { padding: '10px' } }}>
            <Statistic
              title={<Text type="secondary" style={{ fontSize: 11 }}>失败</Text>}
              value={stats.failed}
              valueStyle={{ color: '#D54941', fontSize: 18, fontWeight: 600 }}
              prefix={<CloseCircleOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 最近任务 */}
      <Card
        bordered={false}
        style={{ borderRadius: 4 }}
        styles={{ body: { padding: '10px' } }}
        title={
          <Space>
            <Text strong style={{ fontSize: 13 }}>最近任务</Text>
          </Space>
        }
        extra={
          sortedTasks.length > 12 && (
            <Button
              type="link"
              size="small"
              icon={<ArrowRightOutlined />}
              onClick={() => setShowAllTasks(!showAllTasks)}
              style={{ fontSize: 12 }}
            >
              {showAllTasks ? '收起' : `查看全部 (${sortedTasks.length})`}
            </Button>
          )
        }
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <Spin />
          </div>
        ) : displayTasks.length > 0 ? (
          <Table
            columns={columns}
            dataSource={displayTasks}
            pagination={false}
            size="small"
          />
        ) : (
          <Empty description="暂无任务记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  )
}

export default Home
