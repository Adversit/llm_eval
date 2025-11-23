import os
import subprocess
import sys

def main():
    """启动Streamlit仪表盘应用"""
    
    print("启动文档问答生成管理系统...")
    
    # 检查依赖是否已安装
    required_packages = ['streamlit', 'pandas', 'lxml', 'python-docx']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"{package} 已安装")
        except ImportError:
            missing_packages.append(package)
    
    # 安装缺失的依赖
    if missing_packages:
        print(f"正在安装缺失的依赖: {', '.join(missing_packages)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
        print("依赖安装完成")
    else:
        print("所有依赖已安装")
    
    # 启动Streamlit应用
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py")
    
    print(f"正在启动仪表盘，路径: {dashboard_path}")
    subprocess.call(["streamlit", "run", dashboard_path, "--server.headless", "true"])

if __name__ == "__main__":
    main() 