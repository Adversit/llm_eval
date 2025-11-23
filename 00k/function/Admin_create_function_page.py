import streamlit as st
import pandas as pd
import json
from datetime import datetime
from data_parser import build_comprehensive_structure, parse_question_content, build_flmm_evaluation_structure
import hashlib
import uuid
import os
import threading
import time
import subprocess
import socket

# 线程锁，用于处理并发写入
file_lock = threading.Lock()

# 端口管理文件
PORT_CONFIG_FILE = "data/.port_config.json"

def find_available_port(start_port=8502, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def load_port_config():
    """加载端口配置"""
    if os.path.exists(PORT_CONFIG_FILE):
        try:
            with open(PORT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_port_config(config):
    """保存端口配置"""
    os.makedirs(os.path.dirname(PORT_CONFIG_FILE), exist_ok=True)
    with open(PORT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def start_streamlit_app(folder_path, py_filename, port):
    """后台启动Streamlit应用"""
    try:
        # 构建完整路径
        script_path = os.path.join(folder_path, py_filename)

        # 启动Streamlit进程（后台运行）
        process = subprocess.Popen(
            [
                "streamlit", "run", script_path,
                "--server.port", str(port),
                "--server.headless", "true",
                "--server.address", "localhost"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=folder_path  # 设置工作目录
        )

        return process.pid
    except Exception as e:
        st.error(f"启动Streamlit失败: {e}")
        return None

def update_state_if_changed(state_dict, key, new_value):
    """只有当状态真正发生变化时才更新"""
    if state_dict.get(key, False) != new_value:
        state_dict[key] = new_value
        return True
    return False

def count_questions_in_structure(structure):
    """统计数据结构中的问题总数"""
    total_questions = 0
    for domain, subdomain1s in structure.items():
        for subdomain1, subdomain2s in subdomain1s.items():
            for subdomain2, items in subdomain2s.items():
                for item, questions in items.items():
                    if isinstance(questions, list):
                        total_questions += len(questions)
    return total_questions

def count_capability_items(structure):
    """统计能力项总数"""
    total_items = 0
    for domain, subdomain1s in structure.items():
        for subdomain1, subdomain2s in subdomain1s.items():
            for subdomain2, items in subdomain2s.items():
                total_items += len(items)
    return total_items

def show_company_info():
    """页面1：被评估方信息"""
    st.title("🏢 被评估方信息")
    st.markdown("### FLMM评估 - 步骤1/4")
    st.markdown("---")
    
    st.info("请输入被评估方的基本信息，用于后续评估项目的创建和管理。")
    
    # 创建两列布局
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        st.header("📝 基本信息")
        
        company_name = st.text_input(
            "被评估方公司名称 *", 
            value=st.session_state.get('company_name', ''),
            placeholder="请输入被评估方的公司全称",
            help="输入要进行FLMM评估的金融机构名称"
        )
        st.session_state.company_name = company_name
        
        scenario_name = st.text_input(
            "评估大模型名称 *",
            value=st.session_state.get('scenario_name', ''),
            placeholder="请输入具体的大模型名称",
            help="例如：智能客服、风险控制、投资顾问等"
        )
        st.session_state.scenario_name = scenario_name
        
        scenario_description = st.text_area(
            "评估业务场景描述 *",
            value=st.session_state.get('scenario_description', ''),
            placeholder="请详细描述该业务场景的具体内容、应用范围和预期目标...",
            height=120,
            help="详细描述业务场景的背景、应用方式、预期效果等"
        )
        st.session_state.scenario_description = scenario_description
        
        st.markdown("---")
        
        # 功能列表管理
        st.subheader("⚙️ 功能模块管理")
        
        # 初始化功能列表
        if 'functions_list' not in st.session_state:
            st.session_state.functions_list = []
        
        # 添加功能的表单
        with st.expander("➕ 添加新功能", expanded=len(st.session_state.functions_list) == 0):
            with st.form("add_function_form"):
                function_name = st.text_input("功能名称", placeholder="例如：信息总结")
                function_description = st.text_area("功能描述", placeholder="请详细描述该功能的作用和应用场景", height=80)
                
                if st.form_submit_button("✅ 添加功能"):
                    if function_name and function_description:
                        st.session_state.functions_list.append({
                            'name': function_name,
                            'description': function_description
                        })
                        st.success(f"✅ 功能「{function_name}」添加成功！")
                        st.rerun()
                    else:
                        st.warning("⚠️ 请填写完整的功能名称和描述")
        
        # 显示已添加的功能
        if st.session_state.functions_list:
            st.write("**已添加的功能模块：**")
            for i, func in enumerate(st.session_state.functions_list):
                col_func1, col_func2 = st.columns([0.8, 0.2])
                with col_func1:
                    st.write(f"**{i+1}. {func['name']}**")
                    st.caption(func['description'])
                with col_func2:
                    if st.button("🗑️", key=f"delete_func_{i}", help="删除此功能"):
                        st.session_state.functions_list.pop(i)
                        st.rerun()
    
    with col2:
        st.header("📊 信息概览")
        
        # 检查必填字段
        required_fields = [company_name, scenario_name, scenario_description]
        filled_fields = sum(1 for field in required_fields if field and field.strip())
        
        st.metric("信息完整度", f"{filled_fields}/3")
        st.metric("功能模块数", len(st.session_state.functions_list))
        
        if filled_fields == 3:
            st.success("✅ 基本信息已完整")
        else:
            st.warning("⚠️ 请完善必填信息")
        
        st.markdown("---")
        st.subheader("📋 后续步骤")
        st.write("1. 📝 填写基本信息")
        st.write("2. 📋 选择问卷内容")
        st.write("3. 选择证明材料")
        st.write("4. 🔍 预览确认生成")
    
    # 导航按钮
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        st.info("这是第一步，请填写完整信息后继续")
    
    with col_btn2:
        can_continue = all([company_name, scenario_name, scenario_description])
        if st.button("📋 下一步：选择问卷", type="primary", use_container_width=True, disabled=not can_continue):
            if can_continue:
                st.session_state.current_page = "questionnaire_selection"
                st.rerun()
            else:
                st.warning("⚠️ 请填写完整的基本信息")

def show_questionnaire_selection():
    """页面2：问卷筛选"""
    st.title("📋 问卷内容选择")
    st.markdown("### FLMM评估 - 步骤2/4")
    st.markdown("---")
    
    # 获取数据结构
    structure = build_comprehensive_structure()
    
    if not structure:
        st.error("❌ 无法读取FLMM调研表数据，请检查data/FLMM调研表.xlsx文件是否存在")
        st.stop()
    
    # 显示数据概览
    total_questions = count_questions_in_structure(structure)
    total_items = count_capability_items(structure)
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    with col_info1:
        st.metric("能力域数量", len(structure))
    with col_info2:
        subdomain1_count = sum(len(subdomain1s) for subdomain1s in structure.values())
        st.metric("能力子域1数量", subdomain1_count)
    with col_info3:
        st.metric("能力项数量", total_items)
    with col_info4:
        st.metric("总问题数量", total_questions)
    
    st.markdown("---")
    
    # 初始化选择状态
    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = {}
    
    # 创建两列布局
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.header(" 能力项选择")
        st.info("请选择需要评估的能力项。您可以按能力域、子域或具体能力项进行选择。")
        
        # 遍历能力域
        for domain, subdomain1s in structure.items():
            st.subheader(f"{domain}")
            
            # 能力域级别的全选
            domain_key = f"domain_{domain}"
            domain_selected = st.checkbox(
                f"✅ 全选「{domain}」所有能力项",
                key=domain_key,
                value=st.session_state.selected_items.get(domain_key, False)
            )
            # 只有当状态发生变化时才更新
            if update_state_if_changed(st.session_state.selected_items, domain_key, domain_selected):
                pass
            
            # 遍历能力子域1 - 使用expander
            for subdomain1, subdomain2s in subdomain1s.items():
                with st.expander(f"📂 {subdomain1}", expanded=st.session_state.selected_items.get(domain_key, False)):
                    
                    # 能力子域1级别的选择
                    subdomain1_key = f"subdomain1_{domain}_{subdomain1}"
                    current_subdomain1_value = st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False)
                    subdomain1_selected = st.checkbox(
                        f"📌 选择「{subdomain1}」所有项",
                        key=subdomain1_key,
                        value=current_subdomain1_value,
                        disabled=st.session_state.selected_items.get(domain_key, False)
                    )
                    # 只有当状态发生变化时才更新
                    if update_state_if_changed(st.session_state.selected_items, subdomain1_key, subdomain1_selected):
                        pass
                    
                    # 遍历能力子域2 - 不使用expander，改用容器和缩进
                    for subdomain2, items in subdomain2s.items():
                        if subdomain2:  # 只有当能力子域2不为空时才显示
                            st.markdown(f"**📋 {subdomain2}**")
                            
                            # 能力子域2级别的选择
                            subdomain2_key = f"subdomain2_{domain}_{subdomain1}_{subdomain2}"
                            current_subdomain2_value = st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(subdomain2_key, False)
                            subdomain2_selected = st.checkbox(
                                f"🔖 选择「{subdomain2}」所有项",
                                key=subdomain2_key,
                                value=current_subdomain2_value,
                                disabled=st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False)
                            )
                            # 只有当状态发生变化时才更新
                            if update_state_if_changed(st.session_state.selected_items, subdomain2_key, subdomain2_selected):
                                pass
                            
                            # 遍历能力项 - 添加缩进
                            for item, questions in items.items():
                                item_key = f"item_{domain}_{subdomain1}_{subdomain2}_{item}"
                                
                                # 使用列来创建缩进效果
                                col_indent, col_item = st.columns([0.1, 0.9])
                                with col_item:
                                    current_item_value = st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(subdomain2_key, False) or st.session_state.selected_items.get(item_key, False)
                                    item_selected = st.checkbox(
                                        f"📄 {item}",
                                        key=item_key,
                                        value=current_item_value,
                                        disabled=st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(subdomain2_key, False)
                                    )
                                    # 只有当状态发生变化时才更新
                                    if update_state_if_changed(st.session_state.selected_items, item_key, item_selected):
                                        pass
                                    
                                    # 如果选中该能力项，显示问题预览
                                    if item_selected or st.session_state.selected_items.get(subdomain2_key, False) or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(domain_key, False):
                                        question_count = len(questions) if isinstance(questions, list) else 0
                                        st.caption(f"　　包含 {question_count} 个调研问题")
                        else:
                            # 如果能力子域2为空，直接显示能力项
                            for item, questions in items.items():
                                item_key = f"item_{domain}_{subdomain1}__{item}"
                                current_item_value = st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(item_key, False)
                                item_selected = st.checkbox(
                                    f"📄 {item}",
                                    key=item_key,
                                    value=current_item_value,
                                    disabled=st.session_state.selected_items.get(domain_key, False) or st.session_state.selected_items.get(subdomain1_key, False)
                                )
                                # 只有当状态发生变化时才更新
                                if update_state_if_changed(st.session_state.selected_items, item_key, item_selected):
                                    pass
                                
                                # 如果选中该能力项，显示问题预览
                                if item_selected or st.session_state.selected_items.get(subdomain1_key, False) or st.session_state.selected_items.get(domain_key, False):
                                    question_count = len(questions) if isinstance(questions, list) else 0
                                    st.caption(f"　　包含 {question_count} 个调研问题")
    
    with col2:
        st.header("📊 筛选结果")
        
        # 收集选中的内容
        selected_questions = []
        selected_items_info = []
        
        for domain, subdomain1s in structure.items():
            domain_key = f"domain_{domain}"
            domain_selected = st.session_state.selected_items.get(domain_key, False)
            
            for subdomain1, subdomain2s in subdomain1s.items():
                subdomain1_key = f"subdomain1_{domain}_{subdomain1}"
                subdomain1_selected = st.session_state.selected_items.get(subdomain1_key, False)
                
                for subdomain2, items in subdomain2s.items():
                    subdomain2_key = f"subdomain2_{domain}_{subdomain1}_{subdomain2}"
                    subdomain2_selected = st.session_state.selected_items.get(subdomain2_key, False)
                    
                    for item, questions in items.items():
                        if subdomain2:
                            item_key = f"item_{domain}_{subdomain1}_{subdomain2}_{item}"
                        else:
                            item_key = f"item_{domain}_{subdomain1}__{item}"
                            
                        item_selected = st.session_state.selected_items.get(item_key, False)
                        
                        if domain_selected or subdomain1_selected or subdomain2_selected or item_selected:
                            question_count = len(questions) if isinstance(questions, list) else 0
                            selected_items_info.append({
                                'domain': domain,
                                'subdomain1': subdomain1,
                                'subdomain2': subdomain2,
                                'item': item,
                                'questions': questions if isinstance(questions, list) else [],
                                'question_count': question_count
                            })
                            if isinstance(questions, list):
                                selected_questions.extend(questions)
        
        # 显示统计信息
        if selected_items_info:
            # 统计卡片
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric("选中能力项", len(selected_items_info))
            with metrics_col2:
                st.metric("总问题数", len(selected_questions))
            
            st.markdown("---")
            
            # 显示选中的能力项摘要
            st.subheader("📋 已选择的能力项")
            for i, info in enumerate(selected_items_info, 1):
                if info['subdomain2']:
                    st.write(f"**{i}.** {info['domain']} → {info['subdomain1']} → {info['subdomain2']} → {info['item']}")
                else:
                    st.write(f"**{i}.** {info['domain']} → {info['subdomain1']} → {info['item']}")
                st.caption(f"包含 {info['question_count']} 个调研问题")
            
            st.markdown("---")
            
            # 问题详情展示
            st.subheader("📝 调研问题详情")
            for info in selected_items_info:
                if info['question_count'] > 0:
                    with st.expander(f"📄 {info['item']} ({info['question_count']}个问题)"):
                        for j, question in enumerate(info['questions'], 1):
                            st.write(f"{j}. {question}")
            
            st.markdown("---")
            
            # 导航按钮
            col_nav1, col_nav2 = st.columns([1, 1])
            
            with col_nav1:
                if st.button("⬅️ 上一步：基本信息", type="secondary", use_container_width=True):
                    st.session_state.current_page = "company_info"
                    st.rerun()
            
            with col_nav2:
                if st.button("下一步：选择证明材料", type="primary", use_container_width=True):
                    # 保存选中的数据到session state
                    st.session_state.selected_questionnaire_data = {
                        'selected_items_info': selected_items_info,
                        'selected_questions': selected_questions,
                        'total_items': len(selected_items_info),
                        'total_questions': len(selected_questions)
                    }
                    # 跳转到证明材料选择页面
                    st.session_state.current_page = "evidence_selection"
                    st.rerun()
        else:
            st.info("👈 请在左侧选择需要评估的能力项")
            st.markdown("""
            **使用说明：**
            1. 在左侧选择需要的能力项
            2. 可以按能力域全选，或选择具体的子域和能力项
            3. 右侧会实时显示筛选结果
            4. 确认后点击"下一步"进入问卷创建页面
            
            **数据来源：** 从 `data/FLMM调研表.xlsx` 文件自动读取
            **选择对象：** 能力项及其对应的调研问题
            """)

def show_evidence_selection():
    """页面3：证明材料筛选"""
    st.title("证明材料选择")
    st.markdown("### FLMM评估 - 步骤3/4")
    st.markdown("---")
    
    # 获取FLMM自评表数据结构
    flmm_structure = build_flmm_evaluation_structure()
    
    if not flmm_structure:
        st.error("❌ 无法读取FLMM自评表数据，请检查data/FLMM自评表.xlsx文件是否存在")
        st.stop()
    
    # 显示数据概览
    total_capability_items = 0
    for domain, subdomain1s in flmm_structure.items():
        for subdomain1, subdomain2s in subdomain1s.items():
            for subdomain2, items in subdomain2s.items():
                total_capability_items += len(items)
    
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    with col_info1:
        st.metric("能力域数量", len(flmm_structure))
    with col_info2:
        subdomain1_count = sum(len(subdomain1s) for subdomain1s in flmm_structure.values())
        st.metric("能力子域1数量", subdomain1_count)
    with col_info3:
        subdomain2_count = sum(len(subdomain2s) for subdomain1s in flmm_structure.values() for subdomain2s in subdomain1s.values())
        st.metric("能力子域2数量", subdomain2_count)
    with col_info4:
        st.metric("总能力项数", total_capability_items)
        
        st.markdown("---")
        
    # 初始化选择状态
    if 'selected_evidence_items' not in st.session_state:
        st.session_state.selected_evidence_items = {}
    
    # 创建两列布局
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.header(" 能力项选择")
        st.info("请选择需要收集证明材料的能力项。您可以按能力域、子域或具体能力项进行选择。")
        
        # 遍历能力域
        for domain, subdomain1s in flmm_structure.items():
            st.subheader(f"{domain}")
            
            # 能力域级别的全选
            domain_key = f"evidence_domain_{domain}"
            domain_selected = st.checkbox(
                f"✅ 全选「{domain}」所有能力项",
                key=domain_key,
                value=st.session_state.selected_evidence_items.get(domain_key, False)
            )
            update_state_if_changed(st.session_state.selected_evidence_items, domain_key, domain_selected)
            
            # 遍历能力子域1 - 使用expander
            for subdomain1, subdomain2s in subdomain1s.items():
                with st.expander(f"📂 {subdomain1}", expanded=st.session_state.selected_evidence_items.get(domain_key, False)):
                    
                    # 能力子域1级别的选择
                    subdomain1_key = f"evidence_subdomain1_{domain}_{subdomain1}"
                    current_subdomain1_value = st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False)
                    subdomain1_selected = st.checkbox(
                        f"📌 选择「{subdomain1}」所有项",
                        key=subdomain1_key,
                        value=current_subdomain1_value,
                        disabled=st.session_state.selected_evidence_items.get(domain_key, False)
                    )
                    update_state_if_changed(st.session_state.selected_evidence_items, subdomain1_key, subdomain1_selected)
                    
                    # 遍历能力子域2
                    for subdomain2, items in subdomain2s.items():
                        if subdomain2:  # 只有当能力子域2不为空时才显示
                            st.markdown(f"**📋 {subdomain2}**")
                            
                            # 能力子域2级别的选择
                            subdomain2_key = f"evidence_subdomain2_{domain}_{subdomain1}_{subdomain2}"
                            current_subdomain2_value = st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False) or st.session_state.selected_evidence_items.get(subdomain2_key, False)
                            subdomain2_selected = st.checkbox(
                                f"🔖 选择「{subdomain2}」所有项",
                                key=subdomain2_key,
                                value=current_subdomain2_value,
                                disabled=st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False)
                            )
                            update_state_if_changed(st.session_state.selected_evidence_items, subdomain2_key, subdomain2_selected)
                            
                            # 遍历能力项 - 添加缩进
                            for item in items:
                                item_key = f"evidence_item_{domain}_{subdomain1}_{subdomain2}_{item}"
                                
                                # 使用列来创建缩进效果
                                col_indent, col_item = st.columns([0.1, 0.9])
                                with col_item:
                                    current_item_value = st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False) or st.session_state.selected_evidence_items.get(subdomain2_key, False) or st.session_state.selected_evidence_items.get(item_key, False)
                                    item_selected = st.checkbox(
                                        f"📄 {item}",
                                        key=item_key,
                                        value=current_item_value,
                                        disabled=st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False) or st.session_state.selected_evidence_items.get(subdomain2_key, False)
                                    )
                                    update_state_if_changed(st.session_state.selected_evidence_items, item_key, item_selected)
                        else:
                            # 如果能力子域2为空，直接显示能力项
                            for item in items:
                                item_key = f"evidence_item_{domain}_{subdomain1}__{item}"
                                current_item_value = st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False) or st.session_state.selected_evidence_items.get(item_key, False)
                                item_selected = st.checkbox(
                                    f"📄 {item}",
                                    key=item_key,
                                    value=current_item_value,
                                    disabled=st.session_state.selected_evidence_items.get(domain_key, False) or st.session_state.selected_evidence_items.get(subdomain1_key, False)
                                )
                                update_state_if_changed(st.session_state.selected_evidence_items, item_key, item_selected)
    
    with col2:
        st.header("📊 筛选结果")
        
        # 收集选中的证明材料项
        selected_evidence_info = []
        
        for domain, subdomain1s in flmm_structure.items():
            domain_key = f"evidence_domain_{domain}"
            domain_selected = st.session_state.selected_evidence_items.get(domain_key, False)
            
            for subdomain1, subdomain2s in subdomain1s.items():
                subdomain1_key = f"evidence_subdomain1_{domain}_{subdomain1}"
                subdomain1_selected = st.session_state.selected_evidence_items.get(subdomain1_key, False)
                
                for subdomain2, items in subdomain2s.items():
                    subdomain2_key = f"evidence_subdomain2_{domain}_{subdomain1}_{subdomain2}"
                    subdomain2_selected = st.session_state.selected_evidence_items.get(subdomain2_key, False)
                    
                    for item in items:
                        if subdomain2:
                            item_key = f"evidence_item_{domain}_{subdomain1}_{subdomain2}_{item}"
                        else:
                            item_key = f"evidence_item_{domain}_{subdomain1}__{item}"
                            
                        item_selected = st.session_state.selected_evidence_items.get(item_key, False)
                        
                        if domain_selected or subdomain1_selected or subdomain2_selected or item_selected:
                            selected_evidence_info.append({
                                'domain': domain,
                                'subdomain1': subdomain1,
                                'subdomain2': subdomain2,
                                'item': item
                            })
        
        # 显示统计信息
        if selected_evidence_info:
            st.metric("选中能力项", len(selected_evidence_info))
            
            st.markdown("---")
            
            # 显示选中的能力项摘要
            st.subheader("📋 已选择的能力项")
            for i, info in enumerate(selected_evidence_info, 1):
                if info['subdomain2']:
                    st.write(f"**{i}.** {info['domain']} → {info['subdomain1']} → {info['subdomain2']} → {info['item']}")
                else:
                    st.write(f"**{i}.** {info['domain']} → {info['subdomain1']} → {info['item']}")
            
            st.markdown("---")
            
            # 保存选择结果到session state
            st.session_state.selected_evidence_data = {
                'selected_items_info': selected_evidence_info,
                'total_items': len(selected_evidence_info)
            }
        else:
            st.info("👈 请在左侧选择需要收集证明材料的能力项")
    
    # 导航按钮
    st.markdown("---")
    col_nav1, col_nav2 = st.columns([1, 1])
    
    with col_nav1:
        if st.button("⬅️ 上一步：选择问卷", type="secondary", use_container_width=True):
            st.session_state.current_page = "questionnaire_selection"
            st.rerun()
    
    with col_nav2:
        if st.button("🔍 下一步：预览确认", type="primary", use_container_width=True):
            st.session_state.current_page = "final_preview"
            st.rerun()

