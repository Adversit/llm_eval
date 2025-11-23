# LLM 评估平台

一个基于 **React + FastAPI** 的专业大语言模型评估平台，提供统一的用户界面和现代化的交互体验。

## 项目概述

本平台集成了三大核心评估模块，采用前后端分离架构，提供完整的 LLM 评估解决方案：

1. **QA问答管理模块** - 智能问答对生成和质量评估
2. **LLM_EVAL双阶段评测系统** - 两阶段专业评估流程
3. **FLMM问卷平台** - 问卷创建和数据分析

---

## 技术栈

### 后端
- **FastAPI 0.109** - 高性能异步Web框架
- **Python 3.8+** - 编程语言
- **Uvicorn** - ASGI服务器
- **Pydantic 2.5** - 数据验证
- **Pandas** - 数据处理
- **OpenPyXL** - Excel文件处理

### 前端
- **React 18.2** + **TypeScript 5.2** - UI框架
- **Vite 5.0** - 现代化构建工具
- **Ant Design 5.12** - 企业级UI组件库
- **TanStack Query 5.14** - 强大的数据管理
- **Recharts 2.10** - 数据可视化
- **Framer Motion 10.16** - 流畅动画效果
- **Axios** - HTTP客户端

---

## 快速开始

### 环境要求

- **Python 3.8+**
- **Node.js 16+**
- **Conda** (推荐)

### 安装步骤

#### 1. 克隆项目

```bash
cd D:\work\project\LLM_eval
```

#### 2. 后端安装

```bash
# 激活conda环境
conda activate damoxingeval

# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt
```

#### 3. 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

#### 4. 环境配置

确保 `LLM_EVAL/config/.env` 文件存在并配置了API密钥：

```env
SILICONFLOW_API_KEY=your_api_key_here
```

### 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
# Windows
start.bat
```

启动脚本会自动：
- 设置正确的虚拟环境
- 启动后端服务（端口 8000）
- 启动前端服务（端口 5173）

#### 方式二：手动启动

**启动后端：**
```bash
conda activate damoxingeval
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端：**
```bash
cd frontend
npm run dev
```

### 访问应用

- **前端页面**: http://localhost:5173
- **后端API文档**: http://localhost:8000/api/docs
- **ReDoc文档**: http://localhost:8000/api/redoc

---

## 功能模块

### 1. QA问答管理模块 📄

批量文档解析、智能问答对生成与质量评估。

**核心功能**:
- Word/Excel文档批量处理
- 基于大模型的智能问答对生成
- 答案质量自动评估
- Excel结果导出

**页面**:
- `/qa/generate` - 问答对生成
- `/qa/evaluate` - 质量评估
- `/qa/results` - 结果分析

---

### 2. LLM_EVAL双阶段评测系统 ⚖️

专业的两阶段评估流程，支持多文件批量处理和可视化分析。

**核心功能**:
- 双阶段评估流程（第一阶段答题 + 第二阶段评分）
- 多文件批量上传
- 实时进度监控
- 评估结果可视化
- HTML/Excel报告生成

**页面**:
- `/eval/info` - 信息填写
- `/eval/upload` - 文件上传
- `/eval/process` - 评估进程
- `/eval/analysis` - 结果分析

**工作流程**:
1. **信息填写** - 配置测试模型和评估模型参数
2. **文件上传** - 上传评估数据文件
3. **评估过程** - 执行双阶段自动评测
4. **结果分析** - 查看详细报告和图表

---

### 3. FLMM问卷平台 📋

专业的问卷设计、分发与数据分析工具。

**核心功能**:
- 问卷创建与管理
- 多种题型支持（单选、多选、文本、评分）
- 问卷回答收集
- 数据统计分析
- 可视化报表

**页面**:
- `/flmm/create` - 问卷创建
- `/flmm/analysis` - 结果分析

---

## 项目结构

```
LLM_eval/
├── backend/                 # FastAPI后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── api/            # API路由
│   │   │   ├── qa.py       # QA模块API
│   │   │   ├── evaluation.py  # 评估API
│   │   │   ├── upload.py   # 文件上传API
│   │   │   └── flmm.py     # FLMM API
│   │   └── models/         # Pydantic数据模型
│   └── requirements.txt    # Python依赖
│
├── frontend/               # React前端
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   │   ├── QA/        # QA模块（3个页面）
│   │   │   ├── Evaluation/  # 评估模块（4个页面）
│   │   │   ├── FLMM/      # FLMM模块（2个页面）
│   │   │   └── Home.tsx   # 首页
│   │   ├── components/    # 公共组件
│   │   ├── services/      # API服务层
│   │   └── App.tsx        # 应用主组件
│   ├── package.json       # Node依赖
│   └── vite.config.ts     # Vite配置
│
├── QA/                    # QA原始模块
│   ├── config.py          # QA配置
│   ├── get_qa.py          # 问答生成
│   └── evaluate_qa.py     # 质量评估
│
├── LLM_EVAL/              # 评估原始模块
│   ├── config/            # 配置文件
│   ├── first_stage/       # 第一阶段评估
│   ├── second_stage/      # 第二阶段评估
│   └── visiualization/    # 可视化界面
│
├── start.bat              # Windows启动脚本
└── CLAUDE.md             # 系统配置说明
```

