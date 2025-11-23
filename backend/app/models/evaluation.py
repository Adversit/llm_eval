"""评估系统数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EvaluationInfo(BaseModel):
    """评估基本信息"""
    llm_name: str = Field(..., description="LLM模型名称")
    evaluation_type: str = Field(..., description="评估类型: stage1, stage2, both")
    description: Optional[str] = Field(None, description="评估描述")

class EvaluationCreateRequest(BaseModel):
    """创建评估任务请求"""
    info: EvaluationInfo
    files: List[str] = Field(..., description="文件路径列表")
    stage1_answer_threshold: float = Field(default=60.0, ge=0, le=100)
    stage1_reasoning_threshold: float = Field(default=60.0, ge=0, le=100)
    stage2_answer_threshold: float = Field(default=60.0, ge=0, le=100)
    stage2_reasoning_threshold: float = Field(default=60.0, ge=0, le=100)
    evaluation_rounds: int = Field(default=1, ge=1, le=5)

class EvaluationTask(BaseModel):
    """评估任务"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = Field(default=0, ge=0, le=100)
    current_stage: str = Field(default="准备中")
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[dict] = None
    llm_name: Optional[str] = None
    evaluation_type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    files: Optional[List[str]] = None
    stage_progress: Optional[dict] = None
    file_progress: Optional[dict] = None  # 文件级进度
    step_progress: Optional[dict] = None  # 步骤级进度（细粒度）
    has_stage2: Optional[bool] = None  # 是否包含第二阶段

class EvaluationResult(BaseModel):
    """评估结果"""
    task_id: str
    llm_name: str
    total_files: int
    processed_files: int
    stage1_results: Optional[dict] = None
    stage2_results: Optional[dict] = None
    overall_score: Optional[float] = None
    report_path: Optional[str] = None
