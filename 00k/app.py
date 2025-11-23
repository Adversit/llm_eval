import streamlit as st
import sys
import os

# 添加父目录到路径以导入shared_styles
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 添加function目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'function'))

# 导入功能模块
from function.Admin_create_function_page import Admin_create_function_page
from function.Admin_analyse_function_page import Admin_analyse_function_page
from function.Admin_manage_services_page import Admin_manage_services_page

# 导入统一样式
from shared_styles import apply_unified_theme, create_header, create_footer, create_workflow_step

def main():
    """主应用入口"""
    st.set_page_config(
        page_title="FLMM评估问卷管理平台",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 应用统一主题
    apply_unified_theme()

    # 创建美化的头部
    create_header(
        title="FLMM评估问卷管理平台",
        subtitle="专业的问卷筛选、项目生成与评估分析工具",
        icon="📋"
    )

    # 侧边栏导航
    with st.sidebar:
        # 侧边栏标题
        st.markdown("""
        <div style="
            text-align: center;
            padding: 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 1.5rem;
        ">
            <h2 style="margin: 0; font-size: 1.3rem;">⚙️ 功能模块</h2>
        </div>
        """, unsafe_allow_html=True)

        # 功能选择
        selected_function = st.radio(
            "选择功能模块",
            ["问卷创建管理", "问卷结果分析", "服务管理"],
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 模块说明
        if selected_function == "问卷创建管理":
            desc = "创建和管理评估问卷，配置评估维度和标准"
        elif selected_function == "问卷结果分析":
            desc = "分析问卷结果，生成评估报告和数据可视化"
        else:
            desc = "管理已启动的Streamlit服务，查看状态和链接"

        st.markdown(f"""
        <div class="info-card">
            <strong>📝 当前模块</strong><br>
            <p style="margin: 0.5rem 0 0 0; color: #666;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 工作流程
        st.markdown("### 📋 工作流程")
        create_workflow_step(
            icon="1️⃣",
            name="问卷创建管理",
            description="设计问卷结构",
            status="active" if selected_function == "问卷创建管理" else "pending"
        )
        create_workflow_step(
            icon="2️⃣",
            name="问卷结果分析",
            description="分析评估结果",
            status="active" if selected_function == "问卷结果分析" else "pending"
        )
        create_workflow_step(
            icon="3️⃣",
            name="服务管理",
            description="管理运行中的服务",
            status="active" if selected_function == "服务管理" else "pending"
        )

    # 主内容区域
    st.markdown("---")

    if selected_function == "问卷创建管理":
        # 调用问卷创建功能
        Admin_create_function_page()

    elif selected_function == "问卷结果分析":
        # 调用问卷结果分析功能
        Admin_analyse_function_page()

    elif selected_function == "服务管理":
        # 调用服务管理功能
        Admin_manage_services_page()

    # 添加页脚
    create_footer(
        system_name="FLMM评估问卷管理平台",
        additional_info="提供问卷设计、数据收集、结果分析一站式服务"
    )

if __name__ == "__main__":
    main()
