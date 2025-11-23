"""
净利润分析LLM服务模块
包含净利润分析相关的所有LLM功能
"""

import json
import traceback
import streamlit as st
import pandas as pd
from .base_llm_service import format_value_for_ai


# 定义盈利分析子指标的类型 (收益/成本)
PROFIT_SUB_METRIC_TYPES = {
    "营业总收入": "收益",
    "营业成本": "成本",
    "税金及附加": "成本",
    "销售费用": "成本",
    "管理费用": "成本",
    "研发费用": "成本",
    "财务费用": "成本",
    "其他收益": "收益",
    "投资收益": "收益",
    "净敞口套期收益": "收益",
    "公允价值变动收益": "收益",
    "信用减值损失": "成本", # 损失为负值，损失减少（delta为正）是好事
    "资产减值损失": "成本", # 损失为负值，损失减少（delta为正）是好事
    "资产处置收益": "收益",
    "营业外收入": "收益",
    "营业外支出": "成本",
    "所得税费用": "成本",
    # 根据实际 PROFIT_STATEMENT_STRUCTURE_FLAT 的 value 可能需要调整或补充
    "主营业务收入": "收益",
    "其他业务收入": "收益",
    "主营业务成本": "成本",
    "其他业务成本": "成本",
    "利息收入": "收益", # 通常计入财务费用，但若单独列示
    "利息支出": "成本", # 通常计入财务费用
    "汇兑收益": "收益", # 通常计入财务费用，收益为正，损失为负
}


def get_net_profit_inflection_points(client, model_name, series_data_string, original_col_name):
    """
    识别净利润时间序列中的重要转折点（拐点）并返回JSON格式结果
    """
    system_prompt = f"""你是一位专业的财务分析师。你的任务是识别'{original_col_name}'时间序列中的重要转折点（拐点）。

重要转折点定义为**明确的方向性趋势发生逆转**的点，这些点必须位于时间序列的**中间位置**，不能是起始点或终端点。

转折点类型：
- **峰值拐点**：该点的数值比前一个点高，且比后一个点高，标志着上升趋势转为下降趋势
- **谷值拐点**：该点的数值比前一个点低，且比后一个点低，标志着下降趋势转为上升趋势

对于每个识别出的真正转折点，请提供：
1. "t0_date": 转折点的日期（使用输入数据中的YYYY-MM-DD格式）
2. "description": 对为什么这个日期是重要转折点的简要解释（例如："峰值：趋势从增长转为下降"，"谷值：趋势从下降转为增长"）
3. "trend_after_point": 该转折点**之后立即开始的新趋势方向**。可能的值："growth"（如果趋势转为上升）或"decline"（如果趋势转为下降）

**识别规则：**
- 峰值：当前值 > 前一个值 且 当前值 > 后一个值，"trend_after_point"="decline"
- 谷值：当前值 < 前一个值 且 当前值 < 后一个值，"trend_after_point"="growth"

**严格排除以下情况：**
- **绝对不要识别第一个数据点**（时间序列的起始点）
- **绝对不要识别最后一个数据点**（时间序列的终端点）
- 只有微小变化的点（变化幅度不足以构成明显转折）
- 平台期中的小波动

**分析步骤：**
1. 忽略第一个和最后一个数据点
2. 对于中间的每个点，检查它是否同时满足：前值→当前值→后值的关系形成明显的峰值或谷值
3. 只识别真正的局部极值点

将结果输出为JSON对象列表，每个对象包含"t0_date"、"description"和"trend_after_point"。

：
2023-06-30    100
2023-09-30    150
2023-12-31    200  ← 峰值（200>150且200>120）
2024-03-31    120  ← 谷值（120<200且120<180）
2024-06-30    180  ← 峰值（180>120且180>160）
2024-09-30    160
2024-12-31    140
2025-03-31    130  ← 终端点，不识别

JSON输出示例：
[
  {{ "t0_date": "2023-12-31", "description": "峰值：趋势从增长转为下降", "trend_after_point": "decline" }},
  {{ "t0_date": "2024-03-31", "description": "谷值：趋势从下降转为增长", "trend_after_point": "growth" }},
  {{ "t0_date": "2024-06-30", "description": "峰值：趋势从增长转为下降", "trend_after_point": "decline" }}
]

如果在数据中没有找到符合条件的拐点，请返回空列表"[]"。
记住：绝对不要将第一个点或最后一个点识别为拐点！


实际数据：（'{original_col_name}'，8个数据点）

"""
    user_prompt = f"以下是'{original_col_name}'数据（确保你的JSON输出中的't0_date'使用这些确切的日期，并包含'trend_after_point'）：\n{series_data_string}\n请识别重要的转折点并按指定的JSON格式输出。"

    raw_response_content = "N/A"
    json_string_to_parse = ""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        raw_response_content = response.choices[0].message.content
        json_string_to_parse = raw_response_content.strip()

        if json_string_to_parse.startswith("```json"):
            json_string_to_parse = json_string_to_parse[7:]
        if json_string_to_parse.startswith("```"):
            json_string_to_parse = json_string_to_parse[3:]
        if json_string_to_parse.endswith("```"):
            json_string_to_parse = json_string_to_parse[:-3]
        json_string_to_parse = json_string_to_parse.strip()

        if not json_string_to_parse: # Handle empty string after stripping
             return {"success": False, "error_message": "AI returned an empty response after cleaning.",
                    "traceback_str": "AI response was empty or only contained markdown backticks.",
                    "raw_response_content": raw_response_content}

        parsed_json = json.loads(json_string_to_parse)
        if isinstance(parsed_json, list):
            return {"success": True, "data": parsed_json}
        else:
            return {"success": False,
                    "error_message": f"AI未按预期返回拐点列表 (返回类型: {type(parsed_json)}), 而是一个JSON对象。",
                    "traceback_str": f"Expected a JSON list, but got {type(parsed_json)}.",
                    "raw_response_content": json_string_to_parse} # Return the parsed, non-list JSON

    except json.JSONDecodeError as jde:
        return {"success": False,
                "error_message": f"AI未能返回有效的JSON格式用于拐点分析: {str(jde)}",
                "traceback_str": traceback.format_exc(),
                "raw_response_content": raw_response_content,
                "attempted_parse_string": json_string_to_parse}
    except Exception as e:
        return {"success": False,
                "error_message": f"调用LLM识别 '{original_col_name}' 拐点时发生意外错误: {str(e)}",
                "traceback_str": traceback.format_exc(),
                "raw_response_content": raw_response_content}


