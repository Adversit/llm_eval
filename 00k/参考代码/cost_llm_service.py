"""
成本分析LLM服务模块
包含成本分析相关的所有LLM功能
"""

import streamlit as st
import pandas as pd
from .base_llm_service import format_value_for_ai


# 定义成本分析子指标的类型 (均为"成本"型)
COST_SUB_METRIC_TYPES = {
    "营业成本": "成本",
    "营业税金及附加": "成本", # 有时也称 税金及附加
    "销售费用": "成本",
    "管理费用": "成本",
    "研发费用": "成本",
    "财务费用": "成本",
    # 根据用户提供的成本构成，补充其他可能的成本项
    "利息费用": "成本", # 通常可能包含在财务费用中，但若单独列示
    "资产减值损失": "成本", # 在利润表概念中是损失，计入成本加总
    "信用减值损失": "成本", # 同上
    # 根据实际 COST_STATEMENT_STRUCTURE_FLAT 可能需要调整或补充
    # 例如，如果主营业务成本和其他业务成本分开列示
    "主营业务成本": "成本",
    "其他业务成本": "成本",
}


def get_cost_summary_part1_current_situation(client, model_name, current_period_data, primary_metric_col):
    """生成成本分析报告的第一部分：当前期整体变化情况。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据提供的成本相关财务数据，生成成本分析报告的第一部分。
**重要：你的回答不应包含此部分的标题（例如："1. 当前期整体变化情况"）或章节编号。**

**智能数值格式化要求：**
在描述数值时，请自动将大数值转换为更易读的格式：
- 10万以下：使用"元"，可使用万元表示（如：8.5万元）
- 10万-1000万：使用"万元"（如：151.03万元）
- 1000万以上：使用"亿元"（如：1.15亿元）
- 确保转换准确性，保留合适的小数位数（一般1-2位）
- 保持变化的正负符号，缺失数据明确标注

**分析内容要求：**
- **绝对变化**：明确说明 {primary_metric_col} 的绝对变化量（以易读的单位表示）
- **相对变化**：以百分比形式说明相对变化幅度
- **变化方向**：明确判断是"增加"还是"减少"
- **严禁趋势描述**：不要使用"呈上升趋势"、"逐步下降"等表述，只说明本期与上期的对比结果

**输出格式要求：**
- 不得包含任何形式的表格（Markdown表格、HTML表格等）
- 数据驱动，严禁主观分析或超越数据范围的解释
- 使用专业财务术语，但确保语言清晰易懂
- 客观分析，不带感情色彩
- 重点内容可用markdown格式加粗强调

**参考结构（供参考，可灵活调整）：**
本期{primary_metric_col}较上期发生了[具体变化描述]。绝对变化量为[具体数值]，相对变化幅度为[百分比]，总体表现为[增加/减少]。

请根据上述要求，严格基于数据生成当前期整体变化情况分析。
"""

    current_data_summary_parts = [
        f"当前报告期基础数据:",
        f"- 主要成本指标 ({primary_metric_col}):",
        f"  - {current_period_data.get('current_to_date', 'N/A')} 值: {format_value_for_ai(current_period_data.get(f'current_{primary_metric_col}_t0'))}",
        f"  - {current_period_data.get('current_from_date', 'N/A')} 值: {format_value_for_ai(current_period_data.get(f'current_{primary_metric_col}_t_minus_1'))}",
        f"  - 环比变化量: {format_value_for_ai(current_period_data.get(f'current_delta_{primary_metric_col}'))}",
    ]
    
    user_prompt = "请根据以下当前报告期数据，生成成本分析报告的第一部分：\n" + "\n".join(current_data_summary_parts)
    
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
        yield f"调用AI总结成本第一部分时出错: {str(e)}"


