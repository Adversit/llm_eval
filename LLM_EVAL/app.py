import streamlit as st
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 添加父目录到路径以导入shared_styles
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入统一样式
from shared_styles import apply_unified_theme

# 导入四个界面
from visiualization.information_form import InformationFormInterface
from visiualization.file_upload import FileUploadInterface
from visiualization.evaluation_process import EvaluationProcessInterface
from visiualization.result_analysis import ResultAnalysisInterface

def initialize_session_state():
    """统一初始化session state，避免状态分散"""
    defaults = {
        # 评估状态
        'evaluation_completed': False,
        'evaluation_results': None,
        'evaluation_started': False,
        'evaluation_running': False,

        # 信息表单
        'info_completed': False,
        'evaluation_info': None,
        'selected_model': "",
        'current_timestamp': None,
        'timestamped_model_name': None,

        # 文件上传
        'selected_files': [],
        'newly_uploaded_files': [],
        'evaluation_params': None,
        'stage1_answer_threshold': 60.0,
        'stage1_reasoning_threshold': 60.0,
        'stage2_answer_threshold': 60.0,
        'stage2_reasoning_threshold': 60.0,
        'evaluation_rounds': 1,

        # UI控制
        'reset_to_initial_upload': False,
        'show_info_form_in_upload': False,
        'active_tab': 0,  # 新增：当前活动的tab索引
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_workflow_status():
    """获取工作流状态，用于导航和UI提示"""
    status = {
        'step': 1,
        'step_name': '信息填写',
        'can_proceed': False,
        'next_step': 2
    }

    if st.session_state.get('info_completed') or st.session_state.get('evaluation_info'):
        status['step'] = 2
        status['step_name'] = '文件上传'
        status['can_proceed'] = True

    if st.session_state.get('selected_files') and st.session_state.get('evaluation_params'):
        status['step'] = 2
        status['step_name'] = '文件上传（已配置）'
        status['can_proceed'] = True
        status['next_step'] = 3

    if st.session_state.get('evaluation_started'):
        status['step'] = 3
        status['step_name'] = '评估进行中'
        status['can_proceed'] = True
        status['next_step'] = 3

    if st.session_state.get('evaluation_completed'):
        status['step'] = 4
        status['step_name'] = '查看结果'
        status['can_proceed'] = True
        status['next_step'] = 4

    return status


def main():
    """主应用程序

    改进:
    - 统一的状态管理
    - 智能导航提示
    - 更清晰的工作流指引
    """
    # 设置页面配置
    st.set_page_config(
        page_title="智能评估与报告生成系统",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化session state
    initialize_session_state()

    # 应用统一主题样式
    apply_unified_theme()

    # 添加增强的自定义CSS样式（保留原有特定样式）
    st.markdown("""
    <style>
    /* 主标题样式 */
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* 选项卡样式 - 增大尺寸 */
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

    /* 按钮样式增强 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }

    /* 警告和信息框样式 */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }

    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    /* 数据框样式 */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }

    /* 卡片样式 */
    .css-1kyxreq {
        border-radius: 10px;
        padding: 1rem;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    /* 输入框样式 */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* 文件上传器样式 */
    .stFileUploader {
        border-radius: 10px;
        border: 2px dashed #667eea;
        padding: 1rem;
        background-color: #f8f9fa;
    }

    /* 指标卡片样式 */
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    /* 展开器样式 */
    .streamlit-expanderHeader {
        border-radius: 8px;
        background-color: #f8f9fa;
        font-weight: 500;
    }

    /* 日志文本样式 */
    .stText {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 13px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 获取工作流状态
    workflow_status = get_workflow_status()

    # 主标题（带工作流进度指示）
    st.markdown(f"""
    <div class="main-header">
        <h1>智能评估与报告生成系统</h1>
        <p>专业的大模型能力评估平台 - 提供标准化评估报告</p>
        <p style="font-size: 14px; margin-top: 10px;">当前步骤: <strong>{workflow_status['step_name']}</strong> (步骤 {workflow_status['step']}/4)</p>
    </div>
    """, unsafe_allow_html=True)

    # 添加侧边栏工作流指引
    with st.sidebar:
        # 系统标题
        st.markdown("""
        <div style="
            text-align: center;
            padding: 1rem 0.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 1.5rem;
        ">
            <h2 style="margin: 0; font-size: 1.3rem;">⚖️ 智能评估与报告生成系统</h2>
            <p style="margin: 0.3rem 0 0 0; font-size: 0.85rem; opacity: 0.9;">专业评估平台</p>
        </div>
        """, unsafe_allow_html=True)

        # 工作流程
        st.markdown("### 📋 工作流程")
        steps = [
            ("1️⃣", "信息填写", 1, "配置模型"),
            ("2️⃣", "文件上传", 2, "选择数据"),
            ("3️⃣", "评估过程", 3, "运行测试"),
            ("4️⃣", "结果分析", 4, "查看报告")
        ]

        for icon, name, step_num, desc in steps:
            if step_num < workflow_status['step']:
                st.markdown(f"""
                <div style="
                    padding: 0.5rem;
                    margin: 0.3rem 0;
                    border-left: 3px solid #4caf50;
                    background-color: #f1f8f4;
                    border-radius: 5px;
                ">
                    {icon} <s>{name}</s> ✅
                    <br><small style="color: #666;">{desc}</small>
                </div>
                """, unsafe_allow_html=True)
            elif step_num == workflow_status['step']:
                st.markdown(f"""
                <div style="
                    padding: 0.5rem;
                    margin: 0.3rem 0;
                    border-left: 3px solid #667eea;
                    background-color: #f0f4ff;
                    border-radius: 5px;
                ">
                    {icon} <strong>{name}</strong> 👈
                    <br><small style="color: #667eea;"><strong>{desc}</strong></small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    padding: 0.5rem;
                    margin: 0.3rem 0;
                    border-left: 3px solid #e0e0e0;
                    background-color: #fafafa;
                    border-radius: 5px;
                    opacity: 0.6;
                ">
                    {icon} {name}
                    <br><small style="color: #999;">{desc}</small>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # 当前配置信息
        st.markdown("### ⚙️ 当前配置")

        if st.session_state.get('selected_model'):
            st.markdown(f"""
            <div style="
                padding: 0.5rem;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin-bottom: 0.5rem;
            ">
                <strong>🤖 测试模型</strong><br>
                <span style="font-size: 0.9rem; color: #667eea;">{st.session_state['selected_model']}</span>
            </div>
            """, unsafe_allow_html=True)

        eval_info = st.session_state.get('evaluation_info')
        if eval_info and isinstance(eval_info, dict) and eval_info.get('eval_model_name'):
            eval_model = eval_info['eval_model_name']
            st.markdown(f"""
            <div style="
                padding: 0.5rem;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin-bottom: 0.5rem;
            ">
                <strong>📊 评估模型</strong><br>
                <span style="font-size: 0.9rem; color: #764ba2;">{eval_model}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.get('selected_files'):
            file_count = len(st.session_state['selected_files'])
            st.markdown(f"""
            <div style="
                padding: 0.5rem;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin-bottom: 0.5rem;
            ">
                <strong>📁 数据文件</strong><br>
                <span style="font-size: 0.9rem; color: #4caf50;">{file_count} 个文件</span>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.get('evaluation_completed'):
            st.markdown("""
            <div style="
                padding: 0.7rem;
                background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                color: white;
                border-radius: 8px;
                text-align: center;
                margin-top: 1rem;
            ">
                <strong>✅ 评估已完成</strong>
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.get('evaluation_running'):
            st.markdown("""
            <div style="
                padding: 0.7rem;
                background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
                color: white;
                border-radius: 8px;
                text-align: center;
                margin-top: 1rem;
            ">
                <strong>⏳ 评估进行中...</strong>
            </div>
            """, unsafe_allow_html=True)

    # 创建四个选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["📝 信息填写", "📁 文件上传", "⚙️ 评估过程", "📊 结果分析"])
    
    # 信息填写界面
    with tab1:
        info_form = InformationFormInterface()
        info_form.render()
    
    # 文件上传界面
    with tab2:
        # 检查是否已完成信息填写
        if not st.session_state.get('info_completed', False) and not st.session_state.get('evaluation_info'):
            st.warning("⚠️ 请先在「信息填写」选项卡中完成基本信息的填写")
            st.info("💡 完成信息填写后，即可开始上传评估文件")
            st.info("👈 请切换到「信息填写」选项卡开始")
        else:
            file_upload = FileUploadInterface()
            file_upload.render()

    # 评估过程界面
    with tab3:
        # 检查是否已完成信息填写
        if not st.session_state.get('info_completed', False) and not st.session_state.get('evaluation_info'):
            st.warning("⚠️ 请先在「信息填写」选项卡中完成基本信息的填写")
            st.info("👈 请切换到「信息填写」选项卡开始")
        elif not st.session_state.get('selected_files'):
            st.warning("⚠️ 请先在「文件上传」选项卡中上传文件并配置参数")
            st.info("👈 请切换到「文件上传」选项卡")
        else:
            evaluation_process = EvaluationProcessInterface()
            evaluation_process.render()

    # 结果分析界面
    with tab4:
        # 检查是否已完成信息填写
        if not st.session_state.get('info_completed', False) and not st.session_state.get('evaluation_info'):
            st.warning("⚠️ 请先在「信息填写」选项卡中完成基本信息的填写")
            st.info("👈 请切换到「信息填写」选项卡开始")
        elif not st.session_state.get('evaluation_completed'):
            st.warning("⚠️ 评估尚未完成")
            if st.session_state.get('evaluation_running'):
                st.info("⏳ 评估正在进行中，请切换到「评估过程」选项卡查看进度")
            elif st.session_state.get('selected_files'):
                st.info("💡 请在「文件上传」选项卡点击「开始测评」按钮")
            else:
                st.info("💡 请先上传文件并配置评估参数")
        else:
            result_analysis = ResultAnalysisInterface()
            result_analysis.render()
    
    # 添加页脚信息
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>⚖️ 智能评估与报告生成系统 | 专业能力评估 | 标准化报告输出</p>
        <p><small>使用流程：信息填写 → 文件上传 → 评估过程 → 结果分析</small></p>
        <p><small>系统会自动保存评估结果到 data/{模型名}{时间戳}/ 目录下</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()