def get_summary_part1_current_situation(client, model_name, current_period_data, primary_metric_col):
    """生成财务分析报告的第一部分：当前报告期XX环比变化情况。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据提供的财务数据，生成财务分析报告的第一部分。
**重要：你的回答不应包含此部分的标题（例如："1. 当前报告期XX环比变化情况"）或章节编号。**
报告应严格遵循以下内容结构，并使用中文撰写：

   - **绝对变化**：明确指出 {primary_metric_col} (净利润) 从上一期到当前报告期的绝对值变化（例如，从X增加/减少到Y，环比增加/减少Z金额）以及相对变化百分比。
     当发生由盈转亏或由亏转盈时，变化百分比可能超过100%或出现符号反转，请简要说明是由于盈亏状态转变导致，而非简单理解为基数符号问题。**仅陈述数据，不包含任何原因分析或影响解读。**
   # Removed the "趋势描述" (Trend Description) requirement.

**通用指令：**
- **禁止信息解读**：内容仅陈述指标的数值变化，严格禁止进行任何原因分析、影响判断、趋势解读或业务场景联想。
- **数据驱动**：所有分析和结论都必须基于用户提供的数据。
- **专业术语**：使用专业财务术语，但要确保语言简明扼要，易于业务人员理解。
- **客观中立**：保持客观的分析立场。
- **智能数值格式化**：
    - 对于金额数值，请智能选择最合适的单位：
      * 10万以下：使用"元"（如：85,000元）
      * 10万-1000万：使用"万元"（如：151.03万元）
      * 1000万以上：使用"亿元"（如：1.15亿元）
    - 确保数值转换的准确性，保留合适的小数位数（一般保留1-2位小数）
    - 变化量请保留正负号
- **处理缺失数据**：如果数据不完整 (例如 'N/A')，请在报告中明确指出。
- **突出重点**：总结性、重点观点可用markdown格式的加粗。

请严格按照上述结构和要求生成报告的这【第一部分】。
"""

    current_data_summary_parts = [
        f"当前报告期基础数据:",
        f"- 主要指标 ({primary_metric_col}):",
        f"  - {current_period_data.get('current_to_date', 'N/A')} 值: {format_value_for_ai(current_period_data.get(f'current_{primary_metric_col}_t0'))}",
        f"  - {current_period_data.get('current_from_date', 'N/A')} 值: {format_value_for_ai(current_period_data.get(f'current_{primary_metric_col}_t_minus_1'))}",
        f"  - 环比变化量: {format_value_for_ai(current_period_data.get(f'current_delta_{primary_metric_col}'))}",
    ]
    
    user_prompt = "请根据以下当前报告期数据，生成财务分析报告的第一部分：\n" + "\n".join(current_data_summary_parts)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, 
            stream=True      
        )
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
    except Exception as e:
        yield f"调用AI总结第一部分时出错: {str(e)}"