def get_cost_summary_part2_driving_factors(client, model_name, current_period_data, primary_metric_col, secondary_metric_info, context_part1):
    """生成成本分析报告的第二部分：驱动因素分析。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据提供的成本分析数据，生成成本分析报告的第二部分。
**重要：你的回答不应包含此部分的标题（例如："2. 驱动因素分析"）或章节编号。**

**智能数值格式化要求：**
在描述数值时，请自动将大数值转换为更易读的格式：
- 10万以下：使用"元"，可使用万元表示（如：8.5万元）
- 10万-1000万：使用"万元"（如：151.03万元）
- 1000万以上：使用"亿元"（如：1.15亿元）
- 确保转换准确性，保留合适的小数位数（一般1-2位）
- 保持变化的正负符号，准确显示贡献度百分比
- 缺失数据明确标注为"数据缺失"

**分析内容要求：**
- **数据驱动分析**：严格基于提供的数据进行分析，不允许任何主观解释
- **子指标变化**：详细说明各个成本子项的变化量（使用易读单位）
- **贡献度分析**：准确描述各子项对总成本变化的贡献度百分比
- **影响排序**：按照绝对贡献度大小对子指标进行排序说明
- **禁止原因推测**：不得进行任何原因分析或市场环境推测

**输出格式要求：**
- 不得包含任何形式的表格（Markdown表格、HTML表格等）
- 使用专业财务术语，确保语言清晰
- 客观陈述，不带主观判断
- 重点数据可用markdown格式加粗强调

**分析结构（供参考）：**
对 {primary_metric_col} 的变化进行子项分解分析显示：[按贡献度排序逐一说明各子项的变化量和贡献度]

请根据上述要求，严格基于数据生成驱动因素分析。
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
        
        # 从 COST_SUB_METRIC_TYPES 获取类型，默认为 "成本"
        sub_metric_type = COST_SUB_METRIC_TYPES.get(sm_display_name, "成本")
        # 进一步确认，如果 sm_name_key 在里面也用它
        if sub_metric_type == "成本" and sm_name_key in COST_SUB_METRIC_TYPES:
             sub_metric_type = COST_SUB_METRIC_TYPES.get(sm_name_key, "成本")

        interpretation_result = interpret_cost_sub_metric_details(
            primary_metric_name=primary_metric_col,
            primary_metric_delta=primary_metric_delta_val,
            sub_metric_display_name=sm_display_name,
            sub_metric_delta=sm_delta,
            sub_metric_contribution=sm_contrib,
            sub_metric_type=sub_metric_type # Should generally be "成本"
        )
        interpreted_secondary_metrics.append({
            "name_display": sm_display_name,
            "delta_formatted": format_value_for_ai(sm_delta),
            "contribution_formatted": f"{sm_contrib:+.1f}%" if isinstance(sm_contrib, (int, float)) and not pd.isna(sm_contrib) else "N/A",
            "impact_type": interpretation_result["impact_type"],
            "explanation": interpretation_result["explanation"]
        })

    # 构建 User Prompt
    user_prompt_part2_intro = f"请参考以下预先分析好的各成本构成子指标对 {primary_metric_col} (总成本) 的业务影响解读：\n"
    user_prompt_part2_details = []
    for item in interpreted_secondary_metrics:
        user_prompt_part2_details.append(
            f"- 指标名称: {item['name_display']}\n"
            f"  - 自身环比变化量: {item['delta_formatted']}\n"
            f"  - 对 {primary_metric_col} 变化的贡献度: {item['contribution_formatted']}\n"
            f"  - **预分析结论**: 影响类型为【{item['impact_type']}】。解读：{item['explanation']}"
        )
    
    user_prompt = (f"以下是已生成的【成本报告第一部分内容】：\n{context_part1}\n\n" 
                   f"请基于以上第一部分内容和以下【预先分析好的各成本子指标影响解读】，继续撰写【成本报告第二部分：驱动因素分析】({primary_metric_col}分析)：\n" +
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
        yield f"调用AI总结成本第二部分(基于预分析)时出错: {str(e)}"


def get_cost_summary_part3_yoy_comparison(client, model_name, full_summary_data, primary_metric_col, secondary_metric_info, context_part1_part2):
    """生成成本分析报告的第三部分：与去年同期对比分析。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家。你的任务是根据【已生成的成本报告前两部分内容】和【预先分析好的各成本子指标完整对比分析】，生成成本分析报告的第三部分。
