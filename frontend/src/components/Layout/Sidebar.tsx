import { useState } from 'react'
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  FundProjectionScreenOutlined,
  BarChartOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'

const { Sider } = Layout

type MenuItem = Required<MenuProps>['items'][number]

const AppSidebar = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // 根据当前路径确定应该显示哪个子菜单
  const getCurrentModule = () => {
    const path = location.pathname
    if (path.startsWith('/qa')) return 'qa-module'
    if (path.startsWith('/flmm')) return 'flmm'
    if (path.startsWith('/eval')) return 'llm-eval'
    return null
  }

  const currentModule = getCurrentModule()

  // 动态菜单配置
  const menuConfigs: Record<string, MenuItem[]> = {
    'qa-module': [
      {
        key: '/qa/process',
        icon: <FundProjectionScreenOutlined />,
        label: '执行流程',
      },
      {
        key: '/qa/analysis',
        icon: <BarChartOutlined />,
        label: '结果分析',
      },
    ],
    'flmm': [
      {
        key: '/flmm/create',
        icon: <FundProjectionScreenOutlined />,
        label: '执行流程',
      },
      {
        key: '/flmm/projects',
        icon: <FolderOutlined />,
        label: '项目管理',
      },
      {
        key: '/flmm/analysis',
        icon: <BarChartOutlined />,
        label: '结果分析',
      },
    ],
    'llm-eval': [
      {
        key: '/eval/workflow',
        icon: <FundProjectionScreenOutlined />,
        label: '执行流程',
      },
      {
        key: '/eval/analysis',
        icon: <BarChartOutlined />,
        label: '结果分析',
      },
    ],
  }

  // 获取当前模块的菜单项
  const currentMenuItems = currentModule ? menuConfigs[currentModule] : []

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    navigate(e.key)
  }

  // 如果在首页，不显示侧边栏
  if (!currentModule) {
    return null
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={(value) => setCollapsed(value)}
      width={220}
      style={{
        background: '#FFFFFF',
        borderRight: '1px solid #E5E6EB',
      }}
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={currentMenuItems}
        onClick={handleMenuClick}
        style={{
          border: 'none',
          height: '100%',
          paddingTop: 16,
        }}
      />
    </Sider>
  )
}

export default AppSidebar
