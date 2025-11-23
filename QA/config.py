"""
QA模块配置管理
统一管理API密钥和其他配置项
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / 'LLM_EVAL' / 'config' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 如果.env文件不存在,尝试从当前目录加载
    load_dotenv()

# API配置
# 注意：由于SiliconFlow账户余额不足，改用DeepSeek API
API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
MODEL = "deepseek-chat"
API_BASE_URL = "https://api.deepseek.com"

# API请求配置
DEFAULT_TIMEOUT = 60  # 秒
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.2

# 验证API密钥是否已配置
if not API_KEY:
    raise ValueError(
        "未找到API密钥。请在环境变量中设置SILICONFLOW_API_KEY，"
        "或在.env文件中配置。"
    )
