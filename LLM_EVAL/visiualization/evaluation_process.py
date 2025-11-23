import streamlit as st
import sys
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from first_stage.stage1_evaluator import Stage1Evaluator
from second_stage.stage2_evaluator import Stage2Evaluator
from utils.result_processor import ResultProcessor
from utils.visual import DataVisualizer
from utils.file_manager_singleton import reset_file_manager_for_new_test

class ProgressTracker:
    """进度追踪器，提供准确的进度计算和预计时间"""

    def __init__(self, total_items: int):
        """初始化进度追踪器

        Args:
            total_items: 总项目数量
        """
        self.total_items = total_items
        self.completed_items = 0
        self.start_time = time.time()
        self.item_times = []  # 记录每个项目的处理时间

    def update(self, completed: int):
        """更新完成数量"""
        if completed > self.completed_items:
            current_time = time.time()
            # 记录单个项目处理时间
            if self.completed_items > 0:
                time_per_item = (current_time - self.start_time) / completed
                self.item_times.append(time_per_item)
                # 只保留最近10个项目的时间，用于动态调整预估
                if len(self.item_times) > 10:
                    self.item_times.pop(0)

        self.completed_items = completed

    def get_progress(self) -> float:
        """获取进度百分比 (0.0 - 1.0)"""
        if self.total_items == 0:
            return 0.0
        return min(self.completed_items / self.total_items, 1.0)

    def get_eta(self) -> Optional[str]:
        """获取预计剩余时间（格式化字符串）"""
        if self.completed_items == 0 or self.total_items == 0:
            return None

        elapsed = time.time() - self.start_time
        remaining_items = self.total_items - self.completed_items

        if remaining_items <= 0:
            return "完成"

        # 使用最近的处理时间来预估
        if self.item_times:
            avg_time_per_item = sum(self.item_times) / len(self.item_times)
        else:
            avg_time_per_item = elapsed / self.completed_items

        eta_seconds = remaining_items * avg_time_per_item

        # 格式化时间
        if eta_seconds < 60:
            return f"{int(eta_seconds)}秒"
        elif eta_seconds < 3600:
            return f"{int(eta_seconds / 60)}分{int(eta_seconds % 60)}秒"
        else:
            hours = int(eta_seconds / 3600)
            minutes = int((eta_seconds % 3600) / 60)
            return f"{hours}小时{minutes}分钟"

    def get_elapsed(self) -> str:
        """获取已用时间（格式化字符串）"""
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{int(elapsed)}秒"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)}分{int(elapsed % 60)}秒"
        else:
            hours = int(elapsed / 3600)
            minutes = int((elapsed % 3600) / 60)
            return f"{hours}小时{minutes}分钟"


