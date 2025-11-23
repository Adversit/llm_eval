"""Unified Streamlit entry point that wraps the three existing modules.
Run via: streamlit run integrated_app.py
"""

import importlib.util
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import streamlit as st
from shared_styles import apply_unified_theme, create_header, create_footer, create_workflow_step

ROOT_DIR = Path(__file__).parent.resolve()

st.set_page_config(
    page_title="多模块智能评估平台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


@contextmanager
def suppress_page_config():
    """Temporarily make st.set_page_config a no-op for sub apps."""
    original = st.set_page_config

    def _noop(*_, **__):
        return None

    st.set_page_config = _noop  # type: ignore[attr-defined]
    try:
        yield
    finally:
        st.set_page_config = original  # type: ignore[attr-defined]


@contextmanager
def push_cwd(path: Path):
    """Temporarily switch the working directory for modules that expect it."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


@st.cache_resource(show_spinner=False)
def load_module(module_key: str, relative_entry: str):
    """Dynamically load a module from a file path once per session."""
    module_path = ROOT_DIR / relative_entry
    module_dir = module_path.parent

    # Ensure module dir is importable for relative imports
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    spec = importlib.util.spec_from_file_location(module_key, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {relative_entry}")

    with suppress_page_config():
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_key] = module
        spec.loader.exec_module(module)
    return module


def render_module(module_id: str, entry_path: str, entry_attr: str = "main"):
    module = load_module(module_id, entry_path)
    module_dir = (ROOT_DIR / entry_path).parent

    if not hasattr(module, entry_attr):
        st.error(f"模块 {module_id} 缺少入口函数 {entry_attr}()")
        return

    module_main = getattr(module, entry_attr)
    with suppress_page_config():
        with push_cwd(module_dir):
            module_main()


MODULES = {
    "FLMM问卷平台": {
        "key": "flmm_app",
        "path": "00k/app.py",
        "description": "问卷筛选、项目生成与评估分析",
    },
    "双阶段评测系统": {
        "key": "llm_eval_app",
        "path": "LLM_EVAL/app.py",
        "description": "双重评判流程，支持多文件评估与可视化",
    },
    "文档问答管理": {
        "key": "qa_dashboard",
        "path": "QA/dashboard.py",
        "description": "批量文档解析、问答生成与质量评估",
    },
}


def main():
    # 应用统一主题
    apply_unified_theme()

    # 创建美化的头部
    create_header(
        title="多模块智能评估统一平台",
        subtitle="在一个应用中集成三大功能模块，提供专业的评估与分析服务",
        icon="🧠"
    )

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
            <h2 style="margin: 0; font-size: 1.3rem;">🎯 功能选择</h2>
        </div>
        """, unsafe_allow_html=True)

        # 模块选择
        app_names = list(MODULES.keys())
        selected = st.radio(
            "选择要运行的模块",
            app_names,
            format_func=lambda n: n,
            label_visibility="collapsed"
        )

        # 模块信息卡片
        st.markdown(f"""
        <div class="info-card">
            <strong>📋 模块说明</strong><br>
            <p style="margin: 0.5rem 0 0 0; color: #666;">{MODULES[selected]['description']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 功能模块列表
        st.markdown("### 📚 可用模块")
        for idx, (name, info) in enumerate(MODULES.items(), 1):
            if name == selected:
                status = "active"
            else:
                status = "pending"

            icon = ["📋", "⚖️", "📄"][idx - 1]
            create_workflow_step(
                icon=icon,
                name=name,
                description=info['description'][:20] + "...",
                status=status
            )

        st.markdown("---")

        # 重置按钮
        if st.button("🔄 重置当前模块状态", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # 渲染选中的模块
    try:
        st.markdown("---")
        render_module(MODULES[selected]["key"], MODULES[selected]["path"])
    except Exception as exc:
        st.error(f"❌ 加载模块时出错：{exc}")
        st.exception(exc)

    # 添加页脚
    create_footer(
        system_name="多模块智能评估统一平台",
        additional_info="集成问卷管理、评测系统、文档问答三大核心功能"
    )


if __name__ == "__main__":
    main()
