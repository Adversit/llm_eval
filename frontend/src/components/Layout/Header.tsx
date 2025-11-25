import { Layout, Avatar, Dropdown, Space, Menu } from 'antd'
import { UserOutlined, SettingOutlined, LogoutOutlined, HomeOutlined, DatabaseOutlined, BarChartOutlined, RobotOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import type { MenuProps } from 'antd'

const { Header } = Layout

const AppHeader = () => {
  const navigate = useNavigate()
  const location = useLocation()

  // 用户下拉菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  // 顶部主导航菜单项
  const topNavItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: 'qa-module',
      icon: <DatabaseOutlined />,
      label: '数据集生成系统',
    },
    {
      key: 'flmm',
      icon: <BarChartOutlined />,
      label: '测试指标获取及分析模块',
    },
    {
      key: 'llm-eval',
      icon: <RobotOutlined />,
      label: '智能评估与报告生成系统',
    },
  ]

  // 根据当前路径确定选中的顶部菜单
  const getSelectedKey = () => {
    const path = location.pathname
    if (path === '/') return '/'
    if (path.startsWith('/qa')) return 'qa-module'
    if (path.startsWith('/flmm')) return 'flmm'
    if (path.startsWith('/eval')) return 'llm-eval'
    return '/'
  }

  // 顶部菜单点击事件
  const handleTopMenuClick: MenuProps['onClick'] = (e) => {
    if (e.key === '/') {
      navigate('/')
    } else if (e.key === 'qa-module') {
      navigate('/qa/process')
    } else if (e.key === 'flmm') {
      navigate('/flmm/create')
    } else if (e.key === 'llm-eval') {
      navigate('/eval/workflow')
    }
  }

  return (
    <Header
      style={{
        background: '#FFFFFF',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
        borderBottom: '1px solid #E5E6EB',
        height: 56,
        lineHeight: '56px',
      }}
    >
      {/* 左侧：Logo + 顶部导航 */}
      <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
        <div
          style={{
            fontSize: '18px',
            fontWeight: 600,
            color: '#252B3A',
            marginRight: 40,
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          面向金融典型应用场景的大模型测试数据集与智能化测试平台
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[getSelectedKey()]}
          items={topNavItems}
          onClick={handleTopMenuClick}
          style={{
            flex: 1,
            border: 'none',
            background: 'transparent',
            lineHeight: '54px',
          }}
        />
      </div>

      {/* 右侧：用户信息 */}
      <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
        <Space style={{ cursor: 'pointer' }}>
          <Avatar
            size="small"
            style={{ backgroundColor: '#0052D9' }}
            icon={<UserOutlined />}
          />
          <span style={{ color: '#252B3A', fontSize: 14 }}>管理员</span>
        </Space>
      </Dropdown>
    </Header>
  )
}

export default AppHeader
