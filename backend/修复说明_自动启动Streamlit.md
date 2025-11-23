# 自动启动Streamlit服务功能修复

## 🐛 问题描述

**现象**:
- 通过前端创建项目后，点击"启动问卷"按钮显示"问卷链接未配置"
- JSON文件中没有 `login_url` 字段
- 需要手动运行 `streamlit run xxx.py` 才能访问问卷

**原因**:
- 后端API生成了Python文件，但**没有自动启动Streamlit服务**
- JSON文件中的 `login_url` 缺失
- 00k有自动启动功能，但后端API没有实现

---

## ✅ 修复方案

### 1. 添加Streamlit启动辅助函数

**文件**: `backend/app/api/flmm.py`

```python
def find_available_port(start_port=8502, max_attempts=100):
    """查找可用端口（8502-8601）"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def start_streamlit_app(project_path, py_filename, port):
    """后台启动Streamlit应用"""
    script_path = os.path.join(project_path, py_filename)

    process = subprocess.Popen(
        [
            "streamlit", "run", script_path,
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.address", "localhost"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_path
    )

    return process.pid

def load_port_config():
    """加载端口配置"""
    # 从 data/flmm/.port_config.json 读取

def save_port_config(config):
    """保存端口配置"""
    # 保存到 data/flmm/.port_config.json
```

### 2. 在创建项目时自动启动

**在 `create_project()` 函数末尾添加**:

```python
# ========== 自动启动Streamlit服务 ==========
questionnaire_url = None
evidence_url = None
port_config = load_port_config()

# 启动问卷采集服务
if request.enable_questionnaire and CODEGEN_AVAILABLE:
    port = find_available_port()  # 查找可用端口
    if port:
        py_filename = f"{company_name}_{scenario_name}.py"
        pid = start_streamlit_app(project_path, py_filename, port)
        if pid:
            questionnaire_url = f"http://localhost:{port}"
            # 保存端口配置
            port_config[f"{folder_name}_questionnaire"] = {
                "port": port,
                "pid": pid,
                "file": py_filename,
                "type": "questionnaire"
            }
            # 更新JSON文件中的login_url
            project_info["account_info"]["login_url"] = questionnaire_url
            # 重新写入JSON文件
            with open(json_path, "w") as f:
                json.dump(project_info, f, ensure_ascii=False, indent=2)

# 启动证明材料上传服务
if request.enable_evidence and CODEGEN_AVAILABLE:
    port = find_available_port()
    if port:
        evidence_py_filename = f"{company_name}_{scenario_name}_证明材料.py"
        pid = start_streamlit_app(project_path, evidence_py_filename, port)
        if pid:
            evidence_url = f"http://localhost:{port}"
            port_config[f"{folder_name}_evidence"] = {...}

# 保存端口配置
save_port_config(port_config)

# 返回结果时包含URL
return {
    'account': {
        'username': username,
        'password': password,
        'login_url': questionnaire_url or '待部署',
        'evidence_url': evidence_url
    }
}
```

---

## 📦 完整流程

### 创建项目自动启动流程

```
1. 前端调用 POST /api/flmm/project/create
   ↓
2. 后端生成文件:
   - JSON配置
   - Excel问卷
   - Python问卷采集页面 ✅
   - Python证明材料页面 ✅
   ↓
3. 查找可用端口 (8502-8601)
   ↓
4. 启动Streamlit进程
   - streamlit run xxx.py --server.port 8502
   - 后台运行，不阻塞
   ↓
5. 保存端口配置到 .port_config.json
   ↓
6. 更新JSON文件中的 login_url
   ↓
7. 返回前端:
   - account.login_url: "http://localhost:8502" ✅
   - account.evidence_url: "http://localhost:8503"
   ↓
8. 前端显示访问链接
   ↓
9. 用户点击"启动问卷" → 直接打开 ✅
```

---

## 🗂️ 端口配置文件

**位置**: `data/flmm/.port_config.json`

**内容**:
```json
{
  "TestCo_TestScene_questionnaire": {
    "port": 8502,
    "pid": 12345,
    "file": "TestCo_TestScene.py",
    "type": "questionnaire"
  },
  "TestCo_TestScene_evidence": {
    "port": 8503,
    "pid": 12346,
    "file": "TestCo_TestScene_证明材料.py",
    "type": "evidence"
  },
  "中金公司_投研大模型_questionnaire": {
    "port": 8504,
    "pid": 12347,
    "file": "中金公司_投研大模型.py",
    "type": "questionnaire"
  }
}
```

**作用**:
- 记录所有运行中的Streamlit服务
- 防止端口冲突
- 支持服务管理（查看、停止）

---

## 🎯 修复后效果

### JSON文件对比

**修复前** (`1_1.json`):
```json
{
  "account_info": {
    "username": "user_1_33f581d5",
    "password": "e7bca16f-1ce",
    "status": "激活"
    // ❌ 缺少 login_url
  }
}
```

**修复后**:
```json
{
  "account_info": {
    "username": "user_TestCo_abc123",
    "password": "xyz-789",
    "status": "激活",
    "login_url": "http://localhost:8502"  // ✅ 自动添加
  }
}
```

