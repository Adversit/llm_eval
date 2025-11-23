"""测试日志配置"""
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

print("=== 测试开始 ===")
logger.info("这是一条 INFO 日志")
logger.warning("这是一条 WARNING 日志")
logger.error("这是一条 ERROR 日志")
print("=== 测试结束 ===")