def get_summary_part2_driving_factors(client, model_name, current_period_data, primary_metric_col, secondary_metric_info, context_part1):
    """生成财务分析报告的第二部分：当前报告期驱动因素分析。使用预计算的子指标影响。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
**非常重要：你必须严格遵循以下所有指令。在你的回答中，严禁使用任何形式的"积极"、"消极"、"正向"、"负向"、"有利"、"不利"、"好"、"坏"等评价性词汇或类似表达。你的任务是客观地呈现预先分析好的信息。**

你是一位非常优秀的财务分析AI专家，专注于成本分析。你的任务是根据提供的财务数据、【已生成的成本报告第一部分内容】以及【预先分析好的各成本构成子指标业务影响解读】，生成成本分析报告的第二部分。

**格式和标题指令：**
- 你的回答不应包含此部分的总标题（例如："2. 当前报告期净利润驱动因素分析"）或章节编号。
- 子章节的标题必须严格使用以下指定的标题，不得修改：
  - "对净利润增长起到促进作用的因素"
  - "对净利润增长起到阻碍作用的因素"  
  - "对净利润降低起到促进作用的因素"
  - "对净利润降低起到阻碍作用的因素"

报告应严格遵循以下内容结构，并使用中文撰写：

   - **净利润概览**：
     基于【报告第一部分内容】，清晰总结当前报告期内 {primary_metric_col} (净利润) 自身的整体变化情况（例如，"{primary_metric_col} 较上一报告期增加/减少XXX万元，增/降幅XX%"）。
     **重要指令：在此概览部分，请仅陈述 {primary_metric_col} 的总体变化事实。禁止对导致这一变化的驱动因素的性质进行任何初步判断或总结。**

   - **净利润驱动因素分析**：
     根据预分析结论中的 `impact_type`，将子指标分类到相应的标题下，每个类别最多只显示前3个最重要的因素（贡献度绝对值最大的3个）：
     
     - **对净利润增长起到促进作用的因素** (找出 `impact_type` 为【对净利润增长起到促进作用】的子指标)
     - **对净利润增长起到阻碍作用的因素** (找出 `impact_type` 为【对净利润增长起到阻碍作用】的子指标)
     - **对净利润降低起到促进作用的因素** (找出 `impact_type` 为【对净利润降低起到促进作用】的子指标)
     - **对净利润降低起到阻碍作用的因素** (找出 `impact_type` 为【对净利润降低起到阻碍作用】的子指标)
     
     **注意：只显示有相应子指标的标题。如果某个类别没有子指标，则不显示该标题。**
     
     对于每个被列出的子指标，你必须严格遵循以下要求：
     - 清晰陈述其指标名称。
     - 准确引用其【自身环比变化量】和【对 {primary_metric_col} 变化的贡献度(%)】的数值 (这些数据均在预分析解读中明确提供)。
     - **业务影响说明：对于此子指标的业务影响，你必须且只能使用预分析解读中提供的 `explanation` 字段的完整原文。不要添加、修改或总结此 `explanation`。不要使用任何其他评价性词语。**

   - **其他影响不显著或数据缺失的因素提及 (可选)**：
     - 如果存在 `impact_type` 为【无显著影响】或【数据缺失】的子指标，可以在报告末尾简要提及，并直接使用其 `explanation` 原文。

**通用指令：**
- **严格依赖预分析结论**：你的核心任务是基于用户提供的、已经过计算和解释的各子指标业务影响，进行准确的分类、组织和忠实的呈现。所有关于子指标影响的描述都必须直接来自预分析的 `explanation` 字段。
- **禁止自行推断或评价**：请勿进行任何数据中未直接体现的深层原因推测、业务场景联想、或对预设核心结论的任何形式的再加工或评价。
- **客观中立**：你的所有输出都必须保持客观中立，不包含任何主观评价。
- **承接上文**：你的分析应自然地承接【报告第一部分内容】。
- **数据驱动**：所有引用的数值（变化量、贡献度）必须精确来自用户在预分析解读中提供的数据。
- **专业术语**：使用专业财务术语。
- **智能数值格式化**：
    - 在描述变化量时，请将原始数值智能转换为更易读的格式：
      * 10万以下：使用"元"（如：自身环比变化量+8.5万元）
      * 10万-1000万：使用"万元"（如：自身环比变化量+151.03万元）
      * 1000万以上：使用"亿元"（如：自身环比变化量+1.15亿元）
    - 确保数值转换的准确性，保留合适的小数位数
    - 变化量保留正负号，贡献度保持百分比格式
- **突出重点**：重点观点语句以及重点数据可用markdown格式的加粗。

请严格按照上述结构和要求生成报告的这【第二部分】。
"""
    # 准备预分析的子指标数据
    interpreted_secondary_metrics = []
    primary_metric_delta_val = current_period_data.get(f'current_delta_{primary_metric_col}')

    if primary_metric_delta_val is None or pd.isna(primary_metric_delta_val):
        yield f"主成本指标 {primary_metric_col} 变化量未知或数据不适用，无法进行驱动因素分析。"
        return

    for sm_info in secondary_metric_info:
        sm_name_key = sm_info['name'] # 内部key
        sm_display_name = sm_info['displayName'] # 用户看到的中文名
        
        sm_delta = current_period_data.get(f'current_delta_{sm_name_key}')
        sm_contrib = current_period_data.get(f'current_contribution_{sm_name_key}')
        
        # 从 PROFIT_SUB_METRIC_TYPES 获取类型，默认为 "未知类型"
        sub_metric_type = PROFIT_SUB_METRIC_TYPES.get(sm_display_name, "未知类型")
        # 进一步确认，如果 sm_name_key 在里面也用它
        if sub_metric_type == "未知类型" and sm_name_key in PROFIT_SUB_METRIC_TYPES:
             sub_metric_type = PROFIT_SUB_METRIC_TYPES.get(sm_name_key, "未知类型")

        interpretation_result = interpret_sub_metric_impact(
            primary_metric_name=primary_metric_col,
            primary_metric_delta=primary_metric_delta_val,
            sub_metric_display_name=sm_display_name,
            sub_metric_delta=sm_delta,
            sub_metric_contribution=sm_contrib,
            sub_metric_type=sub_metric_type,
            is_primary_metric_increase_good=True  # For profit analysis
        )
        interpreted_secondary_metrics.append({
            "name_display": sm_display_name,
            "delta_formatted": format_value_for_ai(sm_delta),
            "contribution_formatted": f"{sm_contrib:+.1f}%" if isinstance(sm_contrib, (int, float)) and not pd.isna(sm_contrib) else "N/A",
            "impact_type": interpretation_result["impact_type"],
            "explanation": interpretation_result["explanation"]
        })

    # 构建 User Prompt
    user_prompt_part2_intro = f"请参考以下预先分析好的各子指标对 {primary_metric_col} 的业务影响解读：\n"
    user_prompt_part2_details = []
    for item in interpreted_secondary_metrics:
        user_prompt_part2_details.append(
            f"- 指标名称: {item['name_display']}\n"
            f"  - 自身环比变化量: {item['delta_formatted']}\n"
            f"  - 对 {primary_metric_col} 变化的贡献度: {item['contribution_formatted']}\n"
            f"  - **预分析结论**: 影响类型为【{item['impact_type']}】。解读：{item['explanation']}"
        )
    
    user_prompt = (f"以下是已生成的【报告第一部分内容】：\n{context_part1}\n\n" 
                   f"请基于以上第一部分内容和以下【预先分析好的各子指标影响解读】，继续撰写【报告第二部分：当前报告期驱动因素分析】({primary_metric_col}分析)：\n" +
                   user_prompt_part2_intro + "\n".join(user_prompt_part2_details))

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, 
            stream=True      
        )
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
    except Exception as e:
        yield f"调用AI总结第二部分(基于预分析)时出错: {str(e)}"


