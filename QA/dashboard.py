import streamlit as st
import os
import sys
import pandas as pd
import time
import tempfile
from datetime import datetime
from complete_workflow import run_complete_workflow

# 添加父目录到路径以导入shared_styles
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入统一样式
from shared_styles import apply_unified_theme, create_header, create_footer, create_workflow_step

st.set_page_config(page_title="文档问答处理仪表盘", layout="wide")

def main():
    # 应用统一主题
    apply_unified_theme()

    # 创建美化的头部
    create_header(
        title="文档问答生成管理系统",
        subtitle="批量文档解析、智能问答生成与质量评估平台",
        icon="📄"
    )
    
    # 初始化session state
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0  # 默认显示第一个标签页
    if 'results' not in st.session_state:
        st.session_state.results = {}
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'current_file' not in st.session_state:
        st.session_state.current_file = ""
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    if 'files_to_process' not in st.session_state:
        st.session_state.files_to_process = []
    if 'processing_params' not in st.session_state:
        st.session_state.processing_params = {}
    if 'process_status' not in st.session_state:
        st.session_state.process_status = {}
    
    # 侧边栏配置
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
            <h2 style="margin: 0; font-size: 1.3rem;">⚙️ 参数配置</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📊 问答生成设置")
        num_pairs = st.number_input("每段内容生成问答对数量", value=1, min_value=1, max_value=10)
        suggest_qa_count = st.checkbox("请模型建议问答对数量", value=True)
        use_suggested_count = st.checkbox("使用模型建议的问答对数量", value=True)

        st.markdown("---")

        st.markdown("### 🎯 质量阈值")
        min_factual_score = st.slider("最低事实依据分数", 1, 10, 7)
        min_overall_score = st.slider("最低总体质量分数", 1, 10, 7)
        qa_sample_percentage = st.slider("评估样本百分比(%)", 10, 100, 30)

        st.markdown("---")

        st.markdown("### 🔧 处理步骤")
        include_reason = st.checkbox("包含评估理由", value=False)
        skip_extract = st.checkbox("跳过内容提取", value=False)
        skip_evaluate = st.checkbox("跳过内容评估", value=False)
        skip_qa = st.checkbox("跳过问答对生成", value=False)
        skip_qa_evaluate = st.checkbox("跳过问答对质量评估", value=True)
    
    # 定义标签页
    tab_names = ["文件上传", "处理状态", "结果查看"]
    tabs = st.tabs(tab_names)
    
    # 文件上传标签页
    with tabs[0]:
        st.header("上传文档文件")
        
        uploaded_files = st.file_uploader(
            "选择Word文档文件(docx/doc)", 
            type=["docx", "doc"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"已上传 {len(uploaded_files)} 个文件:")
            file_data = []
            
            for file in uploaded_files:
                file_size = len(file.getvalue()) / 1024  # KB
                file_data.append({
                    "文件名": file.name,
                    "大小(KB)": f"{file_size:.2f}",
                    "类型": file.type
                })
            
            st.dataframe(pd.DataFrame(file_data))
            
            def on_click_process():
                # 保存上传的文件到临时存储
                temp_files = []
                for file in uploaded_files:
                    # 创建临时文件保存上传的内容
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(file.getvalue())
                        temp_files.append((file.name, tmp_file.name))
                
                # 保存处理参数
                st.session_state.processing_params = {
                    'num_pairs': num_pairs,
                    'include_reason': include_reason,
                    'suggest_qa_count': suggest_qa_count,
                    'use_suggested_count': use_suggested_count,
                    'min_factual_score': min_factual_score,
                    'min_overall_score': min_overall_score,
                    'qa_sample_percentage': qa_sample_percentage,
                    'skip_extract': skip_extract,
                    'skip_evaluate': skip_evaluate,
                    'skip_qa': skip_qa,
                    'skip_qa_evaluate': skip_qa_evaluate
                }
                
                # 初始化处理状态
                st.session_state.process_status = {
                    'started_time': datetime.now(),
                    'current_step': '准备中',
                    'step_progress': 0.0,
                    'file_progress': 0.0,
                    'time_elapsed': 0,
                    'estimated_remaining': '计算中...'
                }
                
                # 保存要处理的文件列表
                st.session_state.files_to_process = temp_files
                st.session_state.processing = True
                st.session_state.current_tab = 1  # 切换到状态标签页
            
            # 添加处理按钮
            st.button("开始处理所有文件", on_click=on_click_process)
    
    # 处理状态标签页
    with tabs[1]:
        st.header("文件处理状态")
        
        # 如果有待处理的文件且处理标志为真，开始处理文件
        if st.session_state.processing and st.session_state.files_to_process:
            st.subheader("正在处理...")
            
            # 显示进度信息面板
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 当前处理信息")
                current_file_text = st.empty()
                current_step_text = st.empty()
                time_info_text = st.empty()
            
            with col2:
                st.markdown("### 总体进度")
                files_progress_text = st.empty()
                overall_progress_bar = st.progress(0)
                files_count_text = st.empty()
            
            # 文件进度
            st.markdown("### 文件处理进度")
            file_progress_bar = st.progress(0)
            file_progress_text = st.empty()
            
            # 步骤进度
            st.markdown("### 当前步骤进度")
            step_progress_bar = st.progress(0)
            step_status_text = st.empty()
            
            # 处理日志
            st.markdown("### 处理日志")
            log_container = st.container()
            
            # 创建自定义进度回调函数
            def progress_callback(step_name, step_progress, message=None):
                """处理进度回调函数"""
                # 更新进度信息
                st.session_state.process_status['current_step'] = step_name
                st.session_state.process_status['step_progress'] = step_progress
                
                # 更新UI
                step_progress_bar.progress(step_progress)
                step_status_text.write(f"步骤: {step_name} - 进度: {step_progress:.0%}")
                
                if message:
                    with log_container:
                        st.info(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                
                # 强制更新UI
                time.sleep(0.1)
            
            total_files = len(st.session_state.files_to_process)
            start_time = datetime.now()
            
            for i, (file_name, file_path) in enumerate(st.session_state.files_to_process):
                # 更新当前处理文件
                st.session_state.current_file = file_name
                file_start_time = datetime.now()
                
                # 更新文件进度信息
                current_file_text.write(f"**当前文件:** {file_name}")
                files_progress_text.write(f"**总进度:** {i}/{total_files} 文件")
                files_count_text.write(f"**已完成:** {i} 文件, **剩余:** {total_files - i} 文件")
                
                # 更新时间信息
                elapsed = (datetime.now() - start_time).total_seconds()
                if i > 0:
                    avg_time_per_file = elapsed / i
                    est_remaining = avg_time_per_file * (total_files - i)
                    est_text = f"{est_remaining/60:.1f} 分钟" if est_remaining > 60 else f"{est_remaining:.0f} 秒"
                else:
                    est_text = "计算中..."
                
                time_info_text.write(f"**已用时间:** {elapsed/60:.1f} 分钟 | **预计剩余:** {est_text}")
                
                # 记录处理开始
                with log_container:
                    st.info(f"[{datetime.now().strftime('%H:%M:%S')}] 开始处理文件: {file_name}")
                
                # 处理文件
                try:
                    # 运行处理工作流
                    result = run_complete_workflow(
                        document_path=file_path,
                        progress_callback=progress_callback,
                        **st.session_state.processing_params
                    )
                    
                    # 存储结果
                    st.session_state.results[file_name] = result
                    st.session_state.processed_files.append(file_name)
                    
                    # 记录处理成功
                    with log_container:
                        st.success(f"[{datetime.now().strftime('%H:%M:%S')}] 文件处理成功: {file_name}")
                    
                except Exception as e:
                    # 记录错误
                    st.session_state.results[file_name] = {
                        'success': False,
                        'error': str(e)
                    }
                    st.session_state.processed_files.append(file_name)
                    
                    # 记录处理失败
                    with log_container:
                        st.error(f"[{datetime.now().strftime('%H:%M:%S')}] 文件处理失败: {file_name} - 错误: {str(e)}")
                
                # 删除临时文件
                try:
                    os.unlink(file_path)
                except:
                    pass
                
                # 更新文件进度
                file_process_time = (datetime.now() - file_start_time).total_seconds()
                file_progress = (i + 1) / total_files
                overall_progress_bar.progress(file_progress)
                file_progress_bar.progress(1.0)  # 当前文件完成
                file_progress_text.write(f"文件 {i+1}/{total_files} 处理完成，用时: {file_process_time:.1f} 秒")
                
                # 重置步骤进度
                step_progress_bar.progress(0)
                step_status_text.write("等待下一个文件...")
            
            # 处理完成后清空待处理列表和参数
            total_time = (datetime.now() - start_time).total_seconds()
            st.session_state.files_to_process = []
            st.session_state.processing = False
            
            # 显示完成信息
            st.success(f"所有文件处理完成！共处理 {total_files} 个文件，总耗时: {total_time/60:.1f} 分钟")
            
            # 显示处理结果
            if st.session_state.processed_files:
                st.subheader("处理结果摘要")
                success_count = sum(1 for name in st.session_state.processed_files 
                                   if st.session_state.results.get(name, {}).get('success', False))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总文件数", total_files)
                with col2:
                    st.metric("成功处理", success_count)
                with col3:
                    st.metric("处理失败", total_files - success_count)
                
                st.subheader("详细处理结果")
                results_df = []
                
                for file_name in st.session_state.processed_files:
                    result = st.session_state.results.get(file_name, {})
                    status = "成功" if result.get('success', False) else "失败"
                    error = result.get('error', '')
                    
                    # 获取文件路径信息
                    file_paths = []
                    if result.get('success', False) and 'files' in result:
                        for file_type, file_path in result['files'].items():
                            file_paths.append(f"{file_type}: {os.path.basename(file_path)}")
                    
                    results_df.append({
                        "文件名": file_name,
                        "状态": status,
                        "生成的文件": ", ".join(file_paths) if file_paths else "-",
                        "错误信息": error
                    })
                
                st.dataframe(pd.DataFrame(results_df))
        elif st.session_state.processed_files:
            # 显示已处理文件的结果
            st.success(f"所有文件处理完成，共 {len(st.session_state.processed_files)} 个文件")
            
            success_count = sum(1 for name in st.session_state.processed_files 
                               if st.session_state.results.get(name, {}).get('success', False))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总文件数", len(st.session_state.processed_files))
            with col2:
                st.metric("成功处理", success_count)
            with col3:
                st.metric("处理失败", len(st.session_state.processed_files) - success_count)
            
            st.subheader("详细处理结果")
            results_df = []
            
            for file_name in st.session_state.processed_files:
                result = st.session_state.results.get(file_name, {})
                status = "成功" if result.get('success', False) else "失败"
                error = result.get('error', '')
                
                # 获取文件路径信息
                file_paths = []
                if result.get('success', False) and 'files' in result:
                    for file_type, file_path in result['files'].items():
                        file_paths.append(f"{file_type}: {os.path.basename(file_path)}")
                
                results_df.append({
                    "文件名": file_name,
                    "状态": status,
                    "生成的文件": ", ".join(file_paths) if file_paths else "-",
                    "错误信息": error
                })
            
            st.dataframe(pd.DataFrame(results_df))
        else:
            st.info('无处理记录，请在"文件上传"页面上传并处理文件。')
    
    # 结果查看标签页
    with tabs[2]:
        st.header("处理结果")
        
        if 'results' in st.session_state and st.session_state.results:
            file_names = list(st.session_state.results.keys())
            
            selected_file = st.selectbox("选择文件查看结果", file_names)
            
            if selected_file:
                result = st.session_state.results.get(selected_file, {})
                
                if result.get('success', False):
                    st.success(f"文件 {selected_file} 处理成功")
                    
                    st.subheader("生成的文件")
                    for file_type, file_path in result.get('files', {}).items():
                        st.write(f"- {file_type}: {file_path}")
                        
                        # 对于Excel文件，提供预览功能
                        if file_path.endswith('.xlsx') and os.path.exists(file_path):
                            try:
                                df = pd.read_excel(file_path)
                                st.write(f"{file_type} 内容预览:")
                                st.dataframe(df)
                                
                                st.download_button(
                                    label=f"下载 {file_type}",
                                    data=open(file_path, "rb").read(),
                                    file_name=os.path.basename(file_path),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            except Exception as e:
                                st.error(f"无法预览文件: {str(e)}")
                else:
                    st.error(f"文件 {selected_file} 处理失败")
                    st.write(f"错误: {result.get('error', '未知错误')}")
        else:
            st.info("无处理结果可查看")
    
    # 根据session_state切换标签页
    if st.session_state.current_tab > 0:
        # 只在初始渲染后切换，避免反复重新渲染
        js = f"""
        <script>
            var tabs = window.parent.document.querySelectorAll('div[data-testid="stHorizontalBlock"] button[role="tab"]');
            if (tabs.length === 3) {{
                tabs[{st.session_state.current_tab}].click();
            }}
        </script>
        """
        st.components.v1.html(js, height=0)

    # 添加页脚
    create_footer(
        system_name="文档问答生成管理系统",
        additional_info="使用流程：上传文档 → 配置参数 → 处理生成 → 查看结果"
    )

if __name__ == "__main__":
    main() 