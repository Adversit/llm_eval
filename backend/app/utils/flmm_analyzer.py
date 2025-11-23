"""
FLMM问卷结果分析工具
调用00k目录中的分析函数
"""
import sys
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from collections import Counter

# 添加00k目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '00k'))

# 导入00k中的分析函数
try:
    from function.Admin_analyse_function_page import (
        get_available_projects,
        load_questionnaire_results,
        load_questionnaire_file,
        get_option_mapping,
        analyze_single_choice_question,
        analyze_multiple_choice_question,
        generate_overall_statistics,
        create_capability_distribution_chart,
        calculate_question_expectation,
        analyze_user_demand_matching,
        analyze_automation_improvement,
        analyze_decision_support,
        analyze_customer_loyalty,
        analyze_time_cost_saving
    )
    FLMM_FUNCTIONS_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入00k分析函数: {e}")
    FLMM_FUNCTIONS_AVAILABLE = False


# ========== 辅助函数 ==========

def convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def get_projects_list(base_path: str = None) -> List[Dict[str, Any]]:
    """
    获取所有FLMM评估项目列表

    Returns:
        项目列表，每个项目包含folder_name, result_file, project_info等
    """
    if not FLMM_FUNCTIONS_AVAILABLE:
        return []

    if base_path is None:
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        base_path = os.path.join(project_root, "data", "flmm", "projects")

    projects = []

    if not os.path.exists(base_path):
        return projects

    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            # 查找评估结果文件
            result_files = [f for f in os.listdir(item_path) if f.endswith('_评估结果.xlsx')]
            if result_files:
                # 尝试读取项目信息
                json_files = [f for f in os.listdir(item_path)
                             if f.endswith('.json') and not f.endswith('_评估结果.json')
                             and not f.endswith('_证明材料上传记录.json')]
                project_info = None
                if json_files:
                    try:
                        import json
                        with open(os.path.join(item_path, json_files[0]), 'r', encoding='utf-8') as f:
                            project_info = json.load(f)
                    except:
                        project_info = None

                projects.append({
                    'folder_name': item,
                    'result_file': os.path.join(item_path, result_files[0]),
                    'project_info': project_info,
                    'display_name': item.replace('_', ' - ')
                })

    return projects


