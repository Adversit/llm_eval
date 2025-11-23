import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from collections import Counter
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from function.llm_service import load_llm_config, get_llm_analysis, get_llm_analysis_stream

# 设置matplotlib中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

def get_available_projects():
    """获取data目录下所有可用的评估项目"""
    data_dir = "data"
    projects = []
    
    if not os.path.exists(data_dir):
        return projects
    
    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)
        if os.path.isdir(item_path):
            # 查找评估结果文件
            result_files = [f for f in os.listdir(item_path) if f.endswith('_评估结果.xlsx')]
            if result_files:
                # 尝试读取项目信息
                json_files = [f for f in os.listdir(item_path) if f.endswith('.json') and not f.endswith('_评估结果.json')]
                project_info = None
                if json_files:
                    try:
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

def load_questionnaire_results(file_path):
    """加载问卷结果数据"""
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        st.error(f"加载问卷结果失败: {e}")
        return None

def load_questionnaire_file(project_folder):
    """加载原始问卷文件以获取完整选项文本"""
    try:
        questionnaire_files = [f for f in os.listdir(project_folder) if f.endswith('_问卷.xlsx')]
        if questionnaire_files:
            questionnaire_path = os.path.join(project_folder, questionnaire_files[0])
            df = pd.read_excel(questionnaire_path)
            return df
        return None
    except Exception as e:
        return None

def get_option_mapping(questionnaire_df, question_text):
    """从原始问卷获取选项字母到完整文本的映射"""
    try:
        question_row = questionnaire_df[questionnaire_df['问题主干'] == question_text]
        if not question_row.empty:
            options_text = question_row.iloc[0]['答案选项']
            if pd.notna(options_text):
                options_list = options_text.split('|')
                # 创建字母到选项的映射 A->选项1, B->选项2 等
                mapping = {}
                for i, option in enumerate(options_list):
                    letter = chr(65 + i)  # A=65, B=66, C=67...
                    mapping[letter] = option.strip()
                return mapping
    except:
        pass
    return {}

def analyze_single_choice_question(df, question_num, question_text, questionnaire_df=None):
    """分析单选题"""
    question_data = df[df['题号'] == question_num]
    
    if question_data.empty:
        return None

    total_responses = len(question_data)
    if total_responses == 0:
        return None
    
    # 设定选项文本长度阈值
    TEXT_LIMIT = 20
    
    # 获取选项映射
    option_mapping = get_option_mapping(questionnaire_df, question_text) if questionnaire_df is not None else {}
    
    # 如果有选项映射，显示所有选项；否则只显示有答案的选项
    if option_mapping:
        # 显示所有选项，包括未选择的
        all_options = sorted(option_mapping.keys())
        display_labels = []
        display_values = []
        
        for option_letter in all_options:
            count = question_data[question_data['回答'] == option_letter].shape[0]
            proportion = count / total_responses
            full_option = option_mapping[option_letter]
            # 截断过长的选项文本
            if len(full_option) > TEXT_LIMIT:
                full_option = full_option[:TEXT_LIMIT] + "..."
            display_labels.append(f"{option_letter}. {full_option}")
            display_values.append(proportion)
    else:
        # 没有选项映射时，统计实际答案
        answer_counts = question_data['回答'].value_counts().sort_index()
        display_labels = []
        display_values = []
        for option_letter, count in answer_counts.items():
            proportion = count / total_responses
            display_labels.append(option_letter)
            display_values.append(proportion)
    
    # 处理标题，避免重复题号
    title = question_text if str(question_num) + '、' in question_text else f"{question_num}、{question_text}"
    
    # 创建plotly柱状图
    fig = go.Figure(data=go.Bar(
        x=display_labels,
        y=display_values,
        texttemplate='%{y:.1%}',
        textposition='outside',
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="",
        yaxis_title="选择比例",
        showlegend=False,
        height=500,  # 固定高度
        width=None,  # 让宽度自适应
        xaxis_tickangle=-45,
        margin=dict(l=50, r=50, t=80, b=150),  # 固定边距
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10), tickformat=".0%", range=[0, 1.05])
    )
    
    return fig

