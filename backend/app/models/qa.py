"""
QA模块数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class QAPair(BaseModel):
    """问答对"""
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    title: Optional[str] = Field(None, description="所属标题")
    content: Optional[str] = Field(None, description="原始内容")
    question_number: Optional[str] = Field(None, description="问题编号")

class QAEvaluation(BaseModel):
    """问答对评估结果"""
    question: str
    answer: str
    factual_score: float = Field(..., ge=0, le=10, description="事实依据分数(0-10)")
    completeness_score: float = Field(..., ge=0, le=10, description="回答完整性分数(0-10)")
    overall_score: float = Field(..., ge=0, le=10, description="总体质量分数(0-10)")
    key_points: List[str] = Field(default_factory=list, description="关键信息点")
    supported_points: List[str] = Field(default_factory=list, description="有依据的信息点")
    unsupported_points: List[str] = Field(default_factory=list, description="无依据的信息点")
    evaluation_reason: str = Field(..., description="评估理由")
    is_passed: bool = Field(..., description="是否通过质量检验")

class QAGenerateRequest(BaseModel):
    """生成问答对请求"""
    num_pairs_per_section: int = Field(default=5, ge=1, le=20, description="每个部分生成的问答对数量")
    use_suggested_count: bool = Field(default=False, description="是否使用建议的问答对数量")

class QAEvaluateRequest(BaseModel):
    """评估问答对请求"""
    min_factual_score: int = Field(default=7, ge=0, le=10, description="最低事实依据分数阈值")
    min_overall_score: int = Field(default=7, ge=0, le=10, description="最低总体质量分数阈值")
    sample_percentage: float = Field(default=100, ge=1, le=100, description="抽查的百分比")


class QAEvaluateTaskRequest(QAEvaluateRequest):
    """基于已生成任务的评估请求"""
    source_task_id: str = Field(..., description="源问答生成任务ID")

class QAResponse(BaseModel):
    """通用QA响应"""
    success: bool
    message: str
    data: Optional[dict] = None

class QATaskStatus(BaseModel):
    """QA任务状态"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = Field(default=0, ge=0, le=100)
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_file: Optional[str] = None
    current_step: Optional[str] = None
    logs: Optional[List[dict]] = None