**重要：你的回答不应包含此部分的标题（例如："3. 与去年同期对比分析"）或章节编号。**

**智能数值格式化要求：**
在复制预分析结论时，如果其中包含大数值，请智能转换为更易读的格式：
- 10万以下：使用"元"（如：8.5万元）
- 10万-1000万：使用"万元"（如：151.03万元）
- 1000万以上：使用"亿元"（如：1.15亿元）
- 确保转换准确性，保留合适的小数位数

**重要输出原则：**
1. **结构：** 对于每一项分析，请务必遵循【先给出核心观点/结论，再进行详细数据支持和逻辑阐述】的结构。
2. **格式：** 你的回答不应包含此部分的标题或章节编号。所有输出均为纯文本，严禁包含任何Markdown表格、HTML表格或任何其他形式的表格。
3. **语言要求：** 使用通俗易懂的语言，避免使用"同比"、"环比"等专业术语，改用"相较于去年同期"、"今年与去年相比"等更直观的表述。

**分析内容结构：**

   - **主指标总体评价**：
     首先分析 {primary_metric_col} (总成本) 本身相较于去年同期的变化表现，给出总体结论。

   - **子指标对比分析**：
     对每个子指标，你必须严格按照以下格式输出：
     
     **[子指标名称]：**
     [完整复制预分析结论中的sub_metric_analysis和contribution_analysis内容，但需要将其中的数值转换为更易读的格式]
     
     **绝对禁止的行为：**
     - 禁止修改预分析结论中的任何逻辑和表述
     - 禁止重新组织预分析结论的语言结构
     - 禁止总结或简化预分析结论的内容
     - 禁止添加自己的解释或评价
     - 禁止改变预分析结论的判断和观点
     
     **允许的行为：**
     - 将预分析结论中的大数值转换为更易读的万元、亿元格式
     - 保持原有的逻辑结构和表述方式

   - **整体成本表现总结**：
     基于主指标和各子指标的分析，对本期整体成本表现相较去年同期给出明确判断（改善/恶化/结构分化），并总结关键驱动因素。

