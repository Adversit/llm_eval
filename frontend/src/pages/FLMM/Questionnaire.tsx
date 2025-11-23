import { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Form,
  Radio,
  Checkbox,
  Button,
  Space,
  Alert,
  Modal,
  Input,
  Spin,
  Progress,
  Divider,
  Tag,
  message,
} from 'antd'
import {
  FormOutlined,
  CheckCircleOutlined,
  LockOutlined,
  UserOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'

const { Title, Paragraph, Text } = Typography

interface Answer {
  question: string
  answer: string | string[]
  options: string[]
  capability_item: string
  domain: string
  question_number: number
  is_multiple_choice: boolean
}

const FLMMQuestionnaire = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [sessionUsername, setSessionUsername] = useState('')
  const [projectInfo] = useState<any>(null)
  const [questionnaireData] = useState<any[]>([])
  const [answers, setAnswers] = useState<Record<string, Answer>>({})
  const [submitted, setSubmitted] = useState(false)
  const [questionnaireId] = useState(`q_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  // 登录验证
  const handleLogin = () => {
    // TODO: 实现实际的登录验证
    // 这里需要调用后端API验证用户名和密码
    if (username && password) {
      setIsLoggedIn(true)
      setSessionUsername(username)
      message.success('登录成功！')
    } else {
      message.error('请输入用户名和密码')
    }
  }

  // 加载问卷数据
  useEffect(() => {
    if (isLoggedIn) {
      // TODO: 从后端加载问卷数据和项目信息
      // 这里需要根据用户名获取对应的问卷
      // loadQuestionnaireData()
    }
  }, [isLoggedIn])

  // 处理答案变更
  const handleAnswerChange = (
    questionKey: string,
    value: string | string[],
    questionData: any
  ) => {
    setAnswers({
      ...answers,
      [questionKey]: {
        question: questionData.question,
        answer: value,
        options: questionData.options,
        capability_item: questionData.capability_item,
        domain: questionData.domain,
        question_number: questionData.question_number,
        is_multiple_choice: questionData.is_multiple_choice,
      },
    })
  }

  // 提交问卷
  const handleSubmit = async () => {
    // 验证所有问题是否都已回答
    const totalQuestions = questionnaireData.length
    const answeredQuestions = Object.keys(answers).length

    if (answeredQuestions < totalQuestions) {
      message.warning(`请回答所有问题！已回答 ${answeredQuestions}/${totalQuestions} 题`)
      return
    }

    try {
      // TODO: 调用后端API提交答案
      // await flmmService.submitResponse({
      //   questionnaire_id: questionnaireId,
      //   username: sessionUsername,
      //   answers: answers,
      //   submitted_time: new Date().toISOString()
      // })

      setSubmitted(true)
      Modal.success({
        title: '问卷提交成功！',
        content: (
          <div>
            <p>您的问卷ID: <Text copyable>{questionnaireId}</Text></p>
            <p>提交时间: {new Date().toLocaleString()}</p>
            <p>感谢您的参与！</p>
          </div>
        ),
      })
    } catch (error) {
      message.error('提交失败，请重试')
    }
  }

  // 渲染登录页面
  if (!isLoggedIn) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card
            style={{
              width: 450,
              borderRadius: 4,
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            }}
          >
            <div style={{ textAlign: 'center', marginBottom: 32 }}>
              <SafetyOutlined style={{ fontSize: 48, color: '#667eea' }} />
              <Title level={2} style={{ marginTop: 16 }}>
                FLMM问卷填写系统
              </Title>
              <Paragraph type="secondary">
                请使用提供的账号密码登录
              </Paragraph>
            </div>

            <Form layout="vertical" onFinish={handleLogin}>
              <Form.Item label="用户名" required>
                <Input
                  size="large"
                  prefix={<UserOutlined />}
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </Form.Item>

              <Form.Item label="密码" required>
                <Input.Password
                  size="large"
                  prefix={<LockOutlined />}
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  block
                  style={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                  }}
                >
                  登录
                </Button>
              </Form.Item>
            </Form>

            <Alert
              message="提示"
              description="请使用管理员提供的用户名和密码登录系统。如有问题，请联系系统管理员。"
              type="info"
              showIcon
            />
          </Card>
        </motion.div>
      </div>
    )
  }

  // 渲染提交成功页面
  if (submitted) {
    return (
      <div style={{ minHeight: '100vh', padding: 40 }}>
        <Card
          style={{
            maxWidth: 800,
            margin: '0 auto',
            textAlign: 'center',
            borderRadius: 4,
          }}
        >
          <div style={{ padding: '60px 40px' }}>
            <CheckCircleOutlined
              style={{ fontSize: 80, color: '#52c41a', marginBottom: 24 }}
            />
            <Title level={2}>问卷提交成功！</Title>
            <Paragraph>
              您的问卷ID: <Text code copyable>{questionnaireId}</Text>
            </Paragraph>
            <Paragraph type="secondary">
              感谢您的参与！您的反馈对我们非常重要。
            </Paragraph>
            <Divider />
            <Space>
              <Button
                type="primary"
                onClick={() => {
                  setSubmitted(false)
                  setAnswers({})
                }}
              >
                重新填写
              </Button>
              <Button onClick={() => setIsLoggedIn(false)}>退出登录</Button>
            </Space>
          </div>
        </Card>
      </div>
    )
  }

  // 渲染问卷填写页面
  return (
    <div style={{ minHeight: '100vh', padding: 24, background: '#f5f5f5' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24, borderRadius: 4 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={2} style={{ margin: 0 }}>
                <FormOutlined /> FLMM能力评估问卷
              </Title>
              {projectInfo && (
                <Paragraph type="secondary" style={{ margin: '8px 0 0 0' }}>
                  企业: {projectInfo.company_name} | 场景: {projectInfo.scenario_name}
                </Paragraph>
              )}
            </div>
            <div style={{ textAlign: 'right' }}>
              <Text type="secondary">登录用户: {sessionUsername}</Text>
              <br />
              <Button size="small" type="link" onClick={() => setIsLoggedIn(false)}>
                退出登录
              </Button>
            </div>
          </div>

          <Alert
            message="填写说明"
            description="请根据实际使用情况如实填写本问卷。所有问题均为必答题，请确保完整回答所有问题后再提交。"
            type="info"
            showIcon
          />

          <Progress
            percent={Math.round((Object.keys(answers).length / questionnaireData.length) * 100)}
            status="active"
            format={(percent) =>
              `已完成 ${Object.keys(answers).length}/${questionnaireData.length} 题 (${percent}%)`
            }
          />
        </Space>
      </Card>

      {/* 问卷内容 */}
      {questionnaireData.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 60, borderRadius: 4 }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>加载问卷数据中...</Paragraph>
        </Card>
      ) : (
        <>
          {/* 按能力项分组显示问题 */}
          {Object.entries(
            questionnaireData.reduce((groups: any, q: any) => {
              const key = q.capability_item
              if (!groups[key]) groups[key] = []
              groups[key].push(q)
              return groups
            }, {})
          ).map(([capabilityItem, questions]: [string, any]) => (
            <Card
              key={capabilityItem}
              title={
                <Space>
                  <Tag color="blue">能力项</Tag>
                  <Text strong>{capabilityItem}</Text>
                </Space>
              }
              style={{ marginBottom: 16, borderRadius: 4 }}
            >
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                {questions.map((q: any, index: number) => {
                  const questionKey = `${capabilityItem}_${index}`
                  return (
                    <div key={questionKey}>
                      <Title level={5}>
                        第 {q.question_number} 题{' '}
                        {q.is_multiple_choice && <Tag color="orange">多选题</Tag>}
                      </Title>
                      <Paragraph>{q.question}</Paragraph>

                      {q.is_multiple_choice ? (
                        <Checkbox.Group
                          style={{ display: 'flex', flexDirection: 'column' }}
                          value={answers[questionKey]?.answer as string[]}
                          onChange={(checkedValues) =>
                            handleAnswerChange(questionKey, checkedValues, q)
                          }
                        >
                          <Space direction="vertical">
                            {q.options.map((option: string, optIndex: number) => (
                              <Checkbox key={optIndex} value={option}>
                                {option}
                              </Checkbox>
                            ))}
                          </Space>
                        </Checkbox.Group>
                      ) : (
                        <Radio.Group
                          style={{ display: 'flex', flexDirection: 'column' }}
                          value={answers[questionKey]?.answer as string}
                          onChange={(e) =>
                            handleAnswerChange(questionKey, e.target.value, q)
                          }
                        >
                          <Space direction="vertical">
                            {q.options.map((option: string, optIndex: number) => (
                              <Radio key={optIndex} value={option}>
                                {option}
                              </Radio>
                            ))}
                          </Space>
                        </Radio.Group>
                      )}

                      {index < questions.length - 1 && <Divider />}
                    </div>
                  )
                })}
              </Space>
            </Card>
          ))}

          {/* 提交按钮 */}
          <Card style={{ borderRadius: 4 }}>
            <div style={{ textAlign: 'center', padding: 20 }}>
              <Button
                type="primary"
                size="large"
                icon={<CheckCircleOutlined />}
                onClick={handleSubmit}
                disabled={Object.keys(answers).length < questionnaireData.length}
                style={{
                  background:
                    Object.keys(answers).length < questionnaireData.length
                      ? undefined
                      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  minWidth: 200,
                }}
              >
                提交问卷
              </Button>
              <Paragraph type="secondary" style={{ marginTop: 16 }}>
                {Object.keys(answers).length < questionnaireData.length
                  ? `还有 ${questionnaireData.length - Object.keys(answers).length} 题未回答`
                  : '所有问题已回答，可以提交了'}
              </Paragraph>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

export default FLMMQuestionnaire
