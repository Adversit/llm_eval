"""
统一的Streamlit样式配置
用于保持所有模块的视觉风格一致
"""

# 主题配色方案
THEME_COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
    'info': '#2196f3',
    'bg_light': '#f8f9fa',
    'bg_white': '#ffffff',
    'text_dark': '#333333',
    'text_light': '#666666',
    'border': '#e9ecef',
}

# 统一CSS样式
UNIFIED_CSS = """
<style>
/* ========== 全局样式 ========== */
.main {
    background-color: #f8f9fa;
}

/* ========== 主标题样式 ========== */
.main-header {
    text-align: center;
    padding: 2rem 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 15px;
    margin-bottom: 2rem;
    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
}

.main-header h1 {
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
}

.main-header p {
    margin: 0.5rem 0 0 0;
    font-size: 1.1rem;
    opacity: 0.95;
}

/* ========== 选项卡样式 ========== */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 30px;
}

.stTabs [data-baseweb="tab"] {
    height: 80px;
    min-height: 80px;
    padding: 0 40px;
    background-color: #ffffff;
    border-radius: 12px;
    border: 3px solid transparent;
    font-weight: 600;
    font-size: 18px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #e9ecef;
    border-color: #667eea;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white !important;
    border-color: #667eea;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    transform: translateY(-2px);
}

/* ========== 按钮样式 ========== */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.75rem 2rem;
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
}

.stButton > button[kind="secondary"] {
    background-color: white;
    border-color: #667eea;
    color: #667eea;
}

/* ========== 卡片样式 ========== */
.info-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    margin-bottom: 1rem;
    border-left: 4px solid #667eea;
    transition: all 0.3s ease;
}

.info-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
}

.success-card {
    border-left-color: #4caf50;
}

.warning-card {
    border-left-color: #ff9800;
}

.error-card {
    border-left-color: #f44336;
}

/* ========== 警告和信息框样式 ========== */
.stAlert {
    border-radius: 10px;
    border-left: 4px solid;
    padding: 1rem 1.5rem;
    font-size: 1rem;
}

/* ========== 进度条样式 ========== */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}

.stProgress > div > div {
    background-color: #e9ecef;
    border-radius: 10px;
}

/* ========== 数据框样式 ========== */
.stDataFrame {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ========== 侧边栏样式 ========== */
[data-testid="stSidebar"] {
    background-color: #f8f9fa;
}

[data-testid="stSidebar"] > div {
    padding-top: 2rem;
}

/* 侧边栏标题 */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #333;
    font-weight: 600;
}

/* ========== 输入框样式 ========== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > select,
.stTextArea > div > div > textarea {
    border-radius: 8px;
    border: 2px solid #e9ecef;
    transition: all 0.3s ease;
    font-size: 1rem;
    padding: 0.75rem;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stSelectbox > div > div > select:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* ========== 选择框样式 ========== */
.stSelectbox > div > div {
    border-radius: 8px;
}

/* ========== 文件上传器样式 ========== */
.stFileUploader {
    border-radius: 12px;
    border: 2px dashed #667eea;
    padding: 2rem;
    background-color: #f8f9fa;
    transition: all 0.3s ease;
}

.stFileUploader:hover {
    background-color: #e9ecef;
    border-color: #764ba2;
}

/* ========== 指标卡片样式 ========== */
.stMetric {
    background-color: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-left: 4px solid #667eea;
}

.stMetric label {
    font-size: 0.9rem;
    color: #666;
    font-weight: 600;
}

.stMetric [data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
    color: #667eea;
}

/* ========== 展开器样式 ========== */
.streamlit-expanderHeader {
    border-radius: 10px;
    background-color: #f8f9fa;
    font-weight: 600;
    padding: 1rem;
    border: 2px solid #e9ecef;
    transition: all 0.3s ease;
}

.streamlit-expanderHeader:hover {
    background-color: #e9ecef;
    border-color: #667eea;
}

/* ========== 滑块样式 ========== */
.stSlider > div > div > div {
    background-color: #667eea;
}

/* ========== 复选框和单选框样式 ========== */
.stCheckbox > label,
.stRadio > label {
    font-weight: 500;
    color: #333;
}

/* ========== 分隔线样式 ========== */
hr {
    margin: 2rem 0;
    border: none;
    border-top: 2px solid #e9ecef;
}

/* ========== 标签样式 ========== */
.stTag {
    background-color: #667eea;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* ========== 表格样式 ========== */
table {
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 10px;
    overflow: hidden;
}

thead tr {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

thead th {
    padding: 1rem;
    font-weight: 600;
}

tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

tbody td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e9ecef;
}

/* ========== 页脚样式 ========== */
.footer {
    text-align: center;
    color: #666;
    padding: 2rem 1rem;
    margin-top: 3rem;
    border-top: 2px solid #e9ecef;
}

.footer p {
    margin: 0.5rem 0;
}

/* ========== 工作流步骤卡片 ========== */
.workflow-step {
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.workflow-step-completed {
    border-left: 4px solid #4caf50;
    background-color: #f1f8f4;
}

.workflow-step-active {
    border-left: 4px solid #667eea;
    background-color: #f0f4ff;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.workflow-step-pending {
    border-left: 4px solid #e0e0e0;
    background-color: #fafafa;
    opacity: 0.6;
}

/* ========== 状态徽章 ========== */
.status-badge {
    display: inline-block;
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
}

.status-success {
    background-color: #4caf50;
    color: white;
}

.status-warning {
    background-color: #ff9800;
    color: white;
}

.status-error {
    background-color: #f44336;
    color: white;
}

.status-info {
    background-color: #2196f3;
    color: white;
}

/* ========== 加载动画 ========== */
.stSpinner > div {
    border-top-color: #667eea !important;
}

/* ========== 响应式设计 ========== */
@media (max-width: 768px) {
    .main-header h1 {
        font-size: 1.8rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 60px;
        min-height: 60px;
        padding: 0 20px;
        font-size: 16px;
    }
}
</style>
"""


