"""
LLM Evaluation Platform - FastAPI Backend
主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import qa, evaluation, upload
import uvicorn
import logging
import logging.config
import json
import sys
import os
from pathlib import Path

# 初始化日志系统
BACKEND_DIR = Path(__file__).parent.parent
LOG_CONFIG_PATH = BACKEND_DIR / "logging_config.json"

if LOG_CONFIG_PATH.exists():
    with open(LOG_CONFIG_PATH, 'r', encoding='utf-8') as f:
        log_config = json.load(f)
    logging.config.dictConfig(log_config)
    logger = logging.getLogger("app.main")
    logger.info("=" * 80)
    logger.info("日志系统初始化完成")
    logger.info(f"日志配置文件: {LOG_CONFIG_PATH}")
    logger.info("=" * 80)
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("app.main")
    logger.warning(f"日志配置文件不存在: {LOG_CONFIG_PATH}")

app = FastAPI(
    title="LLM Evaluation Platform API",
    description="专业的大语言模型评估平台后端服务",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)



# CORS配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React开发服务器
        "http://localhost:5173",  # Vite开发服务器
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的任务"""
    logger.info("=" * 50)
    logger.info("LLM Evaluation Platform 正在启动...")
    logger.info("=" * 50)
    
    # 导入并执行清理逻辑
    from app.api.evaluation import _cleanup_interrupted_tasks
    _cleanup_interrupted_tasks()
    
    logger.info("=" * 50)
    logger.info("应用启动完成！")
    logger.info(f"API 文档: http://localhost:8000/api/docs")
    logger.info("=" * 50)

# 注册API路由
app.include_router(qa.router, prefix="/api/qa", tags=["QA问答对管理"])
app.include_router(evaluation.router, prefix="/api/eval", tags=["双阶段评测系统"])
app.include_router(upload.router, prefix="/api/upload", tags=["文件上传"])

# 导入并注册FLMM路由
from app.api import flmm
app.include_router(flmm.router, prefix="/api/flmm", tags=["FLMM问卷平台"])

@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "LLM Evaluation Platform API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/api/docs"
    }

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "llm-eval-api"}

@app.get("/api/test")
async def test_logging():
    """测试日志"""
    return {"message": "测试成功", "timestamp": "2025-11-23"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