def analyze_multiple_choice_question(df, question_num, question_text, questionnaire_df=None):
    """分析多选题"""
    question_data = df[df['题号'] == question_num]
    
    if question_data.empty:
        return None

    total_responses = len(question_data)
    if total_responses == 0:
        return None
    
    # 设定选项文本长度阈值
    TEXT_LIMIT = 20
    
    # 获取选项映射
    option_mapping = get_option_mapping(questionnaire_df, question_text) if questionnaire_df is not None else {}
    
    # 统计每个选项被选择的次数
    option_counts = Counter()
    
    for answer in question_data['回答']:
        if pd.notna(answer) and answer:
            # 分割多选答案（用分号分隔）
            options = answer.split(';')
            for option in options:
                option = option.strip()
                if option:
                    option_counts[option] += 1
    
    # 如果有选项映射，显示所有选项；否则只显示有选择的选项
    if option_mapping:
        # 显示所有选项，包括未选择的
        all_options = sorted(option_mapping.keys())
        option_data = []
        
        for option_letter in all_options:
            count = option_counts.get(option_letter, 0)  # 未选择的选项计数为0
            proportion = count / total_responses
            full_option = option_mapping[option_letter]
            # 截断过长的选项文本
            if len(full_option) > TEXT_LIMIT:
                full_option = full_option[:TEXT_LIMIT] + "..."
            display_label = f"{option_letter}. {full_option}"
            option_data.append({
                'letter': option_letter,
                'display_label': display_label,
                'count': proportion
            })
    else:
        # 没有选项映射时，只显示有选择的选项
        option_data = []
        for option_letter, count in option_counts.items():
            proportion = count / total_responses
            option_data.append({
                'letter': option_letter,
                'display_label': option_letter,
                'count': proportion
            })
        # 按字母排序
        option_data.sort(key=lambda x: x['letter'])
    
    display_labels = [item['display_label'] for item in option_data]
    display_values = [item['count'] for item in option_data]
    
    # 处理标题，避免重复题号
    title = question_text if str(question_num) + '、' in question_text else f"{question_num}、{question_text}"
    
    # 创建plotly柱状图
    fig = go.Figure(data=go.Bar(
        x=display_labels,
        y=display_values,
        texttemplate='%{y:.1%}',
        textposition='outside',
        marker_color='lightcoral'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="",
        yaxis_title="选择比例",
        showlegend=False,
        height=500,  # 固定高度，与单选题完全一致
        width=None,  # 让宽度自适应
        xaxis_tickangle=-45,
        margin=dict(l=50, r=50, t=80, b=150),  # 固定边距，与单选题完全一致
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10), tickformat=".0%")
    )
    
    return fig

def generate_overall_statistics(df):
    """生成整体统计信息"""
    try:
        total_responses = len(df['问卷ID'].unique()) if '问卷ID' in df.columns else len(df)
    except:
        total_responses = 0
    
    total_questions = len(df['题号'].unique())
    single_choice_count = len(df[df['问题类型'] == '单选题']['题号'].unique())
    multiple_choice_count = len(df[df['问题类型'] == '多选题']['题号'].unique())
    
    return {
        'total_responses': total_responses,
        'total_questions': total_questions,
        'single_choice_count': single_choice_count,
        'multiple_choice_count': multiple_choice_count
    }

def create_capability_distribution_chart(df):
    """创建能力项分布图"""
    item_counts = df.groupby('能力项')['题号'].nunique().reset_index()
    item_counts.columns = ['能力项', '题目数量']
    item_counts = item_counts.sort_values('题目数量', ascending=True)
    
    fig = go.Figure(data=go.Bar(
        x=item_counts['题目数量'],
        y=item_counts['能力项'],
        orientation='h',
        marker_color='lightgreen'
    ))
    
    fig.update_layout(
        title="各能力项题目数量分布",
        xaxis_title="题目数量",
        yaxis_title="能力项",
        height=max(400, len(item_counts) * 30)
    )
    
    return fig

