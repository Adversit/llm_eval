"""
测试 DeepSeek API 密钥是否有效
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / 'LLM_EVAL' / 'config' / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] 已加载配置文件: {env_path}")
else:
    print(f"[ERROR] 配置文件不存在: {env_path}")
    exit(1)

# 读取API密钥
api_key = os.getenv('DEEPSEEK_API_KEY', '')
if not api_key:
    print("[ERROR] 未找到 DEEPSEEK_API_KEY")
    exit(1)

print(f"[OK] API密钥: {api_key[:20]}...{api_key[-10:]}")

# 测试API调用
model = "deepseek-chat"
api_base_url = "https://api.deepseek.com"

print(f"\n正在测试API调用...")
print(f"- 模型: {model}")
print(f"- 端点: {api_base_url}/v1/chat/completions")

try:
    response = requests.post(
        f"{api_base_url}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello, this is a test message."}
            ],
            "max_tokens": 10
        },
        timeout=30
    )

    print(f"\n状态码: {response.status_code}")

    if response.status_code == 200:
        print("[SUCCESS] DeepSeek API密钥有效！")
        result = response.json()
        print(f"[OK] 响应内容: {result.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')}")
    elif response.status_code == 401:
        print("[ERROR] API密钥无效（401 Unauthorized）")
        print(f"响应内容: {response.text}")
    else:
        print(f"[ERROR] API调用失败（状态码: {response.status_code}）")
        print(f"响应内容: {response.text}")

except Exception as e:
    print(f"[ERROR] 发生错误: {str(e)}")
