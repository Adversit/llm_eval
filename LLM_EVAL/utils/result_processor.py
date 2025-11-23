import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from .file_manager_singleton import get_file_manager
from .json_serializer import safe_json_dump

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResultProcessor:
    """结果处理器 - 综合Stage1和Stage2的分析结果"""
    
    def __init__(self):
        """初始化结果处理器"""
        self.file_manager = get_file_manager()
        logger.info("ResultProcessor初始化完成")
    
    def process_single_file_results(self, model_name: str, file_name: str) -> Dict[str, Any]:
        """处理单个文件的Stage1和Stage2结果，生成综合分析
        
        Args:
            model_name: 模型名称
            file_name: 文件名称
            
        Returns:
            Dict: 综合分析结果
        """
        logger.info(f"开始处理单文件结果 - 模型: {model_name}, 文件: {file_name}")
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        # 构建文件路径
        base_dir = timestamped_dir / file_name
        unified_analysis_path = base_dir / f"{file_name}_analysis.json"
        
        # 优先逻辑：检查是否有轮次分析文件，如果有则从轮次文件重新计算
        round_analysis_files = list(base_dir.glob(f"{file_name}_analysis_round_*.json"))
        if round_analysis_files:
            logger.info(f"发现 {len(round_analysis_files)} 个轮次分析文件，从轮次文件重新计算平均值")
            return self._aggregate_round_analyses(round_analysis_files, unified_analysis_path)
        
        # 检查是否已经存在统一的分析文件（仅在没有轮次文件时使用）
        if unified_analysis_path.exists():
            logger.info(f"发现已存在的统一分析文件（无轮次文件）: {unified_analysis_path}")
            return self._load_json_file(unified_analysis_path)
        
        # 旧逻辑：尝试从单独的stage1和stage2文件生成（兼容性）
        stage1_path = base_dir / "stage1_analysis.json"
        stage2_path = base_dir / "stage2_analysis.json"
        
        stage1_data = self._load_json_file(stage1_path)
        stage2_data = self._load_json_file(stage2_path)
        
        if not stage1_data:
            # 尝试从多轮分析文件生成
            return self._generate_from_multi_round_files(base_dir, file_name, unified_analysis_path)
        
        # 检查是否为多轮评估
        is_multi_round = stage1_data.get("evaluation_rounds", 0) > 1
        
        # 生成综合分析
        combined_analysis = self._combine_stage_results(stage1_data, stage2_data, is_multi_round)
        
        # 保存综合分析结果
        self._save_json_file(combined_analysis, unified_analysis_path)
        
        logger.info(f"单文件综合分析完成，结果保存到: {unified_analysis_path}")
        return combined_analysis
    
    def process_multi_file_results(self, model_name: str, enable_multi_file: bool = True) -> Optional[Dict[str, Any]]:
        """处理多个文件的结果，生成汇总分析
        
        Args:
            model_name: 模型名称
            enable_multi_file: 是否启用多文件处理
            
        Returns:
            Dict: 汇总分析结果，如果未启用则返回None
        """
        if not enable_multi_file:
            logger.info("多文件处理未启用，跳过")
            return None
        logger.info(f"开始处理多文件结果 - 模型: {model_name}")
        
        # 使用FileManager查找最新的时间戳目录
        model_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not model_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        # 收集所有文件的分析结果
        all_analyses = []
        file_names = []
        
        for item in model_dir.iterdir():
            if item.is_dir() and item.name != "multi_file":
                file_name = item.name
                analysis_file = item / f"{file_name}_analysis.json"
                
                if analysis_file.exists():
                    analysis_data = self._load_json_file(analysis_file)
                    if analysis_data:
                        all_analyses.append(analysis_data)
                        file_names.append(file_name)
                        logger.info(f"加载文件分析: {file_name}")
                else:
                    # 如果综合分析文件不存在，尝试生成
                    logger.info(f"综合分析文件不存在，尝试生成: {file_name}")
                    try:
                        analysis_data = self.process_single_file_results(model_name, file_name)
                        all_analyses.append(analysis_data)
                        file_names.append(file_name)
                    except Exception as e:
                        logger.warning(f"无法生成文件 {file_name} 的综合分析: {e}")
        
        if not all_analyses:
            raise ValueError(f"未找到任何有效的分析文件在模型目录: {model_name}")
        
        # 生成多文件汇总分析
        multi_analysis = self._aggregate_multi_file_results(all_analyses, file_names, model_name)
        
        # 保存汇总分析结果
        if model_dir:
            multi_dir = model_dir / "multi_file"
            multi_dir.mkdir(exist_ok=True)
            output_path = multi_dir / "multi_analysis.json"
            self._save_json_file(multi_analysis, output_path)
        else:
            raise FileNotFoundError(f"无法找到模型目录: {model_name}")
        
        logger.info(f"多文件汇总分析完成，结果保存到: {output_path}")
        return multi_analysis
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: JSON数据，如果文件不存在或读取失败返回None
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"文件不存在: {file_path}")
                return None
        except Exception as e:
            logger.error(f"读取JSON文件失败 {file_path}: {e}")
            return None
    
    def _save_json_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """保存JSON文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                safe_json_dump(data, f)
        except Exception as e:
            logger.error(f"保存JSON文件失败 {file_path}: {e}")
            raise
    
    def _combine_stage_results(self, stage1_data: Dict[str, Any], 
                              stage2_data: Optional[Dict[str, Any]], 
                              is_multi_round: bool = False) -> Dict[str, Any]:
        """合并Stage1和Stage2的分析结果
        
        Args:
            stage1_data: Stage1分析数据
            stage2_data: Stage2分析数据（可能为None）
            
        Returns:
            Dict: 综合分析结果（简化版，只保留绘图需要的关键信息）
        """
        logger.info("开始合并Stage1和Stage2结果")
        
        # 生成综合统计信息
        combined_stats = self._generate_combined_statistics(stage1_data, stage2_data, is_multi_round)
        
        # 简化的综合结果，保留绘图需要的关键信息
        combined = {
            "model_name": stage1_data.get("model_name", ""),
            "file_name": stage1_data.get("file_name", ""),
            "thresholds": combined_stats["thresholds"],
            "final_correct_answers": combined_stats["final_correct_answers"],
            "final_reasoning_errors": combined_stats["final_reasoning_errors"],
            "final_knowledge_deficiency": combined_stats["final_knowledge_deficiency"],
            "final_capability_insufficient": combined_stats["final_capability_insufficient"],
            "final_accuracy_rate": combined_stats["final_accuracy_rate"],
            "final_reasoning_error_rate": combined_stats["final_reasoning_error_rate"],
            "final_knowledge_deficiency_rate": combined_stats["final_knowledge_deficiency_rate"],
            "final_capability_insufficient_rate": combined_stats["final_capability_insufficient_rate"]
        }
        
        # 添加兼容的statistics字段，供评估流程使用
        if is_multi_round:
            # 多轮评估：从aggregated_statistics提取
            stage1_stats = stage1_data.get("aggregated_statistics", {})
            combined["statistics"] = {
                "total_questions": stage1_stats.get("total_questions", 0),
                "correct_answers": stage1_stats.get("avg_correct_answers", 0),
                "reasoning_errors": stage1_stats.get("avg_reasoning_errors", 0),
                "need_retest": stage1_stats.get("avg_need_retest", 0),
                "accuracy_rate": stage1_stats.get("avg_accuracy_rate", 0),
                "reasoning_error_rate": stage1_stats.get("avg_reasoning_error_rate", 0),
                "retest_rate": stage1_stats.get("avg_retest_rate", 0)
            }
        else:
            # 单轮评估：直接使用statistics
            combined["statistics"] = stage1_data.get("statistics", {})
        
        # 添加评估信息
        if is_multi_round:
            combined["evaluation_info"] = {
                "is_multi_round_evaluation": True,
                "evaluation_rounds": combined_stats.get("evaluation_rounds", 1),
                "successful_rounds": combined_stats.get("successful_rounds", 1),
                "aggregation_timestamp": combined_stats.get("aggregation_timestamp"),
                "stage1_round_summary": self._extract_multi_round_summary(stage1_data),
                "stage2_round_summary": self._extract_multi_round_summary(stage2_data) if stage2_data else None
            }
            
            # 添加详细的多轮次数据
            combined["multi_round_details"] = {
                "stage1_all_rounds": self._extract_all_rounds_data(stage1_data),
                "stage2_all_rounds": self._extract_all_rounds_data(stage2_data) if stage2_data else None,
                "variance_statistics": {
                    "stage1_variance": stage1_data.get("variance_statistics", {}),
                    "stage2_variance": stage2_data.get("variance_statistics", {}) if stage2_data else {}
                },
                "round_summaries": {
                    "stage1_summaries": stage1_data.get("round_summaries", []),
                    "stage2_summaries": stage2_data.get("round_summaries", []) if stage2_data else []
                }
            }
        else:
            combined["evaluation_info"] = {
                "is_multi_round_evaluation": False,
                "evaluation_timestamp": stage1_data.get("evaluation_timestamp") or (stage2_data.get("evaluation_timestamp") if stage2_data else None),
                "stage1_info": self._extract_single_round_info(stage1_data),
                "stage2_info": self._extract_single_round_info(stage2_data) if stage2_data else None
            }
        
        return combined
    
    def _generate_combined_statistics(self, stage1_data: Dict[str, Any], 
                                    stage2_data: Optional[Dict[str, Any]], 
                                    is_multi_round: bool = False) -> Dict[str, Any]:
        """生成综合统计信息
        
        Args:
            stage1_data: Stage1分析数据
            stage2_data: Stage2分析数据
            
        Returns:
            Dict: 综合统计信息
        """
        # 根据是否为多轮评估选择不同的数据源
        if is_multi_round:
            # 多轮评估：使用汇总统计数据
            stage1_stats = stage1_data.get("aggregated_statistics", stage1_data.get("statistics", {}))
            total_questions = stage1_stats.get("total_questions", 0)
            
            # 从多轮评估数据中提取阈值
            if "individual_results" in stage1_data and stage1_data["individual_results"]:
                first_result = stage1_data["individual_results"][0]
                stage1_thresholds = first_result.get("thresholds", {
                    "answer_threshold": 6.0,
                    "reasoning_threshold": 6.0
                })
            else:
                stage1_thresholds = stage1_data.get("thresholds", {
                    "answer_threshold": 6.0,
                    "reasoning_threshold": 6.0
                })
        else:
            # 单轮评估：使用常规统计数据
            stage1_stats = stage1_data.get("statistics", {})
            total_questions = stage1_stats.get("total_questions", 0)
            stage1_thresholds = stage1_data.get("thresholds", {
                "answer_threshold": 6.0,
                "reasoning_threshold": 6.0
            })
        
        # 提取Stage2阈值信息（如果存在）
        stage2_thresholds = {
            "answer_threshold": 6.0,
            "reasoning_threshold": 6.0
        }
        if stage2_data:
            if is_multi_round and "individual_results" in stage2_data and stage2_data["individual_results"]:
                first_result = stage2_data["individual_results"][0]
                stage2_thresholds = first_result.get("thresholds", stage2_thresholds)
            else:
                stage2_thresholds = stage2_data.get("thresholds", stage2_thresholds)
        
        # 合并阈值信息
        thresholds = {
            "stage1": stage1_thresholds,
            "stage2": stage2_thresholds
        }
        
        # Stage1的统计（根据是否为多轮评估使用不同字段）
        if is_multi_round:
            correct_answers = stage1_stats.get("avg_correct_answers", stage1_stats.get("correct_answers", 0))
            reasoning_errors_stage1 = stage1_stats.get("avg_reasoning_errors", stage1_stats.get("reasoning_errors", 0))
            need_retest = stage1_stats.get("avg_need_retest", stage1_stats.get("need_retest", 0))
        else:
            correct_answers = stage1_stats.get("correct_answers", 0)
            reasoning_errors_stage1 = stage1_stats.get("reasoning_errors", 0)
            need_retest = stage1_stats.get("need_retest", 0)
        
        combined_stats = {
            "total_questions": total_questions,
            "thresholds": thresholds,
            "stage1_correct_answers": correct_answers,
            "stage1_reasoning_errors": reasoning_errors_stage1,
            "stage1_need_retest": need_retest,
        }
        
        # 如果是多轮评估，添加多轮特有的信息
        if is_multi_round:
            combined_stats.update({
                "evaluation_rounds": stage1_data.get("evaluation_rounds", 1),
                "successful_rounds": stage1_data.get("successful_rounds", 1),
                "aggregation_timestamp": stage1_data.get("aggregation_timestamp")
            })
        
        if stage2_data:
            # 根据是否为多轮评估选择不同的数据源
            if is_multi_round:
                stage2_stats = stage2_data.get("aggregated_statistics", stage2_data.get("statistics", {}))
                knowledge_deficiency = stage2_stats.get("avg_knowledge_deficiency", stage2_stats.get("knowledge_deficiency", 0))
                reasoning_errors_stage2 = stage2_stats.get("avg_reasoning_errors", stage2_stats.get("reasoning_errors", 0))
                capability_insufficient = stage2_stats.get("avg_capability_insufficient", stage2_stats.get("capability_insufficient", 0))
            else:
                stage2_stats = stage2_data.get("statistics", {})
                knowledge_deficiency = stage2_stats.get("knowledge_deficiency", 0)
                reasoning_errors_stage2 = stage2_stats.get("reasoning_errors", 0)
                capability_insufficient = stage2_stats.get("capability_insufficient", 0)
            
            combined_stats.update({
                "stage2_knowledge_deficiency": knowledge_deficiency,
                "stage2_reasoning_errors": reasoning_errors_stage2,
                "stage2_capability_insufficient": capability_insufficient,
            })
            
            # 计算最终分类统计
            final_correct = correct_answers  # Stage1中直接正确的
            final_reasoning_errors = reasoning_errors_stage1 + reasoning_errors_stage2  # Stage1和Stage2的推理错误
            final_knowledge_deficiency = knowledge_deficiency  # Stage2中的知识缺失
            final_capability_insufficient = capability_insufficient  # Stage2中的能力不足
            
            combined_stats.update({
                "final_correct_answers": final_correct,
                "final_reasoning_errors": final_reasoning_errors,
                "final_knowledge_deficiency": final_knowledge_deficiency,
                "final_capability_insufficient": final_capability_insufficient,
                "final_accuracy_rate": (final_correct / total_questions * 100) if total_questions > 0 else 0,
                "final_reasoning_error_rate": (final_reasoning_errors / total_questions * 100) if total_questions > 0 else 0,
                "final_knowledge_deficiency_rate": (final_knowledge_deficiency / total_questions * 100) if total_questions > 0 else 0,
                "final_capability_insufficient_rate": (final_capability_insufficient / total_questions * 100) if total_questions > 0 else 0,
            })
        else:
            # 如果没有Stage2数据，使用Stage1的统计作为最终结果
            combined_stats.update({
                "stage2_knowledge_deficiency": 0,
                "stage2_reasoning_errors": 0,
                "stage2_capability_insufficient": 0,
                "final_correct_answers": correct_answers,
                "final_reasoning_errors": reasoning_errors_stage1,
                "final_knowledge_deficiency": 0,
                "final_capability_insufficient": need_retest,  # 未进行Stage2的问题归类为能力不足
                "final_accuracy_rate": stage1_stats.get("accuracy_rate", 0),
                "final_reasoning_error_rate": stage1_stats.get("reasoning_error_rate", 0),
                "final_knowledge_deficiency_rate": 0,
                "final_capability_insufficient_rate": stage1_stats.get("retest_rate", 0),
            })
        
        return combined_stats
    
    def _aggregate_multi_file_results(self, all_analyses: List[Dict[str, Any]], 
                                    file_names: List[str], model_name: str) -> Dict[str, Any]:
        """汇总多个文件的分析结果
        
        Args:
            all_analyses: 所有文件的分析结果列表
            file_names: 文件名列表
            model_name: 模型名称
            
        Returns:
            Dict: 汇总分析结果
        """
        logger.info(f"开始汇总 {len(all_analyses)} 个文件的分析结果")
        
        # 提取阈值信息（使用第一个文件的阈值，假设所有文件使用相同阈值）
        thresholds = {
            "stage1": {
                "answer_threshold": 6.0,
                "reasoning_threshold": 6.0
            },
            "stage2": {
                "answer_threshold": 6.0,
                "reasoning_threshold": 6.0
            }
        }
        if all_analyses and "thresholds" in all_analyses[0]:
            thresholds = all_analyses[0]["thresholds"]
        
        # 初始化汇总统计
        aggregated_stats = {
            "total_questions": 0,
            "thresholds": thresholds,
            "stage1_correct_answers": 0,
            "stage1_reasoning_errors": 0,
            "stage1_need_retest": 0,
            "stage2_knowledge_deficiency": 0,
            "stage2_reasoning_errors": 0,
            "stage2_capability_insufficient": 0,
            "final_correct_answers": 0,
            "final_reasoning_errors": 0,
            "final_knowledge_deficiency": 0,
            "final_capability_insufficient": 0,
        }
        
        # 汇总各文件的统计数据
        for analysis in all_analyses:
            # 直接从简化的分析结果中获取数据
            aggregated_stats["total_questions"] += (
                analysis.get("final_correct_answers", 0) + 
                analysis.get("final_reasoning_errors", 0) + 
                analysis.get("final_knowledge_deficiency", 0) + 
                analysis.get("final_capability_insufficient", 0)
            )
            aggregated_stats["final_correct_answers"] += analysis.get("final_correct_answers", 0)
            aggregated_stats["final_reasoning_errors"] += analysis.get("final_reasoning_errors", 0)
            aggregated_stats["final_knowledge_deficiency"] += analysis.get("final_knowledge_deficiency", 0)
            aggregated_stats["final_capability_insufficient"] += analysis.get("final_capability_insufficient", 0)
        
        # 计算汇总比例
        total_questions = aggregated_stats["total_questions"]
        if total_questions > 0:
            aggregated_stats.update({
                "final_accuracy_rate": (aggregated_stats["final_correct_answers"] / total_questions * 100),
                "final_reasoning_error_rate": (aggregated_stats["final_reasoning_errors"] / total_questions * 100),
                "final_knowledge_deficiency_rate": (aggregated_stats["final_knowledge_deficiency"] / total_questions * 100),
                "final_capability_insufficient_rate": (aggregated_stats["final_capability_insufficient"] / total_questions * 100),
            })
        
        # 检查是否有多轮评估的文件
        multi_round_files = []
        single_round_files = []
        
        for i, analysis in enumerate(all_analyses):
            if analysis.get("evaluation_info", {}).get("is_multi_round_evaluation", False):
                multi_round_files.append({
                    "file_name": file_names[i],
                    "round_info": analysis.get("evaluation_info", {})
                })
            else:
                single_round_files.append(file_names[i])
        
        # 构建简化的汇总结果，只保留绘图需要的信息
        multi_analysis = {
            "model_name": model_name,
            "analysis_type": "multi_file_aggregation",
            "processed_files": file_names,
            "file_count": len(file_names),
            "aggregation_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "thresholds": thresholds,
            "final_correct_answers": aggregated_stats["final_correct_answers"],
            "final_reasoning_errors": aggregated_stats["final_reasoning_errors"],
            "final_knowledge_deficiency": aggregated_stats["final_knowledge_deficiency"],
            "final_capability_insufficient": aggregated_stats["final_capability_insufficient"],
            "final_accuracy_rate": aggregated_stats["final_accuracy_rate"],
            "final_reasoning_error_rate": aggregated_stats["final_reasoning_error_rate"],
            "final_knowledge_deficiency_rate": aggregated_stats["final_knowledge_deficiency_rate"],
            "final_capability_insufficient_rate": aggregated_stats["final_capability_insufficient_rate"],
            "evaluation_composition": {
                "multi_round_files": multi_round_files,
                "single_round_files": single_round_files,
                "multi_round_count": len(multi_round_files),
                "single_round_count": len(single_round_files)
            }
        }
        
        return multi_analysis
    
    def _aggregate_round_analyses(self, round_analysis_files: List, unified_analysis_path) -> Dict[str, Any]:
        """汇总多轮次的分析文件
        
        Args:
            round_analysis_files: 轮次分析文件路径列表
            unified_analysis_path: 统一分析文件路径
            
        Returns:
            Dict: 汇总的分析结果
        """
        logger.info(f"开始汇总 {len(round_analysis_files)} 个轮次分析文件")
        
        # 加载所有轮次的分析数据
        round_analyses = []
        for file_path in sorted(round_analysis_files):
            data = self._load_json_file(file_path)
            if data:
                round_analyses.append(data)
                logger.info(f"加载轮次分析文件: {file_path.name}")
        
        if not round_analyses:
            raise ValueError("没有有效的轮次分析文件")
        
        # 使用第一个轮次的结构作为模板
        template = round_analyses[0]
        
        # 汇总分析结果
        aggregated = {
            "model_name": template.get("model_name", ""),
            "file_name": template.get("file_name", ""),
            "thresholds": template.get("thresholds", {}),
            "evaluation_info": {
                "is_multi_round_evaluation": True,
                "evaluation_rounds": len(round_analyses),
                "successful_rounds": len(round_analyses),
                "aggregation_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # 汇总统计数据
        total_questions = 0
        total_correct_answers = 0
        total_reasoning_errors = 0
        total_knowledge_deficiency = 0
        total_capability_insufficient = 0
        
        for analysis in round_analyses:
            stats = analysis.get("statistics", {})
            total_questions = stats.get("total_questions", 0)  # 每轮问题数相同
            total_correct_answers += stats.get("correct_answers", 0)
            total_reasoning_errors += stats.get("reasoning_errors", 0)
            total_knowledge_deficiency += stats.get("knowledge_deficiency", 0)
            total_capability_insufficient += stats.get("capability_insufficient", 0)
        
        # 计算平均值
        num_rounds = len(round_analyses)
        avg_correct_answers = total_correct_answers / num_rounds
        avg_reasoning_errors = total_reasoning_errors / num_rounds
        avg_knowledge_deficiency = total_knowledge_deficiency / num_rounds
        avg_capability_insufficient = total_capability_insufficient / num_rounds
        
        # 构建统计信息（兼容评估流程）
        aggregated["statistics"] = {
            "total_questions": total_questions,
            "correct_answers": avg_correct_answers,
            "reasoning_errors": avg_reasoning_errors,
            "need_retest": avg_capability_insufficient,  # 兼容Stage1逻辑
            "knowledge_deficiency": avg_knowledge_deficiency,
            "capability_insufficient": avg_capability_insufficient,
            "accuracy_rate": (avg_correct_answers / total_questions * 100) if total_questions > 0 else 0,
            "reasoning_error_rate": (avg_reasoning_errors / total_questions * 100) if total_questions > 0 else 0,
            "knowledge_deficiency_rate": (avg_knowledge_deficiency / total_questions * 100) if total_questions > 0 else 0,
            "capability_insufficient_rate": (avg_capability_insufficient / total_questions * 100) if total_questions > 0 else 0
        }
        
        # 最终结果（用于可视化）
        aggregated.update({
            "final_correct_answers": avg_correct_answers,
            "final_reasoning_errors": avg_reasoning_errors,
            "final_knowledge_deficiency": avg_knowledge_deficiency,
            "final_capability_insufficient": avg_capability_insufficient,
            "final_accuracy_rate": aggregated["statistics"]["accuracy_rate"],
            "final_reasoning_error_rate": aggregated["statistics"]["reasoning_error_rate"],
            "final_knowledge_deficiency_rate": aggregated["statistics"]["knowledge_deficiency_rate"],
            "final_capability_insufficient_rate": aggregated["statistics"]["capability_insufficient_rate"]
        })
        
        # 保存汇总结果
        self._save_json_file(aggregated, unified_analysis_path)
        logger.info(f"轮次分析汇总完成，结果保存到: {unified_analysis_path}")
        
        return aggregated
    
    def _generate_from_multi_round_files(self, base_dir, file_name: str, unified_analysis_path) -> Dict[str, Any]:
        """从多轮分析文件生成统一分析（兼容旧格式）
        
        Args:
            base_dir: 基础目录
            file_name: 文件名
            unified_analysis_path: 统一分析文件路径
            
        Returns:
            Dict: 统一分析结果
        """
        # 尝试从stage1_multi_round_analysis.json生成
        multi_round_path = base_dir / "stage1_multi_round_analysis.json"
        if multi_round_path.exists():
            logger.info(f"从多轮分析文件生成统一分析: {multi_round_path}")
            stage1_data = self._load_json_file(multi_round_path)
            if stage1_data:
                # 检查是否有stage2数据
                stage2_multi_path = base_dir / "stage2_multi_round_analysis.json"
                stage2_data = self._load_json_file(stage2_multi_path)
                
                # 生成综合分析
                combined_analysis = self._combine_stage_results(stage1_data, stage2_data, True)
                self._save_json_file(combined_analysis, unified_analysis_path)
                return combined_analysis
        
        raise FileNotFoundError(f"无法找到有效的分析文件用于生成: {unified_analysis_path}")
    
    def create_round_analysis(self, model_name: str, file_name: str, round_number: int, 
                            stage1_data: Dict[str, Any], stage2_data: Optional[Dict[str, Any]] = None) -> str:
        """创建单轮次的综合分析文件
        
        Args:
            model_name: 模型名称
            file_name: 文件名称
            round_number: 轮次编号
            stage1_data: Stage1分析数据
            stage2_data: Stage2分析数据（可选）
            
        Returns:
            str: 保存的文件路径
        """
        logger.info(f"创建轮次分析 - 模型: {model_name}, 文件: {file_name}, 轮次: {round_number}")
        
        # 使用FileManager查找最新的时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        base_dir = timestamped_dir / file_name
        
        # 合并Stage1和Stage2数据
        combined_analysis = self._combine_single_round_results(stage1_data, stage2_data)
        
        # 添加轮次信息
        combined_analysis["round_number"] = round_number
        combined_analysis["round_timestamp"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存轮次分析文件
        round_analysis_path = base_dir / f"{file_name}_analysis_round_{round_number}.json"
        self._save_json_file(combined_analysis, round_analysis_path)
        
        logger.info(f"轮次分析完成，结果保存到: {round_analysis_path}")
        return str(round_analysis_path)
    
    def _combine_single_round_results(self, stage1_data: Dict[str, Any], 
                                    stage2_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并单轮次的Stage1和Stage2结果
        
        Args:
            stage1_data: Stage1分析数据
            stage2_data: Stage2分析数据（可选）
            
        Returns:
            Dict: 合并后的分析结果
        """
        # 基础信息
        combined = {
            "model_name": stage1_data.get("model_name", ""),
            "file_name": stage1_data.get("file_name", ""),
            "thresholds": {
                "stage1": stage1_data.get("thresholds", {}),
                "stage2": stage2_data.get("thresholds", {}) if stage2_data else {}
            }
        }
        
        # 获取Stage1统计
        stage1_stats = stage1_data.get("statistics", {})
        total_questions = stage1_stats.get("total_questions", 0)
        correct_answers = stage1_stats.get("correct_answers", 0)
        reasoning_errors_stage1 = stage1_stats.get("reasoning_errors", 0)
        need_retest = stage1_stats.get("need_retest", 0)
        
        if stage2_data:
            # 有Stage2数据
            stage2_stats = stage2_data.get("statistics", {})
            knowledge_deficiency = stage2_stats.get("knowledge_deficiency", 0)
            reasoning_errors_stage2 = stage2_stats.get("reasoning_errors", 0)
            capability_insufficient = stage2_stats.get("capability_insufficient", 0)
            
            # 最终统计
            final_correct = correct_answers
            final_reasoning_errors = reasoning_errors_stage1 + reasoning_errors_stage2
            final_knowledge_deficiency = knowledge_deficiency
            final_capability_insufficient = capability_insufficient
        else:
            # 只有Stage1数据
            final_correct = correct_answers
            final_reasoning_errors = reasoning_errors_stage1
            final_knowledge_deficiency = 0
            final_capability_insufficient = need_retest
        
        # 构建统计信息
        combined["statistics"] = {
            "total_questions": total_questions,
            "correct_answers": final_correct,
            "reasoning_errors": final_reasoning_errors,
            "knowledge_deficiency": final_knowledge_deficiency,
            "capability_insufficient": final_capability_insufficient,
            "accuracy_rate": (final_correct / total_questions * 100) if total_questions > 0 else 0,
            "reasoning_error_rate": (final_reasoning_errors / total_questions * 100) if total_questions > 0 else 0,
            "knowledge_deficiency_rate": (final_knowledge_deficiency / total_questions * 100) if total_questions > 0 else 0,
            "capability_insufficient_rate": (final_capability_insufficient / total_questions * 100) if total_questions > 0 else 0
        }
        
        # 兼容字段（用于评估流程）
        combined["statistics"]["need_retest"] = final_capability_insufficient
        combined["statistics"]["retest_rate"] = combined["statistics"]["capability_insufficient_rate"]
        
        return combined
    
    def _extract_round_info(self, stage_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """提取轮次信息
        
        Args:
            stage_data: 阶段数据
            
        Returns:
            Dict: 轮次信息，如果不存在返回None
        """
        if not stage_data:
            return None
        
        round_info = stage_data.get("round_info")
        if round_info:
            return {
                "current_round": round_info.get("current_round"),
                "total_rounds": round_info.get("total_rounds"),
                "round_progress": round_info.get("round_progress"),
                "round_percentage": round_info.get("round_percentage")
            }
        
        # 如果没有round_info但有round_number，说明是单轮但来自多轮评估
        if "round_number" in stage_data:
            return {
                "current_round": stage_data.get("round_number"),
                "total_rounds": stage_data.get("total_rounds"),
                "round_progress": f"{stage_data.get('round_number')}/{stage_data.get('total_rounds')}",
                "round_percentage": round((stage_data.get('round_number', 1) / stage_data.get('total_rounds', 1)) * 100, 2)
            }
        
        return None
    
    def _create_combined_round_summary(self, stage1_data: Dict[str, Any], 
                                     stage2_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建综合轮次摘要
        
        Args:
            stage1_data: Stage1数据
            stage2_data: Stage2数据
            
        Returns:
            Dict: 综合轮次摘要
        """
        summary = {
            "evaluation_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stages_evaluated": ["stage1"]
        }
        
        # 从Stage1获取轮次信息
        stage1_round_info = self._extract_round_info(stage1_data)
        if stage1_round_info:
            summary.update({
                "current_round": stage1_round_info["current_round"],
                "total_rounds": stage1_round_info["total_rounds"],
                "round_progress": stage1_round_info["round_progress"]
            })
        
        # 如果有Stage2数据，添加到摘要中
        if stage2_data:
            summary["stages_evaluated"].append("stage2")
            stage2_round_info = self._extract_round_info(stage2_data)
            if stage2_round_info:
                # 验证轮次一致性
                if (stage1_round_info and 
                    stage1_round_info["current_round"] != stage2_round_info["current_round"]):
                    summary["round_consistency_warning"] = f"Stage1轮次({stage1_round_info['current_round']})与Stage2轮次({stage2_round_info['current_round']})不一致"
        
        return summary
    
    def _extract_detailed_rounds(self, stage_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """提取详细的轮次数据
        
        Args:
            stage_data: 阶段数据
            
        Returns:
            Dict: 详细轮次数据，如果不存在返回None
        """
        if not stage_data:
            return None
        
        detailed_rounds = {}
        
        # 提取当前轮次的统计信息
        if "statistics" in stage_data:
            detailed_rounds["current_round_statistics"] = stage_data["statistics"]
        
        # 提取分数分布信息
        if "score_distribution" in stage_data:
            detailed_rounds["current_round_score_distribution"] = stage_data["score_distribution"]
        
        # 提取文件路径信息
        file_paths = {}
        for path_key in ["test_results_path", "eval_results_path", "analysis_file_path"]:
            if path_key in stage_data:
                file_paths[path_key] = stage_data[path_key]
        
        if file_paths:
            detailed_rounds["file_paths"] = file_paths
        
        # 提取数据质量信息
        if "data_quality" in stage_data:
            detailed_rounds["data_quality"] = stage_data["data_quality"]
        
        return detailed_rounds if detailed_rounds else None
    
    def _extract_multi_round_summary(self, stage_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """提取多轮评估的摘要信息
        
        Args:
            stage_data: 阶段数据
            
        Returns:
            Dict: 多轮评估摘要，如果不存在返回None
        """
        if not stage_data:
            return None
        
        summary = {}
        
        # 提取基本轮次信息
        if "evaluation_rounds" in stage_data:
            summary["evaluation_rounds"] = stage_data["evaluation_rounds"]
        if "successful_rounds" in stage_data:
            summary["successful_rounds"] = stage_data["successful_rounds"]
        if "aggregation_timestamp" in stage_data:
            summary["aggregation_timestamp"] = stage_data["aggregation_timestamp"]
        
        # 提取汇总统计
        if "aggregated_statistics" in stage_data:
            summary["aggregated_statistics"] = stage_data["aggregated_statistics"]
        
        # 提取方差统计
        if "variance_statistics" in stage_data:
            summary["variance_statistics"] = stage_data["variance_statistics"]
        
        return summary if summary else None
    
    def _extract_all_rounds_data(self, stage_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """提取所有轮次的详细数据
        
        Args:
            stage_data: 阶段数据
            
        Returns:
            Dict: 所有轮次的详细数据，如果不存在返回None
        """
        if not stage_data:
            return None
        
        all_rounds = {}
        
        # 提取详细轮次统计
        if "detailed_round_statistics" in stage_data:
            all_rounds["detailed_round_statistics"] = stage_data["detailed_round_statistics"]
        
        # 提取轮次摘要
        if "round_summaries" in stage_data:
            all_rounds["round_summaries"] = stage_data["round_summaries"]
        
        # 提取个别结果
        if "individual_results" in stage_data:
            # 只保留关键信息，避免文件过大
            simplified_results = []
            for result in stage_data["individual_results"]:
                simplified_result = {
                    "round_number": result.get("round_number"),
                    "statistics": result.get("statistics"),
                    "score_distribution": result.get("score_distribution"),
                    "evaluation_timestamp": result.get("evaluation_timestamp"),
                    "analysis_file_path": result.get("analysis_file_path")
                }
                simplified_results.append(simplified_result)
            all_rounds["individual_results_summary"] = simplified_results
        
        # 提取评估摘要
        if "evaluation_summary" in stage_data:
            all_rounds["evaluation_summary"] = stage_data["evaluation_summary"]
        
        return all_rounds if all_rounds else None
    
    def _extract_single_round_info(self, stage_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """提取单轮评估的信息
        
        Args:
            stage_data: 阶段数据
            
        Returns:
            Dict: 单轮评估信息，如果不存在返回None
        """
        if not stage_data:
            return None
        
        info = {}
        
        # 提取基本信息
        if "evaluation_timestamp" in stage_data:
            info["evaluation_timestamp"] = stage_data["evaluation_timestamp"]
        if "statistics" in stage_data:
            info["statistics"] = stage_data["statistics"]
        if "score_distribution" in stage_data:
            info["score_distribution"] = stage_data["score_distribution"]
        if "data_quality" in stage_data:
            info["data_quality"] = stage_data["data_quality"]
        if "analysis_file_path" in stage_data:
            info["analysis_file_path"] = stage_data["analysis_file_path"]
        
        return info if info else None
    
    def process_all_results(self, model_name: str, enable_multi_file: bool = True) -> Dict[str, Any]:
        """处理指定模型的所有结果（单文件+多文件汇总）
        
        Args:
            model_name: 模型名称
            enable_multi_file: 是否启用多文件处理
            
        Returns:
            Dict: 包含所有处理结果的字典
        """
        logger.info(f"开始处理模型 {model_name} 的所有结果")
        
        results = {
            "model_name": model_name,
            "single_file_results": [],
            "multi_file_result": None
        }
        
        # 处理所有单文件结果
        model_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if model_dir and model_dir.exists():
            for item in model_dir.iterdir():
                if item.is_dir() and item.name not in ["multi_file", "结果分析"]:
                    file_name = item.name
                    try:
                        single_result = self.process_single_file_results(model_name, file_name)
                        results["single_file_results"].append({
                            "file_name": file_name,
                            "result": single_result
                        })
                    except Exception as e:
                        logger.error(f"处理单文件 {file_name} 失败: {e}")
        
        # 处理多文件汇总
        if enable_multi_file:
            try:
                multi_result = self.process_multi_file_results(model_name, enable_multi_file)
                results["multi_file_result"] = multi_result
            except Exception as e:
                logger.error(f"处理多文件汇总失败: {e}")
        else:
            results["multi_file_result"] = None
        
        logger.info(f"模型 {model_name} 的所有结果处理完成")
        return results
    
    def process_specified_files(self, model_name: str, file_names: List[str], 
                               enable_multi_file: bool = True) -> Dict[str, Any]:
        """处理指定的文件列表
        
        Args:
            model_name: 模型名称
            file_names: 要处理的文件名列表
            enable_multi_file: 是否启用多文件汇总
            
        Returns:
            Dict: 处理结果
        """
        logger.info(f"开始处理指定文件列表: {file_names}")
        
        results = {
            "model_name": model_name,
            "specified_files": file_names,
            "single_file_results": [],
            "multi_file_result": None
        }
        
        # 处理指定的单文件结果
        for file_name in file_names:
            try:
                single_result = self.process_single_file_results(model_name, file_name)
                results["single_file_results"].append({
                    "file_name": file_name,
                    "result": single_result
                })
                logger.info(f"文件 {file_name} 处理成功")
            except Exception as e:
                logger.error(f"处理文件 {file_name} 失败: {e}")
        
        # 如果启用多文件处理且有多个文件，则生成汇总
        if enable_multi_file and len(results["single_file_results"]) > 1:
            try:
                # 收集成功处理的文件分析结果
                successful_analyses = []
                successful_file_names = []
                
                for item in results["single_file_results"]:
                    successful_analyses.append(item["result"])
                    successful_file_names.append(item["file_name"])
                
                # 生成多文件汇总
                multi_analysis = self._aggregate_multi_file_results(
                    successful_analyses, successful_file_names, model_name
                )
                
                # 保存汇总结果
                timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
                if timestamped_dir:
                    multi_dir = timestamped_dir / "multi_file"
                    multi_dir.mkdir(exist_ok=True)
                    output_path = multi_dir / "multi_analysis.json"
                self._save_json_file(multi_analysis, output_path)
                
                results["multi_file_result"] = multi_analysis
                logger.info(f"指定文件的多文件汇总完成")
                
            except Exception as e:
                logger.error(f"指定文件的多文件汇总失败: {e}")
        
        logger.info(f"指定文件列表处理完成")
        return results


def main():
    """测试ResultProcessor功能"""
    try:
        processor = ResultProcessor()
        
        # 测试模型名称
        model_name = "deepseek"
        
        print("=== 结果处理器测试 ===")
        
        # 测试单文件处理
        print("\n=== 单文件结果处理测试 ===")
        try:
            single_result = processor.process_single_file_results(model_name, "test")
            print(f"单文件处理成功")
            print(f"总问题数: {single_result['combined_statistics']['total_questions']}")
            print(f"最终正确率: {single_result['combined_statistics']['final_accuracy_rate']:.2f}%")
        except Exception as e:
            print(f"单文件处理失败: {e}")
        
        # 测试多文件处理（启用）
        print("\n=== 多文件汇总处理测试（启用） ===")
        try:
            multi_result = processor.process_multi_file_results(model_name, enable_multi_file=True)
            if multi_result:
                print(f"多文件处理成功")
                print(f"处理文件数: {multi_result['file_count']}")
                print(f"正确回答: {multi_result['final_correct_answers']}")
                print(f"汇总正确率: {multi_result['final_accuracy_rate']:.2f}%")
            else:
                print("多文件处理被跳过")
        except Exception as e:
            print(f"多文件处理失败: {e}")
        
        # 测试多文件处理（禁用）
        print("\n=== 多文件汇总处理测试（禁用） ===")
        try:
            multi_result = processor.process_multi_file_results(model_name, enable_multi_file=False)
            print(f"多文件处理: {'跳过' if multi_result is None else '意外执行'}")
        except Exception as e:
            print(f"多文件处理失败: {e}")
        
        # 测试完整处理
        print("\n=== 完整结果处理测试 ===")
        try:
            all_results = processor.process_all_results(model_name, enable_multi_file=True)
            print(f"完整处理成功")
            print(f"单文件结果数: {len(all_results['single_file_results'])}")
            print(f"多文件汇总: {'成功' if all_results['multi_file_result'] else '失败'}")
        except Exception as e:
            print(f"完整处理失败: {e}")
        
        # 测试指定文件处理
        print("\n=== 指定文件处理测试 ===")
        try:
            specified_files = ["test"]  # 可以添加更多文件名
            specified_results = processor.process_specified_files(
                model_name, specified_files, enable_multi_file=False
            )
            print(f"指定文件处理成功")
            print(f"处理文件: {specified_results['specified_files']}")
            print(f"成功处理数: {len(specified_results['single_file_results'])}")
            print(f"多文件汇总: {'成功' if specified_results['multi_file_result'] else '未启用'}")
        except Exception as e:
            print(f"指定文件处理失败: {e}")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()