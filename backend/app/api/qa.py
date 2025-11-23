"""
QA问答对管理API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import os
import sys
import uuid
from datetime import datetime
import shutil
import asyncio
import json

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from app.models.qa import (
    QAEvaluateTaskRequest,
    QAResponse,
    QATaskStatus
)
from app.utils.persistence import DataPersistence
from QA.evaluate_qa import process_qa_and_evaluate
from QA.complete_workflow import run_complete_workflow

router = APIRouter()

# 数据持久化目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'qa')

# 存储任务状态 - 使用持久化
task_storage = DataPersistence(DATA_DIR, 'tasks.json')

# 临时文件目录
TEMP_DIR = os.path.join(DATA_DIR, 'temp')
RESULTS_DIR = os.path.join(DATA_DIR, 'results')
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')

# 确保目录存在
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


def _update_task(task_id: str, **kwargs):
    """更新任务数据并持久化"""
    task = task_storage[task_id]
    task.update(kwargs)
    task_storage[task_id] = task


def _append_task_log(task_id: str, message: Optional[str]):
    if not message:
        return
    task = task_storage[task_id]
    logs = task.setdefault('logs', [])
    logs.append({
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'message': message
    })
    task_storage[task_id] = task


def _normalize_datetime(value):
    """将可能的字符串/日期时间值转换为datetime"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
    return datetime.min


