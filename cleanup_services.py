#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理FLMM服务的僵尸进程"""
import requests

API_BASE = "http://localhost:8000/api/flmm"

def cleanup_services():
    """清理僵尸服务"""
    try:
        response = requests.post(f"{API_BASE}/services/cleanup")
        result = response.json()
        
        if result.get('success'):
            print(f"✅ {result.get('message')}")
            if result.get('cleaned'):
                print("\n清理的服务:")
                for service in result['cleaned']:
                    reason = service.get('reason', '未知原因')
                    print(f"  - {service['service']} (PID: {service['pid']}, Port: {service['port']}, 原因: {reason})")
        else:
            print(f"❌ 清理失败")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def list_services():
    """列出所有服务"""
    try:
        response = requests.get(f"{API_BASE}/services/list")
        result = response.json()
        
        if result.get('success'):
            services = result.get('services', [])
            print(f"\n📋 当前服务列表 (共 {len(services)} 个):")
            
            if not services:
                print("  (无运行中的服务)")
            else:
                for service in services:
                    status = "🟢 运行中" if service['is_running'] else "🔴 已停止"
                    print(f"\n  {status} {service['service_key']}")
                    print(f"    项目: {service['folder_name']}")
                    print(f"    类型: {service['type']}")
                    print(f"    端口: {service['port']}")
                    print(f"    PID: {service['pid']}")
                    if service.get('process_name'):
                        print(f"    进程名: {service['process_name']}")
                    print(f"    启动时间: {service['start_time']}")
        else:
            print(f"❌ 获取服务列表失败")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("FLMM 服务管理工具")
    print("=" * 60)
    
    # 先列出当前服务
    list_services()
    
    # 清理僵尸服务
    print("\n" + "=" * 60)
    print("开始清理僵尸服务...")
    print("=" * 60)
    cleanup_services()
    
    # 再次列出服务
    print("\n" + "=" * 60)
    print("清理后的服务列表:")
    print("=" * 60)
    list_services()
