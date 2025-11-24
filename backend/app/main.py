"""
LLM Evaluation Platform - FastAPI Backend
主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import qa, evaluation, upload
import uvicorn

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