def _format_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def process_qa_generation(
    task_id: str,
    file_path: str,
    output_dir: str,
    num_pairs: int,
    use_suggested: bool,
    include_reason: bool,
    suggest_qa_count: bool,
    min_density: int,
    min_quality: int,
    skip_extract: bool,
    skip_evaluate: bool,
    skip_qa: bool,
    skip_qa_evaluate: bool,
    min_factual_score: int,
    min_overall_score: int,
    qa_sample_percentage: float,
):
    """后台任务：生成问答对"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        def progress_callback(step_name, step_progress, message=None, **kwargs):
            """
            扩展的进度回调，支持文件级和步骤级进度

            kwargs可包含:
            - current_file: 当前文件索引
            - total_files: 总文件数
            - current_filename: 当前文件名
            - file_progress_percent: 当前文件完成百分比
            - step_name_detail: 详细步骤名称（如"第一阶段"）
            - current_question: 当前问题索引
            - total_questions: 总问题数
            """
            progress_percent = max(0, min(100, round(step_progress * 100, 2)))

            update_data = {
                'status': 'processing',
                'message': message or '处理中',
                'progress': progress_percent,
                'current_step': step_name
            }

            # 添加文件级进度
            if any(k in kwargs for k in ['current_file', 'total_files', 'current_filename', 'file_progress_percent']):
                update_data['file_progress'] = {
                    'current_file': kwargs.get('current_file', 0),
                    'total_files': kwargs.get('total_files', 1),
                    'current_filename': kwargs.get('current_filename', ''),
                    'file_progress_percent': kwargs.get('file_progress_percent', 0)
                }

            # 添加步骤级进度（总是发送，确保进度条3能更新）
            update_data['step_progress'] = {
                'current_step': kwargs.get('step_name_detail', step_name),
                'step_progress_percent': kwargs.get('step_progress_percent', progress_percent),  # 默认使用总进度
                'current_question': kwargs.get('current_question', 0),
                'total_questions': kwargs.get('total_questions', 0)
            }

            _update_task(task_id, **update_data)
            _append_task_log(task_id, f"[{step_name}] {message}" if message else step_name)

        _update_task(
            task_id,
            status='processing',
            message='正在生成问答对...',
            current_step='初始化',
            progress=1
        )

        result = run_complete_workflow(
            document_path=file_path,
            output_dir=output_dir,
            num_pairs=num_pairs,
            include_reason=include_reason,
            suggest_qa_count=suggest_qa_count,
            use_suggested_count=use_suggested,
            min_density_score=min_density,
            min_quality_score=min_quality,
            skip_extract=skip_extract,
            skip_evaluate=skip_evaluate,
            skip_qa=skip_qa,
            skip_qa_evaluate=skip_qa_evaluate,
            min_factual_score=min_factual_score,
            min_overall_score=min_overall_score,
            qa_sample_percentage=qa_sample_percentage,
            progress_callback=progress_callback
        )

        if result.get('success'):
            qa_excel = result['files'].get('qa_excel') if result.get('files') else None
            if qa_excel and os.path.exists(qa_excel):
                # 构建artifacts列表
                artifacts = []
                if result.get('files'):
                    for key, file_path in result['files'].items():
                        if file_path and os.path.exists(file_path):
                            artifacts.append({
                                'type': key,
                                'path': file_path,
                                'filename': os.path.basename(file_path),
                                'size_bytes': os.path.getsize(file_path)
                            })

                _update_task(
                    task_id,
                    status='completed',
                    progress=100,
                    message='问答对生成完成',
                    result_file=qa_excel,
                    completed_at=datetime.now(),
                    artifacts=artifacts,
                    metadata={
                        'output_dir': output_dir,
                    'files': result['files'],
                    'parameters': {
                        'num_pairs': num_pairs,
                        'include_reason': include_reason,
                        'suggest_qa_count': suggest_qa_count,
                        'use_suggested_count': use_suggested,
                        'min_density_score': min_density,
                        'min_quality_score': min_quality,
                        'skip_extract': skip_extract,
                        'skip_evaluate': skip_evaluate
                    }
                },
                    current_step='完成'
                )
                _append_task_log(task_id, '问答对生成完成')
            else:
                _update_task(
                    task_id,
                    status='failed',
                    message='问答对生成完成但未找到输出文件',
                    progress=100
                )
                _append_task_log(task_id, '未找到问答输出文件')
        else:
            _update_task(
                task_id,
                status='failed',
                message=result.get('error', '问答对生成失败')
            )
            _append_task_log(task_id, result.get('error', '问答对生成失败'))

    except Exception as e:
        _update_task(
            task_id,
            status='failed',
            message=f'生成过程出错: {str(e)}'
        )
        _append_task_log(task_id, f'异常: {str(e)}')
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)


def process_qa_evaluation(task_id: str, file_path: str, output_path: str, min_factual: int, min_overall: int, sample_pct: float):
    """后台任务：评估问答对"""
    try:
        def progress_callback(step_name, step_progress, message=None):
            progress_percent = max(0, min(100, round(step_progress * 100, 2)))
            _update_task(
                task_id,
                status='processing',
                message=message or '处理中',
                progress=progress_percent,
                current_step=step_name
            )
            _append_task_log(task_id, f"[{step_name}] {message}" if message else step_name)

        progress_callback('初始化', 0.01, '开始问答质量评估')

        success = process_qa_and_evaluate(
            qa_excel=file_path,
            output_excel=output_path,
            min_factual_score=min_factual,
            min_overall_score=min_overall,
            sample_percentage=sample_pct,
            progress_callback=progress_callback
        )

        if success:
            _update_task(
                task_id,
                status='completed',
                progress=100,
                message='问答对评估完成',
                result_file=output_path,
                completed_at=datetime.now(),
                current_step='完成'
            )
            _append_task_log(task_id, '评估完成')
        else:
            _update_task(
                task_id,
                status='failed',
                message='问答对评估失败'
            )
            _append_task_log(task_id, '评估失败')

    except Exception as e:
        _update_task(
            task_id,
            status='failed',
            message=f'评估过程出错: {str(e)}'
        )
        _append_task_log(task_id, f'异常: {str(e)}')
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/generate", response_model=QAResponse)
async def generate_qa_pairs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    num_pairs_per_section: int = Query(5, ge=1, le=20),
    use_suggested_count: bool = Query(False),
    include_reason: bool = Query(True),
    suggest_qa_count: bool = Query(True),
    min_density_score: int = Query(5, ge=1, le=10),
    min_quality_score: int = Query(5, ge=1, le=10),
    skip_extract: bool = Query(False),
    skip_evaluate: bool = Query(False),
    skip_qa: bool = Query(False),
    skip_qa_evaluate: bool = Query(True),
    min_factual_score: int = Query(7, ge=0, le=10),
    min_overall_score: int = Query(7, ge=0, le=10),
    qa_sample_percentage: float = Query(100, ge=1, le=100)
):
    """
    基于Word文档生成问答对

    - **files**: Word文件列表（doc/docx）
    - **num_pairs_per_section**: 每个部分生成的问答对数量（1-20）
    - **use_suggested_count**: 是否使用建议的问答对数量
    - **include_reason**: 是否保留内容筛选的评分理由
    - **suggest_qa_count**: 是否让模型建议问答数量
    - **min_density_score**: 最低信息密度分数（1-10）
    - **min_quality_score**: 最低信息质量分数（1-10）
    - **skip_extract**: 跳过内容提取（需确保已有对应结果文件）
    - **skip_evaluate**: 跳过内容评估（需确保已有对应结果文件）
    - **skip_qa**: 跳过问答对生成
    - **skip_qa_evaluate**: 跳过问答对质量评估
    - **min_factual_score**: 最低事实依据分数（0-10）
    - **min_overall_score**: 最低总体质量分数（0-10）
    - **qa_sample_percentage**: 问答质量评估的抽查百分比（1-100）
    """
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="请至少上传一个Word文件")

        for upload in files:
            if not upload.filename.lower().endswith(('.doc', '.docx')):
                raise HTTPException(status_code=400, detail=f"文件 {upload.filename} 不是支持的Word格式")

        created_tasks = []

        for upload in files:
            task_id = str(uuid.uuid4())

            file_path = os.path.join(UPLOADS_DIR, f"{task_id}_{upload.filename}")
            output_dir = os.path.join(RESULTS_DIR, task_id)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)

            task_storage[task_id] = {
                'task_id': task_id,
                'status': 'pending',
                'progress': 0,
                'message': '任务已创建，等待处理',
                'created_at': datetime.now(),
                'completed_at': None,
                'result_file': None,
                'task_type': 'generation',
                'source_filename': upload.filename,
                'source_task_id': None,
                'metadata': {
                    'parameters': {
                        'num_pairs': num_pairs_per_section,
                        'include_reason': include_reason,
                        'suggest_qa_count': suggest_qa_count,
                        'use_suggested_count': use_suggested_count,
                        'min_density_score': min_density_score,
                        'min_quality_score': min_quality_score,
                        'skip_extract': skip_extract,
                        'skip_evaluate': skip_evaluate,
                        'skip_qa': skip_qa,
                        'skip_qa_evaluate': skip_qa_evaluate
                    }
                },
                'current_step': '等待中',
                'logs': []
            }

            background_tasks.add_task(
                process_qa_generation,
                task_id,
                file_path,
                output_dir,
                num_pairs_per_section,
                use_suggested_count,
                include_reason,
                suggest_qa_count,
                min_density_score,
                min_quality_score,
                skip_extract,
                skip_evaluate,
                skip_qa,
                skip_qa_evaluate,
                min_factual_score,
                min_overall_score,
                qa_sample_percentage
            )

            created_tasks.append({
                'task_id': task_id,
                'filename': upload.filename
            })

        return QAResponse(
            success=True,
            message=f"已创建 {len(created_tasks)} 个问答任务",
            data={'tasks': created_tasks}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成问答对失败: {str(e)}")


@router.get("/task/{task_id}", response_model=QATaskStatus)
async def get_task_status(task_id: str):
    """
    获取任务状态

    - **task_id**: 任务ID
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]
    return QATaskStatus(**task)


