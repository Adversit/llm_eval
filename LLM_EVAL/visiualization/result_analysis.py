import streamlit as st
import json
import pandas as pd
from pathlib import Path
from PIL import Image
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))
from utils.file_manager_singleton import get_file_manager, reset_file_manager_for_new_test
from utils.report_generator import ReportGenerator
from utils.html_report_generator import HTMLReportGenerator

class ResultAnalysisInterface:
    """结果分析界面"""
    
    def __init__(self):
        """初始化结果分析界面"""
        self.file_manager = get_file_manager()
        self.report_generator = ReportGenerator()
        self.html_report_generator = HTMLReportGenerator()
    
    def render(self):
        """渲染结果分析界面"""
        st.header("📊 结果分析")
        
        # 检查是否有评估结果
        if not st.session_state.get('evaluation_completed', False):
            st.warning("⚠️ 请先完成评估过程")
            return
        
        if 'evaluation_results' not in st.session_state:
            st.error("❌ 未找到评估结果数据")
            return
        
        results = st.session_state.evaluation_results
        model_name = results['model_name']
        file_names = results['file_names']
        enable_multi_file = results['enable_multi_file']
        
        # 显示单文件结果
        self._display_single_file_results(model_name, file_names)
        
        # 如果有多个文件，显示多文件汇总结果
        if enable_multi_file and len(file_names) > 1:
            st.markdown("---")
            self._display_multi_file_results(model_name)
        
        # 重新开始测评按钮
        st.markdown("---")
        self._render_restart_button()
    
    def _display_single_file_results(self, model_name: str, file_names: List[str]):
        """显示单文件结果"""
        st.subheader("📄 单文件分析结果")
        
        # 如果有多个文件，使用选项卡显示
        if len(file_names) > 1:
            tabs = st.tabs([f"📄 {name}" for name in file_names])
            
            for i, (tab, file_name) in enumerate(zip(tabs, file_names)):
                with tab:
                    self._display_file_analysis(model_name, file_name)
        else:
            # 单个文件直接显示
            file_name = file_names[0]
            self._display_file_analysis(model_name, file_name)
    
    def _display_file_analysis(self, model_name: str, file_name: str):
        """显示单个文件的分析结果"""
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.error(f"❌ 未找到模型 {model_name} 的时间戳目录")
            return

        # 读取分析文件
        analysis_path = timestamped_dir / file_name / f"{file_name}_analysis.json"

        if not analysis_path.exists():
            st.error(f"❌ 未找到文件 {file_name} 的分析结果")
            return

        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    st.error(f"❌ 分析文件 {analysis_path} 为空")
                    return
                analysis_data = json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"❌ 分析文件格式错误: {str(e)}")
            st.error(f"文件路径: {analysis_path}")
            return
        except Exception as e:
            st.error(f"❌ 读取分析文件失败: {str(e)}")
            st.error(f"文件路径: {analysis_path}")
            return

        # 显示下载按钮（在表格上方）
        self._render_single_file_download(model_name, file_name, analysis_data, timestamped_dir)

        # 显示智能分析报告（可折叠）- 暂时禁用
        # with st.expander("📋 查看智能分析报告", expanded=False):
        #     try:
        #         report_md = self.report_generator.generate_analysis_report(analysis_data)
        #         st.markdown(report_md)
        #     except Exception as e:
        #         st.error(f"❌ 生成报告失败: {str(e)}")

        # 显示分析表格
        self._display_analysis_table(analysis_data, f"{file_name} 分析结果")

        # 显示可视化图片
        self._display_visualizations(model_name, file_name)
    
    def _display_multi_file_results(self, model_name: str):
        """显示多文件汇总结果"""
        st.subheader("📊 多文件汇总分析")
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.error(f"❌ 未找到模型 {model_name} 的时间戳目录")
            return
        
        # 读取多文件汇总分析
        multi_analysis_path = timestamped_dir / "multi_file" / "multi_analysis.json"
        
        if not multi_analysis_path.exists():
            st.error("❌ 未找到多文件汇总分析结果")
            return
        
        try:
            with open(multi_analysis_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    st.error(f"❌ 多文件汇总分析文件为空")
                    return
                multi_analysis_data = json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"❌ 多文件汇总分析文件格式错误: {str(e)}")
            st.error(f"文件路径: {multi_analysis_path}")
            return
        except Exception as e:
            st.error(f"❌ 读取多文件汇总分析失败: {str(e)}")
            st.error(f"文件路径: {multi_analysis_path}")
            return
        
        # 显示汇总分析表格（不显示评估类型）
        self._display_multi_file_analysis_table(multi_analysis_data, "多文件汇总分析结果")
        
        # 显示下载按钮
        self._render_complete_download(model_name, file_names)

        # 显示多文件汇总可视化图片
        self._display_multi_file_visualizations(model_name)

    def _render_single_file_download(self, model_name: str, file_name: str,
                                     analysis_data: Dict[str, Any], timestamped_dir: Path):
        """渲染单个文件的下载按钮"""
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            # 下载分析报告 - 暂时禁用
            # try:
            #     report_md = self.report_generator.generate_analysis_report(analysis_data)
            #     st.download_button(
            #         label="📄 下载分析报告 (Markdown)",
            #         data=report_md,
            #         file_name=f"{file_name}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            #         mime="text/markdown",
            #         use_container_width=True,
            #         key=f"download_report_{file_name}"
            #     )
            # except Exception as e:
            #     st.error(f"❌ 生成报告失败: {str(e)}")
            # 下载HTML评估表
            try:
                # 获取评估参数
                evaluation_params = st.session_state.get('evaluation_params', {})

                # 生成HTML报告
                html_content = self.html_report_generator.generate_report(
                    analysis_data, evaluation_params
                )

                st.download_button(
                    label="📋 下载评估表 (HTML)",
                    data=html_content,
                    file_name=f"{file_name}_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"download_html_{file_name}"
                )
            except Exception as e:
                st.error(f"❌ 生成HTML报告失败: {str(e)}")

        with col2:
            # 下载原始数据
            try:
                st.download_button(
                    label="📊 下载原始数据 (JSON)",
                    data=json.dumps(analysis_data, ensure_ascii=False, indent=2),
                    file_name=f"{file_name}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"download_json_{file_name}"
                )
            except Exception as e:
                st.error(f"❌ 下载数据失败: {str(e)}")

        st.markdown("---")

    def _render_complete_download(self, model_name: str, file_names: List[str]):
        """渲染完整打包下载按钮"""
        st.markdown("---")
        st.subheader("📦 下载完整评估包")
        st.write("下载包含所有报告、数据和可视化图表的完整ZIP文件")

        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.error("❌ 未找到时间戳目录")
            return

        try:
            zip_buffer = self.report_generator.create_download_package(
                model_name, file_names, timestamped_dir
            )

            st.download_button(
                label="📥 下载完整评估包 (ZIP)",
                data=zip_buffer,
                file_name=f"{model_name}_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True,
                key="download_complete_package"
            )
        except Exception as e:
            st.error(f"❌ 创建下载包失败: {str(e)}")

        st.markdown("---")

    def _display_analysis_table(self, analysis_data: Dict[str, Any], title: str):
        """显示分析结果表格"""
        st.write(f"**{title}**")
        
        # 检查是否为多轮评估
        evaluation_info = analysis_data.get('evaluation_info', {})
        is_multi_round = evaluation_info.get('is_multi_round_evaluation', False)
        
        # 显示重要信息（大字体）
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 显示文件名称（如果存在）
            if 'file_name' in analysis_data:
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                           f"<p style='font-size: 18px; font-weight: bold; margin: 0; color: #1f77b4;'>📄 文件名称</p>"
                           f"<p style='font-size: 16px; margin: 5px 0 0 0; color: #333;'>{analysis_data.get('file_name', 'N/A')}</p>"
                           f"</div>", unsafe_allow_html=True)
        
        with col2:
            # 显示文件数量（如果存在）
            if 'file_count' in analysis_data:
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                           f"<p style='font-size: 18px; font-weight: bold; margin: 0; color: #1f77b4;'>📊 文件数量</p>"
                           f"<p style='font-size: 16px; margin: 5px 0 0 0; color: #333;'>{analysis_data.get('file_count', 'N/A')}</p>"
                           f"</div>", unsafe_allow_html=True)
        
        with col3:
            # 第三列留空或显示其他信息
            pass
        
        # 轮次信息已删除
        
        # 显示基本统计表格
        self._display_basic_statistics_table(analysis_data)
        
        # 如果是多轮评估，显示详细轮次表格
        if is_multi_round:
            self._display_round_details_table(analysis_data)
    

    
    def _display_basic_statistics_table(self, analysis_data: Dict[str, Any]):
        """显示基本统计表格"""
        st.write("**📊 最终统计结果**")
        
        # 创建表格数据
        table_data = []
        
        # 基本信息
        table_data.append(["模型名称", analysis_data.get('model_name', 'N/A')])
        
        if 'processed_files' in analysis_data:
            files_str = ", ".join(analysis_data['processed_files'])
            table_data.append(["处理文件", files_str])
        
        # 分隔线
        table_data.append(["---", "---"])
        
        # 统计结果
        table_data.append(["正确回答数", str(analysis_data.get('final_correct_answers', 0))])
        table_data.append(["推理错误数", str(analysis_data.get('final_reasoning_errors', 0))])
        table_data.append(["知识缺失数", str(analysis_data.get('final_knowledge_deficiency', 0))])
        table_data.append(["能力不足数", str(analysis_data.get('final_capability_insufficient', 0))])
        
        # 分隔线
        table_data.append(["---", "---"])
        
        # 比例统计
        table_data.append(["正确率", f"{analysis_data.get('final_accuracy_rate', 0):.2f}%"])
        table_data.append(["推理错误率", f"{analysis_data.get('final_reasoning_error_rate', 0):.2f}%"])
        table_data.append(["知识缺失率", f"{analysis_data.get('final_knowledge_deficiency_rate', 0):.2f}%"])
        table_data.append(["能力不足率", f"{analysis_data.get('final_capability_insufficient_rate', 0):.2f}%"])
        
        # 创建DataFrame并显示
        df = pd.DataFrame(table_data, columns=["指标", "值"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def _display_round_details_table(self, analysis_data: Dict[str, Any]):
        """显示轮次详细信息表格"""
        st.write("**🔍 各轮次详细结果**")
        
        # 检查是否为多轮评估
        evaluation_info = analysis_data.get('evaluation_info', {})
        is_multi_round = evaluation_info.get('is_multi_round_evaluation', False)
        
        if not is_multi_round:
            st.info("📝 当前为单轮评估，无轮次详细数据")
            return
        
        # 获取文件信息
        model_name = analysis_data.get('model_name')
        file_name = analysis_data.get('file_name')
        
        if not model_name or not file_name:
            st.info("📝 缺少必要的文件信息，无法显示轮次详情")
            return
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.error(f"❌ 未找到模型 {model_name} 的时间戳目录")
            return
        
        base_dir = timestamped_dir / file_name
        
        # 创建选项卡来分别显示Stage1和Stage2的轮次详情
        stage_tabs = []
        stage_data = []
        
        # 检查Stage1多轮分析文件
        stage1_multi_path = base_dir / "stage1_multi_round_analysis.json"
        if stage1_multi_path.exists():
            try:
                with open(stage1_multi_path, 'r', encoding='utf-8') as f:
                    stage1_data = json.load(f)
                if stage1_data and stage1_data.get('individual_results'):
                    stage_tabs.append("📊 Stage1 轮次详情")
                    stage_data.append(('stage1', stage1_data))
            except Exception as e:
                st.warning(f"⚠️ 读取Stage1多轮分析文件失败: {str(e)}")
        
        # 检查Stage2多轮分析文件
        stage2_multi_path = base_dir / "stage2_multi_round_analysis.json"
        if stage2_multi_path.exists():
            try:
                with open(stage2_multi_path, 'r', encoding='utf-8') as f:
                    stage2_data = json.load(f)
                if stage2_data and stage2_data.get('individual_results'):
                    stage_tabs.append("📊 Stage2 轮次详情")
                    stage_data.append(('stage2', stage2_data))
            except Exception as e:
                st.warning(f"⚠️ 读取Stage2多轮分析文件失败: {str(e)}")
        
        if not stage_tabs:
            st.info("📝 暂无详细轮次数据")
            return
        
        # 创建选项卡
        tabs = st.tabs(stage_tabs)
        
        for tab, (stage_name, data) in zip(tabs, stage_data):
            with tab:
                self._display_stage_round_table(stage_name, data)
    
    def _display_stage_round_table(self, stage_name: str, stage_data: Dict[str, Any]):
        """显示特定阶段的轮次表格"""
        individual_results = stage_data.get('individual_results', [])
        
        if not individual_results:
            st.info(f"📝 {stage_name.upper()} 暂无轮次数据")
            return
        
        # 准备表格数据
        round_table_data = []
        
        for result in individual_results:
            round_num = result.get('round_number', 'N/A')
            stats = result.get('statistics', {})
            score_dist = result.get('score_distribution', {})
            timestamp = result.get('evaluation_timestamp', 'N/A')
            
            if stage_name == 'stage1':
                # Stage1 的统计字段
                correct = stats.get('correct_answers', 0)
                reasoning_errors = stats.get('reasoning_errors', 0)
                need_retest = stats.get('need_retest', 0)
                accuracy_rate = stats.get('accuracy_rate', 0)
                
                round_table_data.append([
                    f"第{round_num}轮",
                    str(correct),
                    str(reasoning_errors),
                    str(need_retest),
                    f"{accuracy_rate:.2f}%",
                    f"{score_dist.get('avg_answer_score', 0):.2f}",
                    f"{score_dist.get('avg_reasoning_score', 0):.2f}",
                    timestamp.split(' ')[0] if timestamp != 'N/A' else 'N/A'
                ])
            
            elif stage_name == 'stage2':
                # Stage2 的统计字段
                knowledge_def = stats.get('knowledge_deficiency', 0)
                reasoning_errors = stats.get('reasoning_errors', 0)
                capability_insuf = stats.get('capability_insufficient', 0)
                knowledge_rate = stats.get('knowledge_deficiency_rate', 0)
                
                round_table_data.append([
                    f"第{round_num}轮",
                    str(knowledge_def),
                    str(reasoning_errors),
                    str(capability_insuf),
                    f"{knowledge_rate:.2f}%",
                    f"{score_dist.get('avg_answer_score', 0):.2f}",
                    f"{score_dist.get('avg_reasoning_score', 0):.2f}",
                    timestamp.split(' ')[0] if timestamp != 'N/A' else 'N/A'
                ])
        
        # 创建DataFrame
        if stage_name == 'stage1':
            columns = ["轮次", "正确回答", "推理错误", "需要重测", "准确率", "平均答案分数", "平均推理分数", "评估日期"]
        else:  # stage2
            columns = ["轮次", "知识缺失", "推理错误", "能力不足", "知识缺失率", "平均答案分数", "平均推理分数", "评估日期"]
        
        df = pd.DataFrame(round_table_data, columns=columns)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 显示方差统计（如果存在）
        self._display_variance_statistics(stage_name, stage_data)
    
    def _display_visualizations(self, model_name: str, file_name: str):
        """显示单文件的可视化图片"""
        st.write("**📈 可视化图表**")
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.warning("⚠️ 未找到时间戳目录")
            return
        
        # 图片在时间戳目录/文件名目录/visualizations下
        viz_dir = timestamped_dir / file_name / "visualizations"
        
        if not viz_dir.exists():
            st.warning("⚠️ 未找到可视化图片目录")
            return
        
        # 查找图片文件
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(viz_dir.glob(ext))
        
        if not image_files:
            st.warning("⚠️ 未找到可视化图片")
            return
        
        # 显示图片
        cols = st.columns(2)
        
        for i, image_path in enumerate(sorted(image_files)):
            try:
                image = Image.open(image_path)
                col_idx = i % 2
                
                with cols[col_idx]:
                    st.image(image, width=None)
                    # 使用自定义HTML显示更大的文件名标签
                    st.markdown(f"<p style='text-align: center; font-size: 16px; font-weight: bold; margin-top: 5px; color: #333;'>{image_path.stem}</p>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"❌ 无法显示图片 {image_path.name}: {str(e)}")
    
    def _display_multi_file_visualizations(self, model_name: str):
        """显示多文件汇总的可视化图片"""
        st.write("**📈 多文件汇总可视化图表**")
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            st.warning("⚠️ 未找到时间戳目录")
            return
        
        # 多文件汇总图片在multi_file目录下的visualizations
        viz_dir = timestamped_dir / "multi_file" / "visualizations"
        
        if not viz_dir.exists():
            st.warning("⚠️ 未找到多文件汇总可视化图片目录")
            return
        
        # 查找图片文件
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(viz_dir.glob(ext))
        
        if not image_files:
            st.warning("⚠️ 未找到多文件汇总可视化图片")
            return
        
        # 显示图片
        cols = st.columns(2)
        
        for i, image_path in enumerate(sorted(image_files)):
            try:
                image = Image.open(image_path)
                col_idx = i % 2
                
                with cols[col_idx]:
                    st.image(image, width=None)
                    # 使用自定义HTML显示更大的文件名标签
                    st.markdown(f"<p style='text-align: center; font-size: 16px; font-weight: bold; margin-top: 5px; color: #333;'>{image_path.stem}</p>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"❌ 无法显示图片 {image_path.name}: {str(e)}")
    
    def _render_restart_button(self):
        """渲染重新开始测评按钮（带确认对话框）"""
        st.subheader("🔄 重新开始")

        st.write("点击下方按钮重新开始测评（将清除当前所有评估数据）")

        # 添加确认机制
        if 'show_restart_confirmation' not in st.session_state:
            st.session_state.show_restart_confirmation = False

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            if not st.session_state.show_restart_confirmation:
                # 第一步：点击按钮显示确认提示
                if st.button("🔄 重新开始测评", type="primary", use_container_width=True, key="restart_evaluation_button"):
                    st.session_state.show_restart_confirmation = True
                    st.rerun()
            else:
                # 第二步：显示确认对话框
                st.warning("⚠️ 确认要重新开始吗？这将清除当前所有评估数据和配置。")

                confirm_col1, confirm_col2 = st.columns(2)

                with confirm_col1:
                    if st.button("✅ 确认重新开始", type="primary", use_container_width=True, key="confirm_restart"):
                        # 获取当前模型名称并重置FileManager的时间戳
                        current_model = st.session_state.get('selected_model', '')
                        if current_model:
                            reset_file_manager_for_new_test(current_model)

                        # 清除所有session state
                        keys_to_clear = [
                            'evaluation_params', 'evaluation_started', 'evaluation_running',
                            'evaluation_completed', 'evaluation_results', 'selected_files',
                            'newly_uploaded_files', 'current_timestamp', 'timestamped_model_name',
                            'info_completed', 'evaluation_info', 'selected_model',
                            'show_restart_confirmation'
                        ]

                        for key in keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]

                        # 清除文件选择状态
                        keys_to_remove = []
                        for key in st.session_state.keys():
                            if key.startswith('file_'):
                                keys_to_remove.append(key)

                        for key in keys_to_remove:
                            del st.session_state[key]

                        # 设置重置标志，让file_upload界面显示信息填写界面
                        st.session_state.reset_to_initial_upload = True
                        st.session_state.show_info_form_in_upload = True

                        st.success("✅ 已重置所有状态，请重新配置评估参数")
                        st.info("💡 下次开始新测试时将生成新的时间戳目录")
                        st.info("🔄 请切换到「文件上传」选项卡，首先重新填写评估信息")
                        st.rerun()

                with confirm_col2:
                    if st.button("❌ 取消", use_container_width=True, key="cancel_restart"):
                        st.session_state.show_restart_confirmation = False
                        st.rerun()
    
    def _get_file_info_summary(self, model_name: str, file_names: List[str]) -> Dict[str, Any]:
        """获取文件信息摘要"""
        summary = {
            'total_files': len(file_names),
            'successful_files': 0,
            'failed_files': 0,
            'total_questions': 0,
            'total_correct': 0,
            'files_detail': []
        }
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            return summary
        
        for file_name in file_names:
            analysis_path = timestamped_dir / file_name / f"{file_name}_analysis.json"
            
            file_info = {
                'name': file_name,
                'status': 'success' if analysis_path.exists() else 'failed',
                'questions': 0,
                'correct': 0,
                'accuracy': 0.0
            }
            
            if analysis_path.exists():
                try:
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            continue  # 跳过空文件
                        data = json.loads(content)
                    
                    correct = data.get('final_correct_answers', 0)
                    reasoning_errors = data.get('final_reasoning_errors', 0)
                    knowledge_deficiency = data.get('final_knowledge_deficiency', 0)
                    capability_insufficient = data.get('final_capability_insufficient', 0)
                    
                    total_q = correct + reasoning_errors + knowledge_deficiency + capability_insufficient
                    
                    file_info.update({
                        'questions': total_q,
                        'correct': correct,
                        'accuracy': (correct / total_q * 100) if total_q > 0 else 0.0
                    })
                    
                    summary['successful_files'] += 1
                    summary['total_questions'] += total_q
                    summary['total_correct'] += correct
                    
                except Exception:
                    file_info['status'] = 'failed'
                    summary['failed_files'] += 1
            else:
                summary['failed_files'] += 1
            
            summary['files_detail'].append(file_info)
        
        return summary
    
    def _display_multi_file_analysis_table(self, analysis_data: Dict[str, Any], title: str):
        """显示多文件汇总分析结果表格（不显示评估类型）"""
        st.write(f"**{title}**")
        
        # 显示重要信息（大字体）- 只显示文件名称和文件数量
        col1, col2 = st.columns(2)
        
        with col1:
            # 显示处理的文件列表
            if 'processed_files' in analysis_data:
                files_str = ", ".join(analysis_data['processed_files'])
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                           f"<p style='font-size: 18px; font-weight: bold; margin: 0; color: #1f77b4;'>📄 处理文件</p>"
                           f"<p style='font-size: 16px; margin: 5px 0 0 0; color: #333;'>{files_str}</p>"
                           f"</div>", unsafe_allow_html=True)
        
        with col2:
            # 显示文件数量
            if 'file_count' in analysis_data:
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                           f"<p style='font-size: 18px; font-weight: bold; margin: 0; color: #1f77b4;'>📊 文件数量</p>"
                           f"<p style='font-size: 16px; margin: 5px 0 0 0; color: #333;'>{analysis_data.get('file_count', 'N/A')}</p>"
                           f"</div>", unsafe_allow_html=True)
        
        # 显示基本统计表格
        self._display_basic_statistics_table(analysis_data)
    
    def _display_variance_statistics(self, stage_name: str, stage_data: Dict[str, Any]):
        """显示方差统计信息"""
        evaluation_summary = stage_data.get('evaluation_summary', {})
        
        if not evaluation_summary:
            return
        
        st.write(f"**📈 {stage_name.upper()} 轮次统计分析**")
        
        col1, col2, col3 = st.columns(3)
        
        # 最佳轮次
        best_round = evaluation_summary.get('best_round', {})
        if best_round:
            with col1:
                st.metric(
                    "最佳轮次", 
                    f"第{best_round.get('round', 'N/A')}轮",
                    help="基于主要指标的最佳表现轮次"
                )
        
        # 最差轮次
        worst_round = evaluation_summary.get('worst_round', {})
        if worst_round:
            with col2:
                st.metric(
                    "最差轮次", 
                    f"第{worst_round.get('round', 'N/A')}轮",
                    help="基于主要指标的最差表现轮次"
                )
        
        # 最稳定指标
        stable_metric = evaluation_summary.get('most_stable_metric', 'N/A')
        if stable_metric != 'N/A':
            with col3:
                metric_names = {
                    'accuracy_rate': '准确率',
                    'reasoning_error_rate': '推理错误率',
                    'retest_rate': '重测率',
                    'knowledge_deficiency_rate': '知识缺失率',
                    'capability_insufficient_rate': '能力不足率'
                }
                display_name = metric_names.get(stable_metric, stable_metric)
                st.metric(
                    "最稳定指标", 
                    display_name,
                    help="标准差最小的评估指标"
                )