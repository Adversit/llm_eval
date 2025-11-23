"""
FLMM数据解析模块
用于解析FLMM调研表和自评表Excel文件
"""
import pandas as pd
import re
import os
from typing import Dict, List, Tuple, Optional


def parse_question_content(question_text: str, scenario_name: str = "") -> Tuple[Optional[str], List[str]]:
    """
    解析问题内容，提取问题主干和选项
    处理{name}替换，提取A、B、C、D、E等选项
    """
    if not question_text or question_text in ["nan", "", "调研问题"]:
        return None, []

    # 替换{name}为场景名称
    processed_question = question_text.replace("{name}", scenario_name)

    # 使用正则表达式分离问题主干和选项
    # 匹配模式：问题主干 + 选项（A. B. C. 等）
    pattern = r'(.*?)\s*([A-Z]\..*)'
    match = re.search(pattern, processed_question, re.DOTALL)

    if match:
        question_stem = match.group(1).strip()
        options_text = match.group(2).strip()

        # 提取选项，去掉字母标识，只保留选项内容
        option_pattern = r'[A-Z]\.\s*([^A-Z]*?)(?=[A-Z]\.|$)'
        options = re.findall(option_pattern, options_text, re.DOTALL)
        options = [opt.strip() for opt in options if opt.strip()]

        return question_stem, options
    else:
        # 如果没有找到选项格式，返回原问题
        return processed_question, []