@router.post("/evaluate-task", response_model=QAResponse)
async def evaluate_existing_task(
    background_tasks: BackgroundTasks,
    request: QAEvaluateTaskRequest
):
    """基于已完成的问答生成任务进行质量评估"""

    source_task_id = request.source_task_id

    if source_task_id not in task_storage:
        raise HTTPException(status_code=404, detail="源任务不存在")

    source_task = task_storage[source_task_id]
    if source_task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="源任务尚未完成")

    qa_file = source_task.get('result_file')
    if not qa_file or not os.path.exists(qa_file):
        raise HTTPException(status_code=404, detail="源任务问答结果不存在")

    # 生成新的评估任务ID
    task_id = str(uuid.uuid4())
    output_dir = os.path.join(RESULTS_DIR, task_id)
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{os.path.splitext(os.path.basename(qa_file))[0]}_evaluated.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # 为评估创建临时副本，避免删除源文件
    temp_input = os.path.join(TEMP_DIR, f"{task_id}_qa.xlsx")
    shutil.copy2(qa_file, temp_input)

    task_storage[task_id] = {
        'task_id': task_id,
        'status': 'pending',
        'progress': 0,
        'message': '评估任务已创建，等待处理',
        'created_at': datetime.now(),
        'completed_at': None,
        'result_file': None,
        'task_type': 'evaluation',
        'source_filename': source_task.get('source_filename'),
        'source_task_id': source_task_id,
        'metadata': {
            'qa_source_file': qa_file
        },
        'current_step': '等待中',
        'logs': []
    }

    background_tasks.add_task(
        process_qa_evaluation,
        task_id,
        temp_input,
        output_path,
        request.min_factual_score,
        request.min_overall_score,
        request.sample_percentage
    )

    return QAResponse(
        success=True,
        message="问答对评估任务已创建",
        data={'task_id': task_id}
    )