def get_summary_part3_yoy_comparison(client, model_name, full_summary_data, primary_metric_col, secondary_metric_info, context_part1_part2):
    """生成财务分析报告的第三部分：与去年同期对比分析（采用预计算方式）。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据提供的财务数据、【已生成的报告前两部分内容】以及【预先分析好的各净利润子指标完整对比分析】，生成财务分析报告的第三部分。

**最重要的要求：对于子指标分析，你必须逐字逐句地完整复制预分析结论中的 `complete_analysis` 内容，严禁进行任何形式的修改、总结、重新表述或语言优化。**

**重要输出原则：**
1. **结构：** 对于每一项分析，请务必遵循【先给出核心观点/结论，再进行详细数据支持和逻辑阐述】的结构。
2. **格式：** 你的回答不应包含此部分的标题或章节编号。所有输出均为纯文本，严禁包含任何Markdown表格、HTML表格或任何其他形式的表格。
3. **语言要求：** 使用通俗易懂的语言，避免使用"同比"、"环比"等专业术语，改用"相较于去年同期"、"今年与去年相比"等更直观的表述。
4. **智能数值格式化：** 在复制预分析结论时，如果其中包含大数值，请智能转换为更易读的格式：
   - 10万以下：使用"元"（如：8.5万元）
   - 10万-1000万：使用"万元"（如：151.03万元）
   - 1000万以上：使用"亿元"（如：1.15亿元）
   - 确保转换准确性，保留合适的小数位数

**分析内容结构：**

   - **主指标总体评价**：
     首先分析 {primary_metric_col} (净利润) 本身相较于去年同期的变化表现，给出总体结论。

   - **子指标对比分析**：
     对每个子指标，你必须严格按照以下格式输出：
     
     **[子指标名称]：**
     [完整复制预分析结论中的complete_analysis内容，但需要将其中的数值转换为更易读的格式]
     
     **绝对禁止的行为：**
     - 禁止修改预分析结论中的任何逻辑和表述
     - 禁止重新组织预分析结论的语言结构
     - 禁止总结或简化预分析结论的内容
     - 禁止添加自己的解释或评价
     - 禁止改变预分析结论的判断和观点
     
     **允许的行为：**
     - 将预分析结论中的大数值转换为更易读的万元、亿元格式
     - 保持原有的逻辑结构和表述方式

   - **整体盈利表现总结**：
     基于主指标和各子指标的分析，对本期整体盈利表现相较去年同期给出明确判断（改善/恶化/结构分化），并总结关键驱动因素。

**严格执行指令：**
- **完全依赖预分析结论**：你的唯一任务是将预分析结论中的 `complete_analysis` 字段内容原封不动地复制到相应的子指标分析中，仅允许进行数值格式的优化。
- **数值格式优化原则**：对于子指标分析部分，你可以将预分析结论中的数值转换为更易读的格式，但不得对其他任何内容进行修改。
- **逐字复制+格式优化**：必须逐字逐句地复制预分析结论，同时将大数值智能转换为万元、亿元格式。
- **格式要求**：只需要在每个子指标名称前加上"**[子指标名称]：**"的格式标识，然后完整复制预分析结论（数值已优化格式）。

**示例格式：**

**营业总收入：**
今年营业总收入的变化量为-203.20万元，比去年同期的-132.96万元少了+70.23万元，该项收益表现恶化。 从子指标贡献度变化情况看，营业总收入对*净利润(元)下降的贡献度从去年同期的+758.2%上升至今年的+842.3%，其加剧下降的负向作用增强。

请严格按照上述要求生成报告的这【第三部分】。记住：对于子指标分析，你的任务就是复制粘贴+数值格式优化，不是创作。
"""

    # 预分析所有子指标的同比对比
    interpreted_yoy_metrics = []
    primary_metric_delta_current = full_summary_data.get(f'current_delta_{primary_metric_col}')
    primary_metric_delta_ly = full_summary_data.get(f'ly_delta_{primary_metric_col}')

    # 分析主指标的同比变化
    primary_diff_delta = None
    if pd.notna(primary_metric_delta_current) and pd.notna(primary_metric_delta_ly):
        primary_diff_delta = primary_metric_delta_current - primary_metric_delta_ly

    primary_yoy_analysis = {
        "metric_name": primary_metric_col,
        "current_delta": format_value_for_ai(primary_metric_delta_current),
        "ly_delta": format_value_for_ai(primary_metric_delta_ly),
        "diff_delta": format_value_for_ai(primary_diff_delta),
        "analysis": ""
    }

    if pd.notna(primary_diff_delta):
        if primary_diff_delta > 0.01:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量增加了{format_value_for_ai(primary_diff_delta)}，盈利表现改善。"
        elif primary_diff_delta < -0.01:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量减少了{format_value_for_ai(abs(primary_diff_delta))}，盈利表现恶化。"
        else:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量基本持平，盈利表现稳定。"
    else:
        primary_yoy_analysis["analysis"] = f"由于{primary_metric_col}的当前期或去年同期数据缺失，无法进行有效的对比分析。"

    # 预分析各子指标
    for sm_info in secondary_metric_info:
        sm_name_key = sm_info['name']
        sm_display_name = sm_info['displayName']
        
        sm_delta_current = full_summary_data.get(f'current_delta_{sm_name_key}')
        sm_delta_ly = full_summary_data.get(f'ly_delta_{sm_name_key}')
        sm_contrib_current = full_summary_data.get(f'current_contribution_{sm_name_key}')
        sm_contrib_ly = full_summary_data.get(f'ly_contribution_{sm_name_key}')
        
        # 从 PROFIT_SUB_METRIC_TYPES 获取类型，默认为 "未知类型"
        sub_metric_type = PROFIT_SUB_METRIC_TYPES.get(sm_display_name, "未知类型")
        if sub_metric_type == "未知类型" and sm_name_key in PROFIT_SUB_METRIC_TYPES:
             sub_metric_type = PROFIT_SUB_METRIC_TYPES.get(sm_name_key, "未知类型")

        yoy_interpretation_result = interpret_profit_yoy_comparison_details(
            primary_metric_name=primary_metric_col,
            primary_metric_delta_current=primary_metric_delta_current,
            primary_metric_delta_ly=primary_metric_delta_ly,
            sub_metric_display_name=sm_display_name,
            sub_metric_delta_current=sm_delta_current,
            sub_metric_delta_ly=sm_delta_ly,
            sub_metric_contribution_current=sm_contrib_current,
            sub_metric_contribution_ly=sm_contrib_ly,
            sub_metric_type=sub_metric_type
        )
        
        interpreted_yoy_metrics.append({
            "name_display": sm_display_name,
            "analysis_type": yoy_interpretation_result["analysis_type"],
            "complete_analysis": yoy_interpretation_result["complete_analysis"],
            "formatted_data": yoy_interpretation_result["formatted_data"]
        })

    # 构建 User Prompt
    user_prompt_part3_intro = f"请参考以下预先分析好的各净利润子指标完整对比分析：\n\n"
    
    # 主指标分析
    user_prompt_part3_intro += f"**主指标 {primary_metric_col} 对比分析：**\n"
    user_prompt_part3_intro += f"- 今年变化量: {primary_yoy_analysis['current_delta']}\n"
    user_prompt_part3_intro += f"- 去年同期变化量: {primary_yoy_analysis['ly_delta']}\n"
    user_prompt_part3_intro += f"- 变化量差异: {primary_yoy_analysis['diff_delta']}\n"
    user_prompt_part3_intro += f"- **预分析结论**: {primary_yoy_analysis['analysis']}\n\n"
    
    # 子指标分析
    user_prompt_part3_intro += f"**各净利润子指标完整对比分析：**\n"
    user_prompt_part3_details = []
    for item in interpreted_yoy_metrics:
        user_prompt_part3_details.append(
            f"- 指标名称: {item['name_display']}\n"
            f"  - 今年变化量: {item['formatted_data']['current_delta']}\n"
            f"  - 去年同期变化量: {item['formatted_data']['ly_delta']}\n"
            f"  - 今年贡献度: {item['formatted_data']['current_contrib']}\n"
            f"  - 去年同期贡献度: {item['formatted_data']['ly_contrib']}\n"
            f"  - **预分析完整结论**: {item['complete_analysis']}"
        )

    # 添加调试输出
    debug_info = f"\n\n=== 调试信息 ===\n"
    debug_info += f"主指标变化方向: {'增长' if pd.notna(primary_metric_delta_current) and primary_metric_delta_current > 0 else '下降' if pd.notna(primary_metric_delta_current) and primary_metric_delta_current < 0 else '未知'}\n"
    debug_info += f"主指标当前期变化量: {format_value_for_ai(primary_metric_delta_current)}\n"
    debug_info += f"主指标去年同期变化量: {format_value_for_ai(primary_metric_delta_ly)}\n\n"
    
    for item in interpreted_yoy_metrics:
        debug_info += f"【{item['name_display']}】预计算完整结论:\n{item['complete_analysis']}\n\n"
    
    debug_info += "=== 调试信息结束 ===\n\n"

    user_prompt = (f"以下是已生成的【报告第一、二部分内容】：\n{context_part1_part2}\n\n" 
                   f"请基于以上前两部分内容和以下【预先分析好的净利润同比对比解读】，继续撰写【报告第三部分：与去年同期对比分析】：\n\n" +
                   user_prompt_part3_intro + "\n".join(user_prompt_part3_details) + debug_info)

    # 后台调试输出
    print("\n" + "="*80)
    print("【盈利分析第三部分 - 后台调试信息】")
    print("="*80)
    print(f"主指标变化方向: {'增长' if pd.notna(primary_metric_delta_current) and primary_metric_delta_current > 0 else '下降' if pd.notna(primary_metric_delta_current) and primary_metric_delta_current < 0 else '未知'}")
    print(f"主指标当前期变化量: {format_value_for_ai(primary_metric_delta_current)}")
    print(f"主指标去年同期变化量: {format_value_for_ai(primary_metric_delta_ly)}")
    print("\n【各子指标预计算完整结论】:")
    for item in interpreted_yoy_metrics:
        print(f"\n{item['name_display']}:")
        print(f"  今年变化量: {item['formatted_data']['current_delta']}")
        print(f"  去年同期变化量: {item['formatted_data']['ly_delta']}")
        print(f"  今年贡献度: {item['formatted_data']['current_contrib']}")
        print(f"  去年同期贡献度: {item['formatted_data']['ly_contrib']}")
        print(f"  预计算完整结论: {item['complete_analysis']}")
    
    print(f"\n【AI System Prompt】:")
    print(system_prompt)
    print(f"\n【AI User Prompt】:")
    print(user_prompt)
    print("="*80)
    print("【调试信息结束】")
    print("="*80 + "\n")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, 
            stream=True      
        )
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
    except Exception as e:
        yield f"调用AI总结第三部分(基于预分析)时出错: {str(e)}"


