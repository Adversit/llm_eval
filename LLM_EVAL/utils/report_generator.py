import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import io
import pandas as pd


class ReportGenerator:
    """评估报告生成器"""

    def __init__(self):
        pass

    def generate_analysis_report(self, analysis_data: Dict[str, Any]) -> str:
        """生成智能分析报告

        Args:
            analysis_data: 分析数据

        Returns:
            str: Markdown格式的分析报告
        """
        report = []

        # 标题
        report.append("# 📊 LLM-as-judge 评估分析报告\n")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n")

        # 基本信息
        report.append("## 📋 基本信息\n")
        report.append(f"- **模型名称**: {analysis_data.get('model_name', 'N/A')}")
        report.append(f"- **文件名称**: {analysis_data.get('file_name', 'N/A')}")

        eval_info = analysis_data.get('evaluation_info', {})
        if eval_info:
            rounds = eval_info.get('evaluation_rounds', 1)
            # 根据实际轮次判断：轮次大于1才是多轮评估
            is_multi_round = rounds > 1
            report.append(f"- **评估模式**: {'多轮评估' if is_multi_round else '单轮评估'}")
            if is_multi_round:
                report.append(f"- **评估轮次**: {rounds} 轮")

        report.append("\n---\n")

        # 整体表现
        report.append("## 🎯 整体表现总结\n")

        total_questions = analysis_data.get('total_questions', 0)
        correct_answers = analysis_data.get('final_correct_answers', 0)
        reasoning_errors = analysis_data.get('final_reasoning_errors', 0)
        knowledge_deficiency = analysis_data.get('final_knowledge_deficiency', 0)
        capability_insufficient = analysis_data.get('final_capability_insufficient', 0)

        accuracy_rate = analysis_data.get('final_accuracy_rate', 0)

        report.append(f"### 📈 关键指标\n")
        report.append(f"- **总问题数**: {total_questions}")
        report.append(f"- **正确回答**: {correct_answers} ({accuracy_rate:.2f}%)")
        report.append(f"- **推理错误**: {reasoning_errors}")
        report.append(f"- **知识缺失**: {knowledge_deficiency}")
        report.append(f"- **能力不足**: {capability_insufficient}\n")

        # 性能等级评估
        report.append("### ⭐ 性能等级\n")
        performance_level = self._get_performance_level(accuracy_rate)
        report.append(f"**{performance_level['emoji']} {performance_level['level']}**\n")
        report.append(f"_{performance_level['description']}_\n")

        report.append("\n---\n")

        # 详细分析
        report.append("## 🔍 详细分析\n")

        # 优势分析
        report.append("### ✅ 优势表现\n")
        strengths = self._analyze_strengths(analysis_data)
        for strength in strengths:
            report.append(f"- {strength}")
        report.append("")

        # 问题分析
        report.append("### ⚠️ 问题分析\n")
        weaknesses = self._analyze_weaknesses(analysis_data)
        for weakness in weaknesses:
            report.append(f"- {weakness}")
        report.append("")

        # 改进建议
        report.append("### 💡 改进建议\n")
        suggestions = self._generate_suggestions(analysis_data)
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"{i}. {suggestion}")
        report.append("")

        report.append("\n---\n")

        # 阶段性分析
        report.append("## 📊 阶段性表现\n")

        # Stage1分析
        stage1_stats = analysis_data.get('stage1', {}).get('statistics', {})
        if stage1_stats:
            report.append("### Stage1 - 基础问答\n")
            report.append(f"- 正确率: {stage1_stats.get('accuracy_rate', 0):.2f}%")
            report.append(f"- 需要重测: {stage1_stats.get('need_retest', 0)} 题")
            report.append(f"- 重测率: {stage1_stats.get('retest_rate', 0):.2f}%\n")

        # Stage2分析
        stage2_stats = analysis_data.get('stage2', {}).get('statistics', {})
        if stage2_stats and stage2_stats.get('total_questions', 0) > 0:
            report.append("### Stage2 - 深度评估\n")
            report.append(f"- 处理问题: {stage2_stats.get('total_questions', 0)} 题")
            report.append(f"- 知识缺失: {stage2_stats.get('knowledge_deficiency', 0)} 题")
            report.append(f"- 推理错误: {stage2_stats.get('reasoning_errors', 0)} 题")
            report.append(f"- 能力不足: {stage2_stats.get('capability_insufficient', 0)} 题\n")

        report.append("\n---\n")

        # 结论
        report.append("## 📝 结论\n")
        conclusion = self._generate_conclusion(analysis_data)
        report.append(conclusion)
        report.append("\n")

        report.append("---\n")
        report.append("_本报告由 LLM-as-judge 评估系统自动生成_")

        return "\n".join(report)

    def _get_performance_level(self, accuracy_rate: float) -> Dict[str, str]:
        """根据准确率评定性能等级"""
        if accuracy_rate >= 90:
            return {
                'emoji': '🏆',
                'level': '卓越 (Excellent)',
                'description': '模型表现出色，准确率超过90%，达到了优秀水平。'
            }
        elif accuracy_rate >= 75:
            return {
                'emoji': '🥇',
                'level': '良好 (Good)',
                'description': '模型表现良好，准确率在75%-90%之间，有一定的提升空间。'
            }
        elif accuracy_rate >= 60:
            return {
                'emoji': '🥈',
                'level': '中等 (Fair)',
                'description': '模型表现中等，准确率在60%-75%之间，需要改进。'
            }
        elif accuracy_rate >= 40:
            return {
                'emoji': '🥉',
                'level': '及格 (Passing)',
                'description': '模型基本达到及格线，准确率在40%-60%之间，有较大改进空间。'
            }
        else:
            return {
                'emoji': '⚠️',
                'level': '需要改进 (Needs Improvement)',
                'description': '模型表现不佳，准确率低于40%，建议重点优化。'
            }

    def _analyze_strengths(self, analysis_data: Dict[str, Any]) -> List[str]:
        """分析优势"""
        strengths = []

        accuracy_rate = analysis_data.get('final_accuracy_rate', 0)
        reasoning_error_rate = analysis_data.get('final_reasoning_error_rate', 0)
        knowledge_deficiency_rate = analysis_data.get('final_knowledge_deficiency_rate', 0)

        if accuracy_rate >= 75:
            strengths.append(f"**高准确率**: 模型达到了 {accuracy_rate:.2f}% 的准确率，表现优秀")

        if reasoning_error_rate < 10:
            strengths.append(f"**推理能力强**: 推理错误率仅为 {reasoning_error_rate:.2f}%，逻辑推理能力突出")

        if knowledge_deficiency_rate < 15:
            strengths.append(f"**知识覆盖广**: 知识缺失率为 {knowledge_deficiency_rate:.2f}%，知识库较为完善")

        # Stage1表现
        stage1_accuracy = analysis_data.get('stage1', {}).get('statistics', {}).get('accuracy_rate', 0)
        if stage1_accuracy >= 70:
            strengths.append(f"**基础问答能力强**: Stage1准确率达到 {stage1_accuracy:.2f}%")

        if not strengths:
            strengths.append("模型在各项指标中表现稳定，具备基础的问答能力")

        return strengths

    def _analyze_weaknesses(self, analysis_data: Dict[str, Any]) -> List[str]:
        """分析问题"""
        weaknesses = []

        reasoning_error_rate = analysis_data.get('final_reasoning_error_rate', 0)
        knowledge_deficiency_rate = analysis_data.get('final_knowledge_deficiency_rate', 0)
        capability_insufficient_rate = analysis_data.get('final_capability_insufficient_rate', 0)
        accuracy_rate = analysis_data.get('final_accuracy_rate', 0)

        if accuracy_rate < 60:
            weaknesses.append(f"**准确率偏低**: 整体准确率仅为 {accuracy_rate:.2f}%，需要重点提升")

        if reasoning_error_rate > 20:
            weaknesses.append(f"**推理能力不足**: 推理错误率高达 {reasoning_error_rate:.2f}%，逻辑推理需要加强")
        elif reasoning_error_rate > 10:
            weaknesses.append(f"**推理错误较多**: 推理错误率为 {reasoning_error_rate:.2f}%，存在改进空间")

        if knowledge_deficiency_rate > 25:
            weaknesses.append(f"**知识覆盖不足**: 知识缺失率为 {knowledge_deficiency_rate:.2f}%，知识库需要扩充")
        elif knowledge_deficiency_rate > 15:
            weaknesses.append(f"**部分知识盲区**: 知识缺失率为 {knowledge_deficiency_rate:.2f}%，建议补充相关知识")

        if capability_insufficient_rate > 15:
            weaknesses.append(f"**能力限制**: 能力不足率为 {capability_insufficient_rate:.2f}%，模型能力需要提升")

        # Stage1重测率分析
        retest_rate = analysis_data.get('stage1', {}).get('statistics', {}).get('retest_rate', 0)
        if retest_rate > 30:
            weaknesses.append(f"**首轮通过率低**: Stage1重测率高达 {retest_rate:.2f}%，基础问答能力有待提高")

        if not weaknesses:
            weaknesses.append("未发现显著问题，模型整体表现良好")

        return weaknesses

    def _generate_suggestions(self, analysis_data: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        reasoning_error_rate = analysis_data.get('final_reasoning_error_rate', 0)
        knowledge_deficiency_rate = analysis_data.get('final_knowledge_deficiency_rate', 0)
        capability_insufficient_rate = analysis_data.get('final_capability_insufficient_rate', 0)
        accuracy_rate = analysis_data.get('final_accuracy_rate', 0)

        # 根据不同问题给出针对性建议
        if accuracy_rate < 60:
            suggestions.append("**整体优化**: 考虑使用更大规模的训练数据集，或升级到参数量更大的模型版本")

        if knowledge_deficiency_rate > 20:
            suggestions.append("**知识增强**: 扩充训练语料，特别是在知识缺失较多的领域补充专业知识")
            suggestions.append("**RAG集成**: 考虑集成检索增强生成（RAG）系统，动态补充外部知识")

        if reasoning_error_rate > 15:
            suggestions.append("**推理训练**: 增加逻辑推理和思维链（Chain-of-Thought）训练样本")
            suggestions.append("**提示词优化**: 优化prompt设计，引导模型进行更严谨的逻辑推理")

        if capability_insufficient_rate > 15:
            suggestions.append("**模型升级**: 考虑使用能力更强的模型或进行针对性的微调（Fine-tuning）")

        # 通用建议
        retest_rate = analysis_data.get('stage1', {}).get('statistics', {}).get('retest_rate', 0)
        if retest_rate > 25:
            suggestions.append("**基础能力强化**: Stage1重测率较高，建议重点提升基础问答能力")

        if accuracy_rate >= 75:
            suggestions.append("**持续监控**: 模型表现良好，建议持续监控性能，定期评估新数据集")
            suggestions.append("**边界测试**: 尝试更具挑战性的测试用例，探索模型的能力边界")

        if not suggestions:
            suggestions.append("模型表现稳定，建议继续保持当前训练策略")

        return suggestions

    def _generate_conclusion(self, analysis_data: Dict[str, Any]) -> str:
        """生成结论"""
        accuracy_rate = analysis_data.get('final_accuracy_rate', 0)
        total_questions = analysis_data.get('total_questions', 0)
        correct_answers = analysis_data.get('final_correct_answers', 0)

        conclusion = f"在本次评估中，模型共处理了 **{total_questions}** 个问题，"
        conclusion += f"正确回答了 **{correct_answers}** 个，整体准确率为 **{accuracy_rate:.2f}%**。"

        if accuracy_rate >= 75:
            conclusion += " 模型表现**良好**，已达到实用水平。"
        elif accuracy_rate >= 60:
            conclusion += " 模型表现**尚可**，但仍有较大提升空间。"
        else:
            conclusion += " 模型表现**需要改进**，建议重点优化。"

        # 主要问题总结
        reasoning_error_rate = analysis_data.get('final_reasoning_error_rate', 0)
        knowledge_deficiency_rate = analysis_data.get('final_knowledge_deficiency_rate', 0)

        main_issues = []
        if reasoning_error_rate > 15:
            main_issues.append("推理能力")
        if knowledge_deficiency_rate > 20:
            main_issues.append("知识覆盖")

        if main_issues:
            conclusion += f" 主要改进方向应聚焦在**{'、'.join(main_issues)}**方面。"

        return conclusion

    def create_download_package(self, model_name: str, file_names: List[str],
                               timestamped_dir: Path) -> io.BytesIO:
        """创建可下载的打包文件

        Args:
            model_name: 模型名称
            file_names: 文件名列表
            timestamped_dir: 时间戳目录

        Returns:
            io.BytesIO: ZIP文件的字节流
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 添加分析报告
            for file_name in file_names:
                analysis_path = timestamped_dir / file_name / f"{file_name}_analysis.json"
                if analysis_path.exists():
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)

                    # 生成Markdown报告
                    report_md = self.generate_analysis_report(analysis_data)
                    zip_file.writestr(f"reports/{file_name}_report.md", report_md)

                    # 添加原始JSON
                    zip_file.write(analysis_path, f"data/{file_name}_analysis.json")

            # 添加可视化图片
            for file_name in file_names:
                viz_dir = timestamped_dir / file_name / "visualizations"
                if viz_dir.exists():
                    for img_file in viz_dir.glob("*.png"):
                        zip_file.write(img_file, f"visualizations/{file_name}/{img_file.name}")

            # 添加多文件汇总（如果存在）
            multi_file_dir = timestamped_dir / "multi_file"
            if multi_file_dir.exists():
                multi_analysis = multi_file_dir / "multi_analysis.json"
                if multi_analysis.exists():
                    zip_file.write(multi_analysis, "data/multi_file_analysis.json")

                multi_viz = multi_file_dir / "visualizations"
                if multi_viz.exists():
                    for img_file in multi_viz.glob("*.png"):
                        zip_file.write(img_file, f"visualizations/multi_file/{img_file.name}")

            # 添加README
            readme = self._generate_readme(model_name, file_names)
            zip_file.writestr("README.md", readme)

        zip_buffer.seek(0)
        return zip_buffer

    def _generate_readme(self, model_name: str, file_names: List[str]) -> str:
        """生成README文件"""
        readme = []
        readme.append("# LLM-as-judge 评估报告包\n")
        readme.append(f"**模型名称**: {model_name}")
        readme.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        readme.append(f"**文件数量**: {len(file_names)}\n")

        readme.append("## 📁 文件结构\n")
        readme.append("```")
        readme.append("├── README.md                 # 本文件")
        readme.append("├── reports/                  # 分析报告（Markdown格式）")
        for file_name in file_names:
            readme.append(f"│   └── {file_name}_report.md")
        readme.append("├── data/                     # 原始数据（JSON格式）")
        for file_name in file_names:
            readme.append(f"│   ├── {file_name}_analysis.json")
        readme.append("│   └── multi_file_analysis.json  # 多文件汇总")
        readme.append("└── visualizations/           # 可视化图表")
        for file_name in file_names:
            readme.append(f"    └── {file_name}/")
        readme.append("        └── multi_file/       # 多文件汇总图表")
        readme.append("```\n")

        readme.append("## 📖 使用说明\n")
        readme.append("1. **查看报告**: 打开 `reports/` 目录下的 Markdown 文件")
        readme.append("2. **查看数据**: `data/` 目录包含完整的JSON数据")
        readme.append("3. **查看图表**: `visualizations/` 目录包含所有可视化图表\n")

        readme.append("## 📊 报告说明\n")
        readme.append("每个报告包含以下内容：")
        readme.append("- 📋 基本信息")
        readme.append("- 🎯 整体表现总结")
        readme.append("- 🔍 详细分析（优势、问题、建议）")
        readme.append("- 📊 阶段性表现")
        readme.append("- 📝 结论\n")

        readme.append("---")
        readme.append("_由 LLM-as-judge 评估系统生成_")

        return "\n".join(readme)
