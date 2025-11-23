"""
测试自动启动Streamlit功能
"""
import subprocess
import socket
import os
import json
import time

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

def start_streamlit_app(project_path, py_filename, port):
    """后台启动Streamlit应用"""
    try:
        script_path = os.path.join(project_path, py_filename)

        # 确定streamlit可执行文件路径
        streamlit_cmd = "D:/Anaconda3/envs/damoxingeval/Scripts/streamlit.exe"
        if not os.path.exists(streamlit_cmd):
            streamlit_cmd = "streamlit"

        # 启动Streamlit进程
        process = subprocess.Popen(
            [
                streamlit_cmd, "run", script_path,
                "--server.port", str(port),
                "--server.headless", "true",
                "--server.address", "localhost"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_path
        )

        return process.pid
    except Exception as e:
        print(f"启动Streamlit失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# 测试
print("=" * 60)
print("测试自动启动Streamlit功能")
print("=" * 60)

# 查找可用端口
print("\n1. 查找可用端口...")
port = find_available_port()
if port:
    print(f"   [OK] 找到可用端口: {port}")
else:
    print("   [ERROR] 未找到可用端口")
    exit(1)

# 启动Streamlit
print("\n2. 启动Streamlit应用...")
project_path = "data/flmm/projects/中金公司_投顾大模型1"
py_filename = "中金公司_投顾大模型1.py"

if os.path.exists(os.path.join(project_path, py_filename)):
    pid = start_streamlit_app(project_path, py_filename, port)
    if pid:
        print(f"   [OK] Streamlit启动成功 (PID: {pid})")
        print(f"   访问地址: http://localhost:{port}")

        # 等待几秒让服务启动
        print("\n3. 等待服务启动 (5秒)...")
        time.sleep(5)

        # 检查端口是否在监听
        print("\n4. 检查服务状态...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    print(f"   [OK] 端口{port}正在监听，服务启动成功！")
                else:
                    print(f"   [ERROR] 端口{port}未监听")
        except Exception as e:
            print(f"   [ERROR] 检查失败: {e}")

        print(f"\n测试完成！请在浏览器访问: http://localhost:{port}")
        print(f"请手动停止进程 (PID: {pid}) 或使用: taskkill //PID {pid} //F")
    else:
        print("   [ERROR] Streamlit启动失败")
else:
    print(f"   [ERROR] Python文件不存在: {os.path.join(project_path, py_filename)}")

print("\n" + "=" * 60)