def parse_flmm_questionnaire(file_path: str) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:
    """
    解析FLMM调研表Excel数据
    列结构：能力域、能力子域1、能力子域2、能力项、调研问题

    返回：
        - structure: 四层级嵌套字典结构
        - df: 原始DataFrame
    """
    try:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None, None

        df = pd.read_excel(file_path)
        print(f"Excel文件形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")

        # 构建层次化数据结构
        structure = {}

        # 处理5列结构：能力域、能力子域1、能力子域2、能力项、调研问题
        for index, row in df.iterrows():
            # 跳过完全空行
            if pd.isna(row.iloc[0]) and pd.isna(row.iloc[1]) and pd.isna(row.iloc[2]) and pd.isna(row.iloc[3]) and pd.isna(row.iloc[4]):
                continue

            # 获取各级数据，处理空值和合并单元格
            capability_domain = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
            capability_subdomain1 = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ""
            capability_subdomain2 = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ""
            capability_item = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else ""
            research_question = str(row.iloc[4]).strip() if not pd.isna(row.iloc[4]) else ""

            # 跳过标题行或无效数据
            if capability_domain in ["nan", "能力域", ""] and capability_subdomain1 in ["nan", "能力子域1", ""]:
                continue

            # 处理合并单元格的情况，使用前一个有效值
            if capability_domain == "nan" or capability_domain == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_domain = str(df.iloc[prev_idx, 0]).strip()
                        if prev_domain not in ["nan", "", "能力域"]:
                            capability_domain = prev_domain
                            break

            if capability_subdomain1 == "nan" or capability_subdomain1 == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_subdomain1 = str(df.iloc[prev_idx, 1]).strip()
                        if prev_subdomain1 not in ["nan", "", "能力子域1"]:
                            capability_subdomain1 = prev_subdomain1
                            break

            if capability_subdomain2 == "nan" or capability_subdomain2 == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_subdomain2 = str(df.iloc[prev_idx, 2]).strip()
                        if prev_subdomain2 not in ["nan", "", "能力子域2"]:
                            capability_subdomain2 = prev_subdomain2
                            break

            if capability_item == "nan" or capability_item == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_item = str(df.iloc[prev_idx, 3]).strip()
                        if prev_item not in ["nan", "", "能力项"]:
                            capability_item = prev_item
                            break

            # 只有当调研问题不为空时才添加
            if research_question and research_question not in ["nan", "", "调研问题"]:
                # 构建层次结构：能力域 -> 能力子域1 -> 能力子域2 -> 能力项 -> 调研问题列表
                if capability_domain not in structure:
                    structure[capability_domain] = {}

                if capability_subdomain1 not in structure[capability_domain]:
                    structure[capability_domain][capability_subdomain1] = {}

                if capability_subdomain2 not in structure[capability_domain][capability_subdomain1]:
                    structure[capability_domain][capability_subdomain1][capability_subdomain2] = {}

                if capability_item not in structure[capability_domain][capability_subdomain1][capability_subdomain2]:
                    structure[capability_domain][capability_subdomain1][capability_subdomain2][capability_item] = []

                structure[capability_domain][capability_subdomain1][capability_subdomain2][capability_item].append(research_question)

        return structure, df

    except Exception as e:
        print(f"解析FLMM数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def parse_flmm_evaluation(file_path: str) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:
    """
    解析FLMM自评表Excel数据，用于证明材料收集
    列结构：能力域、能力子域1、能力子域2、能力项

    返回：
        - structure: 四层级嵌套字典结构（能力项为列表）
        - df: 原始DataFrame
    """
    try:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None, None

        df = pd.read_excel(file_path)
        print(f"FLMM自评表文件形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")

        # 构建层次化数据结构
        structure = {}

        # 处理4列结构：能力域、能力子域1、能力子域2、能力项
        for index, row in df.iterrows():
            # 跳过完全空行
            if all(pd.isna(row.iloc[i]) for i in range(4)):
                continue

            # 获取各级数据，处理空值和合并单元格
            capability_domain = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
            capability_subdomain1 = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ""
            capability_subdomain2 = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ""
            capability_item = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else ""

            # 跳过标题行或无效数据
            if capability_domain in ["nan", "能力域", ""] and capability_subdomain1 in ["nan", "能力子域1", ""]:
                continue

            # 处理合并单元格的情况
            if capability_domain == "nan" or capability_domain == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_domain = str(df.iloc[prev_idx, 0]).strip()
                        if prev_domain not in ["nan", "", "能力域"]:
                            capability_domain = prev_domain
                            break

            if capability_subdomain1 == "nan" or capability_subdomain1 == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_subdomain1 = str(df.iloc[prev_idx, 1]).strip()
                        if prev_subdomain1 not in ["nan", "", "能力子域1"]:
                            capability_subdomain1 = prev_subdomain1
                            break

            if capability_subdomain2 == "nan" or capability_subdomain2 == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_subdomain2 = str(df.iloc[prev_idx, 2]).strip()
                        if prev_subdomain2 not in ["nan", "", "能力子域2"]:
                            capability_subdomain2 = prev_subdomain2
                            break

            if capability_item == "nan" or capability_item == "":
                if index > 0:
                    for prev_idx in range(index-1, -1, -1):
                        prev_item = str(df.iloc[prev_idx, 3]).strip()
                        if prev_item not in ["nan", "", "能力项"]:
                            capability_item = prev_item
                            break

            # 只有当能力项不为空时才添加
            if capability_item and capability_item not in ["nan", "", "能力项"]:
                # 构建层次结构
                if capability_domain not in structure:
                    structure[capability_domain] = {}

                if capability_subdomain1 not in structure[capability_domain]:
                    structure[capability_domain][capability_subdomain1] = {}

                if capability_subdomain2 not in structure[capability_domain][capability_subdomain1]:
                    structure[capability_domain][capability_subdomain1][capability_subdomain2] = set()

                structure[capability_domain][capability_subdomain1][capability_subdomain2].add(capability_item)

        # 将集合转换为列表
        for domain in structure:
            for subdomain1 in structure[domain]:
                for subdomain2 in structure[domain][subdomain1]:
                    structure[domain][subdomain1][subdomain2] = list(structure[domain][subdomain1][subdomain2])

        return structure, df

    except Exception as e:
        print(f"解析FLMM自评表失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def get_flmm_questionnaire_structure(base_path: str = None) -> Dict:
    """获取FLMM调研表结构"""
    if base_path is None:
        # 获取项目根目录（backend的上一级目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        base_path = os.path.join(project_root, "data", "flmm")

    file_path = os.path.join(base_path, "FLMM调研表.xlsx")
    structure, _ = parse_flmm_questionnaire(file_path)
    return structure if structure else {}


def get_flmm_evaluation_structure(base_path: str = None) -> Dict:
    """获取FLMM自评表结构"""
    if base_path is None:
        # 获取项目根目录（backend的上一级目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        base_path = os.path.join(project_root, "data", "flmm")

    file_path = os.path.join(base_path, "FLMM自评表.xlsx")
    structure, _ = parse_flmm_evaluation(file_path)
    return structure if structure else {}