def calculate_question_expectation(df, question_num):
    """计算单个问题的期望值"""
    question_data = df[df['题号'] == question_num]
    if question_data.empty:
        return None

    total_responses = len(question_data)
    if total_responses == 0:
        return None

    score_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
    
    answer_counts = question_data['回答'].value_counts()
    
    total_score = 0
    for answer, count in answer_counts.items():
        total_score += score_map.get(str(answer).strip(), 0) * count
        
    expected_value = total_score / total_responses
    return expected_value

def analyze_user_demand_matching(df):
    """分析用户需求匹配度"""
    keywords = {
        'understanding': "是否能准确理解您的基本查询需求",
        'accuracy': "提供的信息准确率大约在什么水平",
        'satisfaction': "回应您需求的满意度是"
    }
    
    results = {}
    unique_questions = df[['题号', '问题']].drop_duplicates()
    question_info = {}

    for q_type, keyword in keywords.items():
        matched_row = unique_questions[unique_questions['问题'].str.contains(keyword, na=False)]
        if not matched_row.empty:
            q_num = matched_row.iloc[0]['题号']
            q_text = matched_row.iloc[0]['问题']
            
            expectation = calculate_question_expectation(df, q_num)
            if expectation is not None:
                question_info[q_type] = {
                    'text': q_text,
                    'num': q_num,
                    'expectation': expectation,
                    'score': int(expectation)
                }

    if len(question_info) == 3:
        final_score = min(info['score'] for info in question_info.values())
        results['final_score'] = final_score
        results['details'] = question_info
        
        rating_descriptions = {
            1: "大模型能够识别基本的用户需求，但准确性和相关性较低",
            2: "大模型能够识别和理解较为复杂的用户需求，提供的信息有一定的准确性和相关性",
            3: "大模型能够准确识别和理解复杂的用户需求，提供的信息高度相关且准确",
            4: "大模型不仅能够准确识别和理解复杂的用户需求，还能提供个性化的建议和解决方案",
            5: "大模型在识别和理解用户需求方面达到卓越水平，能够实时适应用户需求变化并提供最优解决方案"
        }
        results['final_rating_description'] = rating_descriptions.get(final_score, "无评级")

        return results
    else:
        return None

def analyze_automation_improvement(df):
    """分析业务自动化提升率"""
    keywords = {
        'complexity': "能够自动化处理的业务复杂度如何",
        'intervention': "完成业务流程时，需要人工干预和监督的任务占比约为",
        'improvement': "您估计业务自动化程度提升了多少？"
    }
    
    results = {}
    unique_questions = df[['题号', '问题']].drop_duplicates()
    question_info = {}

    for q_type, keyword in keywords.items():
        matched_row = unique_questions[unique_questions['问题'].str.contains(keyword, na=False)]
        if not matched_row.empty:
            q_num = matched_row.iloc[0]['题号']
            q_text = matched_row.iloc[0]['问题']
            
            expectation = calculate_question_expectation(df, q_num)
            if expectation is not None:
                question_info[q_type] = {
                    'text': q_text,
                    'num': q_num,
                    'expectation': expectation,
                    'score': int(expectation)
                }

    if len(question_info) == 3:
        final_score = min(info['score'] for info in question_info.values())
        results['final_score'] = final_score
        results['details'] = question_info
        
        rating_descriptions = {
            1: "仅能实现部分任务的自动化，需要大量人工干预",
            2: "能够实现较多任务的自动化，但仍需相当一部分人工监督",
            3: "能够实现大部分任务的自动化，人工干预较少",
            4: "能够实现几乎所有任务的自动化，人工干预极少",
            5: "能够实现完全的任务自动化，几乎无需人工干预"
        }
        results['final_rating_description'] = rating_descriptions.get(final_score, "无评级")

        return results
    else:
        return None

