import { Breadcrumb } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import { useLocation, Link } from 'react-router-dom'

const AppBreadcrumb = () => {
  const location = useLocation()

  // 路由映射表
  const routeMap: Record<string, { parent?: string; title: string }> = {
    '/': { title: '工作台' },
    '/qa/process': { parent: '数据集生成系统', title: '执行流程' },
    '/qa/analysis': { parent: '数据集生成系统', title: '结果分析' },
    '/flmm/create': { parent: '测试指标获取及分析模块', title: '执行流程' },
    '/flmm/projects': { parent: '测试指标获取及分析模块', title: '项目管理' },
    '/flmm/analysis': { parent: '测试指标获取及分析模块', title: '结果分析' },
    '/flmm/questionnaire': { parent: '测试指标获取及分析模块', title: '问卷填写' },
    '/eval/workflow': { parent: '智能评估与报告生成系统', title: '执行流程' },
    '/eval/analysis': { parent: '智能评估与报告生成系统', title: '结果分析' },
  }

  const currentRoute = routeMap[location.pathname]

  // 如果在首页，不显示面包屑
  if (location.pathname === '/') {
    return null
  }

  const breadcrumbItems = [
    {
      title: (
        <Link to="/">
          <HomeOutlined />
        </Link>
      ),
    },
  ]

  if (currentRoute) {
    if (currentRoute.parent) {
      breadcrumbItems.push({
        title: currentRoute.parent,
      })
    }
    breadcrumbItems.push({
      title: currentRoute.title,
    })
  }

  return (
    <div style={{ padding: '12px 0', background: 'transparent' }}>
      <Breadcrumb items={breadcrumbItems} />
    </div>
  )
}

export default AppBreadcrumb
