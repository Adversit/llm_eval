import { useState } from 'react'
import {
  Card,
  Typography,
  Select,
  Row,
  Col,
  Statistic,
  Space,
  Empty,
  Spin,
  Tag,
  Alert,
} from 'antd'
import {
  BarChartOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
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
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { flmmService } from '../../services/flmmService'

const { Title, Text } = Typography
const { Option } = Select

// 企业级配色
const CHART_COLORS = ['#0052D9', '#00A870', '#FF8800', '#D54941', '#8E44AD', '#16A085']

// 评级颜色
const RATING_COLORS: Record<number, string> = {
  1: '#D54941',
  2: '#FF8800',
  3: '#FADB14',
  4: '#00A870',
  5: '#0052D9',
}

const FLMMAnalysis = () => {
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  // 获取可分析的项目列表
  const { data: projectsData, isLoading: projectsLoading } = useQuery({
    queryKey: ['flmm-analysis-projects'],
    queryFn: () => flmmService.getAnalysisProjects(),
  })

  // 获取项目基本统计
  const { data: statisticsData, isLoading: statisticsLoading } = useQuery({
    queryKey: ['flmm-project-statistics', selectedProject],
    queryFn: () => flmmService.getProjectStatistics(selectedProject!),
    enabled: !!selectedProject,
  })

  // 获取逐题分析
  const { data: questionsData, isLoading: questionsLoading } = useQuery({
    queryKey: ['flmm-project-questions', selectedProject],
    queryFn: () => flmmService.getProjectQuestions(selectedProject!),
    enabled: !!selectedProject,
  })

  // 获取5维度评级
  const { data: ratingsData, isLoading: ratingsLoading } = useQuery({
    queryKey: ['flmm-project-ratings', selectedProject],
    queryFn: () => flmmService.getProjectRatings(selectedProject!),
    enabled: !!selectedProject,
  })

  const statistics = statisticsData?.statistics
  const questions = questionsData?.questions || []
  const ratings = ratingsData?.ratings || {}

  // 准备图表数据
  const prepareChartData = (
    answerDistribution: Record<string, number>,
    optionMapping: Record<string, string>,
    totalResponses: number
  ) => {
    return Object.entries(answerDistribution).map(([key, count]) => ({
      name: optionMapping[key] || key,
      value: count,
      percentage: ((count / totalResponses) * 100).toFixed(1),
    }))
  }

  // 渲染评级卡片
  const renderRatingCard = (name: string, score: number, description: string) => {
    const color = RATING_COLORS[score] || '#999'

    return (
      <Card bordered={false} style={{ borderRadius: 4, height: '100%' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle" align="center">
          <Text strong style={{ fontSize: 16 }}>{name}</Text>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: 48,
              fontWeight: 600,
              color,
              lineHeight: 1,
            }}>
              {score}
            </div>
            <Text type="secondary" style={{ fontSize: 14 }}>/ 5</Text>
          </div>
          <div style={{
            width: '100%',
            height: 8,
            background: '#F0F0F0',
            borderRadius: 4,
            overflow: 'hidden',
          }}>
            <div style={{
              width: `${(score / 5) * 100}%`,
              height: '100%',
              background: color,
              transition: 'width 0.3s',
            }} />
          </div>
          <Text type="secondary" style={{ fontSize: 12, textAlign: 'center' }}>
            {description}
          </Text>
        </Space>
      </Card>
    )
  }

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          测试指标评估分析
        </Title>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          查看评估项目的详细分析、统计数据和五维度评级
        </Text>
      </div>

      {/* 项目选择 */}
      <Card bordered={false} style={{ marginBottom: 24, borderRadius: 4 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>选择评估项目</Text>
          <Select
            placeholder="请选择要分析的评估项目"
            style={{ width: '100%' }}
            value={selectedProject}
            onChange={setSelectedProject}
            size="large"
            loading={projectsLoading}
          >
            {projectsData?.projects?.map((project: any) => (
              <Option key={project.folder_name} value={project.folder_name}>
                {project.display_name || project.folder_name}
              </Option>
            ))}
          </Select>
        </Space>
      </Card>

      {/* 内容区 */}
      {!selectedProject ? (
        <Card bordered={false} style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
          <Empty description="请选择一个评估项目查看分析结果" />
        </Card>
      ) : (
        <>
          {/* 基本统计 */}
          {statisticsLoading ? (
            <Card bordered={false} style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
              <Spin size="large" tip="加载统计数据..." />
            </Card>
          ) : statistics ? (
            <Card
              bordered={false}
              title={<Text strong>基本统计</Text>}
              style={{ marginBottom: 24, borderRadius: 4 }}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ background: '#F0F5FF', borderRadius: 4 }}>
                    <Statistic
                      title="问卷份数"
                      value={statistics.total_responses}
                      prefix={<FileTextOutlined />}
                      valueStyle={{ color: '#0052D9', fontWeight: 600 }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ background: '#F6FFED', borderRadius: 4 }}>
                    <Statistic
                      title="题目总数"
                      value={statistics.total_questions}
                      prefix={<CheckCircleOutlined />}
                      valueStyle={{ color: '#00A870', fontWeight: 600 }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ background: '#FFF7E6', borderRadius: 4 }}>
                    <Statistic
                      title="单选题"
                      value={statistics.single_choice_count}
                      valueStyle={{ color: '#FF8800', fontWeight: 600 }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card bordered={false} style={{ background: '#FFF1F0', borderRadius: 4 }}>
                    <Statistic
                      title="多选题"
                      value={statistics.multiple_choice_count}
                      valueStyle={{ color: '#D54941', fontWeight: 600 }}
                    />
                  </Card>
                </Col>
              </Row>
            </Card>
          ) : null}

          {/* 五维度评级 */}
          {ratingsLoading ? (
            <Card bordered={false} style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0', marginBottom: 24 }}>
              <Spin size="large" tip="计算评级中..." />
            </Card>
          ) : Object.keys(ratings).length > 0 ? (
            <Card
              bordered={false}
              title={
                <Space>
                  <BarChartOutlined />
                  <Text strong>五维度评级分析</Text>
                </Space>
              }
              style={{ marginBottom: 24, borderRadius: 4 }}
            >
              <Alert
                message="评级说明"
                description="基于问卷回答的期望值计算得出，评分范围1-5级，5级为最高"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />
              <Row gutter={[16, 16]}>
                {Object.entries(ratings).map(([key, rating]: [string, any]) => (
                  <Col xs={24} sm={12} lg={8} xl={4.8} key={key}>
                    {renderRatingCard(rating.name, rating.score, rating.description)}
                  </Col>
                ))}
              </Row>
            </Card>
          ) : null}

          {/* 逐题分析 */}
          {questionsLoading ? (
            <Card bordered={false} style={{ borderRadius: 4, textAlign: 'center', padding: '60px 0' }}>
              <Spin size="large" tip="分析问题数据..." />
            </Card>
          ) : questions.length > 0 ? (
            <Card
              bordered={false}
              title={
                <Space>
                  <Text strong>逐题分析</Text>
                  <Tag color="blue">{questions.length} 题</Tag>
                </Space>
              }
              style={{ borderRadius: 4 }}
            >
              <Row gutter={[16, 16]}>
                {questions.map((question: any, index: number) => {
                  const chartData = prepareChartData(
                    question.answer_distribution,
                    question.option_mapping,
                    question.total_responses
                  )

                  return (
                    <Col xs={24} lg={12} key={index}>
                      <Card
                        size="small"
                        title={
                          <Space direction="vertical" size={0} style={{ width: '100%' }}>
                            <Space>
                              <Tag color={question.question_type === '单选题' ? 'blue' : 'orange'}>
                                {question.question_type}
                              </Tag>
                              <Text strong>题 {question.question_num}</Text>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 13 }}>
                              {question.question_text}
                            </Text>
                          </Space>
                        }
                        extra={<Tag>{question.total_responses} 人</Tag>}
                        style={{ marginBottom: 16, borderRadius: 4 }}
                      >
                        {chartData.length > 0 ? (
                          <ResponsiveContainer width="100%" height={280}>
                            {chartData.length <= 5 ? (
                              <PieChart>
                                <Pie
                                  data={chartData}
                                  cx="50%"
                                  cy="50%"
                                  labelLine={false}
                                  label={({ name, percentage }) => `${name}: ${percentage}%`}
                                  outerRadius={80}
                                  fill="#8884d8"
                                  dataKey="value"
                                >
                                  {chartData.map((_, i) => (
                                    <Cell key={`cell-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                  ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                              </PieChart>
                            ) : (
                              <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
                                <XAxis
                                  dataKey="name"
                                  angle={-45}
                                  textAnchor="end"
                                  height={80}
                                  tick={{ fontSize: 11 }}
                                />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="value" fill="#0052D9" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            )}
                          </ResponsiveContainer>
                        ) : (
                          <div style={{ textAlign: 'center', padding: '40px 0' }}>
                            <Text type="secondary">暂无数据</Text>
                          </div>
                        )}
                      </Card>
                    </Col>
                  )
                })}
              </Row>
            </Card>
          ) : null}
        </>
      )}
    </div>
  )
}

export default FLMMAnalysis