def show_final_preview():
    """页面4：预览确认"""
    st.title("🔍 预览确认")
    st.markdown("### FLMM评估 - 步骤4/4")
    st.markdown("---")
            
    st.info("请确认以下信息，然后选择评估功能并生成项目。")
    
    # 创建两列布局
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        st.header("📋 项目信息预览")
        
        # 被评估方信息
        st.subheader("🏢 被评估方信息")
        company_name = st.session_state.get('company_name', '')
        scenario_name = st.session_state.get('scenario_name', '')
        scenario_description = st.session_state.get('scenario_description', '')
        functions_list = st.session_state.get('functions_list', [])
        
        if company_name and scenario_name and scenario_description:
            st.write(f"**公司名称：** {company_name}")
            st.write(f"**场景名称：** {scenario_name}")
            st.write(f"**场景描述：** {scenario_description}")
            if functions_list:
                st.write(f"**功能模块：** {len(functions_list)} 个")
                for i, func in enumerate(functions_list, 1):
                    st.write(f"  {i}. {func['name']}")
        else:
            st.warning("⚠️ 基本信息不完整，请返回第一步填写")
        
        st.markdown("---")
        
        # 问卷选择信息
        st.subheader("📋 问卷选择")
        questionnaire_data = st.session_state.get('selected_questionnaire_data', {})
        if questionnaire_data:
            st.write(f"**已选择能力项：** {questionnaire_data.get('total_items', 0)} 项")
            st.write(f"**总问题数：** {questionnaire_data.get('total_questions', 0)} 题")
            
            with st.expander("查看选中的问卷内容", expanded=False):
                items_info = questionnaire_data.get('selected_items_info', [])
                for i, item in enumerate(items_info, 1):
                    if item['subdomain2']:
                        st.write(f"{i}. {item['domain']} → {item['subdomain1']} → {item['subdomain2']} → {item['item']}")
                    else:
                        st.write(f"{i}. {item['domain']} → {item['subdomain1']} → {item['item']}")
                    st.caption(f"   包含 {item['question_count']} 个问题")
        else:
            st.warning("⚠️ 未选择问卷内容，请返回第二步选择")
        
        st.markdown("---")
        
        # 证明材料选择信息
        st.subheader("证明材料选择")
        evidence_data = st.session_state.get('selected_evidence_data', {})
        if evidence_data:
            st.write(f"**已选择能力项：** {evidence_data.get('total_items', 0)} 项")
            
            with st.expander("查看选中的证明材料能力项", expanded=False):
                items_info = evidence_data.get('selected_items_info', [])
                for i, item in enumerate(items_info, 1):
                    if item['subdomain2']:
                        st.write(f"{i}. {item['domain']} → {item['subdomain1']} → {item['subdomain2']} → {item['item']}")
                    else:
                        st.write(f"{i}. {item['domain']} → {item['subdomain1']} → {item['item']}")
        else:
            st.info("ℹ️ 未选择证明材料项，将不生成证明材料收集功能")
    
    with col2:
        st.header("⚙️ 项目设置")
        
        # 评估功能设置
        st.subheader("📊 评估功能设置")
        
        # 根据选择的内容自动判断可用功能
        has_questionnaire = bool(questionnaire_data)
        has_evidence = bool(evidence_data)
        
        enable_questionnaire = st.checkbox(
            "启用问卷数据收集", 
            value=has_questionnaire,
            disabled=not has_questionnaire,
            help="生成问卷采集页面" + ("" if has_questionnaire else "（需要先选择问卷内容）")
        )
        
        enable_evidence = st.checkbox(
            "启用证明材料收集", 
            value=has_evidence,
            disabled=not has_evidence,
            help="生成证明材料上传页面" + ("" if has_evidence else "（需要先选择证明材料项）")
        )
        
        st.markdown("---")
        
        # 账号生成设置
        st.subheader("🔐 账号生成设置")
        
        auto_generate_account = st.checkbox("自动生成登录账号", value=True)
        
        if not auto_generate_account:
            custom_username = st.text_input("自定义用户名", placeholder="请输入用户名")
            custom_password = st.text_input("自定义密码", type="password", placeholder="请输入密码")
        else:
            import uuid
            auto_username = f"user_{company_name[:4] if company_name else 'temp'}_{str(uuid.uuid4())[:8]}"
            auto_password = str(uuid.uuid4())[:12]
            st.text_input("生成的用户名", value=auto_username, disabled=True)
            st.text_input("生成的密码", value=auto_password, disabled=True, type="password")
        
        st.markdown("---")
        
        # 项目概览
        st.subheader("📊 项目概览")
        
        # 检查是否可以生成
        can_generate = all([
            company_name, scenario_name, scenario_description,
            enable_questionnaire or enable_evidence
        ])
        
        if can_generate:
            st.success("✅ 项目信息完整，可以生成")
            
            # 显示将生成的文件
            st.write("**将生成的文件：**")
            st.write(f"项目文件夹：`{company_name}_{scenario_name}/`")
            st.write(f"📄 项目信息：`{company_name}_{scenario_name}.json`")
            
            if enable_questionnaire:
                st.write(f"📊 问卷文件：`{company_name}_{scenario_name}_问卷.xlsx`")
                st.write(f"💻 问卷采集页面：`{company_name}_{scenario_name}.py`")
            
            if enable_evidence:
                st.write(f"证明材料页面：`{company_name}_{scenario_name}_证明材料.py`")
                st.write(f"📂 证明材料文件夹：`证明材料/`")
        else:
            st.warning("⚠️ 信息不完整或未选择评估功能")
    
    # 导航和生成按钮
        st.markdown("---")
    col_nav1, col_nav2 = st.columns([1, 1])
    
    with col_nav1:
        if st.button("⬅️ 上一步：选择证明材料", type="secondary", use_container_width=True):
            st.session_state.current_page = "evidence_selection"
            st.rerun()
        
    with col_nav2:
        if st.button("🚀 确认生成项目", type="primary", use_container_width=True, disabled=not can_generate):
            if can_generate:
                # 生成项目
                generate_project(
                    company_name=company_name,
                    scenario_name=scenario_name,
                    scenario_description=scenario_description,
                    functions_list=functions_list,
                    questionnaire_data=questionnaire_data if enable_questionnaire else None,
                    evidence_data=evidence_data if enable_evidence else None,
                    enable_questionnaire=enable_questionnaire,
                    enable_evidence=enable_evidence,
                    auto_generate_account=auto_generate_account,
                    username=auto_username if auto_generate_account else custom_username,
                    password=auto_password if auto_generate_account else custom_password
                )
            else:
                st.warning("⚠️ 请确保信息完整且至少选择一种评估功能")