def apply_unified_theme():
    """应用统一主题到当前页面"""
    import streamlit as st
    st.markdown(UNIFIED_CSS, unsafe_allow_html=True)


def create_header(title: str, subtitle: str = "", icon: str = "🧠"):
    """创建统一的页面头部

    Args:
        title: 主标题
        subtitle: 副标题
        icon: 图标emoji
    """
    import streamlit as st
    header_html = f"""
    <div class="main-header">
        <h1>{icon} {title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def create_footer(system_name: str = "", additional_info: str = ""):
    """创建统一的页面页脚

    Args:
        system_name: 系统名称
        additional_info: 额外信息
    """
    import streamlit as st
    footer_html = f"""
    <div class="footer">
        {f'<p><strong>{system_name}</strong></p>' if system_name else ''}
        {f'<p><small>{additional_info}</small></p>' if additional_info else ''}
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)


def create_info_card(content: str, card_type: str = "info"):
    """创建信息卡片

    Args:
        content: 卡片内容
        card_type: 卡片类型 (info, success, warning, error)
    """
    import streamlit as st
    card_class = f"info-card {card_type}-card" if card_type != "info" else "info-card"
    card_html = f"""
    <div class="{card_class}">
        {content}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def create_status_badge(text: str, status: str = "info"):
    """创建状态徽章

    Args:
        text: 徽章文本
        status: 状态类型 (success, warning, error, info)
    """
    import streamlit as st
    badge_html = f"""
    <span class="status-badge status-{status}">{text}</span>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


def create_workflow_step(icon: str, name: str, description: str, status: str = "pending"):
    """创建工作流步骤卡片

    Args:
        icon: 步骤图标
        name: 步骤名称
        description: 步骤描述
        status: 步骤状态 (completed, active, pending)
    """
    import streamlit as st

    if status == "completed":
        step_html = f"""
        <div class="workflow-step workflow-step-completed">
            {icon} <s>{name}</s> ✅
            <br><small style="color: #666;">{description}</small>
        </div>
        """
    elif status == "active":
        step_html = f"""
        <div class="workflow-step workflow-step-active">
            {icon} <strong>{name}</strong> 👈
            <br><small style="color: #667eea;"><strong>{description}</strong></small>
        </div>
        """
    else:  # pending
        step_html = f"""
        <div class="workflow-step workflow-step-pending">
            {icon} {name}
            <br><small style="color: #999;">{description}</small>
        </div>
        """

    st.markdown(step_html, unsafe_allow_html=True)
