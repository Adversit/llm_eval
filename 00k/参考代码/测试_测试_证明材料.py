import streamlit as st
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
    page_title="测试 - FLMM证明材料收集",
    page_icon="📁",
    layout="wide"
)

# 线程锁，用于处理并发写入
file_lock = threading.Lock()

def load_project_info():
    """加载项目信息"""
    try:
        with open("测试_测试.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载项目信息失败: {e}")
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
        st.error(f"验证登录失败: {e}")
        return False

def show_login_page():
    """显示登录页面"""
    st.title("FLMM证明材料收集")
    st.markdown("### 测试 - 测试")
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

def load_flmm_structure():
    """加载FLMM自评表结构"""
    flmm_structure = {'业务价值提升能力V': {'业务维度': {'业务契合度V1': ['用户需求匹配度', '业务目标一致性'], '业务效能提升率V2': ['业务自动化提升率', '业务平均响应速度提升', '业务处理能力增强'], '决策链路支持力V3': ['多维度分析能力', '决策链路覆盖率', '管理决策支持力', '业务决策支持力'], '业务收益提升V4': ['成本收益比', '业务量提升率', '业务收入提升率'], '业务创新能力V5': ['业务模式创新能力', '产品服务创新能力']}, '客户维度': {'用户满意度V6': ['客户忠诚度', '月活跃用户增长率', '点赞率及点踩率', '用户活跃度', '用户交互时间', '复制内容率']}, '机构管理维度': {'成本节约率V7': ['资本支出节约率', '人力成本节约率', '时间成本节约率']}}, '服务可靠性R': {'平均无故障时间R1': {'成本节约率V7': ['平均无故障时间']}, '易用性R2': {'成本节约率V7': ['用户培训机制', '交互流程设计', '多语言支持能力', '错误处理机制', '用户界面友好度']}, '稳定性R3': {'成本节约率V7': ['鲁棒性', '性能波动控制', '负载承受能力']}, '计量准确性R4': {'成本节约率V7': ['误差控制能力', '数据精确度']}, '工具调用能力R5': {'成本节约率V7': ['工具调用数量', '工具集成能力']}, '可维护性R6': {'成本节约率V7': ['可维护性']}, '可拓展性R7': {'成本节约率V7': ['功能扩展性', '系统扩展性']}, '兼容性R8': {'成本节约率V7': ['兼容性']}, '算力资源能力R9': {'成本节约率V7': ['算力资源能力']}}, '应用安全性S': {'隐私保护能力S1': {'成本节约率V7': ['数据安全性', '用户隐私保护']}, '防攻击能力S2': {'成本节约率V7': ['防指令劫持能力', '防越狱攻击能力']}, '可审查性S3': {'成本节约率V7': ['决策过程透明度', '数据处理可追溯性', '输出结果可验证性']}, '合规性S4': {'成本节约率V7': ['防色情暴力内容能力', '防网络犯罪内容能力', '防反伦理道德内容能力', '防其他违反犯罪内容能力', '防政治敏感内容能力']}, '风险管理能力S5': {'成本节约率V7': ['风险应对与处置', '风险监控与预警', '风险识别与评估']}, '幻觉避免能力S6': {'成本节约率V7': ['数据结果可解释性', '逻辑一致性', '数据真实可验证']}}}
    return flmm_structure

def save_upload_record(username, capability_item, file_names, upload_type):
    """保存上传记录"""
    try:
        record = {
            "username": username,
            "company_name": "测试",
            "scenario_name": "测试",
            "capability_item": capability_item,
            "file_names": file_names,
            "upload_type": upload_type,
            "upload_time": datetime.now().isoformat(),
            "upload_id": str(uuid.uuid4())[:8]
        }
        
        record_filename = f"测试_测试_证明材料上传记录.json"
        
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
        st.error(f"保存上传记录失败: {e}")
        return False

def show_evidence_collection_page():
    """显示证明材料收集页面"""
    st.title("测试 - FLMM证明材料收集")
    st.markdown("### 业务场景：测试")
    st.markdown("---")
    
    st.info("📋 请根据FLMM自评表的能力项结构，选择对应的能力项并上传相关证明材料。")
    
    # 加载FLMM结构
    flmm_structure = load_flmm_structure()
    
    # 初始化选择状态
    if 'selected_capability_item' not in st.session_state:
        st.session_state.selected_capability_item = None
    
    # 创建两列布局
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        st.header(" 能力项选择")
        
        # 展示FLMM结构树
        for domain, subdomain1s in flmm_structure.items():
            st.subheader(f"{domain}")
            
            for subdomain1, subdomain2s in subdomain1s.items():
                with st.expander(f"📂 {subdomain1}", expanded=False):
                    
                    for subdomain2, items in subdomain2s.items():
                        if subdomain2:
                            st.markdown(f"**📋 {subdomain2}**")
                            
                            for item in items:
                                col_indent, col_item = st.columns([0.1, 0.9])
                                with col_item:
                                    if st.button(f"📄 {item}", key=f"select_{item}", use_container_width=True):
                                        st.session_state.selected_capability_item = item
                                        st.rerun()
                        else:
                            for item in items:
                                if st.button(f"📄 {item}", key=f"select_{item}", use_container_width=True):
                                    st.session_state.selected_capability_item = item
                                    st.rerun()
    
    with col2:
        st.header("📤 文件上传")
        
        if st.session_state.selected_capability_item:
            selected_item = st.session_state.selected_capability_item
            st.success(f"已选择能力项：**{selected_item}**")
            
            # 显示当前能力项的文件夹
            item_folder = f"证明材料/{selected_item}"
            
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
                                st.warning(f"ZIP文件解压失败：{e}")
                    
                    # 保存上传记录
                    if save_upload_record(st.session_state.username, selected_item, success_files, upload_type):
                        st.success(f"✅ 成功上传 {len(success_files)} 个文件到「{selected_item}」！")
                    else:
                        st.warning("⚠️ 文件上传成功，但记录保存失败。")
                        
                except Exception as e:
                    st.error(f"❌ 文件上传失败：{e}")
            
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
                        st.write(f"📄 {file}")
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