@router.get("/download/{task_id}")
async def download_result(task_id: str):
    """
    下载结果文件

    - **task_id**: 任务ID
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")

    result_file = task.get('result_file')
    if not result_file or not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        result_file,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=os.path.basename(result_file)
    )


@router.get("/stats")
async def get_qa_stats():
    """
    获取QA统计信息
    """
    total_tasks = len(task_storage)
    completed_tasks = sum(1 for t in task_storage.values() if t['status'] == 'completed')
    failed_tasks = sum(1 for t in task_storage.values() if t['status'] == 'failed')
    processing_tasks = sum(1 for t in task_storage.values() if t['status'] == 'processing')

    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'failed_tasks': failed_tasks,
        'processing_tasks': processing_tasks,
        'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    }


@router.get("/tasks/all")
async def get_all_tasks():
    """
    获取所有任务及其详细信息（用于结果分析）
    """
    all_tasks = []
    for task_id, task_data in task_storage.items():
        created_at = task_data.get('created_at')
        completed_at = task_data.get('completed_at')
        all_tasks.append({
            'task_id': task_id,
            'task_type': task_data.get('task_type', 'generation'),
            'status': task_data.get('status'),
            'filename': task_data.get('source_filename', '未知文件'),
            'created_at': _format_datetime(created_at),
            'completed_at': _format_datetime(completed_at),
            'progress': task_data.get('progress', 0),
            'message': task_data.get('message', ''),
            'source_task_id': task_data.get('source_task_id'),
            'result_file': task_data.get('result_file'),
            '_sort_time': _normalize_datetime(created_at)
        })

    # 按创建时间倒序排列
    all_tasks.sort(key=lambda x: x['_sort_time'], reverse=True)
    for task in all_tasks:
        task.pop('_sort_time', None)

    return {
        'tasks': all_tasks,
        'total': len(all_tasks)
    }


@router.get("/preview/{task_id}")
async def preview_result(task_id: str, limit: int = Query(100, ge=1, le=1000)):
    """
    预览结果文件内容（返回Excel前N行数据）

    - **task_id**: 任务ID
    - **limit**: 返回的最大行数（默认100，最大1000）
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")

    result_file = task.get('result_file')
    if not result_file or not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    try:
        import pandas as pd
        import numpy as np
        import math

        # 读取Excel文件
        df = pd.read_excel(result_file)

        # 限制返回行数
        preview_df = df.head(limit)

        # 转换为JSON前，清除NaN/Inf并转为对象类型，防止浮点列继续产生NaN
        preview_df = preview_df.replace([np.inf, -np.inf], np.nan)
        preview_df = preview_df.astype(object).where(pd.notnull(preview_df), None)

        # 提前清洗每个值，彻底移除NaN/Inf并转换numpy类型
        def _clean_value(val):
            if isinstance(val, (float, np.floating)):
                return float(val) if math.isfinite(val) else None
            if isinstance(val, (int, np.integer)):
                return int(val)
            if isinstance(val, (np.bool_,)):
                return bool(val)
            if pd.isna(val):
                return None
            return val

        # 转换为JSON格式
        records = []
        for row in preview_df.to_dict(orient='records'):
            cleaned_row = {k: _clean_value(v) for k, v in row.items()}
            records.append(cleaned_row)
        data = jsonable_encoder(records)
        columns_clean = []
        for idx, col in enumerate(df.columns):
            if isinstance(col, (float, np.floating)) and not np.isfinite(col):
                columns_clean.append(f"column_{idx}")
            elif pd.isna(col):
                columns_clean.append(f"column_{idx}")
            else:
                columns_clean.append(str(col))
        columns = jsonable_encoder(columns_clean)

        return jsonable_encoder({
            'success': True,
            'data': data,
            'columns': columns,
            'total_rows': len(df),
            'preview_rows': len(preview_df),
            'filename': os.path.basename(result_file)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.get("/progress/{task_id}")
async def stream_progress(task_id: str):
    """
    Server-Sent Events (SSE) 端点，用于实时流式传输任务进度和日志

    返回数据格式：
    - event: progress
      data: {
        "status": "processing",
        "progress": 45,
        "current_step": "问答生成",
        "message": "处理中...",
        "file_progress": {
          "current_file": 2,
          "total_files": 5,
          "current_filename": "document.docx",
          "file_progress_percent": 40
        },
        "step_progress": {
          "current_step": "第一阶段",
          "step_progress_percent": 75,
          "current_question": 45,
          "total_questions": 60
        },
        "timing": {
          "elapsed_seconds": 120,
          "estimated_remaining_seconds": 180,
          "estimated_total_seconds": 300
        }
      }

    - event: log
      data: {
        "timestamp": "2025-01-20 10:30:45",
        "message": "开始处理文件: document.docx"
      }

    - event: complete
      data: {
        "status": "completed",
        "summary": {
          "total_time_seconds": 300,
          "total_files": 5,
          "success_count": 5,
          "fail_count": 0,
          "artifacts": [...]
        }
      }
    """

    async def event_generator():
        """生成SSE事件流"""
        last_log_count = 0
        last_progress = -1
        start_time = None
        avg_time_per_file = None

        try:
            while True:
                # 获取最新任务状态
                if task_id not in task_storage:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "任务不存在"})
                    }
                    break

                task = task_storage[task_id]
                status = task.get('status', 'pending')

                # 初始化开始时间
                if start_time is None and status == 'processing':
                    start_time = datetime.now()

                # 构建进度数据
                progress_data = {
                    'status': status,
                    'progress': task.get('progress', 0),
                    'current_step': task.get('current_step', ''),
                    'message': task.get('message', ''),
                }

                # 添加文件级进度（如果有）
                if 'file_progress' in task:
                    fp = task['file_progress']
                    progress_data['file_progress'] = {
                        'current_file': fp.get('current_file', 0),
                        'total_files': fp.get('total_files', 0),
                        'current_filename': fp.get('current_filename', ''),
                        'file_progress_percent': fp.get('file_progress_percent', 0)
                    }

                # 添加步骤级进度（如果有）
                if 'step_progress' in task:
                    sp = task['step_progress']
                    progress_data['step_progress'] = {
                        'current_step': sp.get('current_step', ''),
                        'step_progress_percent': sp.get('step_progress_percent', 0),
                        'current_question': sp.get('current_question', 0),
                        'total_questions': sp.get('total_questions', 0)
                    }

                # 计算时间预估
                if start_time and status == 'processing':
                    elapsed = (datetime.now() - start_time).total_seconds()

                    # 基于文件进度计算预估时间
                    if 'file_progress' in task:
                        fp = task['file_progress']
                        current_file = fp.get('current_file', 0)
                        total_files = fp.get('total_files', 1)

                        if current_file > 0:
                            avg_time_per_file = elapsed / current_file
                            remaining_files = total_files - current_file
                            estimated_remaining = avg_time_per_file * remaining_files
                            estimated_total = avg_time_per_file * total_files
                        else:
                            estimated_remaining = None
                            estimated_total = None
                    else:
                        # 基于总体进度计算
                        progress_pct = task.get('progress', 0)
                        if progress_pct > 0:
                            estimated_total = (elapsed / progress_pct) * 100
                            estimated_remaining = estimated_total - elapsed
                        else:
                            estimated_remaining = None
                            estimated_total = None

                    progress_data['timing'] = {
                        'elapsed_seconds': int(elapsed),
                        'estimated_remaining_seconds': int(estimated_remaining) if estimated_remaining else None,
                        'estimated_total_seconds': int(estimated_total) if estimated_total else None
                    }

                # 发送进度更新（仅当进度变化时）
                current_progress = task.get('progress', 0)
                if current_progress != last_progress:
                    yield {
                        "event": "progress",
                        "data": json.dumps(progress_data, ensure_ascii=False)
                    }
                    last_progress = current_progress

                # 发送新增日志
                logs = task.get('logs', [])
                if len(logs) > last_log_count:
                    new_logs = logs[last_log_count:]
                    for log in new_logs:
                        yield {
                            "event": "log",
                            "data": json.dumps(log, ensure_ascii=False)
                        }
                    last_log_count = len(logs)

                # 如果任务完成或失败，发送完成事件
                if status in ['completed', 'failed']:
                    completion_data = {
                        'status': status,
                        'message': task.get('message', ''),
                    }

                    # 添加汇总报告
                    if status == 'completed':
                        total_time = (datetime.now() - start_time).total_seconds() if start_time else 0

                        summary = {
                            'total_time_seconds': int(total_time),
                            'result_file': task.get('result_file', ''),
                        }

                        # 如果有文件进度信息，添加统计
                        if 'file_progress' in task:
                            fp = task['file_progress']
                            summary['total_files'] = fp.get('total_files', 0)
                            summary['success_count'] = fp.get('success_count', fp.get('total_files', 0))
                            summary['fail_count'] = fp.get('fail_count', 0)

                        # 添加生成的文件列表
                        if 'artifacts' in task:
                            summary['artifacts'] = task['artifacts']

                        completion_data['summary'] = summary

                    yield {
                        "event": "complete",
                        "data": json.dumps(completion_data, ensure_ascii=False)
                    }
                    break

                # 等待后再次检查（处理中0.5秒，其他2秒）
                await asyncio.sleep(0.5 if status == 'processing' else 2)

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    # 直接使用StreamingResponse输出SSE格式，避免额外依赖
    async def sse_wrapper():
        async for chunk in event_generator():
            # 每个事件块按SSE协议格式输出
            yield f"event: {chunk['event']}\n".encode('utf-8')
            yield f"data: {chunk['data']}\n\n".encode('utf-8')

    return StreamingResponse(sse_wrapper(), media_type="text/event-stream")