def analyze_decision_support(df):
    """分析业务决策支持力"""
    keywords = {
        'effectiveness': "辅助业务工作决策的效果如何",
        'coverage': "可支持的决策环节占整个业务决策链条",
        'accuracy': "在理解您的要求时，准确率约为多少"
    }
    
    results = {}
    unique_questions = df[['题号', '问题']].drop_duplicates()
    question_info = {}

    for q_type, keyword in keywords.items():
        matched_row = unique_questions[unique_questions['问题'].str.contains(keyword, na=False)]
        if not matched_row.empty:
            q_num = matched_row.iloc[0]['题号']
            q_text = matched_row.iloc[0]['问题']
            
            expectation = calculate_question_expectation(df, q_num)
            if expectation is not None:
                question_info[q_type] = {
                    'text': q_text,
                    'num': q_num,
                    'expectation': expectation,
                    'score': int(expectation)
                }

    if len(question_info) == 3:
        final_score = min(info['score'] for info in question_info.values())
        results['final_score'] = final_score
        results['details'] = question_info
        
        rating_descriptions = {
            1: "组织尚未认识到大模型在业务决策中的潜力，或尚未开始相关技术的探索与应用",
            2: "组织开始尝试将大模型技术应用于业务决策支持，进行初步的业务预测与分析",
            3: "组织能够有效管理和整合大模型技术，用于支持复杂决策，并实现一定程度的自动化",
            4: "组织能够利用大模型技术实现高度智能化的业务决策支持，显著优化决策效率与效果",
            5: "组织不仅能够高效利用大模型优化当前决策，还能预见未来趋势，实现真正的自主与协同决策"
        }
        results['final_rating_description'] = rating_descriptions.get(final_score, "无评级")

        return results
    else:
        return None

def analyze_customer_loyalty(df):
    """分析客户忠诚度"""
    keywords = {
        'trust': "接受与信任程度如何",
        'frequency': "高频使用"
    }
    
    results = {}
    unique_questions = df[['题号', '问题']].drop_duplicates()
    question_info = {}

    for q_type, keyword in keywords.items():
        matched_row = unique_questions[unique_questions['问题'].str.contains(keyword, na=False)]
        if not matched_row.empty:
            q_num = matched_row.iloc[0]['题号']
            q_text = matched_row.iloc[0]['问题']
            
            expectation = calculate_question_expectation(df, q_num)
            if expectation is not None:
                question_info[q_type] = {
                    'text': q_text,
                    'num': q_num,
                    'expectation': expectation,
                    'score': int(expectation)
                }

    if len(question_info) == 2:
        final_score = min(info['score'] for info in question_info.values())
        results['final_score'] = final_score
        results['details'] = question_info
        
        rating_descriptions = {
            1: "客户忠诚度提升有限，用户推荐意愿较低，留存率较差",
            2: "客户忠诚度有所提升，用户体验有待改进",
            3: "客户忠诚度显著提升，应用较为成熟，用户留存率较好",
            4: "客户忠诚度极大提升，应用非常成熟，能够提供高度个性化和精准的服务",
            5: "客户忠诚度达到极致，用户体验极为出色，用户对应用的依赖性和满意度极高"
        }
        results['final_rating_description'] = rating_descriptions.get(final_score, "无评级")

        return results
    else:
        return None

def analyze_time_cost_saving(df):
    """分析时间成本节約率"""
    keyword = "是否能够帮助您有效降低工作时间成本"
    q_type = "saving"
    
    results = {}
    unique_questions = df[['题号', '问题']].drop_duplicates()
    question_info = {}
    
    matched_row = unique_questions[unique_questions['问题'].str.contains(keyword, na=False)]
    if not matched_row.empty:
        q_num = matched_row.iloc[0]['题号']
        q_text = matched_row.iloc[0]['问题']
        
        expectation = calculate_question_expectation(df, q_num)
        if expectation is not None:
            score = int(expectation)
            question_info[q_type] = {
                'text': q_text,
                'num': q_num,
                'expectation': expectation,
                'score': score
            }

    if len(question_info) == 1:
        final_score = question_info[q_type]['score']
        results['final_score'] = final_score
        results['details'] = question_info
        
        rating_descriptions = {
            1: "大模型在金融业务场景中对时间成本的节约效果较低，任务完成时间减少不明显",
            2: "大模型在金融业务场景中对时间成本的节约有所提升，但仍有较大的优化空间",
            3: "大模型在金融业务场景中对时间成本的节约达到中等水平，任务完成时间显著减少",
            4: "大模型在金融业务场景中对时间成本的节约效果较好，任务完成时间大幅减少",
            5: "大模型在金融业务场景中对时间成本的节约效果极佳，任务完成时间显著缩短"
        }
        results['final_rating_description'] = rating_descriptions.get(final_score, "无评级")
        return results
            
    return None