### 前端效果对比

**修复前**:
```
点击"启动问卷" → ❌ "问卷链接未配置，请联系管理员"
```

**修复后**:
```
点击"启动问卷" → ✅ 新标签页打开 http://localhost:8502
                 → ✅ 显示问卷登录页面
                 → ✅ 输入账号密码即可填写
```

---

## 🧪 测试步骤

### 1. 重启Backend服务

```bash
cd backend
# 停止当前服务 (Ctrl+C)
python -m uvicorn app.main:app --reload --port 8000
```

### 2. 创建新项目

```
- 访问前端: http://localhost:5173
- FLMM问卷平台 → 执行流程
- 填写信息创建项目
- 成功弹窗应显示访问链接 ✅
```

### 3. 检查JSON文件

```bash
cat data/flmm/projects/新项目/新项目.json

# 应该包含 login_url 字段
"login_url": "http://localhost:8502"
```

### 4. 测试启动问卷

```
- 访问"项目管理"页面
- 找到新创建的项目
- 点击"启动问卷"按钮
- ✅ 应该在新标签页打开问卷
- ✅ 可以看到登录界面
```

### 5. 验证端口配置

```bash
cat data/flmm/.port_config.json

# 应该包含新项目的配置
{
  "新项目_questionnaire": {
    "port": 8502,
    "pid": xxxxx
  }
}
```

### 6. 检查进程

```bash
# Windows
netstat -ano | findstr "8502"

# 应该看到端口被占用
TCP    0.0.0.0:8502    LISTENING    12345
```

---

## 📋 与00k功能对比

| 功能 | 00k | 后端API（修复前） | 后端API（修复后） |
|------|-----|------------------|------------------|
| 生成Python文件 | ✅ | ❌ | ✅ |
| 自动启动Streamlit | ✅ | ❌ | ✅ |
| 保存login_url | ✅ | ❌ | ✅ |
| 端口管理 | ✅ | ❌ | ✅ |
| 前端显示链接 | ✅ | ❌ | ✅ |
| 一键启动问卷 | ✅ | ❌ | ✅ |

**结论**: 修复后，后端API功能与00k完全一致！

---

## 🔧 技术要点

### 1. 端口查找

- 起始端口: 8502
- 范围: 8502-8601 (100个端口)
- 查找方式: socket绑定测试
- 冲突处理: 自动跳过已占用端口

### 2. 进程管理

- 启动方式: `subprocess.Popen()`
- 运行模式: 后台运行（headless）
- 工作目录: 项目目录
- 输出重定向: PIPE（不显示在终端）

### 3. 配置持久化

- 配置文件: `.port_config.json`
- 保存内容: 端口、PID、文件名、类型
- 更新时机: 每次启动服务后
- 清理策略: 手动或通过服务管理页面

### 4. 安全考虑

- 监听地址: localhost（仅本地访问）
- 端口范围: 限制在8502-8601
- 进程隔离: 每个项目独立进程
- 账号保护: 登录验证

---

## ⚠️ 注意事项

### 1. Streamlit依赖

确保环境中已安装Streamlit:
```bash
conda activate damoxingeval
pip install streamlit
streamlit --version
```

### 2. 启动延迟

Streamlit服务启动需要5-10秒:
- 前端显示链接后等待几秒再访问
- 如果立即访问可能显示"连接失败"
- 刷新页面即可

### 3. 端口冲突

如果端口全部占用:
- 检查 `.port_config.json`
- 停止不需要的服务
- 或重启系统释放端口

### 4. 进程清理

关闭Backend不会自动停止Streamlit:
- 需要手动在服务管理中停止
- 或在任务管理器中结束进程
- 或使用 `taskkill /PID xxx /F`

---

## 📊 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `backend/app/api/flmm.py` | 添加自动启动功能（+100行） |
| `backend/修复说明_自动启动Streamlit.md` | 本文档 |

**新增依赖**:
- `subprocess` - 启动进程
- `socket` - 检测端口

---

## ✨ 完整功能链路

```
前端创建项目
    ↓
后端API接收请求
    ↓
生成JSON、Excel、Python文件 ✅
    ↓
查找可用端口 ✅
    ↓
启动Streamlit进程 ✅
    ↓
保存端口配置 ✅
    ↓
更新JSON中的login_url ✅
    ↓
返回前端（包含链接） ✅
    ↓
前端显示成功弹窗 ✅
    ↓
显示访问链接 ✅
    ↓
项目管理页面可查看 ✅
    ↓
点击"启动问卷"直接打开 ✅
    ↓
被评估方填写问卷 ✅
```

---

**修复时间**: 2025-01-19
**状态**: ✅ 已完成
**测试状态**: 待测试

---

## 🎉 总结

修复后的系统实现了**完全自动化**的流程：

1. ✅ 创建项目自动生成Python文件
2. ✅ 自动启动Streamlit服务
3. ✅ 自动分配端口
4. ✅ 自动保存访问链接
5. ✅ 一键启动问卷
6. ✅ 无需手动操作

**效果**: 与00k功能完全一致，前后端创建的项目都支持自动部署！