---

## API端点

### QA模块 (`/api/qa`)
- `POST /api/qa/generate` - 生成问答对
- `POST /api/qa/evaluate` - 评估问答质量
- `GET /api/qa/task/{task_id}` - 查询任务状态
- `GET /api/qa/download/{task_id}` - 下载结果
- `GET /api/qa/stats` - 获取统计信息

### 评估系统 (`/api/eval`)
- `POST /api/eval/upload` - 上传评估文件
- `POST /api/eval/create` - 创建评估任务
- `GET /api/eval/task/{task_id}` - 查询任务状态
- `GET /api/eval/results/{task_id}` - 获取评估结果
- `GET /api/eval/stats` - 获取统计信息

### FLMM平台 (`/api/flmm`)
- `POST /api/flmm/questionnaire` - 创建问卷
- `GET /api/flmm/questionnaire/{id}` - 获取问卷详情
- `GET /api/flmm/questionnaires` - 获取问卷列表
- `POST /api/flmm/response` - 提交问卷回答
- `GET /api/flmm/analysis/{id}` - 获取问卷分析
- `GET /api/flmm/stats` - 获取平台统计

---

## 设计特性

### UI/UX设计
- **现代化设计** - 紫色渐变主题 (#667eea → #764ba2)
- **流畅动画** - Framer Motion提供的页面过渡和元素动画
- **丰富图表** - 柱状图、折线图、饼图等多种可视化
- **响应式布局** - 适配各种屏幕尺寸
- **实时更新** - 自动轮询任务状态

### 技术特点
- **异步处理** - FastAPI后台任务处理长时间运行的评估
- **智能缓存** - TanStack Query自动管理数据缓存
- **文件上传** - 支持拖拽上传和批量处理
- **类型安全** - TypeScript和Pydantic双重保障
- **API密钥管理** - 环境变量安全存储

---

## 开发指南

### 添加新的API端点

1. 在 `backend/app/api/` 中创建或修改路由文件
2. 在 `backend/app/models/` 中定义数据模型
3. 在 `backend/app/main.py` 中注册路由
4. 在 `frontend/src/services/` 中添加API调用
5. 在页面组件中使用 TanStack Query 调用

### 添加新页面

1. 在 `frontend/src/pages/` 对应模块下创建组件
2. 在 `frontend/src/App.tsx` 中添加路由
3. 在侧边栏导航中添加菜单项

### 代码规范

- 遵循 PEP 8（Python）和 ESLint（TypeScript）规范
- 使用类型提示和接口定义
- 添加必要的注释和文档字符串
- 保持代码简洁和可维护性

---

## 故障排除

### 后端启动失败
- 检查 Python 版本（需要 3.8+）
- 确保在 `damoxingeval` 环境中运行
- 确保已安装所有依赖：`pip install -r backend/requirements.txt`
- 检查端口 8000 是否被占用
- 查看日志中的错误信息

### 前端启动失败
- 检查 Node.js 版本（需要 16+）
- 删除 `node_modules` 和 `package-lock.json`，重新安装
- 检查端口 5173 是否被占用

### API调用失败
- 确认后端服务正在运行
- 检查 CORS 配置
- 查看浏览器控制台的网络请求
- 确认 API 基础URL正确

### 模块导入错误
- 确保 PYTHONPATH 包含项目根目录
- 检查 `QA/config.py` 和 `.env` 文件是否存在
- 验证 API 密钥是否正确配置

### 中文显示乱码
- 启动脚本已设置 UTF-8 编码（`chcp 65001`）
- 如仍有问题，检查终端字体是否支持中文

---

## 生产部署

### 后端部署

```bash
# 使用 gunicorn（推荐）
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 前端部署

```bash
# 构建生产版本
npm run build

# 构建产物在 dist/ 目录中
# 可使用 nginx、apache 或任何静态文件服务器托管
```

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 配置说明

### 虚拟环境

本系统使用 conda 环境：`damoxingeval`

```bash
# 激活环境
conda activate damoxingeval

# 所有 Python 操作前必须先激活此环境
```

### API密钥配置

在 `LLM_EVAL/config/.env` 文件中配置：

```env
SILICONFLOW_API_KEY=your_api_key_here
```

---

## 下一步计划

### 待实现功能
- 数据库集成（PostgreSQL/MySQL）
- 用户认证和权限管理
- 实际模块业务逻辑集成
- 报告导出（PDF/Excel）
- WebSocket实时通知
- 批量操作优化
- 历史记录查询

### 性能优化
- Redis缓存
- 分页和虚拟滚动
- 大文件上传优化
- CDN加速

---

## 许可证

本项目采用 MIT 许可证

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 项目文档

---

**最后更新**: 2025-01-17
**版本**: 2.0.0
**维护团队**: LLM Evaluation Team
