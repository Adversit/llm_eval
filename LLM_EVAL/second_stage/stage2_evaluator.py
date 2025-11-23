import os
import json
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

# 导入工具类
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.excel_processor import ExcelProcessor
from utils.test_LLM import LLMTester
from utils.eval_llm import EvalLLM
from utils.file_manager_singleton import get_file_manager
from utils.json_serializer import safe_json_dumps

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stage2Evaluator:
    """第二阶段评估器 - 基于内容的深度评估流程"""
    
    def __init__(self, model_name: str = "deepseek", eval_model_name: str = "siliconflow_deepseek"):
        """初始化第二阶段评估器
        
        Args:
            model_name: 被测试的模型名称
            eval_model_name: 用于评估的模型名称
        """
        self.model_name = model_name
        self.eval_model_name = eval_model_name
        
        # 初始化工具类
        self.llm_tester = LLMTester()
        self.eval_llm = EvalLLM(model_name=eval_model_name)
        self.file_manager = get_file_manager()
        
        # 加载提示词
        self.test_prompt = self._load_prompt("prompt/test2_prompt.txt")
        self.eval_prompt = self._load_prompt("prompt/eval1_prompt.txt")
        
        # 进度回调函数
        self.progress_callback = None
        
        logger.info(f"Stage2Evaluator初始化完成 - 测试模型: {model_name}, 评估模型: {eval_model_name}")
    
    def set_progress_callback(self, callback):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，接受参数 (current, total, question_id, process_type, current_round, total_rounds)
        """
        self.progress_callback = callback
    
    def _load_prompt(self, prompt_path: str) -> str:
        """加载提示词文件
        
        Args:
            prompt_path: 提示词文件路径
            
        Returns:
            str: 提示词内容
        """
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载提示词失败 {prompt_path}: {e}")
            raise
    
    def process_stage1_files(self, file_paths: List[str]) -> Tuple[List[Dict[str, str]], str]:
        """处理一个或多个stage1输出的CSV文件
        
        Args:
            file_paths: stage1_to_stage2_data.csv文件路径列表
            
        Returns:
            Tuple[List[Dict], str]: (包含字典的列表，原始文件名)
        """
        logger.info(f"开始处理 {len(file_paths)} 个stage1输出文件")
        all_data = []
        
        # 从文件路径中提取原始文件名
        # 路径格式: data/{模型名}/{文件名}/stage1_to_stage2_data.csv
        # 我们需要提取{文件名}部分
        if file_paths:
            file_path = Path(file_paths[0])
            # 获取父目录名称作为原始文件名
            main_file_name = file_path.parent.name
        else:
            main_file_name = "unknown"
        
        for file_path in file_paths:
            try:
                logger.info(f"处理文件: {file_path}")
                
                # 读取CSV文件
                df = pd.read_csv(file_path)
                
                # 转换为指定格式
                for _, row in df.iterrows():
                    item = {
                        "id": str(row.get('id', '')),
                        "question": str(row.get('question', '')),
                        "answer": str(row.get('answer', '')),
                        "content": str(row.get('content', ''))
                    }
                    all_data.append(item)
                
                logger.info(f"文件 {file_path} 处理完成，获得 {len(df)} 条数据")
                
            except Exception as e:
                logger.error(f"处理文件 {file_path} 失败: {e}")
                continue
        
        logger.info(f"所有文件处理完成，总共获得 {len(all_data)} 条数据")
        return all_data, main_file_name
    

    
    def test_llm_responses(self, data_list: List[Dict[str, str]], original_file_name: str, output_filename: str = "stage2_test_results.csv", current_round: int = 1, total_rounds: int = 1) -> str:
        """使用LLM测试数据并保存结果
        
        注意：Stage2与Stage1的区别：
        - Stage1: 只使用question作为输入
        - Stage2: 使用question + content作为输入，提供更多上下文信息
        
        Args:
            data_list: 处理后的数据列表
            original_file_name: 原始文件名称（用于保存路径）
            
        Returns:
            str: 保存的CSV文件路径
        """
        logger.info(f"开始Stage2 LLM测试，共 {len(data_list)} 条数据")
        results = []
        
        for i, item in enumerate(data_list, 1):
            try:
                logger.info(f"处理第 {i}/{len(data_list)} 条数据，ID: {item['id']}")
                
                # 调用进度回调函数 - 在实际处理前调用
                if self.progress_callback:
                    self.progress_callback(i-1, len(data_list), item['id'], "testing", current_round, total_rounds)
                
                # Stage2特点：构建测试提示词时同时使用question和content
                # 这与Stage1不同，Stage1只使用question
                test_content = self.test_prompt.format(
                    question=item['question'],
                    excel_data=item['content']
                )
                
                # 调用LLM
                llm_response = self.llm_tester.call_llm(test_content, self.model_name)
                
                # 解析LLM响应
                llm_answer, llm_reasoning = self._parse_llm_response(llm_response)
                
                # 清理文本中的换行符和特殊字符，避免CSV格式问题
                llm_answer = self._clean_text_for_csv(llm_answer)
                llm_reasoning = self._clean_text_for_csv(llm_reasoning)
                
                # 构建结果
                result = {
                    "id": item["id"],
                    "question": self._clean_text_for_csv(item["question"]),
                    "answer": self._clean_text_for_csv(item["answer"]),
                    "llm_answer": llm_answer,
                    "llm_reasoning": llm_reasoning
                }
                results.append(result)
                
                # 调用进度回调函数 - 处理完成后调用
                if self.progress_callback:
                    self.progress_callback(i, len(data_list), item['id'], "testing", current_round, total_rounds)
                
            except Exception as e:
                logger.error(f"处理数据 {item['id']} 失败: {e}")
                # 添加错误结果
                result = {
                    "id": item["id"],
                    "question": self._clean_text_for_csv(item["question"]),
                    "answer": self._clean_text_for_csv(item["answer"]),
                    "llm_answer": f"错误: {str(e)}",
                    "llm_reasoning": "处理失败"
                }
                results.append(result)
                
                # 即使出错也要更新进度
                if self.progress_callback:
                    self.progress_callback(i, len(data_list), item['id'], "testing", current_round, total_rounds)
        
        # 保存结果到CSV
        csv_path = self._save_to_csv(results, original_file_name, output_filename)
        logger.info(f"LLM测试完成，结果保存到: {csv_path}")
        return csv_path
    
    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """解析LLM响应，提取答案和推理过程
        
        Args:
            response: LLM原始响应
            
        Returns:
            Tuple[str, str]: (答案, 推理过程)
        """
        try:
            # 尝试解析JSON格式
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response
            
            parsed = json.loads(json_str)
            return parsed.get("llm_answer", ""), parsed.get("llm_reasoning", "")
        except:
            # 如果解析失败，返回原始响应
            return response, "解析失败"
    
    def evaluate_responses(self, test_results_path: str, original_file_name: str, 
                          original_data: List[Dict[str, str]], output_filename: str = "stage2_evaluation_results.csv", current_round: int = 1, total_rounds: int = 1) -> str:
        """评估LLM响应并保存结果
        
        Args:
            test_results_path: 测试结果CSV文件路径
            original_file_name: 原始文件名称（用于保存路径）
            original_data: 原始数据列表（包含content字段）
            
        Returns:
            str: 保存的评估结果CSV文件路径
        """
        logger.info(f"开始评估LLM响应，读取文件: {test_results_path}")
        
        # 读取测试结果
        df = pd.read_csv(test_results_path)
        results = []
        
        # 创建ID到content的映射
        id_to_content = {item['id']: item['content'] for item in original_data}
        
        # 创建一个新的回调函数用于评估阶段
        eval_callback = None
        if self.progress_callback:
            def eval_callback(current, total, question_id):
                # 这里可以区分是评估阶段的进度
                self.progress_callback(current, total, question_id, "evaluating")
        
        for i, row in df.iterrows():
            try:
                logger.info(f"评估第 {i+1}/{len(df)} 条数据，ID: {row['id']}")
                
                # 调用进度回调函数 - 评估前
                if self.progress_callback:
                    self.progress_callback(i, len(df), row['id'], "evaluating", current_round, total_rounds)
                
                # 获取对应的content
                content = id_to_content.get(str(row['id']), "")
                
                # 构建评估内容，包含question, answer, content, llm_answer, llm_reasoning
                eval_content = self.eval_prompt.format(
                    question=row['question'],
                    answer=row['answer'],
                    llm_answer=row['llm_answer'],
                    llm_reasoning=row['llm_reasoning']
                )
                
                # 调用评估LLM，增加重试机制
                eval_response = self._call_eval_llm_with_retry(eval_content, max_retries=3)
                
                # 解析评估结果
                score_answer, score_reasoning = self._parse_eval_response(eval_response)
                
                # 构建结果
                result = {
                    "id": row["id"],
                    "question": row["question"],
                    "answer": row["answer"],
                    "content": self._clean_text_for_csv(content),
                    "llm_answer": row["llm_answer"],
                    "llm_reasoning": row["llm_reasoning"],
                    "score_answer": score_answer,
                    "score_reasoning": score_reasoning
                }
                results.append(result)
                
                # 调用进度回调函数 - 评估后
                if self.progress_callback:
                    self.progress_callback(i+1, len(df), row['id'], "evaluating", current_round, total_rounds)
                
            except Exception as e:
                logger.error(f"评估数据 {row['id']} 失败: {e}")
                # 添加错误结果
                result = {
                    "id": row["id"],
                    "question": row["question"],
                    "answer": row["answer"],
                    "content": self._clean_text_for_csv(id_to_content.get(str(row['id']), "")),
                    "llm_answer": row["llm_answer"],
                    "llm_reasoning": row["llm_reasoning"],
                    "score_answer": 0,
                    "score_reasoning": 0
                }
                results.append(result)
                
                # 即使出错也要更新进度
                if self.progress_callback:
                    self.progress_callback(i+1, len(df), row['id'], "evaluating", current_round, total_rounds)
        
        # 保存评估结果到CSV
        csv_path = self._save_to_csv(results, original_file_name, output_filename)
        logger.info(f"评估完成，结果保存到: {csv_path}")
        return csv_path
    
    def _call_eval_llm_with_retry(self, eval_content: str, max_retries: int = 3) -> str:
        """带重试机制的评估LLM调用
        
        Args:
            eval_content: 评估内容
            max_retries: 最大重试次数
            
        Returns:
            str: 评估响应
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"评估LLM调用尝试 {attempt + 1}/{max_retries}")
                response = self.eval_llm.call(self.eval_prompt, eval_content)
                
                # 检查响应是否有效
                if response and len(response.strip()) > 0:
                    # 检查是否包含明显的错误信息
                    error_keywords = ['失败', '异常', '未找到', '未启用', '未加载', 'API调用失败', '请求异常']
                    if not any(keyword in response for keyword in error_keywords):
                        logger.info(f"评估LLM调用成功，响应长度: {len(response)}")
                        return response
                    else:
                        logger.warning(f"评估LLM返回错误信息: {response[:200]}...")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"评估LLM调用异常 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        logger.error(f"评估LLM调用失败，已尝试 {max_retries} 次")
        return "评估LLM调用失败"
    
    def _parse_eval_response(self, response: str) -> Tuple[float, float]:
        """解析评估响应，提取分数
        
        Args:
            response: 评估LLM响应
            
        Returns:
            Tuple[float, float]: (答案分数, 推理分数)
        """
        try:
            logger.info(f"原始评估响应长度: {len(response)}")
            logger.info(f"原始评估响应前500字符: {response[:500]}...")
            
            # 检查响应是否包含错误信息
            error_keywords = ['失败', '异常', '未找到', '未启用', '未加载', 'API调用失败', '请求异常', 'timeout', 'error']
            if any(keyword in response.lower() for keyword in error_keywords):
                logger.error(f"评估响应包含错误信息: {response}")
                return 0.0, 0.0
            
            # 尝试多种方式提取JSON
            json_str = ""
            
            # 方法1: 查找```json代码块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                if json_end != -1:
                    json_str = response[json_start:json_end].strip()
            
            # 方法2: 查找```代码块（不带json标记）
            if not json_str and "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                if json_end != -1:
                    potential_json = response[json_start:json_end].strip()
                    # 检查是否看起来像JSON
                    if potential_json.startswith('{') and potential_json.endswith('}'):
                        json_str = potential_json
            
            # 方法3: 查找大括号包围的内容
            if not json_str:
                start_brace = response.find('{')
                if start_brace != -1:
                    # 找到匹配的结束大括号
                    brace_count = 0
                    end_brace = -1
                    for i in range(start_brace, len(response)):
                        if response[i] == '{':
                            brace_count += 1
                        elif response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_brace = i
                                break
                    
                    if end_brace != -1:
                        json_str = response[start_brace:end_brace + 1].strip()
            
            # 方法4: 如果都没找到，尝试整个响应
            if not json_str:
                json_str = response.strip()
            
            logger.info(f"提取的JSON字符串长度: {len(json_str)}")
            logger.info(f"提取的JSON字符串: {json_str}")
            
            # 清理JSON字符串
            json_str = json_str.replace('\n', ' ').replace('\r', ' ')
            json_str = ' '.join(json_str.split())  # 移除多余空格
            
            # 尝试解析JSON
            parsed = json.loads(json_str)
            score_answer = float(parsed.get("score_answer", 0))
            score_reasoning = float(parsed.get("score_reasoning", 0))
            
            # 验证分数范围
            if not (0 <= score_answer <= 100) or not (0 <= score_reasoning <= 100):
                logger.error(f"分数超出范围 [0-100]: 答案={score_answer}, 推理={score_reasoning}")
                return 0.0, 0.0
            
            logger.info(f"解析成功 - 答案分数: {score_answer}, 推理分数: {score_reasoning}")
            return score_answer, score_reasoning
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"尝试解析的JSON字符串: {json_str}")
            logger.error(f"完整响应内容: {response}")
            return 0.0, 0.0
        except Exception as e:
            logger.error(f"解析评估响应时发生未知错误: {e}")
            logger.error(f"响应内容: {response}")
            return 0.0, 0.0
    
    def _clean_text_for_csv(self, text: str) -> str:
        """清理文本以适合CSV格式
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 将换行符替换为空格，避免CSV格式问题
        cleaned = str(text).replace('\n', ' ').replace('\r', ' ')
        # 移除多余的空格
        cleaned = ' '.join(cleaned.split())
        # 移除可能导致CSV解析问题的字符
        cleaned = cleaned.replace('"', '""')  # 转义双引号
        
        return cleaned
    
    def analyze_results(self, eval_results_path: str, original_file_name: str, 
                       answer_threshold: float = 6.0, reasoning_threshold: float = 6.0, 
                       output_filename: str = "stage2_analysis.json") -> Dict[str, Any]:
        """分析评估结果并生成分析报告
        
        Args:
            eval_results_path: 评估结果CSV文件路径
            original_file_name: 原始文件名称（用于保存路径）
            answer_threshold: 答案分数阈值
            reasoning_threshold: 推理分数阈值
            
        Returns:
            Dict: 分析结果
        """
        logger.info(f"开始分析评估结果，阈值设置 - 答案: {answer_threshold}, 推理: {reasoning_threshold}")
        
        # 读取评估结果
        df = pd.read_csv(eval_results_path)
        
        # 分类统计 - Stage2的分类逻辑
        knowledge_deficiency = []  # 知识能力缺失 (两个分数都高)
        reasoning_errors = []  # 推理错误 (答案分数高，推理分数低)
        capability_insufficient = []  # 能力不足 (答案分数低)
        
        for _, row in df.iterrows():
            score_answer = float(row['score_answer'])
            score_reasoning = float(row['score_reasoning'])
            
            if score_answer >= answer_threshold and score_reasoning >= reasoning_threshold:
                # 两个分数都高 - 知识能力缺失
                knowledge_deficiency.append(row.to_dict())
            elif score_answer >= answer_threshold and score_reasoning < reasoning_threshold:
                # 答案分数高，推理分数低 - 推理错误
                reasoning_errors.append(row.to_dict())
            else:
                # 答案分数低 - 能力不足
                capability_insufficient.append(row.to_dict())
        
        # 生成分析报告
        analysis = {
            "model_name": self.model_name,
            "file_name": original_file_name,
            "stage": "stage2",
            "evaluation_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "thresholds": {
                "answer_threshold": answer_threshold,
                "reasoning_threshold": reasoning_threshold
            },
            "statistics": {
                "total_questions": len(df),
                "knowledge_deficiency": len(knowledge_deficiency),
                "reasoning_errors": len(reasoning_errors),
                "capability_insufficient": len(capability_insufficient),
                "knowledge_deficiency_rate": len(knowledge_deficiency) / len(df) * 100,
                "reasoning_error_rate": len(reasoning_errors) / len(df) * 100,
                "capability_insufficient_rate": len(capability_insufficient) / len(df) * 100
            },
            "score_distribution": {
                "avg_answer_score": df['score_answer'].mean(),
                "avg_reasoning_score": df['score_reasoning'].mean(),
                "min_answer_score": df['score_answer'].min(),
                "max_answer_score": df['score_answer'].max(),
                "min_reasoning_score": df['score_reasoning'].min(),
                "max_reasoning_score": df['score_reasoning'].max()
            },
            "detailed_analysis": {
                "knowledge_deficiency_data": knowledge_deficiency,
                "reasoning_errors_data": reasoning_errors,
                "capability_insufficient_data": capability_insufficient,
                "summary": {
                    "knowledge_deficiency_ids": [item["id"] for item in knowledge_deficiency],
                    "reasoning_errors_ids": [item["id"] for item in reasoning_errors],
                    "capability_insufficient_ids": [item["id"] for item in capability_insufficient]
                }
            },
            "data_quality": {
                "valid_scores": len(df[(df['score_answer'] >= 0) & (df['score_answer'] <= 100) &
                                     (df['score_reasoning'] >= 0) & (df['score_reasoning'] <= 100)]),
                "invalid_scores": len(df) - len(df[(df['score_answer'] >= 0) & (df['score_answer'] <= 100) &
                                                  (df['score_reasoning'] >= 0) & (df['score_reasoning'] <= 100)]),
                "zero_scores": len(df[(df['score_answer'] == 0) & (df['score_reasoning'] == 0)])
            }
        }
        
        # 保存分析结果
        analysis_path = self._save_analysis(analysis, original_file_name, output_filename)
        analysis["analysis_file_path"] = analysis_path
        
        # 如果是默认文件名，同时保存统一的分析文件
        if output_filename == "stage2_analysis.json":
            unified_path = self._save_unified_analysis(analysis, original_file_name)
            analysis["unified_analysis_path"] = unified_path
            logger.info(f"统一分析文件保存到: {unified_path}")
        
        logger.info(f"分析完成，结果保存到: {analysis_path}")
        
        return analysis
    
    def _save_to_csv(self, data: List[Dict], original_file_name: str, csv_name: str) -> str:
        """保存数据到CSV文件
        
        Args:
            data: 要保存的数据
            original_file_name: 原始文件名称（不含扩展名）
            csv_name: CSV文件名
            
        Returns:
            str: 保存的文件路径
        """
        # 从原始文件路径中提取文件名（不含扩展名）
        if isinstance(original_file_name, str):
            base_name = Path(original_file_name).stem
        else:
            base_name = str(original_file_name)
        
        # 保存到CSV，使用适当的参数避免格式问题
        if data:
            df = pd.DataFrame(data)
            csv_content = df.to_csv(index=False, encoding='utf-8-sig', 
                                   quoting=csv.QUOTE_ALL, escapechar='\\')
            
            # 使用FileManager保存文件
            csv_path = self.file_manager.save_file(
                model_name=self.model_name,
                file_name=base_name,
                input_name=csv_name,
                content=csv_content,
                file_type='text'
            )
        
        return csv_path
    
    def _save_analysis(self, analysis: Dict, original_file_name: str, output_filename: str = "stage2_analysis.json") -> str:
        """保存分析结果到JSON文件
        
        Args:
            analysis: 分析结果
            original_file_name: 原始文件名称
            
        Returns:
            str: 保存的文件路径
        """
        # 从原始文件路径中提取文件名（不含扩展名）
        if isinstance(original_file_name, str):
            base_name = Path(original_file_name).stem
        else:
            base_name = str(original_file_name)
        
        # 使用FileManager保存JSON文件
        json_content = safe_json_dumps(analysis)
        json_path = self.file_manager.save_file(
            model_name=self.model_name,
            file_name=base_name,
            input_name=output_filename,
            content=json_content,
            file_type='text'
        )
        
        return json_path
    
    def _save_detailed_round_results(self, detailed_round_stats: List[Dict], original_file_name: str) -> str:
        """保存每轮评估的详细结果到CSV文件
        
        Args:
            detailed_round_stats: 每轮详细统计结果
            original_file_name: 原始文件名称
            
        Returns:
            str: 保存的文件路径
        """
        # 从原始文件路径中提取文件名（不含扩展名）
        if isinstance(original_file_name, str):
            base_name = Path(original_file_name).stem
        else:
            base_name = str(original_file_name)
        
        # 准备CSV数据
        csv_data = []
        for round_stat in detailed_round_stats:
            stats = round_stat["statistics"]
            score_dist = round_stat.get("score_distribution", {})
            
            row = {
                "轮次": round_stat["round"],
                "总问题数": stats["total_questions"],
                "知识能力缺失数": stats["knowledge_deficiency"],
                "推理错误数": stats["reasoning_errors"],
                "能力不足数": stats["capability_insufficient"],
                "知识缺失率(%)": round(stats["knowledge_deficiency_rate"], 2),
                "推理错误率(%)": round(stats["reasoning_error_rate"], 2),
                "能力不足率(%)": round(stats["capability_insufficient_rate"], 2),
                "平均答案分数": round(score_dist.get("avg_answer_score", 0), 2),
                "平均推理分数": round(score_dist.get("avg_reasoning_score", 0), 2),
                "最低答案分数": score_dist.get("min_answer_score", 0),
                "最高答案分数": score_dist.get("max_answer_score", 0),
                "最低推理分数": score_dist.get("min_reasoning_score", 0),
                "最高推理分数": score_dist.get("max_reasoning_score", 0)
            }
            csv_data.append(row)
        
        if csv_data:
            # 转换为DataFrame并保存
            df = pd.DataFrame(csv_data)
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')
            
            # 使用FileManager保存文件
            csv_path = self.file_manager.save_file(
                model_name=self.model_name,
                file_name=base_name,
                input_name="stage2_detailed_round_results.csv",
                content=csv_content,
                file_type='text'
            )
            
            logger.info(f"每轮详细结果已保存到: {csv_path}")
            return csv_path
        
        return ""
    
    def _save_all_rounds_raw_data(self, all_results: List[Dict], original_file_name: str) -> str:
        """保存所有轮次的原始评估数据汇总
        
        Args:
            all_results: 所有轮次的评估结果
            original_file_name: 原始文件名称
            
        Returns:
            str: 保存的文件路径
        """
        # 从原始文件路径中提取文件名（不含扩展名）
        if isinstance(original_file_name, str):
            base_name = Path(original_file_name).stem
        else:
            base_name = str(original_file_name)
        
        try:
            # 读取每轮的评估结果CSV文件并合并
            all_raw_data = []
            
            for i, result in enumerate(all_results, 1):
                eval_results_path = result.get("eval_results_path")
                if eval_results_path and Path(eval_results_path).exists():
                    # 读取该轮的评估结果
                    df = pd.read_csv(eval_results_path)
                    # 添加轮次列
                    df['evaluation_round'] = i
                    all_raw_data.append(df)
                    logger.info(f"已读取第 {i} 轮评估数据，共 {len(df)} 条记录")
            
            if all_raw_data:
                # 合并所有轮次的数据
                combined_df = pd.concat(all_raw_data, ignore_index=True)
                
                # 重新排列列的顺序，将轮次列放在前面
                columns = ['evaluation_round'] + [col for col in combined_df.columns if col != 'evaluation_round']
                combined_df = combined_df[columns]
                
                # 保存合并后的数据
                csv_content = combined_df.to_csv(index=False, encoding='utf-8-sig')
                
                csv_path = self.file_manager.save_file(
                    model_name=self.model_name,
                    file_name=base_name,
                    input_name="stage2_all_rounds_raw_data.csv",
                    content=csv_content,
                    file_type='text'
                )
                
                logger.info(f"所有轮次原始数据已保存到: {csv_path}")
                logger.info(f"合并数据总计: {len(combined_df)} 条记录，{len(all_results)} 轮评估")
                return csv_path
            else:
                logger.warning("没有找到可合并的评估数据")
                return ""
                
        except Exception as e:
            logger.error(f"保存所有轮次原始数据失败: {e}")
            return ""
    
    def _find_most_stable_metric(self, variance_stats: Dict[str, float]) -> str:
        """找到最稳定的评估指标（标准差最小的）
        
        Args:
            variance_stats: 方差统计数据
            
        Returns:
            str: 最稳定的指标名称
        """
        std_metrics = {
            "knowledge_deficiency_rate": variance_stats.get("knowledge_deficiency_rate_std", float('inf')),
            "reasoning_error_rate": variance_stats.get("reasoning_error_rate_std", float('inf')),
            "capability_insufficient_rate": variance_stats.get("capability_insufficient_rate_std", float('inf'))
        }
        
        return min(std_metrics, key=std_metrics.get)
    
    def run_multiple_evaluations(self, file_paths: List[str], 
                                num_evaluations: int = 1, 
                                answer_threshold: float = 6.0, 
                                reasoning_threshold: float = 6.0) -> Dict[str, Any]:
        """运行多次评估（用于提高评估准确性）
        
        Args:
            file_paths: stage1输出的CSV文件路径列表
            num_evaluations: 评估次数
            answer_threshold: 答案分数阈值
            reasoning_threshold: 推理分数阈值
            
        Returns:
            Dict: 最终分析结果
        """
        logger.info(f"开始运行 {num_evaluations} 次评估")
        
        # 处理文件（只处理一次）
        data_list, original_file_name = self.process_stage1_files(file_paths)
        
        if num_evaluations == 1:
            # 单轮评估：直接运行一次完整流程
            logger.info("执行单轮评估")
            
            # LLM测试
            test_results_path = self.test_llm_responses(data_list, original_file_name, current_round=1, total_rounds=1)
            
            # 评估响应
            eval_results_path = self.evaluate_responses(test_results_path, original_file_name, data_list, current_round=1, total_rounds=1)
            
            # 分析结果
            analysis = self.analyze_results(eval_results_path, original_file_name, 
                                          answer_threshold, reasoning_threshold)
            
            logger.info("单轮评估完成")
            return analysis
        
        else:
            # 多轮评估：运行多次并汇总结果
            logger.info(f"执行多轮评估，共 {num_evaluations} 轮")
            
            all_results = []
            detailed_round_stats = []
            
            for eval_round in range(num_evaluations):
                logger.info(f"开始第 {eval_round + 1}/{num_evaluations} 轮评估")
                
                try:
                    # LLM测试 - 使用轮次后缀区分文件名
                    test_results_path = self.test_llm_responses(data_list, original_file_name, f"stage2_test_results_round_{eval_round + 1}.csv", eval_round + 1, num_evaluations)
                    
                    # 评估响应
                    eval_results_path = self.evaluate_responses(test_results_path, original_file_name, data_list, f"stage2_evaluation_results_round_{eval_round + 1}.csv", eval_round + 1, num_evaluations)
                    
                    # 分析结果
                    analysis = self.analyze_results(eval_results_path, original_file_name, 
                                                  answer_threshold, reasoning_threshold, f"stage2_analysis_round_{eval_round + 1}.json")
                    
                    # 为每轮结果添加轮次信息
                    analysis["round_number"] = eval_round + 1
                    analysis["total_rounds"] = num_evaluations
                    analysis["test_results_path"] = test_results_path
                    analysis["eval_results_path"] = eval_results_path
                    analysis["is_multi_round_evaluation"] = True
                    analysis["round_info"] = {
                        "current_round": eval_round + 1,
                        "total_rounds": num_evaluations,
                        "round_progress": f"{eval_round + 1}/{num_evaluations}",
                        "round_percentage": round((eval_round + 1) / num_evaluations * 100, 2)
                    }
                    
                    all_results.append(analysis)
                    
                    # 提取统计信息用于汇总
                    round_stat = {
                        "round": eval_round + 1,
                        "statistics": analysis["statistics"],
                        "score_distribution": analysis["score_distribution"]
                    }
                    detailed_round_stats.append(round_stat)
                    
                    logger.info(f"第 {eval_round + 1} 轮评估完成")
                    
                except Exception as e:
                    logger.error(f"第 {eval_round + 1} 轮评估失败: {e}")
                    continue
            
            if not all_results:
                raise Exception("所有轮次评估都失败了")
            
            # 生成多轮评估的汇总分析
            final_analysis = self._aggregate_multi_round_results(all_results, detailed_round_stats, original_file_name)
            
            # 保存汇总分析到统一的analysis文件（这是必须的）
            unified_path = self._save_unified_analysis(final_analysis, original_file_name)
            final_analysis["unified_analysis_path"] = unified_path
            
            # 保存详细的多轮汇总分析
            detailed_path = self._save_analysis(final_analysis, original_file_name, "stage2_multi_round_analysis.json")
            final_analysis["detailed_analysis_path"] = detailed_path
            
            # 保存每轮详细结果的CSV文件
            self._save_detailed_round_results(detailed_round_stats, original_file_name)
            
            # 保存所有轮次的原始评估数据汇总
            self._save_all_rounds_raw_data(all_results, original_file_name)
            
            logger.info(f"多轮评估完成，共成功 {len(all_results)} 轮")
            return final_analysis
    
    def _aggregate_multi_round_results(self, all_results: List[Dict[str, Any]], 
                                     detailed_round_stats: List[Dict], 
                                     original_file_name: str) -> Dict[str, Any]:
        """汇总多轮评估结果
        
        Args:
            all_results: 所有轮次的分析结果
            detailed_round_stats: 详细轮次统计
            original_file_name: 原始文件名
            
        Returns:
            Dict: 汇总分析结果
        """
        logger.info(f"开始汇总 {len(all_results)} 轮评估结果")
        
        # 计算汇总统计
        total_questions = all_results[0]["statistics"]["total_questions"]
        
        # 计算各指标的平均值
        avg_knowledge_deficiency = sum(r["statistics"]["knowledge_deficiency"] for r in all_results) / len(all_results)
        avg_reasoning_errors = sum(r["statistics"]["reasoning_errors"] for r in all_results) / len(all_results)
        avg_capability_insufficient = sum(r["statistics"]["capability_insufficient"] for r in all_results) / len(all_results)
        avg_knowledge_deficiency_rate = sum(r["statistics"]["knowledge_deficiency_rate"] for r in all_results) / len(all_results)
        avg_reasoning_error_rate = sum(r["statistics"]["reasoning_error_rate"] for r in all_results) / len(all_results)
        avg_capability_insufficient_rate = sum(r["statistics"]["capability_insufficient_rate"] for r in all_results) / len(all_results)
        
        # 计算方差统计
        knowledge_deficiency_rates = [r["statistics"]["knowledge_deficiency_rate"] for r in all_results]
        reasoning_error_rates = [r["statistics"]["reasoning_error_rate"] for r in all_results]
        capability_insufficient_rates = [r["statistics"]["capability_insufficient_rate"] for r in all_results]
        
        import numpy as np
        knowledge_deficiency_rate_std = float(np.std(knowledge_deficiency_rates))
        reasoning_error_rate_std = float(np.std(reasoning_error_rates))
        capability_insufficient_rate_std = float(np.std(capability_insufficient_rates))
        
        # 构建汇总分析结果
        aggregated_analysis = {
            "model_name": self.model_name,
            "file_name": original_file_name,
            "stage": "stage2",
            "evaluation_rounds": len(all_results),
            "successful_rounds": len(all_results),
            "aggregation_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "thresholds": all_results[0]["thresholds"],
            "aggregated_statistics": {
                "total_questions": total_questions,
                "avg_knowledge_deficiency": avg_knowledge_deficiency,
                "avg_reasoning_errors": avg_reasoning_errors,
                "avg_capability_insufficient": avg_capability_insufficient,
                "avg_knowledge_deficiency_rate": avg_knowledge_deficiency_rate,
                "avg_reasoning_error_rate": avg_reasoning_error_rate,
                "avg_capability_insufficient_rate": avg_capability_insufficient_rate
            },
            "variance_statistics": {
                "knowledge_deficiency_rate_std": knowledge_deficiency_rate_std,
                "reasoning_error_rate_std": reasoning_error_rate_std,
                "capability_insufficient_rate_std": capability_insufficient_rate_std
            },
            "detailed_round_statistics": detailed_round_stats,
            "individual_results": all_results,
            "evaluation_summary": self._generate_evaluation_summary(all_results, detailed_round_stats)
        }
        
        return aggregated_analysis
    
    def _generate_evaluation_summary(self, all_results: List[Dict[str, Any]], 
                                   detailed_round_stats: List[Dict]) -> Dict[str, Any]:
        """生成评估摘要
        
        Args:
            all_results: 所有轮次结果
            detailed_round_stats: 详细轮次统计
            
        Returns:
            Dict: 评估摘要
        """
        # 找到最佳和最差轮次（基于知识缺失率最低）
        best_round = min(detailed_round_stats, key=lambda x: x["statistics"]["knowledge_deficiency_rate"])
        worst_round = max(detailed_round_stats, key=lambda x: x["statistics"]["knowledge_deficiency_rate"])
        
        # 找到最稳定的指标
        variance_metrics = {
            "knowledge_deficiency_rate": [r["statistics"]["knowledge_deficiency_rate"] for r in all_results],
            "reasoning_error_rate": [r["statistics"]["reasoning_error_rate"] for r in all_results],
            "capability_insufficient_rate": [r["statistics"]["capability_insufficient_rate"] for r in all_results]
        }
        
        import numpy as np
        most_stable_metric = min(variance_metrics.keys(), 
                               key=lambda k: np.std(variance_metrics[k]))
        
        return {
            "best_round": {
                "round": best_round["round"],
                "knowledge_deficiency_rate": best_round["statistics"]["knowledge_deficiency_rate"]
            },
            "worst_round": {
                "round": worst_round["round"],
                "knowledge_deficiency_rate": worst_round["statistics"]["knowledge_deficiency_rate"]
            },
            "most_stable_metric": most_stable_metric,
            "performance_range": {
                "knowledge_deficiency_rate_range": [
                    min(r["statistics"]["knowledge_deficiency_rate"] for r in all_results),
                    max(r["statistics"]["knowledge_deficiency_rate"] for r in all_results)
                ]
            }
        }
    
    def _save_unified_analysis(self, analysis: Dict[str, Any], original_file_name: str) -> str:
        """保存统一的分析文件
        
        Args:
            analysis: 分析结果
            original_file_name: 原始文件名
            
        Returns:
            str: 保存的文件路径
        """
        # 从原始文件路径中提取文件名（不含扩展名）
        if isinstance(original_file_name, str):
            base_name = Path(original_file_name).stem
        else:
            base_name = str(original_file_name)
        
        # 转换为结果处理器期望的格式
        unified_analysis = self._convert_to_unified_format(analysis)
        
        # 使用FileManager保存统一的分析文件
        json_content = safe_json_dumps(unified_analysis)
        json_path = self.file_manager.save_file(
            model_name=self.model_name,
            file_name=base_name,
            input_name=f"{base_name}_analysis.json",
            content=json_content,
            file_type='text'
        )
        
        logger.info(f"统一分析文件已保存到: {json_path}")
        return json_path
    
    def _convert_to_unified_format(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """转换分析结果为统一格式
        
        Args:
            analysis: 原始分析结果
            
        Returns:
            Dict: 统一格式的分析结果
        """
        # 检查是否为多轮评估
        is_multi_round = analysis.get("evaluation_rounds", 0) > 1
        
        if is_multi_round:
            # 多轮评估：从aggregated_statistics中获取数据
            stats = analysis.get("aggregated_statistics", {})
            total_questions = stats.get("total_questions", 0)
            knowledge_deficiency = stats.get("avg_knowledge_deficiency", 0)
            reasoning_errors = stats.get("avg_reasoning_errors", 0)
            capability_insufficient = stats.get("avg_capability_insufficient", 0)
            knowledge_deficiency_rate = stats.get("avg_knowledge_deficiency_rate", 0)
            reasoning_error_rate = stats.get("avg_reasoning_error_rate", 0)
            capability_insufficient_rate = stats.get("avg_capability_insufficient_rate", 0)
        else:
            # 单轮评估：从statistics中获取数据
            stats = analysis.get("statistics", {})
            total_questions = stats.get("total_questions", 0)
            knowledge_deficiency = stats.get("knowledge_deficiency", 0)
            reasoning_errors = stats.get("reasoning_errors", 0)
            capability_insufficient = stats.get("capability_insufficient", 0)
            knowledge_deficiency_rate = stats.get("knowledge_deficiency_rate", 0)
            reasoning_error_rate = stats.get("reasoning_error_rate", 0)
            capability_insufficient_rate = stats.get("capability_insufficient_rate", 0)
        
        # 提取阈值信息
        thresholds = analysis.get("thresholds", {
            "answer_threshold": 6.0,
            "reasoning_threshold": 6.0
        })
        
        # 构建统一格式
        unified_analysis = {
            "model_name": analysis.get("model_name", ""),
            "file_name": analysis.get("file_name", ""),
            "thresholds": {
                "stage1": {
                    "answer_threshold": 6.0,
                    "reasoning_threshold": 6.0
                },
                "stage2": thresholds
            },
            "final_correct_answers": 0,  # Stage2没有直接正确的答案
            "final_reasoning_errors": reasoning_errors,
            "final_knowledge_deficiency": knowledge_deficiency,
            "final_capability_insufficient": capability_insufficient,
            "final_accuracy_rate": 0,  # Stage2没有准确率概念
            "final_reasoning_error_rate": reasoning_error_rate,
            "final_knowledge_deficiency_rate": knowledge_deficiency_rate,
            "final_capability_insufficient_rate": capability_insufficient_rate
        }
        
        # 添加评估信息
        if is_multi_round:
            unified_analysis["evaluation_info"] = {
                "is_multi_round_evaluation": True,
                "evaluation_rounds": analysis.get("evaluation_rounds", 1),
                "successful_rounds": analysis.get("successful_rounds", 1),
                "aggregation_timestamp": analysis.get("aggregation_timestamp"),
                "stage1_round_summary": None,
                "stage2_round_summary": {
                    "evaluation_rounds": analysis.get("evaluation_rounds"),
                    "successful_rounds": analysis.get("successful_rounds"),
                    "aggregated_statistics": analysis.get("aggregated_statistics"),
                    "variance_statistics": analysis.get("variance_statistics")
                }
            }
            
            # 添加多轮详细数据
            unified_analysis["multi_round_details"] = {
                "stage1_all_rounds": None,
                "stage2_all_rounds": {
                    "detailed_round_statistics": analysis.get("detailed_round_statistics", []),
                    "individual_results_summary": analysis.get("individual_results", []),
                    "evaluation_summary": analysis.get("evaluation_summary", {})
                },
                "variance_statistics": {
                    "stage1_variance": {},
                    "stage2_variance": analysis.get("variance_statistics", {})
                }
            }
        else:
            unified_analysis["evaluation_info"] = {
                "is_multi_round_evaluation": False,
                "evaluation_timestamp": analysis.get("evaluation_timestamp"),
                "stage1_info": None,
                "stage2_info": {
                    "evaluation_timestamp": analysis.get("evaluation_timestamp"),
                    "statistics": analysis.get("statistics"),
                    "score_distribution": analysis.get("score_distribution"),
                    "data_quality": analysis.get("data_quality")
                }
            }
        
        return unified_analysis

    def run_complete_evaluation(self, file_paths: List[str], 
                               num_evaluations: int = 1,
                               answer_threshold: float = 6.0, 
                               reasoning_threshold: float = 6.0) -> Dict[str, Any]:
        """运行完整的第二阶段评估流程
        
        Args:
            file_paths: stage1输出的CSV文件路径列表
            num_evaluations: 评估次数
            answer_threshold: 答案分数阈值
            reasoning_threshold: 推理分数阈值
            
        Returns:
            Dict: 完整的评估结果
        """
        logger.info("开始运行完整的第二阶段评估流程")
        
        try:
            if num_evaluations > 1:
                return self.run_multiple_evaluations(file_paths, num_evaluations, 
                                                   answer_threshold, reasoning_threshold)
            else:
                # 单次评估
                data_list, original_file_name = self.process_stage1_files(file_paths)
                test_results_path = self.test_llm_responses(data_list, original_file_name)
                eval_results_path = self.evaluate_responses(test_results_path, original_file_name, data_list)
                analysis = self.analyze_results(eval_results_path, original_file_name, 
                                              answer_threshold, reasoning_threshold)
                return analysis
                
        except Exception as e:
            logger.error(f"完整评估流程失败: {e}")
            raise
    



def main():
    """测试Stage2Evaluator功能"""
    try:
        # 创建评估器实例
        evaluator = Stage2Evaluator(model_name="deepseek")
        
        # 测试文件路径 - 使用stage1输出的CSV文件
        test_files = ["data/deepseek/test/stage1_to_stage2_data.csv"]  # 请替换为实际的测试文件路径
        
        print("=== Stage2 评估器测试 ===")
        print(f"测试模型: {evaluator.model_name}")
        print(f"评估模型: {evaluator.eval_model_name}")
        
        # 运行完整评估
        result = evaluator.run_complete_evaluation(
            file_paths=test_files,
            num_evaluations=1,
            answer_threshold=6.0,
            reasoning_threshold=6.0
        )
        
        print("\n=== 评估结果 ===")
        print(f"总问题数: {result['statistics']['total_questions']}")
        print(f"知识能力缺失: {result['statistics']['knowledge_deficiency']}")
        print(f"推理错误: {result['statistics']['reasoning_errors']}")
        print(f"能力不足: {result['statistics']['capability_insufficient']}")
        print(f"知识缺失率: {result['statistics']['knowledge_deficiency_rate']:.2f}%")
        print(f"推理错误率: {result['statistics']['reasoning_error_rate']:.2f}%")
        print(f"能力不足率: {result['statistics']['capability_insufficient_rate']:.2f}%")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()