def generate_project(company_name, scenario_name, scenario_description, functions_list, 
                    questionnaire_data, evidence_data, enable_questionnaire, enable_evidence,
                    auto_generate_account, username, password):
    """生成评估项目"""
    try:
        # 生成文件夹名称
        folder_name = f"{company_name}_{scenario_name}"
        folder_path = f"data/{folder_name}"
        
# 创建文件夹
        os.makedirs(folder_path, exist_ok=True)
            
            # 1. 整合的评估信息和账号信息json文件
        integrated_info = {
            "evaluation_info": {
                "company_name": company_name,
                "scenario_name": scenario_name,
                "scenario_description": scenario_description,
"functions_list": functions_list,
                "created_time": datetime.now().isoformat(),
                "status": "待评估",
"questionnaire_enabled": enable_questionnaire,
"evidence_enabled": enable_evidence,
"questionnaire_info": questionnaire_data.get('total_items', 0) if questionnaire_data else 0,
"evidence_info": evidence_data.get('total_items', 0) if evidence_data else 0
            },
            "account_info": {
                "username": username,
                "password": password,
                "company_name": company_name,
                "scenario_name": scenario_name,
                "created_time": datetime.now().isoformat(),
                "login_url": "待部署",
                "status": "激活"
            }
        }
        
        json_filename = f"{company_name}_{scenario_name}.json"
        with open(f"{folder_path}/{json_filename}", "w", encoding="utf-8") as f:
            json.dump(integrated_info, f, ensure_ascii=False, indent=2)
                    
        # 2. 生成Excel格式的问卷文件（如果启用问卷收集）
        if enable_questionnaire and questionnaire_data:
            excel_filename = f"{company_name}_{scenario_name}_问卷.xlsx"
            excel_data = []
            
            for item_info in questionnaire_data['selected_items_info']:
                for question in item_info['questions']:
                    # 解析问题内容和选项
                    question_stem, options = parse_question_content(question, scenario_name)
                    
                    if question_stem:
                        # 检查是否包含{function1}占位符
                        if "{function1}" in question_stem:
                            # 为每个功能生成对应的问题
                            if functions_list:
                                for func in functions_list:
                                    # 替换{function1}为具体功能名称
                                    function_question = question_stem.replace("{function1}", func['name'])
                                    options_str = '|'.join(options) if options else '完全不符合|基本不符合|部分符合|基本符合|完全符合'
                                    
                                    excel_data.append({
                                        '能力域': item_info['domain'],
                                        '能力子域1': item_info['subdomain1'],
                                        '能力子域2': item_info['subdomain2'] if item_info['subdomain2'] else '',
                                        '能力项': item_info['item'],
                                        '问题主干': function_question,
                                        '答案选项': options_str,
                                        '被评估方回答': '',
                                        '备注': f"针对功能：{func['name']}"
                                    })
                            else:
                                # 如果没有添加功能，使用原问题（保留占位符）
                                options_str = '|'.join(options) if options else '完全不符合|基本不符合|部分符合|基本符合|完全符合'
                                excel_data.append({
                                    '能力域': item_info['domain'],
                                    '能力子域1': item_info['subdomain1'],
                                    '能力子域2': item_info['subdomain2'] if item_info['subdomain2'] else '',
                                    '能力项': item_info['item'],
                                    '问题主干': question_stem,
                                    '答案选项': options_str,
                                    '被评估方回答': '',
                                    '备注': '需要指定具体功能'
                                })
                        else:
                            # 普通问题，直接添加
                            options_str = '|'.join(options) if options else '完全不符合|基本不符合|部分符合|基本符合|完全符合'
                            excel_data.append({
                                '能力域': item_info['domain'],
                                '能力子域1': item_info['subdomain1'],
                                '能力子域2': item_info['subdomain2'] if item_info['subdomain2'] else '',
                                '能力项': item_info['item'],
                                '问题主干': question_stem,
                                '答案选项': options_str,
                                '被评估方回答': '',
                                '备注': ''
                            })
            
                excel_df = pd.DataFrame(excel_data)
                excel_df.to_excel(f"{folder_path}/{excel_filename}", index=False, engine='openpyxl')
                            
                # 3. 生成问卷采集页面
                py_filename = f"{company_name}_{scenario_name}.py"
                questionnaire_page_code = generate_questionnaire_page_code(
                    company_name, scenario_name, excel_filename, json_filename
                )
            
                with open(f"{folder_path}/{py_filename}", "w", encoding="utf-8") as f:
                    f.write(questionnaire_page_code)
        
        # 4. 证明材料收集页面（如果启用证明材料收集）
        if enable_evidence and evidence_data:
            evidence_py_filename = f"{company_name}_{scenario_name}_证明材料.py"
            
            # 创建证明材料文件夹
            evidence_folder = f"{folder_path}/证明材料"
            os.makedirs(evidence_folder, exist_ok=True)
            
            # 为每个选中的能力项创建文件夹
            for item_info in evidence_data['selected_items_info']:
                item_folder = f"{evidence_folder}/{item_info['item']}"
                os.makedirs(item_folder, exist_ok=True)
            
            # 生成证明材料收集页面代码
            evidence_page_code = generate_evidence_page_code(
                company_name, scenario_name, json_filename, evidence_data
            )
            
            with open(f"{folder_path}/{evidence_py_filename}", "w", encoding="utf-8") as f:
                f.write(evidence_page_code)
        
        st.success("🎉 评估项目创建成功！")

        # 自动启动Streamlit应用并生成访问链接
        questionnaire_url = None
        evidence_url = None

        # 加载端口配置
        port_config = load_port_config()

        if enable_questionnaire:
            # 查找可用端口
            port = find_available_port()
            if port:
                # 启动问卷采集页面
                pid = start_streamlit_app(folder_path, py_filename, port)
                if pid:
                    questionnaire_url = f"http://localhost:{port}"
                    # 保存端口配置
                    port_config[f"{company_name}_{scenario_name}_questionnaire"] = {
                        "port": port,
                        "pid": pid,
                        "file": py_filename,
                        "type": "questionnaire"
                    }
                    # 更新JSON文件中的URL
                    integrated_info["account_info"]["login_url"] = questionnaire_url
                    with open(f"{folder_path}/{json_filename}", "w", encoding="utf-8") as f:
                        json.dump(integrated_info, f, ensure_ascii=False, indent=2)

        if enable_evidence:
            # 查找可用端口
            port = find_available_port()
            if port:
                # 启动证明材料收集页面
                pid = start_streamlit_app(folder_path, evidence_py_filename, port)
                if pid:
                    evidence_url = f"http://localhost:{port}"
                    # 保存端口配置
                    port_config[f"{company_name}_{scenario_name}_evidence"] = {
                        "port": port,
                        "pid": pid,
                        "file": evidence_py_filename,
                        "type": "evidence"
                    }

        # 保存端口配置
        save_port_config(port_config)

        # 生成文件列表
        generated_files = [
            f"项目文件夹：`data/{folder_name}/`",
            f"📄 项目信息：`{json_filename}`"
        ]

        if enable_questionnaire:
            generated_files.extend([
                f"📊 问卷文件：`{excel_filename}`",
                f"💻 问卷采集页面：`{py_filename}`"
            ])

        if enable_evidence:
            generated_files.append(f"证明材料收集页面：`{evidence_py_filename}`")
            generated_files.append(f"📂 证明材料文件夹：`证明材料/`")

        file_list = "\n                        - ".join(generated_files)

        # 显示登录信息和访问链接
        info_message = f"""
        **已生成以下文件：**
        - {file_list}

        **被评估方登录信息：**
        - 用户名：`{username}`
        - 密码：`{password}`
        """

        if questionnaire_url:
            info_message += f"""

        **📋 问卷填写链接（已自动启动）：**
        - 🔗 访问地址：`{questionnaire_url}`
        - ⏰ 服务已在后台运行，请等待5-10秒后访问
        - 💡 提示：使用上述账号密码登录即可填写问卷
        """

        if evidence_url:
            info_message += f"""

        **📁 证明材料上传链接（已自动启动）：**
        - 🔗 访问地址：`{evidence_url}`
        - ⏰ 服务已在后台运行，请等待5-10秒后访问
        - 💡 提示：使用上述账号密码登录即可上传材料
        """

        st.info(info_message)
        
        # 清理session state
        st.success("✅ 项目创建完成！可以开始新的项目创建。")
        if st.button("🔄 创建新项目", type="secondary"):
            # 清理所有相关的session state
            keys_to_clear = [
                'company_name', 'scenario_name', 'scenario_description', 'functions_list',
                'selected_items', 'selected_questionnaire_data', 
                'selected_evidence_items', 'selected_evidence_data'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_page = "company_info"
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ 项目生成失败：{e}")

def generate_questionnaire_page_code(company_name, scenario_name, excel_filename, json_filename):
    """生成问卷采集页面代码"""
    return f'''import streamlit as st
import json
import pandas as pd
from datetime import datetime
import hashlib
import uuid
import os
import threading
import time

# 被评估方问卷采集页面
st.set_page_config(
    page_title="{company_name} - FLMM评估问卷",
    page_icon="📋",
    layout="wide"
)

# 线程锁，用于处理并发写入
file_lock = threading.Lock()

def generate_questionnaire_id():
    """生成问卷ID：时间戳+哈希"""
    timestamp = str(int(time.time() * 1000))  # 毫秒级时间戳
    random_str = str(uuid.uuid4())
    combined = f"{{timestamp}}_{{random_str}}"
    hash_obj = hashlib.md5(combined.encode())
    return f"{{timestamp}}_{{hash_obj.hexdigest()[:8]}}"

def load_questionnaire():
    """加载问卷数据"""
    try:
        # 加载Excel问卷文件
        df = pd.read_excel("{excel_filename}")
        return df
    except Exception as e:
        st.error(f"加载问卷失败: {{e}}")
        return None

def load_project_info():
    """加载项目信息"""
    try:
        with open("{json_filename}", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载项目信息失败: {{e}}")
        return None

def verify_login(username, password):
    """验证登录信息"""
    try:
        project_info = load_project_info()
        if project_info and 'account_info' in project_info:
            account_info = project_info['account_info']
            return (account_info.get('username') == username and 
                   account_info.get('password') == password and
                   account_info.get('status') == '激活')
        return False
    except Exception as e:
        st.error(f"验证登录失败: {{e}}")
        return False

def show_login_page():
    """显示登录页面"""
    st.title("🔐 FLMM评估问卷")
    st.markdown("### {company_name} - {scenario_name}")
    st.markdown("---")
    
    # 登录表单
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("请输入登录信息")
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            submitted = st.form_submit_button("🚀 登录", use_container_width=True, type="primary")
            
            if submitted:
                if username and password:
                    if verify_login(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("✅ 登录成功！正在跳转...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误，请重新输入。")
                else:
                    st.warning("⚠️ 请输入完整的用户名和密码。")

def convert_answer_to_letter(answer, options, is_multiple_choice):
    """将答案选项转换为字母格式"""
    if is_multiple_choice:
        if not answer:
            return ""
        letters = []
        for selected_option in answer:
            try:
                index = options.index(selected_option)
                letters.append(chr(65 + index))  # A=65, B=66, C=67...
            except ValueError:
                continue
        return ";".join(letters)
    else:
        if not answer:
            return ""
        try:
            index = options.index(answer)
            return chr(65 + index)  # A=65, B=66, C=67...
        except ValueError:
            return ""

def save_results_safely(result_data, result_filename):
    """安全保存结果，处理并发问题"""
    with file_lock:
        try:
            # 检查文件是否存在
            if os.path.exists(result_filename):
                # 文件存在，读取现有数据
                existing_df = pd.read_excel(result_filename)
                # 将新数据追加到现有数据
                new_df = pd.DataFrame(result_data)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                # 文件不存在，创建新文件
                combined_df = pd.DataFrame(result_data)
            
            # 保存到Excel文件
            combined_df.to_excel(result_filename, index=False, engine='openpyxl')
            return True
        except Exception as e:
            st.error(f"保存结果失败: {{e}}")
            return False

def show_questionnaire_page():
    """显示问卷页面"""
    st.title("📋 {company_name} - FLMM评估问卷")
    st.markdown("### 业务场景：{scenario_name}")
    
    st.markdown("---")
    
    # 生成或获取问卷ID
    if 'questionnaire_id' not in st.session_state:
        st.session_state.questionnaire_id = generate_questionnaire_id()
    
    # 加载项目信息和问卷数据
    project_info = load_project_info()
    questionnaire_df = load_questionnaire()
    
    if not project_info or questionnaire_df is None:
        st.stop()
    
    # 检查是否已提交
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    if st.session_state.submitted:
        st.success("✅ 您已成功提交问卷！")
        st.info("如需重新填写，请联系管理员。")
        if st.button("🔄 重新填写", type="secondary"):
            # 重置答案状态，但保持登录状态
            if 'answers' in st.session_state:
                del st.session_state.answers
            if 'submitted' in st.session_state:
                del st.session_state.submitted
            if 'questionnaire_id' in st.session_state:
                del st.session_state.questionnaire_id
            st.rerun()
        st.stop()

    
    # 初始化答案存储
    if 'answers' not in st.session_state:
        st.session_state.answers = {{}}
    
    # 按能力项分组显示问题
    current_item = ""
    item_counter = 0
    question_counter = 0
    
    for index, row in questionnaire_df.iterrows():
        # 如果是新的能力项，显示标题
        if row['能力项'] != current_item:
            current_item = row['能力项']
            item_counter += 1
            st.subheader(f"{{item_counter}}. {{current_item}}")
        
        # 显示问题（不显示编号）
        question_counter += 1
        question_key = f"question_{{index}}"
        question_text = row['问题主干']
        
        # 检查是否为多选题
        is_multiple_choice = "（可多选）" in question_text or "(可多选)" in question_text
        
        # 在每个问题前添加适当间距（除了第一个问题）
        if question_counter > 1:
            st.markdown("<br>", unsafe_allow_html=True)
        
        # 使用container来控制布局
        with st.container():
            st.markdown(f"**{{question_counter}}. {{question_text}}**")
            
            # 解析答案选项
            if pd.notna(row['答案选项']) and row['答案选项']:
                options = row['答案选项'].split('|')
            else:
                options = ["完全不符合", "基本不符合", "部分符合", "基本符合", "完全符合"]
            
            # 答题选项（竖直排列，紧凑布局）
            if is_multiple_choice:
                # 多选题使用复选框
                selected_options = []
                for option in options:
                    if st.checkbox(option, key=f"{{question_key}}_{{option}}"):
                        selected_options.append(option)
                answer = selected_options
            else:
                # 单选题使用单选按钮（竖直排列）
                answer = st.radio(
                    "",  # 不显示标签
                    options,
                    key=question_key,
                    index=None,  # 默认不选中任何项
                    horizontal=False,  # 竖直排列
                    label_visibility="collapsed"  # 隐藏标签
                )
            
            st.session_state.answers[question_key] = {{
                'question': question_text,
                'answer': answer,
                'options': options,
                'capability_item': row['能力项'],
                'domain': row['能力域'],
                'question_number': question_counter,
                'is_multiple_choice': is_multiple_choice
            }}
        
        # 问题间分隔，但不要太大
        st.markdown("")
    
    # 提交按钮
    if st.button("📤 提交问卷", type="primary", use_container_width=True):
        # 检查是否所有问题都已回答
        unanswered_questions = []
        for key, value in st.session_state.answers.items():
            if value['is_multiple_choice']:
                if not value['answer']:  # 多选题没有选择任何选项
                    unanswered_questions.append(value['question_number'])
            else:
                if not value['answer']:  # 单选题没有选择
                    unanswered_questions.append(value['question_number'])
        
        if unanswered_questions:
            st.warning(f"请完成所有问题的回答，未回答的问题：第{{', '.join(map(str, unanswered_questions))}}题")
        else:
            # 保存答案到Excel文件
            result_data = []
            for key, value in st.session_state.answers.items():
                # 将答案转换为字母格式
                answer_letter = convert_answer_to_letter(
                    value['answer'], 
                    value['options'], 
                    value['is_multiple_choice']
                )
                
                result_data.append({{
                    '问卷ID': st.session_state.questionnaire_id,
                    '用户名': st.session_state.username,
                    '题号': value['question_number'],
                    '能力域': value['domain'],
                    '能力项': value['capability_item'],
                    '问题': value['question'],
                    '回答': answer_letter,
                    '问题类型': '多选题' if value['is_multiple_choice'] else '单选题',
                    '提交时间': datetime.now().isoformat()
                }})
            
            result_filename = f"{company_name}_{scenario_name}_评估结果.xlsx"
            if save_results_safely(result_data, result_filename):
                # 设置提交状态
                st.session_state.submitted = True
                
                # 同时保存JSON格式的结果
                results_json = {{
                    "questionnaire_id": st.session_state.questionnaire_id,
                    "username": st.session_state.username,
                    "company_name": "{company_name}",
                    "scenario_name": "{scenario_name}",
                    "submitted_time": datetime.now().isoformat(),
                    "answers": st.session_state.answers,
                    "summary": {{
                        "total_questions": len(st.session_state.answers),
                        "completion_rate": "100%"
                    }}
                }}
                
                # 生成JSON文件名包含问卷ID
                json_filename = f"{company_name}_{scenario_name}_评估结果_{{st.session_state.questionnaire_id}}.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(results_json, f, ensure_ascii=False, indent=2)
                
                st.success(f"✅ 问卷提交成功！您的问卷ID：`{{st.session_state.questionnaire_id}}`")
                st.info(f"评估结果已保存为：{{result_filename}}")
                st.rerun()  # 刷新页面显示提交成功状态
            else:
                st.error("❌ 结果保存失败，请稍后再试。")

def main():
    # 初始化登录状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # 根据登录状态显示不同页面
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_questionnaire_page()

if __name__ == "__main__":
    main()
'''
                        
def generate_evidence_page_code(company_name, scenario_name, json_filename, evidence_data):
    """生成证明材料收集页面代码"""
    # 构建层级结构数据
    capability_structure = {}
    for item_info in evidence_data['selected_items_info']:
        domain = item_info['domain']
        subdomain1 = item_info['subdomain1']
        subdomain2 = item_info['subdomain2'] if item_info['subdomain2'] else ''
        item = item_info['item']
        
        if domain not in capability_structure:
            capability_structure[domain] = {}
        if subdomain1 not in capability_structure[domain]:
            capability_structure[domain][subdomain1] = {}
        if subdomain2 not in capability_structure[domain][subdomain1]:
            capability_structure[domain][subdomain1][subdomain2] = []
        capability_structure[domain][subdomain1][subdomain2].append(item)
    
    return f'''import streamlit as st
import json
import pandas as pd
from datetime import datetime
import hashlib
import uuid
import os
import threading
import time
import zipfile
import shutil

# 证明材料收集页面
st.set_page_config(
    page_title="{company_name} - FLMM证明材料收集",
    page_icon="📁",
    layout="wide"
)

# 线程锁，用于处理并发写入
file_lock = threading.Lock()

def load_project_info():
    """加载项目信息"""
    try:
        with open("{json_filename}", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载项目信息失败: {{e}}")
        return None

def verify_login(username, password):
    """验证登录信息"""
    try:
        project_info = load_project_info()
        if project_info and 'account_info' in project_info:
            account_info = project_info['account_info']
            return (account_info.get('username') == username and 
                   account_info.get('password') == password and
                   account_info.get('status') == '激活')
        return False
    except Exception as e:
        st.error(f"验证登录失败: {{e}}")
        return False

def show_login_page():
    """显示登录页面"""
    st.title("FLMM证明材料收集")
    st.markdown("### {company_name} - {scenario_name}")
    st.markdown("---")
    
    # 登录表单
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("请输入登录信息")
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            submitted = st.form_submit_button("🚀 登录", use_container_width=True, type="primary")
            
            if submitted:
                if username and password:
                    if verify_login(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("✅ 登录成功！正在跳转...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误，请重新输入。")
                else:
                    st.warning("⚠️ 请输入完整的用户名和密码。")

def load_capability_structure():
    """加载能力项层级结构"""
    return {capability_structure}

def save_upload_record(username, capability_item, file_names, upload_type):
    """保存上传记录"""
    try:
        record = {{
            "username": username,
            "company_name": "{company_name}",
            "scenario_name": "{scenario_name}",
            "capability_item": capability_item,
            "file_names": file_names,
            "upload_type": upload_type,
            "upload_time": datetime.now().isoformat(),
            "upload_id": str(uuid.uuid4())[:8]
        }}
        
        record_filename = f"{company_name}_{scenario_name}_证明材料上传记录.json"
        
        # 检查文件是否存在
        if os.path.exists(record_filename):
            with open(record_filename, "r", encoding="utf-8") as f:
                records = json.load(f)
                if not isinstance(records, list):
                    records = [records]
        else:
            records = []
        
        records.append(record)
        
        with open(record_filename, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"保存上传记录失败: {{e}}")
        return False

def show_evidence_collection_page():
    """显示证明材料收集页面"""
    st.title("{company_name} - FLMM证明材料收集")
    st.markdown("### 业务场景：{scenario_name}")
    st.markdown("---")
    
    st.info("📋 请根据FLMM自评表的能力项结构，选择对应的能力项并上传相关证明材料。")
    
    # 加载能力项层级结构
    capability_structure = load_capability_structure()
    
    # 初始化选择状态
    if 'selected_capability_item' not in st.session_state:
        st.session_state.selected_capability_item = None
    
    # 创建两列布局
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        st.header(" 能力项选择")
        
        # 展示能力项结构树
        for domain, subdomain1s in capability_structure.items():
            st.subheader(f"{{domain}}")
            
            for subdomain1, subdomain2s in subdomain1s.items():
                with st.expander(f"📂 {{subdomain1}}", expanded=False):
                    
                    for subdomain2, items in subdomain2s.items():
                        if subdomain2:
                            st.markdown(f"**📋 {{subdomain2}}**")
                            
                            for item in items:
                                col_indent, col_item = st.columns([0.1, 0.9])
                                with col_item:
                                    if st.button(f"📄 {{item}}", key=f"select_{{item.replace(' ', '_').replace('/', '_').replace('（', '_').replace('）', '_')}}", use_container_width=True):
                                        st.session_state.selected_capability_item = item
                                        st.rerun()
                        else:
                            for item in items:
                                if st.button(f"📄 {{item}}", key=f"select_{{item.replace(' ', '_').replace('/', '_').replace('（', '_').replace('）', '_')}}", use_container_width=True):
                                    st.session_state.selected_capability_item = item
                                    st.rerun()
    
    
    with col2:
        st.header("📤 文件上传")
        
        if st.session_state.selected_capability_item:
            selected_item = st.session_state.selected_capability_item
            st.success(f"已选择能力项：**{{selected_item}}**")
            
            # 显示当前能力项的文件夹
            item_folder = f"证明材料/{{selected_item}}"
            
            st.markdown("---")
            
            # 文件上传选项
            upload_type = st.radio(
                "选择上传方式：",
                ["单个文件上传", "多个文件上传", "文件夹上传（ZIP）"],
                horizontal=True
            )
            
            uploaded_files = []
            
            if upload_type == "单个文件上传":
                uploaded_file = st.file_uploader(
                    "选择文件",
                    type=["pdf", "doc", "docx", "ppt", "pptx", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "mp4", "avi", "mov"],
                    help="支持：PDF、Word、PPT、Excel、图片、视频等格式"
                )
                if uploaded_file:
                    uploaded_files = [uploaded_file]
                    
            elif upload_type == "多个文件上传":
                uploaded_files = st.file_uploader(
                    "选择多个文件",
                    type=["pdf", "doc", "docx", "ppt", "pptx", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "mp4", "avi", "mov"],
                    accept_multiple_files=True,
                    help="支持：PDF、Word、PPT、Excel、图片、视频等格式"
                )
                
            elif upload_type == "文件夹上传（ZIP）":
                uploaded_zip = st.file_uploader(
                    "上传ZIP压缩包（包含文件夹）",
                    type=["zip"],
                    help="请将文件夹压缩成ZIP格式后上传"
                )
                if uploaded_zip:
                    uploaded_files = [uploaded_zip]
            
            # 上传按钮
            if uploaded_files and st.button("🚀 确认上传", type="primary", use_container_width=True):
                try:
                    success_files = []
                    
                    for uploaded_file in uploaded_files:
                        # 保存文件到对应能力项文件夹
                        file_path = os.path.join(item_folder, uploaded_file.name)
                        
                        # 确保文件夹存在
                        os.makedirs(item_folder, exist_ok=True)
                        
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        success_files.append(uploaded_file.name)
                        
                        # 如果是ZIP文件，解压到对应文件夹
                        if uploaded_file.name.endswith('.zip') and upload_type == "文件夹上传（ZIP）":
                            try:
                                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                                    zip_ref.extractall(item_folder)
                                # 删除ZIP文件，保留解压的内容
                                os.remove(file_path)
                            except Exception as e:
                                st.warning(f"ZIP文件解压失败：{{e}}")
                    
                    # 保存上传记录
                    if save_upload_record(st.session_state.username, selected_item, success_files, upload_type):
                        st.success(f"✅ 成功上传 {{len(success_files)}} 个文件到「{{selected_item}}」！")
                    else:
                        st.warning("⚠️ 文件上传成功，但记录保存失败。")
                        
                except Exception as e:
                    st.error(f"❌ 文件上传失败：{{e}}")
            
            # 显示当前能力项已上传的文件
            st.markdown("---")
            st.subheader("📂 已上传文件")
            
            if os.path.exists(item_folder):
                files_in_folder = []
                for root, dirs, files in os.walk(item_folder):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), item_folder)
                        files_in_folder.append(rel_path)
                
                if files_in_folder:
                    for file in files_in_folder:
                        st.write(f"📄 {{file}}")
                else:
                    st.info("暂无上传文件")
            else:
                st.info("暂无上传文件")
        else:
            st.info("👈 请先在左侧选择要上传证明材料的能力项")

def main():
    # 初始化登录状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # 根据登录状态显示不同页面
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_evidence_collection_page()

if __name__ == "__main__":
    main()
'''

def Admin_create_function_page():
    # 初始化页面状态
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "company_info"
    
    # 根据当前页面显示对应内容
    if st.session_state.current_page == "company_info":
        show_company_info()
    elif st.session_state.current_page == "questionnaire_selection":
        show_questionnaire_selection()
    elif st.session_state.current_page == "evidence_selection":
        show_evidence_selection()
    elif st.session_state.current_page == "final_preview":
        show_final_preview()

if __name__ == "__main__":
    Admin_create_function_page()