class EvaluationProcessInterface:
    """重构后的评估过程界面

    改进:
    - 准确的进度计算
    - 预计剩余时间显示
    - 更流畅的UI更新
    """

    def __init__(self):
        """初始化评估过程界面"""
        pass
    
    def render(self):
        """渲染评估过程界面"""
        st.header("⚙️ 评估过程")

        # 检查是否有评估参数
        if not hasattr(st.session_state, 'evaluation_params') or st.session_state.evaluation_params is None:
            st.warning("⚠️ 请先在文件上传界面配置评估参数")
            st.info("💡 请按照以下步骤操作：")
            st.info("1️⃣ 切换到「信息填写」选项卡填写基本信息")
            st.info("2️⃣ 切换到「文件上传」选项卡上传文件并配置参数")
            st.info("3️⃣ 点击「开始测评」按钮")
            return

        # 检查时间戳是否存在
        if not st.session_state.get('current_timestamp'):
            st.warning("⚠️ 时间戳未初始化，请重新开始评估流程")
            st.info("💡 请返回「文件上传」选项卡重新配置")
            return

        # 检查评估状态
        if st.session_state.get('evaluation_running', False):
            self._run_evaluation_process()
        elif st.session_state.get('evaluation_completed', False):
            st.success("🎉 评估任务已成功完成！")
            st.info("📊 请切换到「结果分析」选项卡查看详细结果")
        else:
            st.info("📋 请在文件上传界面点击'开始测评'按钮开始评估")
            self._display_evaluation_params()
    
    def _display_evaluation_params(self):
        """显示评估参数"""
        params = st.session_state.evaluation_params

        # 检查参数是否存在
        if not params:
            st.info("💡 评估参数尚未配置")
            return

        with st.expander("📊 评估配置详情", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**基本配置:**")
                st.write(f"• 模型: {params.get('model_name', 'N/A')}")
                st.write(f"• 文件数量: {params.get('file_count', 0)}")
                st.write(f"• 评估轮次: {params.get('evaluation_rounds', 1)}")

            with col2:
                st.write("**阈值设置:**")
                st.write(f"• Stage1 答案阈值: {params.get('stage1_answer_threshold', 0.7)}")
                st.write(f"• Stage1 推理阈值: {params.get('stage1_reasoning_threshold', 0.7)}")
                st.write(f"• Stage2 答案阈值: {params.get('stage2_answer_threshold', 0.7)}")
                st.write(f"• Stage2 推理阈值: {params.get('stage2_reasoning_threshold', 0.7)}")

            st.write("**文件列表:**")
            file_paths = params.get('file_paths', [])
            if file_paths:
                for i, file_path in enumerate(file_paths, 1):
                    st.write(f"{i}. `{Path(file_path).name}`")
            else:
                st.write("• 暂无文件")
    
    def _run_evaluation_process(self):
        """运行评估过程"""
        params = st.session_state.evaluation_params
        
        st.subheader("🔄 评估进行中...")
        
        # 创建进度显示容器
        progress_container = st.container()
        log_container = st.container()
        
        with progress_container:
            st.write("**📊 总体进度 (文件级别的宏观进度)**")
            overall_progress = st.progress(0)
            overall_status = st.empty()
            
            st.write("**🔄 问题处理进度 (每个问题的详细处理过程)**")
            question_progress = st.progress(0)
            question_status = st.empty()
        
        with log_container:
            st.markdown("### 📋 评估日志")
            log_placeholder = st.empty()
            
            # 添加日志说明
            st.caption("💡 显示关键进度信息：文件处理、阶段完成、问题统计等")
        
        # 执行评估
        try:
            self._execute_evaluation_workflow(
                params, overall_progress, overall_status, 
                question_progress, question_status, log_placeholder
            )
        except Exception as e:
            st.error(f"❌ 评估过程中发生错误: {str(e)}")
            st.session_state.evaluation_running = False
    
    def _execute_evaluation_workflow(self, params, overall_progress, overall_status, 
                                   question_progress, question_status, log_placeholder):
        """执行评估工作流"""
        logs = []
        total_files = len(params['file_paths'])
        
        # 进度权重分配 (基于实际时间分布)
        INIT_WEIGHT = 0.05      # 初始化: 5%
        STAGE1_WEIGHT = 0.50    # Stage1: 50% (数据处理、LLM测试、评估)
        STAGE2_WEIGHT = 0.30    # Stage2: 30% (深度评估)
        RESULT_WEIGHT = 0.10    # 结果处理: 10%
        VISUAL_WEIGHT = 0.05    # 可视化: 5%
        
        # 日志更新计数器，用于控制更新频率
        log_update_counter = [0]
        
        def log_message(message, log_type="INFO"):
            """记录日志消息"""
            try:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # 根据日志类型添加图标
                if log_type == "ERROR":
                    icon = "❌"
                elif log_type == "WARNING":
                    icon = "⚠️"
                elif log_type == "SUCCESS":
                    icon = "✅"
                else:
                    icon = "ℹ️"
                
                log_entry = f"{timestamp} {icon} {message}"
                logs.append(log_entry)
                
                # 只保留最近25条日志以避免界面过于拥挤
                recent_logs = logs[-25:]
                
                # 控制更新频率，避免过于频繁的界面刷新
                log_update_counter[0] += 1
                if log_update_counter[0] % 2 == 0 or log_type == "ERROR":  # 每2条更新一次，错误立即显示
                    log_text = "\n".join(recent_logs)
                    
                    # 使用markdown显示日志，支持更好的格式
                    with log_placeholder.container():
                        st.text(log_text)
                    
            except Exception as e:
                # 如果日志显示出错，至少不要影响主流程
                pass
        
        # 创建总体进度追踪器
        overall_tracker = ProgressTracker(total_files * params['evaluation_rounds'])

        def update_overall_progress(progress_ratio, stage, file_index=0, file_name="", process_info="", current_round=None, total_rounds=None):
            """更新总体进度条 - 显示文件级别的宏观进度（含预计时间）"""
            # 更新进度条
            overall_progress.progress(min(progress_ratio, 1.0))

            # 更新追踪器
            completed_count = int(progress_ratio * total_files * params['evaluation_rounds'])
            overall_tracker.update(completed_count)

            # 构建状态文本 - 重点显示阶段和文件处理数
            percentage = int(progress_ratio * 100)

            # 根据阶段类型显示不同的图标和描述
            if "Stage1" in stage:
                stage_icon = "1️⃣"
                stage_desc = "基础问答评估"
            elif "Stage2" in stage:
                stage_icon = "2️⃣"
                stage_desc = "深度推理评估"
            elif "初始化" in stage:
                stage_icon = "⚙️"
                stage_desc = "初始化"
            elif "结果处理" in stage:
                stage_icon = "📋"
                stage_desc = "结果处理"
            elif "可视化" in stage:
                stage_icon = "📊"
                stage_desc = "可视化生成"
            else:
                stage_icon = "🔄"
                stage_desc = stage

            # 构建状态文本 - 显示文件处理数、评估轮次和文件名
            if current_round and total_rounds:
                rounds_display = f"评估轮次 {current_round}/{total_rounds}"
            else:
                rounds_display = f"评估轮次 {params['evaluation_rounds']}"

            # 获取时间信息
            elapsed = overall_tracker.get_elapsed()
            eta = overall_tracker.get_eta()

            if file_index > 0 and file_name:
                file_display = f"文件 {file_index}/{total_files}"
                status_text = f"{stage_icon} 总体进度 ({percentage}%) | {stage_desc} | {file_display} | {rounds_display}"
            elif file_name and not file_index:
                # 对于系统级操作，只显示操作类型和评估轮次
                status_text = f"{stage_icon} 总体进度 ({percentage}%) | {stage_desc} | {rounds_display}"
            else:
                # 对于初始化等阶段，也显示评估轮次信息
                status_text = f"{stage_icon} 总体进度 ({percentage}%) | {stage_desc} | {rounds_display}"

            # 添加时间信息
            if eta and eta != "完成":
                status_text += f" | ⏱️ 已用: {elapsed} | 预计剩余: {eta}"
            else:
                status_text += f" | ⏱️ 已用: {elapsed}"

            overall_status.text(status_text)
        
        def create_question_progress_tracker(stage_name, file_name=""):
            """创建问题级别的进度跟踪器 - 精确显示每个问题的处理进度"""
            def callback(current, total, question_id, process_type="", current_round=1, total_rounds=1):
                if total > 0:
                    progress_ratio = min(current / total, 1.0)
                    percentage = int(progress_ratio * 100)
                    
                    # 根据过程类型显示不同的信息
                    if process_type == "testing":
                        if "Stage1" in stage_name:
                            process_icon = "🤖"
                            process_desc = "基础测试"
                            process_detail = "仅使用问题文本"
                        elif "Stage2" in stage_name:
                            process_icon = "🔄"
                            process_desc = "深度重测"
                            process_detail = "使用问题+内容上下文"
                        else:
                            process_icon = "🤖"
                            process_desc = "测试过程"
                            process_detail = ""
                        
                        if question_id:
                            status_text = f"{process_icon} {process_desc} | 文件: {file_name} | 问题 {current}/{total} ({percentage}%) | ID: {question_id}"
                            if process_detail:
                                status_text += f" | {process_detail}"
                        else:
                            status_text = f"{process_icon} {process_desc} | 文件: {file_name} | {current}/{total} ({percentage}%)"
                            
                    elif process_type == "evaluating":
                        if "Stage1" in stage_name:
                            process_icon = "📊"
                            process_desc = "基础评估"
                            process_detail = "评估基础回答质量"
                        elif "Stage2" in stage_name:
                            process_icon = "📋"
                            process_desc = "深度评估"
                            process_detail = "评估深度推理能力"
                        else:
                            process_icon = "📊"
                            process_desc = "评估过程"
                            process_detail = ""
                        
                        if question_id:
                            status_text = f"{process_icon} {process_desc} | 文件: {file_name} | 问题 {current}/{total} ({percentage}%) | ID: {question_id}"
                            if process_detail:
                                status_text += f" | {process_detail}"
                        else:
                            status_text = f"{process_icon} {process_desc} | 文件: {file_name} | {current}/{total} ({percentage}%)"
                            
                    else:
                        # 其他过程（数据处理、初始化等）
                        process_icon = "⚙️"
                        if question_id:
                            status_text = f"{process_icon} {stage_name} | 文件: {file_name} | 项目 {current}/{total} ({percentage}%) | ID: {question_id}"
                        else:
                            status_text = f"{process_icon} {stage_name} | 文件: {file_name} | {current}/{total} ({percentage}%)"
                        
                        if process_type:
                            status_text += f" | {process_type}"
                    
                    # 更新进度条和状态
                    question_progress.progress(progress_ratio)
                    question_status.text(status_text)
                else:
                    question_progress.progress(0)
                    question_status.text(f"⏳ {stage_name} | 文件: {file_name} | 准备中...")
            
            return callback
        
        try:
            # === 1. 初始化阶段 ===
            log_message("🚀 开始评估任务")
            update_overall_progress(0.01, "初始化")
            
            # 确保使用与文件上传一致的时间戳
            from utils.file_manager_singleton import ensure_timestamp_consistency
            session_timestamp = st.session_state.get('current_timestamp')
            if session_timestamp:
                ensure_timestamp_consistency(params['model_name'], session_timestamp)
            else:
                # 如果没有时间戳，说明有问题，需要生成一个
                reset_file_manager_for_new_test(params['model_name'])
            
            # 创建初始化进度回调
            init_callback = create_question_progress_tracker("初始化评估器", "系统")
            init_callback(0, 3, "", "准备中")
            
            # 获取评估模型名称
            eval_model_name = params.get('eval_model_name', 'siliconflow_deepseek_v3')

            stage1_evaluator = Stage1Evaluator(
                model_name=params['model_name'],
                eval_model_name=eval_model_name
            )
            init_callback(1, 3, "", "Stage1评估器完成")

            stage2_evaluator = Stage2Evaluator(
                model_name=params['model_name'],
                eval_model_name=eval_model_name
            )
            init_callback(2, 3, "", "Stage2评估器完成")
            
            init_callback(3, 3, "", "时间戳目录已生成")
            
            log_message(f"📋 准备处理 {total_files} 个文件，共 {params['evaluation_rounds']} 轮评估")
            
            update_overall_progress(INIT_WEIGHT, "初始化完成")
            
            # === 2. Stage1 评估阶段 ===
            log_message("1️⃣ 开始Stage1基础问答评估")
            stage1_results = []
            total_stage1_questions = 0
            total_need_retest = 0
            
            for i, file_path in enumerate(params['file_paths'], 1):
                file_name = Path(file_path).stem
                stage1_progress_base = INIT_WEIGHT + (STAGE1_WEIGHT * (i - 1) / total_files)
                stage1_progress_step = STAGE1_WEIGHT / total_files
                
                log_message(f"📄 文件 {i}/{total_files}: {file_name}")
                update_overall_progress(
                    stage1_progress_base, 
                    "Stage1 基础问答评估", 
                    file_index=i,
                    file_name=file_name,
                    process_info="数据处理"
                )
                
                # 执行Stage1评估并跟踪进度
                stage1_result = self._run_stage1_with_progress(
                    stage1_evaluator, file_path, params, i, file_name, 
                    create_question_progress_tracker, log_message, update_overall_progress,
                    stage1_progress_base, stage1_progress_step
                )
                stage1_results.append(stage1_result)
                
                # 从结果中获取统计信息
                # 检查是否为多轮评估结果
                if 'aggregated_statistics' in stage1_result:
                    # 多轮评估：使用汇总统计数据
                    stats = stage1_result.get('aggregated_statistics', {})
                    total_questions = stats.get('total_questions', 0)
                    need_retest = stats.get('avg_need_retest', 0)
                    correct_answers = stats.get('avg_correct_answers', 0)
                    reasoning_errors = stats.get('avg_reasoning_errors', 0)
                else:
                    # 单轮评估：使用常规统计数据
                    stats = stage1_result.get('statistics', {})
                    total_questions = stats.get('total_questions', 0)
                    need_retest = stats.get('need_retest', 0)
                    correct_answers = stats.get('correct_answers', 0)
                    reasoning_errors = stats.get('reasoning_errors', 0)
                
                total_stage1_questions += total_questions
                total_need_retest += need_retest
                
                log_message(f"✅ {file_name}: 完成 {total_questions} 题，需重测 {need_retest} 题")
                
                update_overall_progress(
                    stage1_progress_base + stage1_progress_step, 
                    "Stage1 基础问答评估", 
                    file_index=i,
                    file_name=file_name,
                    process_info="完成"
                )
            
            log_message(f"1️⃣ Stage1完成: 总计 {total_stage1_questions} 题，需重测 {total_need_retest} 题")
            
            # === 3. Stage2 评估阶段 ===
            log_message("2️⃣ 开始Stage2深度推理评估")
            total_stage2_questions = 0
            
            for i, file_path in enumerate(params['file_paths'], 1):
                file_name = Path(file_path).stem
                stage2_progress_base = INIT_WEIGHT + STAGE1_WEIGHT + (STAGE2_WEIGHT * (i - 1) / total_files)
                stage2_progress_step = STAGE2_WEIGHT / total_files
                
                update_overall_progress(
                    stage2_progress_base, 
                    "Stage2 深度推理评估", 
                    file_index=i,
                    file_name=file_name,
                    process_info="检查需求"
                )
                
                # 执行多轮Stage2评估
                file_stage2_questions = self._run_multi_round_stage2(
                    stage2_evaluator, file_name, params, i, 
                    create_question_progress_tracker, log_message,
                    update_overall_progress, stage2_progress_base, stage2_progress_step
                )
                
                total_stage2_questions += file_stage2_questions
                
                update_overall_progress(
                    stage2_progress_base + stage2_progress_step, 
                    "Stage2 深度推理评估", 
                    file_index=i,
                    file_name=file_name,
                    process_info="完成"
                )
            
            if total_stage2_questions > 0:
                log_message(f"2️⃣ Stage2完成: 总计处理 {total_stage2_questions} 题")
            else:
                log_message("2️⃣ Stage2完成: 所有题目均通过Stage1")
            
            # === 4. 结果处理阶段 ===
            log_message("📊 开始分析评测结果")
            result_progress_base = INIT_WEIGHT + STAGE1_WEIGHT + STAGE2_WEIGHT
            
            processor = ResultProcessor()
            file_names = [Path(fp).stem for fp in params['file_paths']]
            
            # 处理单文件结果
            result_callback = create_question_progress_tracker("结果处理", "系统")
            for i, file_name in enumerate(file_names, 1):
                result_progress = result_progress_base + (RESULT_WEIGHT * i / (total_files + 1))
                update_overall_progress(
                    result_progress, 
                    "结果处理与分析", 
                    file_index=i,
                    file_name=file_name,
                    process_info="单文件分析"
                )
                
                try:
                    # 处理步骤进度
                    result_callback(0, 3, file_name, "加载Stage1结果")
                    result_callback(1, 3, file_name, "加载Stage2结果")
                    result_callback(2, 3, file_name, "合并分析")
                    
                    processor.process_single_file_results(params['model_name'], file_name)
                    
                    result_callback(3, 3, file_name, "✓ 完成")
                    log_message(f"✅ {file_name}: 结果分析完成")
                except Exception as e:
                    log_message(f"❌ {file_name}: 结果处理失败", "ERROR")
                    result_callback(3, 3, file_name, "❌ 失败")
            
            # 多文件汇总
            enable_multi_file = len(file_names) > 1
            if enable_multi_file:
                summary_callback = create_question_progress_tracker("多文件汇总", "系统")
                
                try:
                    summary_callback(0, 3, "", "收集数据")
                    summary_callback(1, 3, "", "生成统计")
                    summary_callback(2, 3, "", "生成报告")
                    
                    processor.process_multi_file_results(params['model_name'], enable_multi_file)
                    
                    summary_callback(3, 3, "", "✓ 汇总完成")
                    log_message("📋 多文件汇总完成")
                except Exception as e:
                    log_message("❌ 多文件汇总失败", "ERROR")
                    summary_callback(3, 3, "", "❌ 汇总失败")
            else:
                skip_summary_callback = create_question_progress_tracker("多文件汇总", "系统")
                skip_summary_callback(1, 1, "", "单文件模式，跳过")
            
            # === 5. 可视化阶段 ===
            log_message("📈 开始生成可视化图表")
            visual_progress_base = INIT_WEIGHT + STAGE1_WEIGHT + STAGE2_WEIGHT + RESULT_WEIGHT
            update_overall_progress(visual_progress_base, "可视化生成")
            
            try:
                visualizer = DataVisualizer()
                visual_callback = create_question_progress_tracker("可视化生成", "系统")
                
                # 生成图表
                chart_steps = len(file_names) * 2 + (2 if len(file_names) > 1 else 0)
                current_step = 0
                
                # 生成单文件图表
                for i, file_name in enumerate(file_names, 1):
                    visual_progress = visual_progress_base + (VISUAL_WEIGHT * 0.8 * i / len(file_names))
                    update_overall_progress(
                        visual_progress, 
                        "可视化生成", 
                        file_index=i,
                        file_name=file_name
                    )
                    
                    # 柱状图
                    current_step += 1
                    visual_callback(current_step, chart_steps, file_name, "生成柱状图")
                    
                    # 饼图
                    current_step += 1
                    visual_callback(current_step, chart_steps, file_name, "生成饼图")
                
                # 实际生成所有图表
                visualization_results = visualizer.visualize_files(params['model_name'], file_names)
                
                # 多文件汇总图表
                if len(file_names) > 1:
                    update_overall_progress(
                        visual_progress_base + VISUAL_WEIGHT * 0.9, 
                        "可视化生成", 
                        file_name="多文件汇总"
                    )
                    
                    current_step += 1
                    visual_callback(current_step, chart_steps, "汇总", "生成汇总柱状图")
                    current_step += 1
                    visual_callback(current_step, chart_steps, "汇总", "生成汇总饼图")
                
                visual_callback(chart_steps, chart_steps, "", "✓ 可视化完成")
                
                log_message("📊 可视化图表生成完成")
                
            except Exception as e:
                log_message("❌ 可视化生成失败", "ERROR")
                error_callback = create_question_progress_tracker("可视化生成", "系统")
                error_callback(1, 1, "", "❌ 图表生成失败")
                visualization_results = None
            
            # === 6. 完成 ===
            update_overall_progress(1.0, "✅ 评估完成")
            complete_callback = create_question_progress_tracker("评估完成", "系统")
            complete_callback(1, 1, "", "🎉 所有任务完成")
            
            # 生成评估总结
            log_message("🎉 评估任务完成", "SUCCESS")
            retest_rate = (total_need_retest/total_stage1_questions*100) if total_stage1_questions > 0 else 0
            log_message(f"📊 总计: {total_stage1_questions}题 | 重测: {total_stage2_questions}题 | 重测率: {retest_rate:.1f}%", "SUCCESS")
            log_message("📋 请切换到'结果分析'查看详细报告", "SUCCESS")
            
            # 强制刷新最终日志显示
            try:
                final_log_text = "\n".join(logs[-25:])
                with log_placeholder.container():
                    st.text(final_log_text)
            except:
                pass
            
            # 保存结果
            st.session_state.evaluation_results = {
                'model_name': params['model_name'],
                'file_names': file_names,
                'visualization_results': visualization_results,
                'enable_multi_file': enable_multi_file,
                'summary_stats': {
                    'total_files': total_files,
                    'total_stage1_questions': total_stage1_questions,
                    'total_stage2_questions': total_stage2_questions,
                    'total_need_retest': total_need_retest
                }
            }
            st.session_state.evaluation_completed = True
            st.session_state.evaluation_running = False
            
            st.success("✅ 评估完成！请切换到 '结果分析' 选项卡查看结果")
            
        except Exception as e:
            log_message(f"评估过程发生错误: {str(e)}", "ERROR")
            
            # 强制刷新错误日志显示
            try:
                error_log_text = "\n".join(logs[-25:])
                with log_placeholder.container():
                    st.text(error_log_text)
            except:
                pass
                
            update_overall_progress(0, "❌ 评估失败")
            error_tracker = create_question_progress_tracker("处理中断", "系统")
            error_tracker(0, 1, "", "❌ 处理中断")
            st.session_state.evaluation_running = False
            raise
    
    def _run_stage1_with_progress(self, stage1_evaluator, file_path, params, file_index, 
                                 file_name, create_question_progress_tracker, log_message, 
                                 update_overall_progress, progress_base, progress_step):
        """执行Stage1评估并跟踪进度 - 区分测试过程和评估过程"""
        
        # 创建Stage1专用的问题进度跟踪器，能够传递轮次信息到总体进度条
        current_round_ref = [1]  # 使用列表来存储当前轮次，便于在回调中修改
        total_rounds_ref = [params['evaluation_rounds']]
        
        def stage1_tracker_with_round_update(current, total, question_id, process_type="", current_round=1, total_rounds=1):
            # 更新轮次信息
            current_round_ref[0] = current_round
            total_rounds_ref[0] = total_rounds
            
            # 调用原始的问题进度跟踪器
            stage1_tracker = create_question_progress_tracker("Stage1", file_name)
            stage1_tracker(current, total, question_id, process_type, current_round, total_rounds)
            
            # 如果是测试或评估过程，更新总体进度条以显示当前轮次
            if process_type in ["testing", "evaluating"]:
                current_progress = progress_base + progress_step * 0.5  # 估算当前进度
                update_overall_progress(
                    current_progress, 
                    "Stage1 基础问答评估", 
                    file_index=file_index,
                    file_name=file_name,
                    process_info=f"{process_type}过程",
                    current_round=current_round,
                    total_rounds=total_rounds
                )
        
        stage1_tracker_with_round_update(0, 1, "", "初始化数据处理")
        
        try:
            # 先读取文件获取问题数量
            from utils.excel_processor import ExcelProcessor
            processor = ExcelProcessor(file_path)
            data_list = processor.process_data()
            total_questions = len(data_list)
            
            stage1_tracker_with_round_update(1, 1, "", f"数据处理完成 ({total_questions}个问题)")
            
            # 更新总体进度 - 数据处理完成，准备开始测试过程
            update_overall_progress(
                progress_base + progress_step * 0.1, 
                "Stage1 基础问答评估", 
                file_index=file_index,
                file_name=file_name,
                process_info="🤖 基础测试过程"
            )
            
            # 设置evaluator的进度回调 - 这里会接收到testing和evaluating的回调
            stage1_evaluator.set_progress_callback(stage1_tracker_with_round_update)
            
            # 执行完整评估 - 内部会调用测试过程和评估过程
            result = stage1_evaluator.run_complete_evaluation(
                file_paths=[file_path],
                num_evaluations=params['evaluation_rounds'],
                answer_threshold=params['stage1_answer_threshold'],
                reasoning_threshold=params['stage1_reasoning_threshold']
            )
            
            # 为每轮创建轮次分析文件（如果是多轮评估）
            self._create_round_analysis_files_for_stage1(result, file_name, params)
            
            # 从结果中获取处理的数据量信息
            stats = result.get('statistics', {})
            actual_questions = stats.get('total_questions', total_questions)
            need_retest = stats.get('need_retest', 0)
            correct_answers = stats.get('correct_answers', 0)
            reasoning_errors = stats.get('reasoning_errors', 0)
            
            stage1_tracker_with_round_update(actual_questions, actual_questions, "", "✓ Stage1完成")
            
            # 更新总体进度 - Stage1完成
            update_overall_progress(
                progress_base + progress_step * 0.9, 
                "Stage1 基础问答评估", 
                file_index=file_index,
                file_name=file_name,
                process_info="基础测试+评估完成"
            )
            
            return result
            
        except Exception as e:
            log_message(f"❌ {file_name}: Stage1处理失败", "ERROR")
            stage1_tracker_with_round_update(1, 1, "", "❌ 处理失败")
            raise
    
    def _run_multi_round_stage2(self, stage2_evaluator, file_name, params, file_index,
                               create_question_progress_tracker, log_message,
                               update_overall_progress, progress_base, progress_step):
        """运行多轮Stage2评估
        
        Args:
            stage2_evaluator: Stage2评估器
            file_name: 文件名
            params: 评估参数
            file_index: 文件索引
            create_question_progress_tracker: 进度跟踪器创建函数
            log_message: 日志记录函数
            update_overall_progress: 总体进度更新函数
            progress_base: 进度基准值
            progress_step: 进度步长
            
        Returns:
            int: 处理的问题总数
        """
        total_questions_processed = 0
        
        # 对每个评估轮次执行Stage2
        for round_num in range(1, params['evaluation_rounds'] + 1):
            # 读取当前轮次的分析文件
            round_analysis = self._load_round_analysis(file_name, round_num)
            if not round_analysis:
                continue
            
            # 检查是否需要Stage2评估
            need_retest = round_analysis.get('statistics', {}).get('need_retest', 0)
            
            if need_retest > 0:
                log_message(f"🔄 {file_name}: 第{round_num}轮需重测 {need_retest}题")
                
                # 构建重测数据文件路径
                if round_num == 1:
                    retest_file_name = "stage1_to_stage2_data.csv"
                else:
                    retest_file_name = f"stage1_to_stage2_data_round{round_num}.csv"
                
                # 执行Stage2评估
                self._run_single_round_stage2(
                    stage2_evaluator, file_name, round_num, retest_file_name,
                    params, file_index, need_retest, create_question_progress_tracker,
                    log_message, update_overall_progress, progress_base, progress_step
                )
                
                total_questions_processed += need_retest
        
        return total_questions_processed
    
    def _load_round_analysis(self, file_name: str, round_num: int) -> Optional[Dict[str, Any]]:
        """加载指定轮次的分析文件
        
        Args:
            file_name: 文件名
            round_num: 轮次编号
            
        Returns:
            Dict: 分析数据，如果文件不存在返回None
        """
        try:
            from utils.file_manager_singleton import get_file_manager
            file_manager = get_file_manager()
            
            # 查找最新的时间戳目录
            timestamped_dir = file_manager.find_latest_timestamp_dir(st.session_state.evaluation_params['model_name'])
            if not timestamped_dir:
                return None
            
            # 构建轮次分析文件路径
            round_analysis_path = timestamped_dir / file_name / f"{file_name}_analysis_round_{round_num}.json"
            
            if round_analysis_path.exists():
                import json
                with open(round_analysis_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return None
                
        except Exception as e:
            return None
    
    def _run_single_round_stage2(self, stage2_evaluator, file_name, round_num, retest_file_name,
                                params, file_index, need_retest_count, create_question_progress_tracker,
                                log_message, update_overall_progress, progress_base, progress_step):
        """运行单轮Stage2评估
        
        Args:
            stage2_evaluator: Stage2评估器
            file_name: 文件名
            round_num: 轮次编号
            retest_file_name: 重测数据文件名
            params: 评估参数
            file_index: 文件索引
            need_retest_count: 需要重测的问题数
            create_question_progress_tracker: 进度跟踪器创建函数
            log_message: 日志记录函数
            update_overall_progress: 总体进度更新函数
            progress_base: 进度基准值
            progress_step: 进度步长
        """
        try:
            from utils.file_manager_singleton import get_file_manager
            file_manager = get_file_manager()
            
            # 查找最新的时间戳目录
            timestamped_dir = file_manager.find_latest_timestamp_dir(params['model_name'])
            if not timestamped_dir:
                raise FileNotFoundError(f"未找到模型 {params['model_name']} 的时间戳目录")
            
            # 构建重测数据文件路径
            retest_file_path = timestamped_dir / file_name / retest_file_name
            
            if not retest_file_path.exists():
                return
            
            # 创建进度跟踪器
            stage2_tracker = create_question_progress_tracker("Stage2", file_name)
            
            def stage2_tracker_with_round_update(current, total, question_id, process_type="", current_round=1, total_rounds=1):
                # 更新轮次信息
                stage2_tracker(current, total, question_id, process_type, round_num, params['evaluation_rounds'])
            
            # 设置evaluator的进度回调
            stage2_evaluator.set_progress_callback(stage2_tracker_with_round_update)
            
            # 执行Stage2评估（单轮）
            result = stage2_evaluator.run_complete_evaluation(
                file_paths=[str(retest_file_path)],
                num_evaluations=1,  # 每轮只执行一次
                answer_threshold=params['stage2_answer_threshold'],
                reasoning_threshold=params['stage2_reasoning_threshold']
            )
            
            # 创建轮次分析文件（Stage1 + Stage2）
            self._create_combined_round_analysis(file_name, round_num, result)
            
        except Exception as e:
            log_message(f"❌ {file_name}: 第{round_num}轮Stage2失败", "ERROR")
            raise
    
    def _create_combined_round_analysis(self, file_name: str, round_num: int, stage2_result: Dict[str, Any]):
        """创建合并的轮次分析文件（Stage1 + Stage2）
        
        Args:
            file_name: 文件名
            round_num: 轮次编号
            stage2_result: Stage2评估结果
        """
        try:
            from utils.result_processor import ResultProcessor
            from utils.file_manager_singleton import get_file_manager
            
            file_manager = get_file_manager()
            processor = ResultProcessor()
            
            # 查找最新的时间戳目录
            timestamped_dir = file_manager.find_latest_timestamp_dir(st.session_state.evaluation_params['model_name'])
            if not timestamped_dir:
                return
            
            # 加载Stage1轮次分析文件
            stage1_round_path = timestamped_dir / file_name / f"{file_name}_analysis_round_{round_num}.json"
            if not stage1_round_path.exists():
                return
            
            import json
            with open(stage1_round_path, 'r', encoding='utf-8') as f:
                stage1_data = json.load(f)
            
            # 创建合并的轮次分析文件
            processor.create_round_analysis(
                st.session_state.evaluation_params['model_name'], 
                file_name, 
                round_num, 
                stage1_data, 
                stage2_result
            )
            
        except Exception as e:
            pass  # 静默处理错误，不影响主流程
    
    def _create_round_analysis_files_for_stage1(self, stage1_result: Dict[str, Any], file_name: str, params: Dict[str, Any]):
        """为Stage1的每轮评估创建轮次分析文件
        
        Args:
            stage1_result: Stage1评估结果
            file_name: 文件名
            params: 评估参数
        """
        try:
            from utils.result_processor import ResultProcessor
            from utils.file_manager_singleton import get_file_manager
            
            processor = ResultProcessor()
            file_manager = get_file_manager()
            
            # 查找最新的时间戳目录
            timestamped_dir = file_manager.find_latest_timestamp_dir(params['model_name'])
            if not timestamped_dir:
                return
            
            base_dir = timestamped_dir / file_name
            
            # 检查是否为多轮评估
            is_multi_round = stage1_result.get("evaluation_rounds", 0) > 1
            
            if is_multi_round:
                # 多轮评估：为每轮创建轮次分析文件
                individual_results = stage1_result.get("individual_results", [])
                for round_result in individual_results:
                    round_number = round_result.get("round_number", 1)
                    
                    # 创建轮次分析文件（只有Stage1数据）
                    processor.create_round_analysis(
                        params['model_name'], 
                        file_name, 
                        round_number, 
                        round_result, 
                        None  # 暂时没有Stage2数据
                    )
            else:
                # 单轮评估：创建第1轮的轮次分析文件
                processor.create_round_analysis(
                    params['model_name'], 
                    file_name, 
                    1, 
                    stage1_result, 
                    None  # 暂时没有Stage2数据
                )
                
        except Exception as e:
            pass  # 静默处理错误，不影响主流程
    
    def _run_stage2_with_progress(self, stage2_evaluator, stage1_evaluator, file_name, 
                                 params, file_index, need_retest_count, create_question_progress_tracker, 
                                 log_message, update_overall_progress, progress_base, progress_step):
        """执行Stage2评估并跟踪进度 - 区分测试过程和评估过程"""
        stage1_to_stage2_path = stage1_evaluator.get_retest_data_path(file_name)
        
        # 创建Stage2专用的问题进度跟踪器，能够传递轮次信息到总体进度条
        current_round_ref = [1]  # 使用列表来存储当前轮次，便于在回调中修改
        total_rounds_ref = [params['evaluation_rounds']]
        
        def stage2_tracker_with_round_update(current, total, question_id, process_type="", current_round=1, total_rounds=1):
            # 更新轮次信息
            current_round_ref[0] = current_round
            total_rounds_ref[0] = total_rounds
            
            # 调用原始的问题进度跟踪器
            stage2_tracker = create_question_progress_tracker("Stage2", file_name)
            stage2_tracker(current, total, question_id, process_type, current_round, total_rounds)
            
            # 如果是测试或评估过程，更新总体进度条以显示当前轮次
            if process_type in ["testing", "evaluating"]:
                current_progress = progress_base + progress_step * 0.5  # 估算当前进度
                update_overall_progress(
                    current_progress, 
                    "Stage2 深度推理评估", 
                    file_index=file_index,
                    file_name=file_name,
                    process_info=f"{process_type}过程",
                    current_round=current_round,
                    total_rounds=total_rounds
                )
        
        if Path(stage1_to_stage2_path).exists():
            log_message(f"开始Stage2深度评估: {file_name} ({need_retest_count}个问题)")
            log_message("  Stage2将重新测试LLM（使用问题+内容上下文）并重新评估")
            stage2_tracker_with_round_update(0, need_retest_count, "", "数据加载中")
            
            try:
                # 读取需要重测的数据
                retest_df = pd.read_csv(stage1_to_stage2_path)
                actual_retest_count = len(retest_df)
                
                log_message(f"Stage2实际处理 {actual_retest_count} 个问题")
                log_message("  开始重新测试过程（提供更多上下文信息）")
                stage2_tracker_with_round_update(1, actual_retest_count, "", f"加载完成 ({actual_retest_count}个问题)")
                
                # 更新总体进度 - 开始Stage2重新测试过程
                update_overall_progress(
                    progress_base + progress_step * 0.1, 
                    "Stage2 深度推理评估", 
                    file_index=file_index,
                    file_name=file_name,
                    process_info="🤖 重新测试过程"
                )
                
                # 设置evaluator的进度回调 - 这里会接收到testing和evaluating的回调
                stage2_evaluator.set_progress_callback(stage2_tracker_with_round_update)
                
                # 执行完整评估 - 内部会调用重新测试过程和重新评估过程
                result = stage2_evaluator.run_complete_evaluation(
                    file_paths=[stage1_to_stage2_path],
                    num_evaluations=params['evaluation_rounds'],
                    answer_threshold=params['stage2_answer_threshold'],
                    reasoning_threshold=params['stage2_reasoning_threshold']
                )
                
                # 从结果中获取处理的数据量信息
                stats = result.get('statistics', {})
                total_questions = stats.get('total_questions', actual_retest_count)
                knowledge_deficiency = stats.get('knowledge_deficiency', 0)
                reasoning_errors = stats.get('reasoning_errors', 0)
                capability_insufficient = stats.get('capability_insufficient', 0)
                
                log_message(f"Stage2完成 - 重新测试并评估了 {total_questions} 个问题")
                log_message(f"  - 知识缺失: {knowledge_deficiency}, 推理错误: {reasoning_errors}, 能力不足: {capability_insufficient}")
                stage2_tracker_with_round_update(total_questions, total_questions, "", "✓ Stage2完成")
                
                # 更新总体进度 - Stage2完成
                update_overall_progress(
                    progress_base + progress_step * 0.9, 
                    "Stage2 深度推理评估", 
                    file_index=file_index,
                    file_name=file_name,
                    process_info="重新测试+评估完成"
                )
                
            except Exception as e:
                log_message(f"Stage2处理失败: {str(e)}", "ERROR")
                stage2_tracker_with_round_update(1, 1, "", "❌ 处理失败")
                
        else:
            log_message(f"文件 {file_name} 的Stage2数据文件不存在，跳过第二阶段")
            stage2_tracker_with_round_update(1, 1, "", "数据缺失，跳过")
    