**严格执行指令：**
- **完全依赖预分析结论**：你的唯一任务是将预分析结论中的 `sub_metric_analysis` 和 `contribution_analysis` 字段内容原封不动地复制到相应的子指标分析中，仅允许进行数值格式的优化。
- **数值格式优化原则**：对于子指标分析部分，你可以将预分析结论中的数值转换为更易读的格式，但不得对其他任何内容进行修改。
- **逐字复制+格式优化**：必须逐字逐句地复制预分析结论，同时将大数值智能转换为万元、亿元格式。
- **格式要求**：只需要在每个子指标名称前加上"**[子指标名称]：**"的格式标识，然后完整复制预分析结论（数值已优化格式）。

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
        if primary_diff_delta < -0.01:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量减少了{format_value_for_ai(abs(primary_diff_delta))}，总成本控制表现改善。"
        elif primary_diff_delta > 0.01:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量增加了{format_value_for_ai(primary_diff_delta)}，总成本控制表现恶化。"
        else:
            primary_yoy_analysis["analysis"] = f"相较于去年同期，本期{primary_metric_col}的变化量基本持平，总成本控制表现稳定。"
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
        
        # 从 COST_SUB_METRIC_TYPES 获取类型，默认为 "成本"
        sub_metric_type = COST_SUB_METRIC_TYPES.get(sm_display_name, "成本")
        if sub_metric_type == "成本" and sm_name_key in COST_SUB_METRIC_TYPES:
             sub_metric_type = COST_SUB_METRIC_TYPES.get(sm_name_key, "成本")

        yoy_interpretation_result = interpret_cost_yoy_comparison_details(
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
            "sub_metric_analysis": yoy_interpretation_result["sub_metric_analysis"],
            "contribution_analysis": yoy_interpretation_result["contribution_analysis"],
            "formatted_data": yoy_interpretation_result["formatted_data"]
        })

    # 构建 User Prompt
    user_prompt_part3_intro = f"请参考以下预先分析好的各成本子指标两维度对比解读：\n\n"
    
    # 主指标分析
    user_prompt_part3_intro += f"**主指标 {primary_metric_col} 对比分析：**\n"
    user_prompt_part3_intro += f"- 今年变化量: {primary_yoy_analysis['current_delta']}\n"
    user_prompt_part3_intro += f"- 去年同期变化量: {primary_yoy_analysis['ly_delta']}\n"
    user_prompt_part3_intro += f"- 变化量差异: {primary_yoy_analysis['diff_delta']}\n"
    user_prompt_part3_intro += f"- **预分析结论**: {primary_yoy_analysis['analysis']}\n\n"
    
    # 子指标分析
    user_prompt_part3_intro += f"**各成本子指标两维度对比分析：**\n"
    user_prompt_part3_details = []
    for item in interpreted_yoy_metrics:
        user_prompt_part3_details.append(
            f"- 指标名称: {item['name_display']}\n"
            f"  - 今年变化量: {item['formatted_data']['current_delta']}\n"
            f"  - 去年同期变化量: {item['formatted_data']['ly_delta']}\n"
            f"  - 今年贡献度: {item['formatted_data']['current_contrib']}\n"
            f"  - 去年同期贡献度: {item['formatted_data']['ly_contrib']}\n"
            f"  - **预分析结论**:\n"
            f"    - 子指标变化情况对比: {item['sub_metric_analysis']}\n"
            f"    - 子指标贡献度变化情况: {item['contribution_analysis']}"
        )

    user_prompt = (f"以下是已生成的【成本报告第一、二部分内容】：\n{context_part1_part2}\n\n" 
                   f"请基于以上前两部分内容和以下【预先分析好的成本同比对比解读】，继续撰写【成本报告第三部分：与去年同期对比分析】：\n\n" +
                   user_prompt_part3_intro + "\n".join(user_prompt_part3_details))

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
        yield f"调用AI总结成本第三部分(基于预分析)时出错: {str(e)}"


def get_cost_summary_part4_insights_and_risks(client, model_name, context_part1_part2_part3):
    """生成成本分析报告的第四部分：洞察与评价。"""
    if not client or not model_name:
        yield "LLM client or model not available for summarization."
        return

    system_prompt = f"""
你是一位非常优秀的财务分析AI专家，专注于成本分析。你的任务是根据【已生成的成本报告前三部分内容】，凝练出核心的洞察和评价，作为成本分析报告的第四部分。
**重要：你的回答不应包含此部分的标题（例如："4. 洞察与评价"）或章节编号。**

**智能数值格式化要求：**
在描述数值时，请自动将大数值转换为更易读的格式：
- 10万以下：使用"元"，可使用万元表示（如：8.5万元）
- 10万-1000万：使用"万元"（如：151.03万元）
- 1000万以上：使用"亿元"（如：1.15亿元）
- 确保转换准确性，保留合适的小数位数（一般1-2位）
- 保持变化的正负符号，缺失数据明确标注

**分析内容结构：**
报告应严格遵循以下内容结构，并使用中文撰写：

   - 基于以上所有分析（特别是与去年同期的对比），凝练出核心的洞察和评价。
   - **成本控制亮点**：指出分析中观察到的成本有效控制或优化的方面。请具体说明，避免空泛的描述。
   - **成本风险预警**：点出潜在的成本失控风险、不合理增长或恶化趋势。请具体说明，并尽可能分析其潜在影响。
   - (可选) **行动建议**：如果基于分析可以提出明确且可操作的成本相关建议，请在此处添加。

**通用指令：**
- **高度凝练**：此部分是对整个成本报告的升华总结，语言务必精炼、有穿透力。
- **承接上文**：你的分析和评价必须紧密围绕之前三个部分提供的信息和分析展开。
- **突出重点**：挑选最重要、最有价值的洞察进行阐述。
- **客观中立**：保持客观，即使在提出评价和建议时。
- **突出重点**：总结性、重点观点可用markdown格式的加粗。
- **其他要求**：与前三部分一致（专业术语等）。

请严格按照上述结构和要求生成报告的这【第四部分】。
"""
    
    user_prompt = (f"以下是已生成的【成本报告第一、二、三部分内容】：\n{context_part1_part2_part3}\n\n" 
                   f"请基于以上完整内容，继续撰写【成本报告第四部分：洞察与评价】：")

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
        yield f"调用AI总结成本第四部分时出错: {str(e)}"