def load_project_results(project_folder: str) -> Optional[pd.DataFrame]:
    """
    加载项目的评估结果Excel文件

    Args:
        project_folder: 项目文件夹名称（如：中金公司_投研大模型）

    Returns:
        DataFrame或None
    """
    try:
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        result_file_path = os.path.join(project_root, "data", "flmm", "projects", project_folder)

        result_files = [f for f in os.listdir(result_file_path) if f.endswith('_评估结果.xlsx')]

        if not result_files:
            return None

        full_path = os.path.join(result_file_path, result_files[0])
        df = pd.read_excel(full_path)
        return df
    except Exception as e:
        print(f"加载项目结果失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_basic_statistics(project_folder: str) -> Optional[Dict[str, Any]]:
    """
    获取项目的基本统计信息

    Args:
        project_folder: 项目文件夹名称

    Returns:
        统计信息字典
    """
    df = load_project_results(project_folder)
    if df is None:
        return None

    if not FLMM_FUNCTIONS_AVAILABLE:
        return None

    stats = generate_overall_statistics(df)
    # 转换numpy类型为Python原生类型
    return convert_numpy_types(stats) if stats else None


def analyze_project_questions(project_folder: str) -> Optional[List[Dict[str, Any]]]:
    """
    逐题分析项目的所有问题

    Args:
        project_folder: 项目文件夹名称

    Returns:
        每题的分析结果列表
    """
    df = load_project_results(project_folder)
    if df is None or not FLMM_FUNCTIONS_AVAILABLE:
        return None

    # 加载原始问卷文件用于选项映射
    questionnaire_df = None
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        questionnaire_path = os.path.join(project_root, "data", "flmm", "projects", project_folder)
        questionnaire_files = [f for f in os.listdir(questionnaire_path) if f.endswith('_问卷.xlsx')]
        if questionnaire_files:
            questionnaire_df = pd.read_excel(os.path.join(questionnaire_path, questionnaire_files[0]))
    except:
        pass

    results = []
    unique_questions = df[['题号', '问题', '问题类型']].drop_duplicates()

    for _, row in unique_questions.iterrows():
        question_num = row['题号']
        question_text = row['问题']
        question_type = row['问题类型']

        question_data = df[df['题号'] == question_num]
        total_responses = len(question_data)

        # 统计答案分布
        if question_type == '单选题':
            answer_counts = question_data['回答'].value_counts().to_dict()
            option_mapping = get_option_mapping(questionnaire_df, question_text) if questionnaire_df is not None else {}
        elif question_type == '多选题':
            # 多选题需要特殊处理
            option_counts = Counter()
            for answer in question_data['回答']:
                if pd.notna(answer) and answer:
                    options = answer.split(';')
                    for option in options:
                        option = option.strip()
                        if option:
                            option_counts[option] += 1
            answer_counts = dict(option_counts)
            option_mapping = get_option_mapping(questionnaire_df, question_text) if questionnaire_df is not None else {}
        else:
            answer_counts = {}
            option_mapping = {}

        results.append({
            'question_num': int(question_num) if pd.notna(question_num) else 0,
            'question_text': str(question_text),
            'question_type': str(question_type),
            'total_responses': int(total_responses),
            'answer_distribution': convert_numpy_types(answer_counts),
            'option_mapping': option_mapping
        })

    return results


def calculate_five_ratings(project_folder: str) -> Optional[Dict[str, Any]]:
    """
    计算FLMM的5个维度评级

    Args:
        project_folder: 项目文件夹名称

    Returns:
        5个维度的评级结果
    """
    df = load_project_results(project_folder)
    if df is None or not FLMM_FUNCTIONS_AVAILABLE:
        return None

    ratings = {}

    # 1. 用户需求匹配度
    try:
        rating1 = analyze_user_demand_matching(df)
        if rating1:
            ratings['user_demand_matching'] = {
                'name': '用户需求匹配度',
                'score': int(rating1.get('final_score', 0)),
                'description': rating1.get('final_rating_description', ''),
                'details': convert_numpy_types(rating1.get('details', {}))
            }
    except Exception as e:
        print(f"计算用户需求匹配度失败: {e}")

    # 2. 业务自动化提升率
    try:
        rating2 = analyze_automation_improvement(df)
        if rating2:
            ratings['automation_improvement'] = {
                'name': '业务自动化提升率',
                'score': int(rating2.get('final_score', 0)),
                'description': rating2.get('final_rating_description', ''),
                'details': convert_numpy_types(rating2.get('details', {}))
            }
    except Exception as e:
        print(f"计算业务自动化提升率失败: {e}")

    # 3. 业务决策支持力
    try:
        rating3 = analyze_decision_support(df)
        if rating3:
            ratings['decision_support'] = {
                'name': '业务决策支持力',
                'score': int(rating3.get('final_score', 0)),
                'description': rating3.get('final_rating_description', ''),
                'details': convert_numpy_types(rating3.get('details', {}))
            }
    except Exception as e:
        print(f"计算业务决策支持力失败: {e}")

    # 4. 客户忠诚度
    try:
        rating4 = analyze_customer_loyalty(df)
        if rating4:
            ratings['customer_loyalty'] = {
                'name': '客户忠诚度',
                'score': int(rating4.get('final_score', 0)),
                'description': rating4.get('final_rating_description', ''),
                'details': convert_numpy_types(rating4.get('details', {}))
            }
    except Exception as e:
        print(f"计算客户忠诚度失败: {e}")

    # 5. 时间成本节约率
    try:
        rating5 = analyze_time_cost_saving(df)
        if rating5:
            ratings['time_cost_saving'] = {
                'name': '时间成本节约率',
                'score': int(rating5.get('final_score', 0)),
                'description': rating5.get('final_rating_description', ''),
                'details': convert_numpy_types(rating5.get('details', {}))
            }
    except Exception as e:
        print(f"计算时间成本节约率失败: {e}")

    return ratings
