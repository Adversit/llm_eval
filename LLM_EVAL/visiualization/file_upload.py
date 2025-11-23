import streamlit as st
import os
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from utils.file_manager_singleton import get_file_manager

class FileUploadInterface:
    """文件上传界面"""
    
    def __init__(self):
        """初始化文件上传界面"""
        pass
    
    def _check_reset_interface(self):
        """检查是否需要重置界面到初始状态"""
        if st.session_state.get('reset_to_initial_upload', False):
            # 清除重置标志
            st.session_state.reset_to_initial_upload = False
            
            # 如果需要显示信息填写界面，不显示重置提示
            if not st.session_state.get('show_info_form_in_upload', False):
                # 显示重置提示
                st.info("🔄 已重置到初始状态，请重新上传文件开始新的测评")
                
                # 为当前模型生成新的时间戳（只在重置时生成）
                model_name = st.session_state.get('selected_model', '')
                if model_name:
                    from utils.file_manager_singleton import get_file_manager
                    file_manager = get_file_manager()
                    timestamp = file_manager.start_new_test(model_name)
                    st.session_state.current_timestamp = timestamp
                    st.session_state.timestamped_model_name = f"{model_name}{timestamp}"
                    st.success(f"✨ 已为新测评生成时间戳: {timestamp}")
            
            # 确保清除所有文件相关的session state
            keys_to_clear = [
                'selected_files', 'newly_uploaded_files'
            ]
            
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 清除所有文件选择状态
            keys_to_remove = []
            for key in st.session_state.keys():
                if key.startswith('file_'):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del st.session_state[key]
    
    def _render_info_form_in_upload(self):
        """在文件上传界面中渲染信息填写表单"""
        st.info("🔄 重新开始测评，请重新填写或确认评估信息")
        
        # 导入信息填写界面
        from visiualization.information_form import InformationFormInterface
        
        # 创建信息填写界面实例并渲染（使用前缀避免key冲突）
        info_form = InformationFormInterface(key_prefix="upload_")
        info_form.render()
        
        # 添加继续按钮
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📁 继续到文件上传", type="primary", use_container_width=True, key="file_upload_continue_button"):
                # 检查是否已完成信息填写
                if st.session_state.get('info_completed', False):
                    # 清除显示信息填写界面的标志
                    st.session_state.show_info_form_in_upload = False
                    st.success("✅ 信息确认完成，现在可以上传文件了")
                    st.rerun()
                else:
                    st.warning("⚠️ 请先完成信息填写")
    
    def render(self):
        """渲染文件上传界面"""
        st.header("📁 文件上传与配置")
        
        # 检查是否需要重置界面
        self._check_reset_interface()
        
        # 检查是否需要显示信息填写界面
        if st.session_state.get('show_info_form_in_upload', False):
            self._render_info_form_in_upload()
        else:
            # 侧边栏配置
            self._render_sidebar()
            
            # 主界面内容
            self._render_main_content()
    
    def _render_sidebar(self):
        """渲染侧边栏配置"""
        st.sidebar.header("⚙️ 评估配置")
        
        # 显示当前选择的模型（从信息填写界面获取）
        current_model = st.session_state.get('selected_model', '')
        if current_model:
            st.sidebar.info(f"🤖 当前评估模型: **{current_model}**")
        else:
            st.sidebar.warning("⚠️ 请先在信息填写界面选择模型")
        
        st.sidebar.markdown("---")
        
        # 2. 第一阶段的两个阈值
        st.sidebar.subheader("🎯 第一阶段阈值设置")
        stage1_answer_threshold = st.sidebar.slider(
            "答案分数阈值",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
            help="第一阶段答案评分的阈值（百分制）"
        )
        stage1_reasoning_threshold = st.sidebar.slider(
            "推理分数阈值",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
            help="第一阶段推理评分的阈值（百分制）"
        )
        
        st.sidebar.markdown("---")
        
        # 3. 第二阶段的两个阈值
        st.sidebar.subheader("🎯 第二阶段阈值设置")
        stage2_answer_threshold = st.sidebar.slider(
            "答案分数阈值 (Stage2)",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
            help="第二阶段答案评分的阈值（百分制）"
        )
        stage2_reasoning_threshold = st.sidebar.slider(
            "推理分数阈值 (Stage2)",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0,
            help="第二阶段推理评分的阈值（百分制）"
        )
        
        st.sidebar.markdown("---")
        
        # 4. 评估次数选择
        evaluation_rounds = st.sidebar.selectbox(
            "评估次数",
            options=[1, 2, 3, 4, 5],
            index=0,
            help="选择评估的轮次，多轮评估可以提高结果的准确性"
        )
        
        # 保存配置到session state
        st.session_state.stage1_answer_threshold = stage1_answer_threshold
        st.session_state.stage1_reasoning_threshold = stage1_reasoning_threshold
        st.session_state.stage2_answer_threshold = stage2_answer_threshold
        st.session_state.stage2_reasoning_threshold = stage2_reasoning_threshold
        st.session_state.evaluation_rounds = evaluation_rounds
    
    def _render_main_content(self):
        """渲染主界面内容"""
        # 文件上传功能
        st.subheader("📤 文件上传")
        
        # 三个选项的文件上传
        upload_option = st.radio(
            "选择上传方式",
            ["上传单个文件", "上传多个文件"],
            horizontal=True
        )
        
        uploaded_files = []
        if upload_option == "上传单个文件":
            uploaded_file = st.file_uploader(
                "选择Excel文件",
                type=['xlsx', 'xls'],
                accept_multiple_files=False,
                help="支持.xlsx和.xls格式的Excel文件"
            )
            if uploaded_file:
                uploaded_files = [uploaded_file]
        else:
            uploaded_files = st.file_uploader(
                "选择多个Excel文件",
                type=['xlsx', 'xls'],
                accept_multiple_files=True,
                help="支持.xlsx和.xls格式的Excel文件"
            )
        
        # 处理上传的文件
        if uploaded_files:
            self._handle_uploaded_files(uploaded_files)
        
        # 显示目标目录下的文件列表
        self._display_existing_files()
        
        # 开始测评按钮
        self._render_evaluation_button()
    
    def _handle_uploaded_files(self, uploaded_files):
        """处理上传的文件"""
        model_name = st.session_state.get('selected_model', '')
        if not model_name:
            st.error("❌ 请先在信息填写界面选择模型")
            return
        
        # 确保使用session state中的时间戳
        from utils.file_manager_singleton import ensure_timestamp_consistency
        session_timestamp = st.session_state.get('current_timestamp')
        
        if not session_timestamp:
            st.error("❌ 时间戳未初始化，请先在信息填写界面完成模型选择")
            return
        
        file_manager = ensure_timestamp_consistency(model_name, session_timestamp)
        target_dir = file_manager._get_file_dir(model_name, "test_data")
        
        st.info(f"📁 文件将保存到: {target_dir}")
        
        newly_uploaded = []
        for uploaded_file in uploaded_files:
            file_path = target_dir / uploaded_file.name
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            newly_uploaded.append(uploaded_file.name)
            st.success(f"✅ 文件 {uploaded_file.name} 上传成功")
        
        # 更新session state中的新上传文件列表
        if 'newly_uploaded_files' not in st.session_state:
            st.session_state.newly_uploaded_files = []
        st.session_state.newly_uploaded_files.extend(newly_uploaded)
    
    def _display_existing_files(self):
        """显示目标目录下的现有文件"""
        model_name = st.session_state.get('selected_model', '')
        if not model_name:
            st.info("请先在信息填写界面选择模型")
            return
        
        # 确保使用session state中的时间戳
        from utils.file_manager_singleton import ensure_timestamp_consistency
        session_timestamp = st.session_state.get('current_timestamp')
        
        # 如果没有时间戳，说明是新会话或者信息填写界面还没有初始化
        if not session_timestamp:
            st.warning("⚠️ 请先在信息填写界面完成模型选择，以初始化时间戳")
            return
        
        file_manager = ensure_timestamp_consistency(model_name, session_timestamp)
        target_dir = file_manager._get_file_dir(model_name, "test_data")
        
        st.subheader("📋 文件列表")
        
        if not target_dir.exists():
            st.info("目标目录不存在，请先上传文件")
            return
        
        # 获取目录下的所有Excel文件
        excel_files = []
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(target_dir.glob(ext))
        
        if not excel_files:
            st.info("目标目录下暂无Excel文件")
            return
        
        # 显示文件列表和选择框
        st.write(f"📂 目录: `{target_dir}`")
        
        # 显示当前时间戳信息
        current_timestamp = st.session_state.get('current_timestamp')
        if current_timestamp:
            timestamped_model_name = f"{model_name}{current_timestamp}"
            st.info(f"🕒 当前会话: {timestamped_model_name}")
        
        # 全选/全不选按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 选择全部", key="select_all"):
                for file_path in excel_files:
                    st.session_state[f"file_{file_path.name}"] = True
        
        with col2:
            if st.button("❌ 取消全选", key="deselect_all"):
                for file_path in excel_files:
                    st.session_state[f"file_{file_path.name}"] = False
        
        st.markdown("---")
        
        # 文件选择列表
        selected_files = []
        newly_uploaded = st.session_state.get('newly_uploaded_files', [])
        
        for file_path in sorted(excel_files):
            file_name = file_path.name
            
            # 确定默认选择状态
            default_selected = file_name in newly_uploaded
            
            # 如果session state中没有这个文件的状态，使用默认状态
            if f"file_{file_name}" not in st.session_state:
                st.session_state[f"file_{file_name}"] = default_selected
            
            # 显示文件选择框 - 只使用session state，不设置value参数
            is_selected = st.checkbox(
                f"📄 {file_name}",
                key=f"file_{file_name}",
                help=f"文件大小: {self._get_file_size(file_path)}"
            )
            
            if is_selected:
                selected_files.append(str(file_path))
        
        # 更新选中的文件列表
        st.session_state.selected_files = selected_files
        
        # 显示选中文件的统计信息
        if selected_files:
            st.success(f"✅ 已选择 {len(selected_files)} 个文件")
            with st.expander("查看选中的文件"):
                for file_path in selected_files:
                    st.write(f"• {Path(file_path).name}")
        else:
            st.warning("⚠️ 请至少选择一个文件进行评估")
    
    def _get_file_size(self, file_path: Path) -> str:
        """获取文件大小的可读格式"""
        try:
            size_bytes = file_path.stat().st_size
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        except:
            return "未知"
    
    def _render_evaluation_button(self):
        """渲染开始测评按钮"""
        st.markdown("---")
        st.subheader("🚀 开始评估")
        
        # 检查模型是否已选择
        model_name = st.session_state.get('selected_model', '')
        if not model_name:
            st.warning("⚠️ 请先在信息填写界面选择模型")
            st.button("开始测评", disabled=True, key="disabled_start_no_model")
            return
        
        # 检查是否有选中的文件
        selected_files = st.session_state.get('selected_files', [])
        
        if not selected_files:
            st.warning("⚠️ 请先选择要评估的文件")
            st.button("开始测评", disabled=True, key="disabled_start_no_files")
            return
        
        # 显示评估配置摘要
        with st.expander("📊 评估配置摘要", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本配置:**")
                st.write(f"• 模型: {model_name}")
                st.write(f"• 文件数量: {len(selected_files)}")
                st.write(f"• 评估轮次: {st.session_state.evaluation_rounds}")
                
                # 显示当前时间戳
                current_timestamp = st.session_state.get('current_timestamp')
                if current_timestamp:
                    st.write(f"• 时间戳: {current_timestamp}")
            
            with col2:
                st.write("**阈值设置:**")
                st.write(f"• Stage1 答案阈值: {st.session_state.stage1_answer_threshold}")
                st.write(f"• Stage1 推理阈值: {st.session_state.stage1_reasoning_threshold}")
                st.write(f"• Stage2 答案阈值: {st.session_state.stage2_answer_threshold}")
                st.write(f"• Stage2 推理阈值: {st.session_state.stage2_reasoning_threshold}")
        
        # 开始测评按钮
        if st.button("🚀 开始测评", type="primary", use_container_width=True, key="start_evaluation_button"):
            # 获取评估模型名称（安全检查）
            eval_info = st.session_state.get('evaluation_info')
            if eval_info and isinstance(eval_info, dict):
                eval_model_name = eval_info.get('eval_model_name', 'siliconflow_deepseek_v3')
            else:
                eval_model_name = 'siliconflow_deepseek_v3'  # 默认值

            # 准备评估参数
            evaluation_params = {
                'model_name': model_name,
                'eval_model_name': eval_model_name,
                'file_paths': selected_files,
                'file_count': len(selected_files),
                'evaluation_rounds': st.session_state.evaluation_rounds,
                'stage1_answer_threshold': st.session_state.stage1_answer_threshold,
                'stage1_reasoning_threshold': st.session_state.stage1_reasoning_threshold,
                'stage2_answer_threshold': st.session_state.stage2_answer_threshold,
                'stage2_reasoning_threshold': st.session_state.stage2_reasoning_threshold
            }
            
            # 保存评估参数到session state
            st.session_state.evaluation_params = evaluation_params
            st.session_state.evaluation_started = True
            st.session_state.evaluation_running = True  # 直接开始评估
            
            # 输出评估信息（按要求）
            st.success("✅ 评估参数已设置完成！")
            st.info("📋 **评估输出信息:**")
            st.write(f"• **需要测评的模型名**: {evaluation_params['model_name']}")
            st.write(f"• **需要测评的文件数量**: {evaluation_params['file_count']}")
            st.write("• **测评文件路径**:")
            for i, file_path in enumerate(evaluation_params['file_paths'], 1):
                st.write(f"  {i}. `{file_path}`")
            
            st.success("🎯 请切换到 **评估过程** 选项卡查看评估进度！")