def get_summary_part4_insights_and_risks(client, model_name, context_part1_part2_part3):
    """生成财务分析报告的第四部分：洞察与评价。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据【已生成的报告前三部分内容】，凝练出核心的洞察和评价，作为财务分析报告的第四部分。
**重要：你的回答不应包含此部分的标题（例如："4. 洞察与评价"）或章节编号。**
报告应严格遵循以下内容结构，并使用中文撰写：

**智能数值格式化要求：**
在描述数值时，请自动将大数值转换为更易读的格式：
- 10万以下：使用"元"，可使用万元表示（如：8.5万元）
- 10万-1000万：使用"万元"（如：151.03万元）
- 1000万以上：使用"亿元"（如：1.15亿元）
- 确保转换准确性，保留合适的小数位数（一般1-2位）
- 保持变化的正负符号，缺失数据明确标注

**分析内容结构：**
   - 基于以上所有分析（特别是与去年同期的对比），凝练出核心的洞察和评价。
   - **积极信号**：指出分析中观察到的积极方面或改善趋势。请具体说明，避免空泛的描述。
   - **风险预警**：点出潜在的风险、挑战或恶化趋势。请具体说明，并尽可能分析其潜在影响。
   - (可选) **行动建议**：如果基于分析可以提出明确且可操作的建议，请在此处添加。

**通用指令：**
- **高度凝练**：此部分是对整个报告的升华总结，语言务必精炼、有穿透力。
- **承接上文**：你的分析和评价必须紧密围绕之前三个部分提供的信息和分析展开。
- **突出重点**：挑选最重要、最有价值的洞察进行阐述。
- **客观中立**：保持客观，即使在提出评价和建议时。
- **突出重点**：总结性、重点观点可用markdown格式的加粗。
- **其他要求**：与前三部分一致（专业术语等）。

请严格按照上述结构和要求生成报告的这【第四部分】。
"""
    
    user_prompt = (f"以下是已生成的【报告第一、二、三部分内容】：\n{context_part1_part2_part3}\n\n" 
                   f"请基于以上完整内容，继续撰写【报告第四部分：洞察与评价】：")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, 
            stream=True      
        )
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
    except Exception as e:
        yield f"调用AI总结第四部分时出错: {str(e)}"


