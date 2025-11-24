import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from './components/Layout/Header'
import AppSidebar from './components/Layout/Sidebar'
import AppBreadcrumb from './components/Layout/Breadcrumb'

// 通用页面
import Home from './pages/Home'

// FLMM问卷平台页面
import FLMMCreate from './pages/FLMM/Create'
import FLMMProjects from './pages/FLMM/Projects'
import FLMMAnalysis from './pages/FLMM/Analysis'
import FLMMQuestionnaire from './pages/FLMM/Questionnaire'

// QA模块页面
import QAProcess from './pages/QA/Process'
import QAStatus from './pages/QA/Status'
import QAAnalysis from './pages/QA/Results'

// 双阶段评测系统页面
import EvaluationWorkflow from './pages/Evaluation/Workflow'
import EvaluationAnalysis from './pages/Evaluation/Analysis'

import './App.css'

const { Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Layout>
        <AppSidebar />
        <Layout>
          <Content style={{ margin: '0', padding: '16px 24px', background: '#F5F7FA' }}>
            <AppBreadcrumb />
            <Routes>
              {/* 首页 */}
              <Route path="/" element={<Home />} />

              {/* FLMM问卷平台 */}
              <Route path="/flmm/create" element={<FLMMCreate />} />
              <Route path="/flmm/projects" element={<FLMMProjects />} />
              <Route path="/flmm/analysis" element={<FLMMAnalysis />} />
              {/* 问卷填写页面保留路由但不在菜单显示 */}
              <Route path="/flmm/questionnaire" element={<FLMMQuestionnaire />} />

              {/* QA模块 */}
              <Route path="/qa/process" element={<QAProcess />} />
              <Route path="/qa/status/:taskId/:taskType" element={<QAStatus />} />
              <Route path="/qa/results" element={<QAAnalysis />} />
              <Route path="/qa/analysis" element={<QAAnalysis />} />

              {/* 双阶段评测系统 */}
              <Route path="/eval/workflow" element={<EvaluationWorkflow />} />
              <Route path="/eval/analysis" element={<EvaluationAnalysis />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App
