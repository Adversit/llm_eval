"""
FLMM问卷平台数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Question(BaseModel):
    """问卷问题"""
    question_id: str
    question_text: str
    question_type: str  # single_choice, multiple_choice, text, rating
    options: Optional[List[str]] = None
    required: bool = True

class Questionnaire(BaseModel):
    """问卷"""
    questionnaire_id: str
    title: str
    description: Optional[str] = None
    questions: List[Question]
    created_at: datetime
    status: str  # draft, published, closed

class QuestionnaireCreateRequest(BaseModel):
    """创建问卷请求"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    questions: List[Question]

class QuestionnaireResponse(BaseModel):
    """问卷回答"""
    response_id: str
    questionnaire_id: str
    answers: Dict[str, Any]
    submitted_at: datetime

class QuestionnaireAnalysis(BaseModel):
    """问卷分析结果"""
    questionnaire_id: str
    total_responses: int
    completion_rate: float
    question_stats: Dict[str, Any]
    created_at: datetime
