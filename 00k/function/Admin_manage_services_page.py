import streamlit as st
import json
import os
import psutil
import subprocess

PORT_CONFIG_FILE = "data/.port_config.json"

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

def check_process_running(pid):
    """检查进程是否在运行"""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def kill_process(pid):
    """终止进程"""
    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=5)
        return True
    except Exception as e:
        try:
            # 如果terminate失败，尝试kill
            process.kill()
            return True
        except:
            return False

def Admin_manage_services_page():
    """服务管理页面"""
    st.title("🔧 Streamlit服务管理")
    st.markdown("### 管理已启动的问卷和证明材料收集服务")
    st.markdown("---")

    # 加载配置
    port_config = load_port_config()

    if not port_config:
        st.info("📋 当前没有运行中的服务")
        st.markdown("""
        **说明：**
        - 当您创建新的评估项目时，系统会自动启动对应的Streamlit服务
        - 服务信息会显示在此页面
        - 您可以在这里查看服务状态、访问链接，以及停止服务
        """)
        return

    st.subheader("📊 服务列表")

    # 统计信息
    col1, col2, col3 = st.columns(3)
    total_services = len(port_config)
    running_services = sum(1 for _, info in port_config.items() if check_process_running(info.get('pid', 0)))
    stopped_services = total_services - running_services

    with col1:
        st.metric("总服务数", total_services)
    with col2:
        st.metric("运行中", running_services, delta=None, delta_color="normal")
    with col3:
        st.metric("已停止", stopped_services, delta=None, delta_color="inverse")

    st.markdown("---")

    # 服务列表
    updated_config = {}
    services_to_remove = []

    for service_key, service_info in port_config.items():
        pid = service_info.get('pid', 0)
        port = service_info.get('port', 0)
        service_type = service_info.get('type', 'unknown')
        file_name = service_info.get('file', 'unknown')

        # 检查进程状态
        is_running = check_process_running(pid)

        # 解析服务名称
        service_name = service_key.replace('_questionnaire', '').replace('_evidence', '')

        with st.container():
            col_info, col_status, col_action = st.columns([3, 1, 1])

            with col_info:
                type_emoji = "📋" if service_type == "questionnaire" else "📁"
                type_text = "问卷填写" if service_type == "questionnaire" else "材料上传"
                st.markdown(f"### {type_emoji} {service_name}")
                st.caption(f"类型: {type_text} | 端口: {port} | PID: {pid}")
                if is_running:
                    url = f"http://localhost:{port}"
                    st.markdown(f"🔗 访问地址: [{url}]({url})")

            with col_status:
                if is_running:
                    st.success("🟢 运行中")
                else:
                    st.error("🔴 已停止")

            with col_action:
                if is_running:
                    if st.button("🛑 停止", key=f"stop_{service_key}", type="secondary"):
                        if kill_process(pid):
                            st.success(f"✅ 服务已停止")
                            services_to_remove.append(service_key)
                            st.rerun()
                        else:
                            st.error("❌ 停止失败")
                else:
                    if st.button("🗑️ 移除", key=f"remove_{service_key}", type="secondary"):
                        services_to_remove.append(service_key)
                        st.rerun()

            st.markdown("---")

        # 如果服务正在运行，保留配置
        if is_running:
            updated_config[service_key] = service_info

    # 移除已停止的服务
    for key in services_to_remove:
        if key in updated_config:
            del updated_config[key]

    # 保存更新后的配置
    if services_to_remove:
        save_port_config(updated_config)

    # 批量操作
    st.markdown("---")
    st.subheader("🔧 批量操作")

    col_batch1, col_batch2 = st.columns(2)

    with col_batch1:
        if st.button("🛑 停止所有服务", type="secondary", use_container_width=True):
            stopped_count = 0
            for service_key, service_info in port_config.items():
                pid = service_info.get('pid', 0)
                if check_process_running(pid):
                    if kill_process(pid):
                        stopped_count += 1

            save_port_config({})
            st.success(f"✅ 已停止 {stopped_count} 个服务")
            st.rerun()

    with col_batch2:
        if st.button("🗑️ 清理已停止服务", type="secondary", use_container_width=True):
            active_config = {k: v for k, v in port_config.items() if check_process_running(v.get('pid', 0))}
            removed_count = len(port_config) - len(active_config)
            save_port_config(active_config)
            st.success(f"✅ 已清理 {removed_count} 个已停止的服务")
            st.rerun()

if __name__ == "__main__":
    Admin_manage_services_page()