def interpret_cost_sub_metric_details(primary_metric_name, primary_metric_delta,
                                      sub_metric_display_name, sub_metric_delta,
                                      sub_metric_contribution, sub_metric_type):
    """
    专为成本分析设计，预先计算成本子指标的业务影响类型和解释文本。
    根据总成本变化方向和子指标贡献度的正负，将影响类型分为四种状态：
    1. 总成本增长(+) + 子指标贡献度(+) → 对总成本增长起到促进作用
    2. 总成本增长(+) + 子指标贡献度(-) → 对总成本增长起到阻碍作用  
    3. 总成本降低(-) + 子指标贡献度(+) → 对总成本降低起到促进作用
    4. 总成本降低(-) + 子指标贡献度(-) → 对总成本降低起到阻碍作用
    """
    impact_type = "无显著影响"
    explanation = ""

    formatted_sub_delta = format_value_for_ai(sub_metric_delta)
    formatted_sub_contrib = f"{sub_metric_contribution:+.1f}%" if isinstance(sub_metric_contribution, (int, float)) and not pd.isna(sub_metric_contribution) else "N/A"

    # 数据缺失检查
    if pd.isna(primary_metric_delta) or pd.isna(sub_metric_delta) or pd.isna(sub_metric_contribution):
        impact_type = "数据缺失"
        explanation = f"{sub_metric_display_name} (类型: {sub_metric_type})、其贡献度或总成本 {primary_metric_name} 的变化量数据缺失，无法准确分析其影响。"
        return {"impact_type": impact_type, "explanation": explanation}

    # 判断是否为无显著影响（贡献度或变化量接近0）
    if abs(sub_metric_contribution) < 0.01:
        impact_type = "无显著影响"
        if primary_metric_delta == 0:
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，但由于总成本 {primary_metric_name} 无整体变化，其对总成本无显著驱动作用。"
        else:
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，对总成本 {primary_metric_name} 变化的贡献度为 {formatted_sub_contrib}，综合判断为对总成本无显著驱动作用。"
        return {"impact_type": impact_type, "explanation": explanation}

    # 根据总成本变化方向和子指标贡献度确定影响类型
    if primary_metric_delta > 0.01:  # 总成本增长
        if sub_metric_contribution > 0:  # 贡献度为正
            impact_type = "对总成本增长起到促进作用"
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，对总成本 {primary_metric_name} 变化的贡献度为 {formatted_sub_contrib}，对总成本增长起到促进作用。"
        else:  # 贡献度为负
            impact_type = "对总成本增长起到阻碍作用"
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，对总成本 {primary_metric_name} 变化的贡献度为 {formatted_sub_contrib}，对总成本增长起到阻碍作用。"
    
    elif primary_metric_delta < -0.01:  # 总成本降低
        if sub_metric_contribution > 0:  # 贡献度为正
            impact_type = "对总成本降低起到促进作用"
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，对总成本 {primary_metric_name} 变化的贡献度为 {formatted_sub_contrib}，对总成本降低起到促进作用。"
        else:  # 贡献度为负
            impact_type = "对总成本降低起到阻碍作用"
            explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，对总成本 {primary_metric_name} 变化的贡献度为 {formatted_sub_contrib}，对总成本降低起到阻碍作用。"
    
    else:  # 总成本基本无变化
        impact_type = "无显著影响"
        explanation = f"{sub_metric_display_name} (类型: {sub_metric_type}) 自身变化量为 {formatted_sub_delta}，但由于总成本 {primary_metric_name} 基本无变化，其对总成本无显著驱动作用。"

    return {"impact_type": impact_type, "explanation": explanation} 