def display_analysis_results(title, results, metric_labels):
    """Helper function to display analysis results in a consistent format."""
    st.markdown("---")
    st.markdown(f'<h3 style="text-align: center;">{title}评级</h3>', unsafe_allow_html=True)
    if results:
        details = results['details']
        final_score = results['final_score']
        final_desc = results['final_rating_description']
        
        metric_cols = st.columns(len(metric_labels))
        for i, (q_type, label) in enumerate(metric_labels.items()):
            with metric_cols[i]:
                score = details[q_type]['score']
                help_text = f"基于问题: \"{details[q_type]['text']}\"\n期望值为: {details[q_type]['expectation']:.2f}"
                
                # 使用Markdown和HTML实现居中对齐的指标卡
                st.markdown(f"""
                <div style="text-align: center;">
                    <p style="font-size: 1.11rem; margin-bottom: 0;">
                        {label}得分
                    </p>
                    <p style="font-size: 2rem; margin-top: 0;">{score}</p>
                </div>
                """, unsafe_allow_html=True)

        score_to_level = {1: "一级", 2: "二级", 3: "三级", 4: "四级", 5: "五级"}
        level_text = score_to_level.get(final_score, "")
        
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge",
            value=final_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': ""},
            gauge={
                'axis': {'range': [0, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#C00000", 'thickness': 0.4},
                'steps': [
                    {'range': [0, 1], 'color': "#E3F2FD"},
                    {'range': [1, 2], 'color': "#90CAF9"},
                    {'range': [2, 3], 'color': "#42A5F5"},
                    {'range': [3, 4], 'color': "#1E88E5"},
                    {'range': [4, 5], 'color': "#0D47A1"},
                ],
                'borderwidth': 0,
                 'threshold': {
                    'line': {'color': "#8E0000", 'width': 4},
                    'thickness': 0.75,
                    'value': final_score
                }
            }
        ))


        fig_gauge.add_annotation(
            x=0.5,
            y=0.19,
            text=f"{level_text}",
            showarrow=False,
            font=dict(
                family="Microsoft YaHei",
                size=48,
                color="#000000"
            )
        )

        fig_gauge.update_layout(height=400, margin=dict(l=20, r=20, t=0, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.markdown(
            f'<div style="background-color: #F2F2F2; padding: 12px 10px; border-radius: 5px; margin-bottom: 40px;">'
            f'<b>评级说明：</b> {final_desc}'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.info(f"ℹ️ 问卷中未找到用于计算**{title}**的全部三个核心问题，无法进行分析。")

def Admin_analyse_function_page():
    """数据分析页面主函数"""
    st.title("📊 问卷结果数据分析")
    st.markdown("### 评估数据可视化分析工具")
    st.markdown("---")
    
    # 获取可用项目
    projects = get_available_projects()
    
    if not projects:
        st.warning("🔍 未找到任何评估结果数据")
        st.info("""
        **说明：**
        - 请确保data目录下存在评估项目文件夹
        - 每个项目文件夹中应包含"[项目名]_评估结果.xlsx"文件
        - 评估结果文件由问卷采集页面自动生成
        """)
        return
    
    # 项目选择
    st.header(" 项目选择")
    
    project_options = {proj['display_name']: proj for proj in projects}
    selected_project_name = st.selectbox(
        "选择要分析的评估项目",
        options=list(project_options.keys()),
        help="选择一个已完成评估的项目进行数据分析"
    )
    
    if not selected_project_name:
        return
    
    selected_project = project_options[selected_project_name]
    
    # 显示项目信息
    st.markdown("---")
    if selected_project['project_info']:
        eval_info = selected_project['project_info'].get('evaluation_info', {})
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("公司名称", eval_info.get('company_name', '未知'))
        with col2:
            st.metric("场景名称", eval_info.get('scenario_name', '未知'))
        with col3:
            st.metric("创建时间", eval_info.get('created_time', '未知')[:10] if eval_info.get('created_time') else '未知')
        with col4:
            st.metric("评估状态", eval_info.get('status', '未知'))

    df = load_questionnaire_results(selected_project['result_file'])
    if df is None:
        return
    
    # 加载原始问卷文件以获取完整选项文本
    project_folder = os.path.dirname(selected_project['result_file'])
    questionnaire_df = load_questionnaire_file(project_folder)
    
    # 整体统计
    stats = generate_overall_statistics(df)

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("问卷份数", stats['total_responses'])
    with col2:
        st.metric("题目总数", stats['total_questions'])
    with col3:
        st.metric("单选题数", stats['single_choice_count'])
    with col4:
        st.metric("多选题数", stats['multiple_choice_count'])
    
    # 能力项分布图
    capability_fig = create_capability_distribution_chart(df)
    st.plotly_chart(capability_fig, use_container_width=True)
    
    # 题目分析 - 按题目顺序，每排2个图
    
    # 获取唯一的题目信息
    questions_info = df[['题号', '问题', '问题类型']].drop_duplicates().sort_values('题号')
    
    # 按题目顺序显示，每排2个图
    questions_list = list(questions_info.iterrows())
    for i in range(0, len(questions_list), 2):
        col1, col2 = st.columns(2)
        
        # 第一个图
        if i < len(questions_list):
            _, row1 = questions_list[i]
            question_num1 = row1['题号']
            question_text1 = row1['问题']
            question_type1 = row1['问题类型']
            
            with col1:
                if question_type1 == '单选题':
                    fig1 = analyze_single_choice_question(df, question_num1, question_text1, questionnaire_df)
                    if fig1:
                        st.plotly_chart(fig1, use_container_width=True)
                elif question_type1 == '多选题':
                    fig1 = analyze_multiple_choice_question(df, question_num1, question_text1, questionnaire_df)
                    if fig1:
                        st.plotly_chart(fig1, use_container_width=True)
        
        # 第二个图
        if i + 1 < len(questions_list):
            _, row2 = questions_list[i + 1]
            question_num2 = row2['题号']
            question_text2 = row2['问题']
            question_type2 = row2['问题类型']
            
            with col2:
                if question_type2 == '单选题':
                    fig2 = analyze_single_choice_question(df, question_num2, question_text2, questionnaire_df)
                    if fig2:
                        st.plotly_chart(fig2, use_container_width=True)
                elif question_type2 == '多选题':
                    fig2 = analyze_multiple_choice_question(df, question_num2, question_text2, questionnaire_df)
                    if fig2:
                        st.plotly_chart(fig2, use_container_width=True)

    # 综合维度分析
    st.markdown("---")
    st.header("📈 各项评级")

    analysis_tasks = [
        {
            "title": "用户需求匹配度",
            "analyzer": analyze_user_demand_matching,
            "labels": {
                'understanding': "理解能力",
                'accuracy': "信息准确率",
                'satisfaction': "用户满意度"
            }
        },
        {
            "title": "业务自动化提升率",
            "analyzer": analyze_automation_improvement,
            "labels": {
                'complexity': "处理复杂度",
                'intervention': "人工干预度",
                'improvement': "自动化提升率"
            }
        },
        {
            "title": "业务决策支持力",
            "analyzer": analyze_decision_support,
            "labels": {
                'effectiveness': "决策效果",
                'coverage': "决策覆盖率",
                'accuracy': "理解准确率"
            }
        },
        {
            "title": "客户忠诚度",
            "analyzer": analyze_customer_loyalty,
            "labels": {
                'trust': "信任与接受度",
                'frequency': "使用频率"
            }
        },
        {
            "title": "时间成本节约率",
            "analyzer": analyze_time_cost_saving,
            "labels": {
                'saving': "时间节约效果"
            }
        }
    ]

    reports = []
    for task in analysis_tasks:
        results = task["analyzer"](df)
        if results:
            reports.append({
                "title": task["title"],
                "results": results,
                "labels": task["labels"]
            })

    for i in range(0, len(reports), 2):
        cols = st.columns(2)

        # 第一个图
        with cols[0]:
            report = reports[i]
            display_analysis_results(report["title"], report["results"], report["labels"])

        # 第二个图
        if i + 1 < len(reports):
            with cols[1]:
                report = reports[i+1]
                display_analysis_results(report["title"], report["results"], report["labels"])

    def prepare_multichoice_data_for_ai(df, questionnaire_df):
        """准备多选题数据以供AI分析"""
        multichoice_questions = df[df['问题类型'] == '多选题']
        unique_questions = multichoice_questions[['题号', '问题']].drop_duplicates().sort_values('题号')
        
        analysis_data = []
        
        for _, row in unique_questions.iterrows():
            q_num = row['题号']
            q_text = row['问题']
            
            question_data = df[df['题号'] == q_num]
            total_responses = len(question_data['问卷ID'].unique())
            if total_responses == 0:
                continue

            option_mapping = get_option_mapping(questionnaire_df, q_text)
            
            option_counts = Counter()
            for answer in question_data['回答']:
                if pd.notna(answer) and answer:
                    options = answer.split(';')
                    for option in options:
                        option = option.strip()
                        if option:
                            option_counts[option] += 1
            
            options_summary = []
            sorted_options = sorted(option_mapping.keys()) if option_mapping else sorted(option_counts.keys())

            for option_letter in sorted_options:
                count = option_counts.get(option_letter, 0)
                proportion = count / total_responses if total_responses > 0 else 0
                option_text = option_mapping.get(option_letter, "未知选项")
                options_summary.append(f"  - 选项 {option_letter} ({option_text}): 选择比例 {proportion:.1%}")
            
            analysis_data.append(f"问题 {q_num}：{q_text}\n" + "\n".join(options_summary))
            
        return "\n\n".join(analysis_data)

    def build_ai_prompt(multichoice_data_summary):
        """构建用于AI分析的提示"""
        return f"""
请根据以下多选题的调研数据，撰写一段深入的分析报告。

你的任务是：
1. **识别核心模式**：不要仅仅复述数据。要找出数据背后隐藏的模式、关联或矛盾之处。例如，用户在一个问题上选择A，在另一个问题上选择B，这背后可能反映了什么共同的心态或现状？
2. **提炼核心结论**：基于你发现的模式，提出2-3个核心的、有价值的结论。
3. **专业化语言**：使用专业、客观、正式的分析师语言，避免口语化表达。
4. **结构清晰**：分析报告应该逻辑连贯，形成一个有机整体，而不是简单的要点罗列。
5. **只总结发现的情况，不提供建议**
以下是需要分析的数据：
---
{multichoice_data_summary}
---

请开始你的分析，直接输出分析报告即可，不需要包含"好的，这是一个分析"等多余的话。
"""

    def generate_deterministic_report(reports, total_responses):
        """
        生成报告的前两个确定性部分。
        """
        report_parts = []
        final_rating_map = {1: "一级", 2: "二级", 3: "三级", 4: "四级", 5: "五级"}

        # --- 段落一：总结性概述 ---
        final_rating_score = min(report['results']['final_score'] for report in reports)
        final_rating_text = final_rating_map.get(final_rating_score, "未评级")
        evaluated_dimensions = [report['title'] for report in reports]
        report_parts.append(" ")
        report_parts.append("#### 一、综合评估总结")
        summary_text = (
            f"本次评估的最终综合评级为**{final_rating_text}**。"
            f"评估共覆盖{len(evaluated_dimensions)}个能力域，包括：{', '.join(evaluated_dimensions)}。"
            f"本次分析结果基于{total_responses}份有效问卷。"
        )
        report_parts.append(summary_text)

        # --- 段落二：分维度详细分析 ---
        report_parts.append("#### 二、各维度表现详述")
        for report in reports:
            title = report['title']
            results = report['results']
            labels = report['labels']
            
            score = results['final_score']
            rating_text = final_rating_map.get(score, "未评级")
            description = results['final_rating_description']
            
            sub_items = [{"name": label, "score": results['details'][q_type]['score']} for q_type, label in labels.items()]
            
            dimension_analysis_detail = ""
            if not sub_items:
                dimension_analysis_detail = ""
            elif len(sub_items) == 1:
                score = sub_items[0]['score']
                dimension_analysis_detail = f"其表现由**{sub_items[0]['name']}**这一子项决定，得分为{score}分。"
            else:
                min_score = min(item['score'] for item in sub_items)
                max_score = max(item['score'] for item in sub_items)

                if min_score == max_score:
                    dimension_analysis_detail = f"该维度下的各子项表现均衡，得分均为{min_score}分。"
                else:
                    lowest_items = [item['name'] for item in sub_items if item['score'] == min_score]
                    highest_items = [item['name'] for item in sub_items if item['score'] == max_score]
                    dimension_analysis_detail = (
                        f"该能力项评级主要受限于{', '.join(lowest_items)}（得分: {min_score}），"
                        f"而在{', '.join(highest_items)}（得分: {max_score}）方面表现相对较好。"
                    )
            
            dimension_analysis = (
                f"{title}的评级为**{rating_text}**，本场景{description}。"
                f"{dimension_analysis_detail}"
            )
            report_parts.append(dimension_analysis)
        
        return "\n\n".join(report_parts)

    # 分析报告生成
    st.markdown("---")
    st.header("📊 评级分析报告")
    
    if reports:
        if st.button("✨ 点击生成分析报告", type="primary", use_container_width=True):
            
            report_box_template = (
                '<div style="background-color: #F8F9FA; border: 1px solid #E9ECEF; padding: 20px; border-radius: 10px;">'
                '{content}'
                '</div>'
            )
            
            # 1. 立即生成并展示确定性内容
            deterministic_content = generate_deterministic_report(reports, stats['total_responses'])
            placeholder = st.empty()
            placeholder.markdown(report_box_template.format(content=deterministic_content), unsafe_allow_html=True)
            
            # 2. 准备AI分析所需数据
            llm_config = load_llm_config()
            multichoice_data = prepare_multichoice_data_for_ai(df, questionnaire_df)
            
            # 3. 执行并流式展示AI分析
            if llm_config and multichoice_data:
                api_key, base_url, model_name = None, None, None
                api_key = llm_config.get("api_key")
                base_url = llm_config.get("base_url")
                model_name = llm_config.get("model_name")
                if not all([api_key, base_url, model_name]):
                    first_key = next(iter(llm_config), None)
                    if first_key and isinstance(llm_config[first_key], dict):
                        config_dict = llm_config[first_key]
                        api_key = config_dict.get("api_key")
                        base_url = config_dict.get("base_url")
                        model_name = config_dict.get("model")

                prompt = build_ai_prompt(multichoice_data)
                
                # 为第三部分准备内容
                ai_content_header = "\n\n#### 三、多选题深度洞察\n\n"
                full_content_so_far = deterministic_content + ai_content_header
                ai_analysis_text = ""

                # 显示加载状态
                placeholder.markdown(report_box_template.format(content=full_content_so_far + "⏳ 调用AI进行深度分析中..."), unsafe_allow_html=True)
                
                # 获取并显示流式响应
                stream = get_llm_analysis_stream(prompt, api_key, base_url, model_name)
                for chunk in stream:
                    ai_analysis_text += chunk
                    placeholder.markdown(report_box_template.format(content=full_content_so_far + ai_analysis_text + "▌"), unsafe_allow_html=True)
                
                # 移除光标并最终显示
                final_content = full_content_so_far + ai_analysis_text
                placeholder.markdown(report_box_template.format(content=final_content), unsafe_allow_html=True)
                st.success("✅ 分析报告已全部生成！")

            elif not llm_config:
                error_msg = "\n\n#### 三、多选题深度洞察\n\n未能加载`model_config.json`配置文件，AI分析模块无法启动。"
                placeholder.markdown(report_box_template.format(content=deterministic_content + error_msg), unsafe_allow_html=True)
            elif not multichoice_data:
                error_msg = "\n\n#### 三、多选题深度洞察\n\n报告中未发现多选题数据，无法进行AI深度洞察。"
                placeholder.markdown(report_box_template.format(content=deterministic_content + error_msg), unsafe_allow_html=True)

    else:
        st.info("ℹ️ 当前没有足够的评级数据可供分析。")

    # 简化的导出功能
    st.markdown("---")

if __name__ == "__main__":
    Admin_analyse_function_page() 