def interpret_sub_metric_impact(primary_metric_name, primary_metric_delta, 
                                sub_metric_display_name, sub_metric_delta, 
                                sub_metric_contribution, sub_metric_type,
                                is_primary_metric_increase_good: bool):
    """
    根据主指标和子指标的变化情况，预先计算子指标的业务影响类型和解释文本。

    Args:
        primary_metric_name (str): 主指标的名称 (例如："净利润").
        primary_metric_delta (float): 主指标的环比变化量.
        sub_metric_display_name (str): 子指标的中文显示名称.
        sub_metric_delta (float): 子指标的自身环比变化量.
        sub_metric_contribution (float): 子指标对主指标变化的贡献度 (%).
        sub_metric_type (str): 子指标的类型 ("收益", "成本", "未知类型").
        is_primary_metric_increase_good (bool): 主指标的增加是否被视为业务上的积极信号.
                                              (True for Profit, False for Cost).

    Returns:
        dict: 包含 "impact_type" 和 "explanation" 的字典.
    """
    impact_type = "中性影响"
    explanation = ""
    
    formatted_sub_delta = format_value_for_ai(sub_metric_delta)
    formatted_sub_contrib = f"{sub_metric_contribution:+.1f}%" if isinstance(sub_metric_contribution, (int, float)) and not pd.isna(sub_metric_contribution) else "N/A"
    
    if pd.isna(sub_metric_delta) or pd.isna(sub_metric_contribution) or pd.isna(primary_metric_delta):
        return {
            "impact_type": "数据缺失",
            "explanation": f"{sub_metric_display_name}、其贡献度或主指标 {primary_metric_name} 的变化量数据缺失，无法准确分析其影响。"
        }

    # Determine impact type based on contribution and whether primary metric increase is good
    current_impact_is_positive = False # Represents if the sub-item's effect is "good" for the current context

    if primary_metric_delta > 0: # Primary metric increased
        if sub_metric_contribution > 0: # Sub-metric pushed in the same direction (primary up, sub pushed up)
            current_impact_is_positive = is_primary_metric_increase_good 
            # If profit up (good) & sub pushed up -> good contributor
            # If cost up (bad) & sub pushed up -> bad contributor
        elif sub_metric_contribution < 0: # Sub-metric pushed in the opposite direction (primary up, sub pushed down)
            current_impact_is_positive = not is_primary_metric_increase_good
            # If profit up (good) & sub pushed down -> bad contributor (hindered profit)
            # If cost up (bad) & sub pushed down -> good contributor (mitigated cost increase)
        else: # sub_metric_contribution == 0
            impact_type = "中性影响"
    elif primary_metric_delta < 0: # Primary metric decreased
        if sub_metric_contribution > 0: # Sub-metric pushed in the same direction (primary down, sub pushed down)
            current_impact_is_positive = not is_primary_metric_increase_good
            # If profit down (bad) & sub pushed down -> bad contributor (worsened profit decrease)
            # If cost down (good) & sub pushed down -> good contributor (drove cost decrease)
        elif sub_metric_contribution < 0: # Sub-metric pushed in the opposite direction (primary down, sub pushed up)
            current_impact_is_positive = is_primary_metric_increase_good
            # If profit down (bad) & sub pushed up -> good contributor (mitigated profit decrease)
            # If cost down (good) & sub pushed up -> bad contributor (hindered cost decrease)
        else: # sub_metric_contribution == 0
            impact_type = "中性影响"
    else: # primary_metric_delta == 0
        impact_type = "中性影响"

    if impact_type != "中性影响": # If already set by contribution == 0 or primary_delta == 0
        pass # Keep as is
    elif current_impact_is_positive:
        impact_type = "积极影响"
    else:
        impact_type = "消极影响"

    # Generate Explanation based on the final impact_type and context
    # Profit Analysis (is_primary_metric_increase_good = True)
    if is_primary_metric_increase_good:
        if primary_metric_delta > 0: # Profit Increased
            if impact_type == "积极影响": # contribution > 0
                if sub_metric_type == "收益": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的增长贡献为正 ({formatted_sub_contrib})，其自身的增长 (变化量: {formatted_sub_delta}) 进一步推动了 {primary_metric_name} 的增加，属积极因素。"
                elif sub_metric_type == "成本": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的增长贡献为正 ({formatted_sub_contrib})，其自身的减少 (变化量: {formatted_sub_delta}) 促进了 {primary_metric_name} 的增加，属积极因素。"
                else: explanation = f"{sub_metric_display_name} (类型未知) 对 {primary_metric_name} 的增长贡献为正 ({formatted_sub_contrib})，其变化推动增长，属积极因素。"
            elif impact_type == "消极影响": # contribution < 0
                if sub_metric_type == "收益": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的增长贡献为负 ({formatted_sub_contrib})，其自身的减少 (变化量: {formatted_sub_delta}) 阻碍了 {primary_metric_name} 的增长，属消极因素。"
                elif sub_metric_type == "成本": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的增长贡献为负 ({formatted_sub_contrib})，其自身的增加 (变化量: {formatted_sub_delta}) 抑制了 {primary_metric_name} 的增长，属消极因素。"
                else: explanation = f"{sub_metric_display_name} (类型未知) 对 {primary_metric_name} 的增长贡献为负 ({formatted_sub_contrib})，其变化阻碍增长，属消极因素。"
        elif primary_metric_delta < 0: # Profit Decreased
            if impact_type == "消极影响": # contribution > 0
                if sub_metric_type == "收益": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的下降贡献为正 ({formatted_sub_contrib})，其自身的减少 (变化量: {formatted_sub_delta}) 加剧了 {primary_metric_name} 的下降，属消极因素。"
                elif sub_metric_type == "成本": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的下降贡献为正 ({formatted_sub_contrib})，其自身的增加 (变化量: {formatted_sub_delta}) 是导致 {primary_metric_name} 下降的因素之一，属消极因素。"
                else: explanation = f"{sub_metric_display_name} (类型未知) 对 {primary_metric_name} 的下降贡献为正 ({formatted_sub_contrib})，其变化加剧下降，属消极因素。"
            elif impact_type == "积极影响": # contribution < 0
                if sub_metric_type == "收益": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的下降贡献为负 ({formatted_sub_contrib})，其自身的增长 (变化量: {formatted_sub_delta}) 起到了缓冲作用，有效减缓了 {primary_metric_name} 的下滑幅度，属积极因素。"
                elif sub_metric_type == "成本": explanation = f"{sub_metric_display_name} ({sub_metric_type}) 对 {primary_metric_name} 的下降贡献为负 ({formatted_sub_contrib})，其自身的显著减少 (变化量: {formatted_sub_delta}) 有效减缓了 {primary_metric_name} 的下滑幅度，属积极因素。"
                else: explanation = f"{sub_metric_display_name} (类型未知) 对 {primary_metric_name} 的下降贡献为负 ({formatted_sub_contrib})，其变化减缓下降，属积极因素。"
    
    # Handle neutral impact type explanation if not already set by specific logic
    if impact_type == "中性影响":
        if primary_metric_delta == 0:
            if not pd.isna(sub_metric_delta) and sub_metric_delta != 0:
                explanation = f"由于 {primary_metric_name} 无整体变化，{sub_metric_display_name} 的变化 (变化量: {formatted_sub_delta}，贡献度: {formatted_sub_contrib}) 被其他因素完全抵消，最终影响中性。"
            elif not pd.isna(sub_metric_delta) and sub_metric_delta == 0:
                explanation = f"由于 {primary_metric_name} 无整体变化，{sub_metric_display_name} 亦无变化 (贡献度: {formatted_sub_contrib})，对 {primary_metric_name} 无实质影响。"
            else: # sub_metric_delta is N/A
                explanation = f"由于 {primary_metric_name} 无整体变化，且 {sub_metric_display_name} 的变化量数据缺失，无法判断其具体影响，视为中性。"
        else: # Contribution was zero, but primary metric did change
            trend_desc = "增长" if primary_metric_delta > 0 else "下降"
            verb_effect = "推动或阻碍" if is_primary_metric_increase_good else ("加剧或减缓" if primary_metric_delta > 0 else "驱动或抑制")
            explanation = f"{sub_metric_display_name} (变化量: {formatted_sub_delta}) 对 {primary_metric_name} {trend_desc}的贡献为零 ({formatted_sub_contrib})，未对其产生实质性的{verb_effect}。"

    # Fallback for "未知类型" if explanation is still empty (should be rare with current structure)
    if sub_metric_type == "未知类型" and not explanation:
        action_desc = ""
        if primary_metric_delta > 0: action_desc = "促进了增长" if impact_type == "积极影响" else "阻碍了增长"
        elif primary_metric_delta < 0: action_desc = "减缓了下降" if impact_type == "积极影响" else "加剧了下降"
        explanation = f"{sub_metric_display_name} (类型未知，贡献度: {formatted_sub_contrib}，变化量: {formatted_sub_delta}) 的影响判定为{impact_type}，因为它{action_desc}。具体业务含义需结合指标实际性质判断。"

    return {"impact_type": impact_type, "explanation": explanation} 