def interpret_cost_yoy_comparison_details(primary_metric_name, primary_metric_delta_current, primary_metric_delta_ly,
                                        sub_metric_display_name, sub_metric_delta_current, sub_metric_delta_ly,
                                        sub_metric_contribution_current, sub_metric_contribution_ly, sub_metric_type):
    """
    专为成本分析第三段落设计，预先计算成本子指标的同比对比分析观点。
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
        sub_metric_type: 子指标类型
    
    Returns:
        dict: 包含三维度分析结果的字典
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
            "sub_metric_analysis": f"由于数据缺失，无法分析{sub_metric_display_name}的变化情况对比。",
            "contribution_analysis": f"由于数据缺失，无法分析{sub_metric_display_name}贡献度的变化情况。",
            "formatted_data": {
                "current_delta": formatted_current_delta,
                "ly_delta": formatted_ly_delta,
                "current_contrib": formatted_current_contrib,
                "ly_contrib": formatted_ly_contrib
            }
        }
    
    # 1. 子指标变化情况对比
    sub_delta_diff = sub_metric_delta_current - sub_metric_delta_ly
    if sub_delta_diff > 0.01:
        sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}多了{format_value_for_ai(sub_delta_diff)}，该项成本控制表现恶化。"
    elif sub_delta_diff < -0.01:
        sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，比去年同期的{formatted_ly_delta}少了{format_value_for_ai(abs(sub_delta_diff))}，该项成本控制表现改善。"
    else:
        sub_metric_analysis = f"今年{sub_metric_display_name}的变化量为{formatted_current_delta}，与去年同期的{formatted_ly_delta}基本持平，该项成本控制表现稳定。"
    
    # 2. 子指标贡献度变化分析
    contrib_diff = sub_metric_contribution_current - sub_metric_contribution_ly
    contribution_analysis = ""
    
    # 判断贡献度正负号是否发生变化
    current_sign = "推高总成本" if sub_metric_contribution_current > 0 else "拉低总成本"
    ly_sign = "推高总成本" if sub_metric_contribution_ly > 0 else "拉低总成本"
    
    if (sub_metric_contribution_current > 0 and sub_metric_contribution_ly < 0) or (sub_metric_contribution_current < 0 and sub_metric_contribution_ly > 0):
        # 贡献度正负号发生变化
        contribution_analysis = f"{sub_metric_display_name}对{primary_metric_name}的影响发生了明显转变，从去年同期的{ly_sign}转变为今年的{current_sign}。今年贡献度为{formatted_current_contrib}，去年同期为{formatted_ly_contrib}。"
    else:
        # 贡献度正负号未发生变化，分析数值变化
        if abs(contrib_diff) > 0.1:
            if contrib_diff > 0:
                contribution_analysis = f"{sub_metric_display_name}对{primary_metric_name}的贡献度从去年同期的{formatted_ly_contrib}上升至今年的{formatted_current_contrib}，其影响力增强。"
            else:
                contribution_analysis = f"{sub_metric_display_name}对{primary_metric_name}的贡献度从去年同期的{formatted_ly_contrib}下降至今年的{formatted_current_contrib}，其影响力减弱。"
        else:
            contribution_analysis = f"{sub_metric_display_name}对{primary_metric_name}的贡献度今年为{formatted_current_contrib}，与去年同期的{formatted_ly_contrib}基本持平，影响力稳定。"
    
    return {
        "analysis_type": "两维度分析",
        "sub_metric_analysis": sub_metric_analysis,
        "contribution_analysis": contribution_analysis,
        "formatted_data": {
            "current_delta": formatted_current_delta,
            "ly_delta": formatted_ly_delta,
            "current_contrib": formatted_current_contrib,
            "ly_contrib": formatted_ly_contrib
        }
    } 