def interpret_profit_yoy_comparison_details(primary_metric_name, primary_metric_delta_current, primary_metric_delta_ly,
                                          sub_metric_display_name, sub_metric_delta_current, sub_metric_delta_ly,
                                          sub_metric_contribution_current, sub_metric_contribution_ly, sub_metric_type):
    """
    专为盈利分析第三段落设计，预先计算盈利子指标的同比对比分析观点。
    使用通俗易懂的语言，避免复杂的同比环比表述。
    
    Args:
        primary_metric_name: 主指标名称
        primary_metric_delta_current: 当前期主指标变化量
        primary_metric_delta_ly: 去年同期主指标变化量
        sub_metric_display_name: 子指标显示名称
        sub_metric_delta_current: 当前期子指标变化量
        sub_metric_delta_ly: 去年同期子指标变化量
        sub_metric_contribution_current: 当前期子指标贡献度
        sub_metric_contribution_ly: 去年同期子指标贡献度
        sub_metric_type: 子指标类型（收益/成本）
    
    Returns:
        dict: 包含完整分析结论的字典
    """
    
    # 格式化数值
    formatted_current_delta = format_value_for_ai(sub_metric_delta_current)
    formatted_ly_delta = format_value_for_ai(sub_metric_delta_ly)
    formatted_current_contrib = f"{sub_metric_contribution_current:+.1f}%" if pd.notna(sub_metric_contribution_current) else "N/A"
    formatted_ly_contrib = f"{sub_metric_contribution_ly:+.1f}%" if pd.notna(sub_metric_contribution_ly) else "N/A"
    
    # 数据缺失检查
    if pd.isna(sub_metric_delta_current) or pd.isna(sub_metric_delta_ly) or pd.isna(sub_metric_contribution_current) or pd.isna(sub_metric_contribution_ly):
        return {
            "analysis_type": "数据缺失",
            "complete_analysis": f"由于数据缺失，无法分析{sub_metric_display_name}的对比情况。",
            "formatted_data": {
                "current_delta": formatted_current_delta,
                "ly_delta": formatted_ly_delta,
                "current_contrib": formatted_current_contrib,
                "ly_contrib": formatted_ly_contrib
            }
        }
    
    # 1. 子指标变化情况对比
    sub_delta_diff = sub_metric_delta_current - sub_metric_delta_ly
    
    if sub_metric_type == "收益":
        # 对于收益类指标，变化量增加是好事
        if sub_delta_diff > 0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}多了{format_value_for_ai(sub_delta_diff)}，该项收益表现改善。"
        elif sub_delta_diff < -0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}少了{format_value_for_ai(abs(sub_delta_diff))}，该项收益表现恶化。"
        else:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，与去年同期的{formatted_ly_delta}基本持平，该项收益表现稳定。"
    elif sub_metric_type == "成本":
        # 对于成本类指标，变化量减少是好事
        if sub_delta_diff > 0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}多了{format_value_for_ai(sub_delta_diff)}，该项成本控制表现恶化。"
        elif sub_delta_diff < -0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}少了{format_value_for_ai(abs(sub_delta_diff))}，该项成本控制表现改善。"
        else:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，与去年同期的{formatted_ly_delta}基本持平，该项成本控制表现稳定。"
    else:
        # 未知类型，中性表述
        if sub_delta_diff > 0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}多了{format_value_for_ai(sub_delta_diff)}。"
        elif sub_delta_diff < -0.01:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}少了{format_value_for_ai(abs(sub_delta_diff))}。"
        else:
            sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，与去年同期的{formatted_ly_delta}基本持平。"
    
    # 2. 贡献度变化分析（考虑主指标变化方向）
    contrib_diff = sub_metric_contribution_current - sub_metric_contribution_ly
    contribution_analysis = ""
    
    # 判断主指标（净利润）的变化方向
    is_profit_increasing = primary_metric_delta_current > 0 if pd.notna(primary_metric_delta_current) else None
    
    # 确定主指标变化方向的描述
    if is_profit_increasing:
        profit_trend_desc = "增长"
    elif is_profit_increasing is False:
        profit_trend_desc = "下降"
    else:
        profit_trend_desc = "变化"  # 当变化方向未知时使用中性表述
    
    # 判断贡献度正负号是否发生变化
    if (sub_metric_contribution_current > 0 and sub_metric_contribution_ly < 0) or (sub_metric_contribution_current < 0 and sub_metric_contribution_ly > 0):
        # 贡献度正负号发生变化
        current_sign_desc = f"对{primary_metric_name}{profit_trend_desc}的正向推动" if sub_metric_contribution_current > 0 else f"对{primary_metric_name}{profit_trend_desc}的负向拖累"
        ly_sign_desc = f"对{primary_metric_name}{profit_trend_desc}的正向推动" if sub_metric_contribution_ly > 0 else f"对{primary_metric_name}{profit_trend_desc}的负向拖累"
        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}的影响发生了明显转变，从去年同期的{ly_sign_desc}转变为今年的{current_sign_desc}。今年对{primary_metric_name}{profit_trend_desc}的贡献度为{formatted_current_contrib}，去年同期为{formatted_ly_contrib}。"
    else:
        # 贡献度正负号未发生变化，分析绝对值变化
        current_abs = abs(sub_metric_contribution_current)
        ly_abs = abs(sub_metric_contribution_ly)
        abs_diff = current_abs - ly_abs
        
        if abs(abs_diff) > 0.1:  # 绝对值变化超过0.1%才认为有显著变化
            if sub_metric_contribution_current > 0 and sub_metric_contribution_ly > 0:
                # 都是正值，分析正面影响力变化
                if abs_diff > 0:
                    if is_profit_increasing:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}上升至今年的{formatted_current_contrib}，其推动增长的正向作用增强。"
                    elif is_profit_increasing is False:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}上升至今年的{formatted_current_contrib}，其加剧下降的负向作用增强。"
                    else:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}上升至今年的{formatted_current_contrib}，其影响力增强。"
                else:
                    if is_profit_increasing:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}下降至今年的{formatted_current_contrib}，其推动增长的正向作用减弱。"
                    elif is_profit_increasing is False:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}下降至今年的{formatted_current_contrib}，其加剧下降的负向作用减弱。"
                    else:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}下降至今年的{formatted_current_contrib}，其影响力减弱。"
            elif sub_metric_contribution_current < 0 and sub_metric_contribution_ly < 0:
                # 都是负值，分析负面影响力变化
                if abs_diff > 0:
                    if is_profit_increasing:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其阻碍增长的负向作用增强。"
                    elif is_profit_increasing is False:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其减缓下降的正向作用增强。"
                    else:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其影响力增强。"
                else:
                    if is_profit_increasing:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其阻碍增长的负向作用减弱。"
                    elif is_profit_increasing is False:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其减缓下降的正向作用减弱。"
                    else:
                        contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其影响力减弱。"
            else:
                # 其他情况（理论上不应该到这里，因为正负号变化已经在上面处理了）
                contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度从去年同期的{formatted_ly_contrib}变化至今年的{formatted_current_contrib}，其影响力发生变化。"
        else:
            # 绝对值变化不显著
            contribution_analysis = f"从子指标贡献度变化情况看，{sub_metric_display_name}对{primary_metric_name}{profit_trend_desc}的贡献度今年为{formatted_current_contrib}，与去年同期的{formatted_ly_contrib}基本持平，影响力稳定。"
    
    # 合并完整分析
    complete_analysis = f"{sub_metric_analysis} {contribution_analysis}"
    
    return {
        "analysis_type": "完整分析",
        "complete_analysis": complete_analysis,
        "formatted_data": {
            "current_delta": formatted_current_delta,
            "ly_delta": formatted_ly_delta,
            "current_contrib": formatted_current_contrib,
            "ly_contrib": formatted_ly_contrib
        }
    } 