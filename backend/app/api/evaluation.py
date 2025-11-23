"""
双阶段评测系统API - 集成LLM_EVAL核心模块
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import Response, StreamingResponse
from typing import List, Optional, Dict, Any, Tuple
import os
import sys
import uuid
from datetime import datetime
import shutil
import json
import logging
from pathlib import Path
from contextlib import contextmanager
import threading
import io
import re
from urllib.parse import quote

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from app.models.evaluation import EvaluationTask
from app.utils.persistence import DataPersistence

router = APIRouter()
logger = logging.getLogger(__name__)

# 数据持久化目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'evaluation')

# LLM_EVAL目录，用于调用已有能力
LLM_EVAL_DIR = os.path.join(PROJECT_ROOT, 'LLM_EVAL')
if LLM_EVAL_DIR not in sys.path:
    sys.path.append(LLM_EVAL_DIR)
LLM_EVAL_DATA_DIR = os.path.join(LLM_EVAL_DIR, 'data')

try:
    from first_stage.stage1_evaluator import Stage1Evaluator
    from second_stage.stage2_evaluator import Stage2Evaluator
    from utils.result_processor import ResultProcessor
    from utils.file_manager_singleton import get_file_manager, reset_file_manager_for_new_test
    from utils.report_generator import ReportGenerator
    from utils.html_report_generator import HTMLReportGenerator
except Exception as import_error:  # pragma: no cover - 运行时捕获
    logger.error("无法导入LLM_EVAL模块: %s", import_error)
    Stage1Evaluator = None  # type: ignore
    Stage2Evaluator = None  # type: ignore
    ResultProcessor = None  # type: ignore
    get_file_manager = None  # type: ignore
    reset_file_manager_for_new_test = None  # type: ignore
    ReportGenerator = None  # type: ignore
    HTMLReportGenerator = None  # type: ignore

try:  # numpy在LLM_EVAL中使用，这里仅用于类型转换
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy缺失时兜底
    np = None

# 存储任务状态 - 使用持久化
eval_task_storage = DataPersistence(DATA_DIR, 'tasks.json')

# 标记是否已执行清理（避免热重载时重复执行）
_cleanup_executed = False

def _cleanup_interrupted_tasks():
    """标记所有未完成的任务为中断状态"""
    global _cleanup_executed
    if _cleanup_executed:
        return
    
    interrupted_count = 0
    for task_id, task in eval_task_storage.items():
        if task.get('status') in ['processing', 'pending']:
            task['status'] = 'interrupted'
            task['message'] = '任务被中断（后端重启）'
            task['completed_at'] = datetime.now().isoformat()
            eval_task_storage[task_id] = task
            interrupted_count += 1
            logger.info(f"标记中断任务: {task_id}")
    if interrupted_count > 0:
        logger.info(f"共标记 {interrupted_count} 个中断任务")
    
    _cleanup_executed = True

# 临时文件和结果目录
EVAL_UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
EVAL_RESULTS_DIR = os.path.join(DATA_DIR, 'results')

os.makedirs(EVAL_UPLOAD_DIR, exist_ok=True)
os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

DEFAULT_EVAL_MODEL = 'siliconflow_deepseek_v3'
EVAL_LOCK = threading.Lock()

STAGE_PROGRESS_RANGES: Dict[str, Tuple[int, int]] = {
    'init': (0, 5),
    'stage1': (5, 65),
    'stage2': (65, 90),
    'result': (90, 100),
}

STAGE_KEY_LABELS: Dict[str, str] = {
    'init': '初始化',
    'stage1': '第一阶段评估',
    'stage2': '第二阶段评估',
    'result': '结果处理',
}

STAGE_NAME_MAP: Dict[str, str] = {
    '准备中': 'init',
    '初始化': 'init',
    '第一阶段评估': 'stage1',
    '第二阶段评估': 'stage2',
    '结果处理': 'result',
    '已完成': 'result',
}

report_generator = ReportGenerator() if 'ReportGenerator' in globals() and ReportGenerator else None
html_report_generator = HTMLReportGenerator() if 'HTMLReportGenerator' in globals() and HTMLReportGenerator else None


@contextmanager
def _llm_eval_workdir():
    """切换到LLM_EVAL目录，确保其相对路径资源可用"""
    if not os.path.isdir(LLM_EVAL_DIR):
        raise RuntimeError('LLM_EVAL目录不存在，无法执行评估任务')
    previous = os.getcwd()
    os.chdir(LLM_EVAL_DIR)
    try:
        yield
    finally:
        os.chdir(previous)


def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_datetime(value: Optional[Any]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _sanitize_for_storage(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _sanitize_for_storage(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_storage(item) for item in data]
    if np is not None:
        if isinstance(data, np.integer):  # type: ignore[attr-defined]
            return int(data)  # type: ignore[call-arg]
        if isinstance(data, np.floating):  # type: ignore[attr-defined]
            return float(data)  # type: ignore[call-arg]
    if isinstance(data, datetime):
        return data.isoformat()
    return data


def _build_initial_stage_progress(evaluation_type: str, stage2_only: bool = False) -> Dict[str, Dict[str, Any]]:
    stage_progress: Dict[str, Dict[str, Any]] = {}
    enable_stage2 = evaluation_type in ('both', 'stage2')
    enable_stage1 = evaluation_type != 'stage2' or not stage2_only
    now_iso = _serialize_datetime(datetime.utcnow())

    for key, label in STAGE_KEY_LABELS.items():
        enabled = True
        if key == 'stage1':
            enabled = enable_stage1
        if key == 'stage2':
            enabled = enable_stage2
        stage_progress[key] = {
            'key': key,
            'label': label,
            'progress': 0,
            'status': 'active' if key == 'init' and enabled else ('disabled' if not enabled else 'pending'),
            'enabled': enabled,
            'message': None,
            'updated_at': now_iso,
        }
    return stage_progress


def _normalize_stage_progress(stage_key: str, progress: Optional[int]) -> int:
    if progress is None:
        return 0
    start, end = STAGE_PROGRESS_RANGES.get(stage_key, (0, 100))
    span = max(end - start, 1)
    normalized = (progress - start) / span * 100
    normalized = max(0.0, min(100.0, normalized))
    return int(normalized)


def _update_stage_progress_for_task(task: Dict[str, Any], stage_label: Optional[str], progress: Optional[int], message: Optional[str], status: Optional[str]) -> None:
    evaluation_type = (task.get('evaluation_type') or 'both').lower()
    stage2_only = (task.get('config') or {}).get('stage2_only', False)
    if 'stage_progress' not in task:
        task['stage_progress'] = _build_initial_stage_progress(evaluation_type, stage2_only)
    stage_progress: Dict[str, Dict[str, Any]] = task['stage_progress']

    if status == 'completed':
        now_iso = _serialize_datetime(datetime.utcnow())
        for entry in stage_progress.values():
            if entry.get('enabled', True):
                entry['progress'] = 100
                entry['status'] = 'completed'
                entry['message'] = message or entry.get('message')
                entry['updated_at'] = now_iso
        return

    if status == 'failed':
        result_entry = stage_progress.get('result')
        if result_entry:
            result_entry['status'] = 'failed'
            result_entry['message'] = message
            result_entry['updated_at'] = _serialize_datetime(datetime.utcnow())

    stage_key = None
    if stage_label:
        stage_key = STAGE_NAME_MAP.get(stage_label)
    if not stage_key and status == 'completed':
        stage_key = 'result'
    if not stage_key:
        return

    entry = stage_progress.get(stage_key)
    if not entry or not entry.get('enabled', True):
        return

    normalized = _normalize_stage_progress(stage_key, progress)
    entry['progress'] = normalized
    entry['message'] = message
    entry['status'] = 'completed' if normalized >= 100 else 'active'
    entry['updated_at'] = _serialize_datetime(datetime.utcnow())

    ordered_keys = ['init', 'stage1', 'stage2', 'result']
    if stage_key in ordered_keys:
        current_index = ordered_keys.index(stage_key)
        for idx, key in enumerate(ordered_keys):
            if key == stage_key:
                continue
            prev_entry = stage_progress.get(key)
            if not prev_entry or not prev_entry.get('enabled', True):
                continue
            if idx < current_index and prev_entry['progress'] < 100:
                prev_entry['progress'] = 100
                prev_entry['status'] = 'completed'
                prev_entry['updated_at'] = _serialize_datetime(datetime.utcnow())


def _timestamp_to_iso_value(timestamp: str) -> Optional[str]:
    try:
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M')
        return dt.isoformat()
    except Exception:
        return None


def _format_timestamp_label(timestamp: str) -> str:
    try:
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M')
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return timestamp


def _list_upload_cache() -> List[Dict[str, Any]]:
    uploads: List[Dict[str, Any]] = []
    upload_dir = Path(EVAL_UPLOAD_DIR)
    if not upload_dir.exists():
        return uploads
    for item in upload_dir.iterdir():
        if item.is_file():
            stats = item.stat()
            uploads.append({
                'file_name': item.name,
                'file_path': str(item.resolve()),
                'size': stats.st_size,
                'updated_at': _serialize_datetime(datetime.fromtimestamp(stats.st_mtime)),
                'source': 'upload',
            })
    uploads.sort(key=lambda x: x.get('updated_at') or '', reverse=True)
    return uploads


def _collect_history_entries(llm_name: Optional[str] = None) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    data_dir = Path(LLM_EVAL_DATA_DIR)
    if not data_dir.exists():
        return history
    pattern = re.compile(r'^(?P<model>.+?)(?P<timestamp>\d{12})$')
    for entry in data_dir.iterdir():
        if not entry.is_dir():
            continue
        match = pattern.match(entry.name)
        if not match:
            continue
        model_name = match.group('model')
        timestamp = match.group('timestamp')
        if llm_name and model_name != llm_name:
            continue
        test_data_dir = entry / 'test_data'
        if not test_data_dir.exists():
            continue
        files: List[Dict[str, Any]] = []
        for suffix in ('*.xlsx', '*.xls', '*.csv', '*.json'):
            for file_path in test_data_dir.glob(suffix):
                stats = file_path.stat()
                files.append({
                    'file_name': file_path.name,
                    'file_path': str(file_path.resolve()),
                    'size': stats.st_size,
                    'timestamp': timestamp,
                    'model_name': model_name,
                    'source': 'history',
                })
        if not files:
            continue
        files.sort(key=lambda x: x['file_name'])
        history.append({
            'model_name': model_name,
            'timestamp': timestamp,
            'display_name': f"{model_name}-{_format_timestamp_label(timestamp)}",
            'created_at': _timestamp_to_iso_value(timestamp),
            'result_dir': str(entry.resolve()),
            'files': files,
        })
    history.sort(key=lambda x: x['timestamp'], reverse=True)
    return history


def _resolve_timestamp_dir(task: Dict[str, Any]) -> Optional[Path]:
    artifacts = (task.get('results') or {}).get('artifacts') or {}
    result_dir = artifacts.get('result_dir')
    if result_dir and os.path.isdir(result_dir):
        return Path(result_dir)
    llm_name = task.get('llm_name')
    if llm_name and get_file_manager:
        try:
            file_manager = get_file_manager()
            directory = file_manager.find_latest_timestamp_dir(llm_name)
            if directory:
                return Path(directory)
        except Exception as exc:
            logger.warning('获取时间戳目录失败: llm=%s error=%s', llm_name, exc)
    return None


def _load_analysis_payload(task: Dict[str, Any], file_name: str) -> Optional[Dict[str, Any]]:
    results = task.get('results') or {}
    files = results.get('files') or []
    target = next((f for f in files if f.get('file_name') == file_name), None)
    if target:
        analysis = target.get('final_analysis')
        if analysis:
            enriched = dict(analysis)
            enriched.setdefault('model_name', results.get('model_name') or task.get('llm_name'))
            enriched.setdefault('file_name', file_name)
            return enriched
    timestamp_dir = _resolve_timestamp_dir(task)
    if timestamp_dir:
        analysis_path = timestamp_dir / file_name / f"{file_name}_analysis.json"
        if analysis_path.exists():
            try:
                with open(analysis_path, 'r', encoding='utf-8') as handle:
                    return json.load(handle)
            except Exception as exc:
                logger.warning('读取分析文件失败: path=%s error=%s', analysis_path, exc)
    return None


def _extract_timestamp_from_dir(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    match = re.search(r'(\d{12})$', path.name)
    if match:
        return match.group(1)
    return None


def _create_download_package(task: Dict[str, Any]) -> io.BytesIO:
    if not report_generator:
        raise HTTPException(status_code=500, detail='报告生成器不可用')
    timestamp_dir = _resolve_timestamp_dir(task)
    if not timestamp_dir or not timestamp_dir.exists():
        raise HTTPException(status_code=404, detail='未找到评估结果目录')
    results = task.get('results') or {}
    files = results.get('files') or []
    file_names = [item.get('file_name') for item in files if item.get('file_name')]
    if not file_names:
        raise HTTPException(status_code=404, detail='该任务暂无可下载文件')
    llm_name = task.get('llm_name') or results.get('model_name') or 'evaluation'
    return report_generator.create_download_package(llm_name, file_names, timestamp_dir)


def _build_download_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task['task_id']
    timestamp_dir = _resolve_timestamp_dir(task)
    timestamp = _extract_timestamp_from_dir(timestamp_dir)
    display_timestamp = _format_timestamp_label(timestamp) if timestamp else None
    files_meta: List[Dict[str, Any]] = []
    results = task.get('results') or {}
    for file_entry in results.get('files', []) or []:
        file_name = file_entry.get('file_name')
        if not file_name:
            continue
        quoted = quote(file_name, safe='')
        files_meta.append({
            'file_name': file_name,
            'display_name': file_entry.get('source_file') or file_name,
            'formats': [
                {
                    'format': 'html',
                    'label': '评估表 (HTML)',
                    'url': f"/eval/downloads/{task_id}/file/{quoted}?format=html",
                },
                {
                    'format': 'json',
                    'label': '原始数据 (JSON)',
                    'url': f"/eval/downloads/{task_id}/file/{quoted}?format=json",
                },
            ],
        })
    return {
        'task_id': task_id,
        'files': files_meta,
        'package': {
            'label': '完整评估包 (ZIP)',
            'url': f"/eval/downloads/{task_id}/package",
        },
        'result_dir': str(timestamp_dir) if timestamp_dir else None,
        'timestamp': timestamp,
        'timestamp_display': display_timestamp,
    }


def _create_history_package(model_name: str, timestamp: str) -> io.BytesIO:
    if not report_generator:
        raise HTTPException(status_code=500, detail='报告生成器不可用')
    if not re.fullmatch(r'\d{12}', timestamp):
        raise HTTPException(status_code=400, detail='时间戳格式不正确')
    safe_model = os.path.basename(model_name)
    timestamp_dir = Path(LLM_EVAL_DATA_DIR) / f"{safe_model}{timestamp}"
    if not timestamp_dir.exists():
        raise HTTPException(status_code=404, detail='未找到指定的历史目录')
    file_names: List[str] = []
    for child in timestamp_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name in ('test_data', 'multi_file', '结果分析'):
            continue
        analysis_file = child / f"{child.name}_analysis.json"
        if analysis_file.exists():
            file_names.append(child.name)
    if not file_names:
        raise HTTPException(status_code=404, detail='历史目录中没有可用的分析文件')
    return report_generator.create_download_package(safe_model, file_names, timestamp_dir)


def _update_task(task_id: str, **fields):
    task = eval_task_storage.get(task_id)
    if not task:
        return
    task.update(fields)
    stage_label = fields.get('current_stage') or task.get('current_stage')
    progress_value = fields.get('progress', task.get('progress'))
    status_value = fields.get('status') or task.get('status')
    message_value = fields.get('message') or task.get('message')
    _update_stage_progress_for_task(task, stage_label, progress_value, message_value, status_value)

    # 更新细粒度进度信息
    if 'file_progress' in fields:
        task['file_progress'] = fields['file_progress']
    if 'step_progress' in fields:
        task['step_progress'] = fields['step_progress']
    if 'has_stage2' in fields:
        task['has_stage2'] = fields['has_stage2']

    eval_task_storage[task_id] = task


def _extract_stage1_rounds(stage1_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rounds = stage1_result.get('individual_results')
    if rounds and isinstance(rounds, list):
        return rounds
    return [stage1_result]


def _build_stage1_summary(stage1_result: Dict[str, Any]) -> Dict[str, Any]:
    rounds = []
    for idx, round_data in enumerate(_extract_stage1_rounds(stage1_result), start=1):
        rounds.append({
            'round_number': round_data.get('round_number', idx),
            'statistics': round_data.get('statistics', {}),
            'score_distribution': round_data.get('score_distribution', {}),
        })
    return {
        'statistics': stage1_result.get('statistics'),
        'aggregated_statistics': stage1_result.get('aggregated_statistics'),
        'evaluation_rounds': stage1_result.get('evaluation_rounds', 1),
        'thresholds': stage1_result.get('thresholds'),
        'score_distribution': stage1_result.get('score_distribution'),
        'rounds': rounds,
    }


def _get_retest_file_path(file_manager, model_name: str, file_name: str, round_number: int) -> str:
    input_name = 'stage1_to_stage2_data.csv' if round_number == 1 else f'stage1_to_stage2_data_round{round_number}.csv'
    return file_manager.get_file_path(model_name, file_name, input_name)


def _summarize_results(file_results: List[Dict[str, Any]], multi_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        'total_files': len(file_results),
        'total_questions': 0,
        'final_correct_answers': 0,
        'final_reasoning_errors': 0,
        'final_knowledge_deficiency': 0,
        'final_capability_insufficient': 0,
        'overall_accuracy_rate': 0.0,
        'files_with_stage2': 0,
        'multi_file_analysis': multi_analysis,
    }
    for entry in file_results:
        final_analysis = entry.get('final_analysis') or {}
        stats = final_analysis.get('statistics', {})
        summary['total_questions'] += stats.get('total_questions', 0)
        summary['final_correct_answers'] += final_analysis.get('final_correct_answers', 0)
        summary['final_reasoning_errors'] += final_analysis.get('final_reasoning_errors', 0)
        summary['final_knowledge_deficiency'] += final_analysis.get('final_knowledge_deficiency', 0)
        summary['final_capability_insufficient'] += final_analysis.get('final_capability_insufficient', 0)
        if any(round_item.get('stage2_executed') for round_item in entry.get('stage2_rounds', [])):
            summary['files_with_stage2'] += 1
    if summary['total_questions'] > 0:
        summary['overall_accuracy_rate'] = round(summary['final_correct_answers'] / summary['total_questions'] * 100, 2)
    return summary


def _summarize_stage2_only(file_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        'total_files': len(file_results),
        'total_questions': 0,
        'knowledge_deficiency': 0,
        'reasoning_errors': 0,
        'capability_insufficient': 0,
    }
    for entry in file_results:
        stats = entry.get('stage2_statistics') or {}
        summary['total_questions'] += stats.get('total_questions', 0)
        summary['knowledge_deficiency'] += stats.get('knowledge_deficiency', 0)
        summary['reasoning_errors'] += stats.get('reasoning_errors', 0)
        summary['capability_insufficient'] += stats.get('capability_insufficient', 0)
    return summary


def _ensure_imported():
    if not all([Stage1Evaluator, Stage2Evaluator, ResultProcessor, get_file_manager, reset_file_manager_for_new_test]):
        raise RuntimeError('LLM_EVAL模块加载失败，无法执行评估')


def _run_stage2_only(files: List[str], llm_name: str, config: Dict[str, Any], progress_cb) -> Dict[str, Any]:
    _ensure_imported()
    stage2_evaluator = Stage2Evaluator(model_name=llm_name, eval_model_name=config.get('eval_model_name', DEFAULT_EVAL_MODEL))
    file_results = []
    total_files = max(len(files), 1)
    for idx, file_path in enumerate(files, start=1):
        file_name = Path(file_path).name
        progress_cb('第二阶段评估', 5 + int(80 * idx / total_files), f'正在处理 {file_name}',
                   file_index=idx, file_name=file_name, current_step='stage2_infer')
        stage2_result = stage2_evaluator.run_complete_evaluation(
            file_paths=[file_path],
            num_evaluations=config.get('evaluation_rounds', 1),
            answer_threshold=config.get('stage2_answer_threshold', 60.0),
            reasoning_threshold=config.get('stage2_reasoning_threshold', 60.0)
        )
        file_results.append({
            'file_name': Path(file_path).stem,
            'source_file': file_path,
            'stage2_statistics': stage2_result.get('statistics', {}),
            'stage2_thresholds': stage2_result.get('thresholds', {}),
            'analysis': {
                'statistics': stage2_result.get('statistics', {}),
                'score_distribution': stage2_result.get('score_distribution', {}),
                'thresholds': stage2_result.get('thresholds', {}),
            }
        })
    progress_cb('结果处理', 92, '正在汇总结果', current_step='analysis')
    summary = _summarize_stage2_only(file_results)
    return {
        'model_name': llm_name,
        'evaluation_type': 'stage2',
        'files': file_results,
        'summary': summary,
        'artifacts': {},
    }


def _run_full_pipeline(files: List[str], llm_name: str, evaluation_type: str, config: Dict[str, Any], progress_cb, current_file_info: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_imported()
    stage1_evaluator = Stage1Evaluator(model_name=llm_name, eval_model_name=config.get('eval_model_name', DEFAULT_EVAL_MODEL))
    stage2_evaluator = Stage2Evaluator(model_name=llm_name, eval_model_name=config.get('eval_model_name', DEFAULT_EVAL_MODEL))
    processor = ResultProcessor()
    file_manager = get_file_manager()

    file_results: List[Dict[str, Any]] = []
    total_files = max(len(files), 1)
    stage1_weight = 55
    stage2_weight = 25 if evaluation_type in ('both', 'stage2') else 0
    result_weight = 15

    for idx, file_path in enumerate(files, start=1):
        file_name = Path(file_path).stem

        # 【重置】开始新文件时，重置当前文件的所有阶段进度
        current_file_info['file_stages'] = {
            'stage1': {'progress': 0, 'current_question': 0, 'total_questions': 0},
            'stage2': {'progress': 0, 'current_question': 0, 'total_questions': 0},
            'result': {'progress': 0, 'current_question': 0, 'total_questions': 0},
        }

        # 更新文件级进度 - Stage1 推理开始
        progress_cb('第一阶段评估', int(5 + stage1_weight * (idx - 1) / total_files), f'准备处理 {file_name}',
                   file_index=idx, file_name=file_name, current_step='stage1_infer')

        # 设置stage1评估器的进度回调
        def stage1_progress_callback(current, total, question_id, process_type='testing', current_round=1, total_rounds=1):
            # 判断是推理阶段还是评估阶段
            step = 'stage1_infer' if process_type == 'testing' else 'stage1_eval'
            step_percent = int((current / total) * 100) if total > 0 else 0

            # 将问题级进度传递给上层
            progress_cb(
                '第一阶段评估',
                int(5 + stage1_weight * ((idx - 1) + current / total) / total_files),
                f'{file_name} - 问题 {current}/{total}',
                file_index=idx,
                file_name=file_name,
                stage_key='stage1',
                current_question=current,
                total_questions=total,
                current_step=step,
                step_progress_percent=step_percent
            )

        stage1_evaluator.set_progress_callback(stage1_progress_callback)

        stage1_result = stage1_evaluator.run_complete_evaluation(
            file_paths=[file_path],
            num_evaluations=config.get('evaluation_rounds', 1),
            answer_threshold=config.get('stage1_answer_threshold', 60.0),
            reasoning_threshold=config.get('stage1_reasoning_threshold', 60.0)
        )

        stage2_rounds: List[Dict[str, Any]] = []
        round_entries = _extract_stage1_rounds(stage1_result)
        for round_index, round_data in enumerate(round_entries, start=1):
            stage2_result = None
            need_retest = round_data.get('statistics', {}).get('need_retest', 0)
            if evaluation_type in ('both', 'stage2') and need_retest > 0:
                try:
                    retest_path = _get_retest_file_path(file_manager, llm_name, file_name, round_index)
                    if os.path.exists(retest_path) and os.path.getsize(retest_path) > 0:
                        # 【重置】开始Stage2前，重置Stage2进度
                        current_file_info['file_stages']['stage2'] = {
                            'progress': 0, 'current_question': 0, 'total_questions': 0
                        }

                        progress_cb('第二阶段评估', int(5 + stage1_weight + stage2_weight * (idx - 1) / total_files),
                                   f'{file_name} 第{round_index}轮二次评估',
                                   file_index=idx, file_name=file_name, stage_key='stage2', current_step='stage2_infer')

                        # 设置stage2评估器的进度回调
                        def stage2_progress_callback(current, total, question_id, process_type='testing', current_round=1, total_rounds=1):
                            step = 'stage2_infer' if process_type == 'testing' else 'stage2_eval'
                            step_percent = int((current / total) * 100) if total > 0 else 0

                            progress_cb(
                                '第二阶段评估',
                                int(5 + stage1_weight + stage2_weight * ((idx - 1) + current / total) / total_files),
                                f'{file_name} - 第二阶段问题 {current}/{total}',
                                file_index=idx,
                                file_name=file_name,
                                stage_key='stage2',
                                current_question=current,
                                total_questions=total,
                                current_step=step,
                                step_progress_percent=step_percent
                            )

                        stage2_evaluator.set_progress_callback(stage2_progress_callback)

                        stage2_result = stage2_evaluator.run_complete_evaluation(
                            file_paths=[retest_path],
                            num_evaluations=1,
                            answer_threshold=config.get('stage2_answer_threshold', 60.0),
                            reasoning_threshold=config.get('stage2_reasoning_threshold', 60.0)
                        )
                except Exception as stage2_error:
                    logger.warning("Stage2评估失败: file=%s round=%s error=%s", file_name, round_index, stage2_error)
            processor.create_round_analysis(llm_name, file_name, round_index, round_data, stage2_result)
            stage2_rounds.append({
                'round_number': round_index,
                'stage1_statistics': round_data.get('statistics', {}),
                'stage2_statistics': stage2_result.get('statistics', {}) if stage2_result else None,
                'stage2_thresholds': stage2_result.get('thresholds', {}) if stage2_result else None,
                'need_retest': need_retest,
                'stage2_executed': stage2_result is not None,
            })

        # 【重置】开始结果处理前，重置result进度
        current_file_info['file_stages']['result'] = {'progress': 0}

        # 开始结果分析
        progress_cb('结果处理', int(5 + stage1_weight + stage2_weight + result_weight * (idx - 0.5) / total_files),
                   f'正在分析 {file_name} 的评估结果',
                   file_index=idx, file_name=file_name, stage_key='result',
                   current_step='analysis', step_progress_percent=0,
                   current_question=0, total_questions=0)
        final_analysis = processor.process_single_file_results(llm_name, file_name)

        # 结果分析完成
        progress_cb('结果处理', int(5 + stage1_weight + stage2_weight + result_weight * idx / total_files),
                   f'{file_name} - 结果分析完成',
                   file_index=idx, file_name=file_name, stage_key='result',
                   current_step='analysis', step_progress_percent=100,
                   current_question=0, total_questions=0)
        file_results.append({
            'file_name': file_name,
            'source_file': file_path,
            'stage1_summary': _build_stage1_summary(stage1_result),
            'stage2_rounds': stage2_rounds,
            'final_analysis': final_analysis,
        })

    multi_analysis = processor.process_multi_file_results(llm_name, enable_multi_file=len(file_results) > 1)
    summary = _summarize_results(file_results, multi_analysis)
    artifacts = {}
    if file_manager:
        timestamp_dir = file_manager.find_latest_timestamp_dir(llm_name)
        if timestamp_dir:
            artifacts['result_dir'] = str(timestamp_dir)

    return {
        'model_name': llm_name,
        'evaluation_type': evaluation_type,
        'files': file_results,
        'summary': summary,
        'artifacts': artifacts,
    }


def process_evaluation_task(task_id: str, files: List[str], eval_info: dict, config: dict):
    """后台任务：执行评估"""
    try:
        llm_name = eval_info.get('llm_name')
        evaluation_type = (eval_info.get('evaluation_type') or 'both').lower()
        if not files:
            raise ValueError('没有可评估的文件')
        for path in files:
            if not os.path.exists(path):
                raise FileNotFoundError(f'文件不存在: {path}')

        # 文件级别进度跟踪
        current_file_info = {
            'current_file_index': 0,
            'total_files': len(files),
            'current_file_name': '',
            'file_stages': {
                'stage1': {'progress': 0, 'current_question': 0, 'total_questions': 0},
                'stage2': {'progress': 0, 'current_question': 0, 'total_questions': 0},
                'result': {'progress': 0, 'current_question': 0, 'total_questions': 0},
            }
        }

        def progress_cb(stage: str, progress: int, message: str, file_index: int = None, file_name: str = None,
                       stage_key: str = None, current_question: int = None, total_questions: int = None,
                       current_step: str = None, step_progress_percent: int = None):
            # 更新文件信息
            if file_index is not None:
                current_file_info['current_file_index'] = file_index
            if file_name is not None:
                current_file_info['current_file_name'] = file_name

            # 更新单文件阶段进度
            if stage_key and stage_key in current_file_info['file_stages']:
                stage_info = current_file_info['file_stages'][stage_key]
                if current_question is not None:
                    stage_info['current_question'] = current_question
                if total_questions is not None:
                    stage_info['total_questions'] = total_questions
                # 根据问题进度计算阶段进度
                if total_questions and total_questions > 0:
                    stage_info['progress'] = int((current_question / total_questions) * 100)

            # 构建符合前端期望的 file_progress 结构（1-based索引）
            file_progress_payload = {
                'current_file': current_file_info.get('current_file_index', 0),  # 1-based
                'total_files': current_file_info.get('total_files', 0),
                'current_filename': current_file_info.get('current_file_name'),
                'file_stages': current_file_info.get('file_stages'),
            }

            # 构建 step_progress 结构
            step_progress_payload = None
            if current_step:
                step_progress_payload = {
                    'current_step': current_step,
                    'step_progress_percent': step_progress_percent if step_progress_percent is not None else 0,
                    'current_question': current_question,
                    'total_questions': total_questions,
                }

            # 计算 has_stage2
            has_stage2 = evaluation_type in ('both', 'stage2')

            _update_task(
                task_id,
                current_stage=stage,
                progress=min(int(progress), 100),
                message=message,
                file_progress=file_progress_payload,
                step_progress=step_progress_payload,
                has_stage2=has_stage2
            )

        # 初始化任务时设置初始进度信息
        initial_file_progress = {
            'current_file': 0,
            'total_files': len(files),
            'current_filename': None,
            'file_stages': {
                'stage1': {'progress': 0, 'current_question': 0, 'total_questions': 0},
                'stage2': {'progress': 0, 'current_question': 0, 'total_questions': 0},
                'result': {'progress': 0},
            }
        }
        initial_step_progress = {
            'current_step': 'stage1_infer',
            'step_progress_percent': 0,
            'current_question': 0,
            'total_questions': 0,
        }
        _update_task(
            task_id,
            status='processing',
            progress=5,
            current_stage='初始化',
            message='正在准备评估任务...',
            file_progress=initial_file_progress,
            step_progress=initial_step_progress,
            has_stage2=evaluation_type in ('both', 'stage2')
        )

        with EVAL_LOCK:
            with _llm_eval_workdir():
                reset_file_manager_for_new_test(llm_name)
                if evaluation_type == 'stage2' and config.get('stage2_only', False):
                    result_payload = _run_stage2_only(files, llm_name, config, progress_cb)
                elif evaluation_type == 'stage2' and not config.get('stage2_only'):
                    result_payload = _run_full_pipeline(files, llm_name, evaluation_type, config, progress_cb, current_file_info)
                else:
                    result_payload = _run_full_pipeline(files, llm_name, evaluation_type, config, progress_cb, current_file_info)

        result_payload = _sanitize_for_storage(result_payload)
        _update_task(
            task_id,
            status='completed',
            progress=100,
            current_stage='已完成',
            message='评估完成',
            completed_at=_serialize_datetime(datetime.utcnow()),
            results=result_payload,
        )
    except Exception as exc:
        logger.exception('评估任务失败: task=%s error=%s', task_id, exc)
        _update_task(
            task_id,
            status='failed',
            progress=0,
            current_stage='失败',
            message=f'评估失败: {exc}',
            completed_at=_serialize_datetime(datetime.utcnow()),
        )


@router.post('/upload')
async def upload_evaluation_files(files: List[UploadFile] = File(...)):
    """上传评估文件"""
    try:
        uploaded_files = []
        for file in files:
            file_id = str(uuid.uuid4())[:8]
            filename = f"{file_id}_{file.filename}"
            file_path = os.path.join(EVAL_UPLOAD_DIR, filename)
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append({
                'filename': file.filename,
                'file_path': file_path,
                'size': os.path.getsize(file_path),
            })
        return {
            'success': True,
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'文件上传失败: {exc}')


@router.get('/files')
async def list_server_files(llm_name: Optional[str] = None):
    """列出服务器端可用的评估文件"""
    uploads = _list_upload_cache()
    history = _collect_history_entries(llm_name)
    return {'uploads': uploads, 'history': history}


@router.get('/models')
async def get_available_models():
    """获取可用的测试模型和评估模型列表"""
    try:
        config_path = Path(LLM_EVAL_DIR) / 'config' / 'config.json'
        if not config_path.exists():
            return {
                'test_models': [],
                'eval_models': [],
                'default_test_model': None,
                'default_eval_model': DEFAULT_EVAL_MODEL,
            }
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 获取测试模型列表
        test_models = []
        for model_key, model_config in config.get('LLM_test', {}).items():
            if model_config.get('enabled', False):
                test_models.append({
                    'key': model_key,
                    'display_name': model_config.get('display_name', model_key),
                    'description': model_config.get('description', ''),
                    'model': model_config.get('model', ''),
                })
        
        # 获取评估模型列表
        eval_models = []
        for model_key, model_config in config.get('eval_llm', {}).items():
            if model_config.get('enabled', False):
                eval_models.append({
                    'key': model_key,
                    'display_name': model_config.get('display_name', model_key),
                    'description': model_config.get('description', ''),
                    'model': model_config.get('model', ''),
                })
        
        return {
            'test_models': test_models,
            'eval_models': eval_models,
            'default_test_model': config.get('default_model'),
            'default_eval_model': config.get('default_eval_model', DEFAULT_EVAL_MODEL),
        }
    except Exception as exc:
        logger.error('获取模型配置失败: %s', exc)
        raise HTTPException(status_code=500, detail=f'获取模型配置失败: {exc}')


@router.post('/create')
async def create_evaluation_task(
    background_tasks: BackgroundTasks,
    llm_name: str = Form(...),
    evaluation_type: str = Form('both'),
    description: Optional[str] = Form(None),
    file_paths: str = Form(...),
    stage1_answer_threshold: float = Form(60.0),
    stage1_reasoning_threshold: float = Form(60.0),
    stage2_answer_threshold: float = Form(60.0),
    stage2_reasoning_threshold: float = Form(60.0),
    evaluation_rounds: int = Form(1),
    eval_model_name: str = Form(DEFAULT_EVAL_MODEL),
):
    """创建评估任务"""
    try:
        files = json.loads(file_paths)
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            raise ValueError('file_paths 参数不合法')
        files = [os.path.abspath(path) for path in files]

        task_id = str(uuid.uuid4())
        now_iso = _serialize_datetime(datetime.utcnow())
        config = {
            'stage1_answer_threshold': stage1_answer_threshold,
            'stage1_reasoning_threshold': stage1_reasoning_threshold,
            'stage2_answer_threshold': stage2_answer_threshold,
            'stage2_reasoning_threshold': stage2_reasoning_threshold,
            'evaluation_rounds': evaluation_rounds,
            'eval_model_name': eval_model_name,
            'stage2_only': evaluation_type.lower() == 'stage2' and all(path.endswith('.csv') for path in files),
        }
        stage_progress = _build_initial_stage_progress(evaluation_type.lower(), config.get('stage2_only', False))
        eval_task_storage[task_id] = {
            'task_id': task_id,
            'status': 'pending',
            'progress': 0,
            'current_stage': '准备中',
            'message': '任务已创建，等待处理',
            'created_at': now_iso,
            'completed_at': None,
            'results': None,
            'llm_name': llm_name,
            'evaluation_type': evaluation_type.lower(),
            'description': description,
            'files': files,
            'config': config,
            'stage_progress': stage_progress,
        }
        background_tasks.add_task(
            process_evaluation_task,
            task_id,
            files,
            {'llm_name': llm_name, 'evaluation_type': evaluation_type.lower(), 'description': description},
            config,
        )
        return {
            'success': True,
            'message': '评估任务已创建',
            'task_id': task_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'创建任务失败: {exc}')


@router.get('/task/{task_id}')
async def get_evaluation_task(task_id: str):
    if task_id not in eval_task_storage:
        raise HTTPException(status_code=404, detail='任务不存在')
    task = eval_task_storage[task_id]
    return EvaluationTask(
        task_id=task['task_id'],
        status=task['status'],
        progress=task['progress'],
        current_stage=task['current_stage'],
        message=task['message'],
        created_at=_parse_datetime(task.get('created_at')),  # type: ignore[arg-type]
        completed_at=_parse_datetime(task.get('completed_at')),  # type: ignore[arg-type]
        results=task.get('results'),
        llm_name=task.get('llm_name'),
        evaluation_type=task.get('evaluation_type'),
        description=task.get('description'),
        config=task.get('config'),
        files=task.get('files'),
        stage_progress=task.get('stage_progress'),
        file_progress=task.get('file_progress'),
        step_progress=task.get('step_progress'),
        has_stage2=task.get('has_stage2'),
    )


@router.get('/tasks')
async def list_evaluation_tasks():
    tasks = []
    for item in eval_task_storage.values():
        tasks.append({
            'task_id': item['task_id'],
            'llm_name': item.get('llm_name'),
            'status': item.get('status'),
            'evaluation_type': item.get('evaluation_type'),
            'description': item.get('description'),
            'created_at': item.get('created_at'),
            'completed_at': item.get('completed_at'),
        })
    tasks.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return {'tasks': tasks}


@router.get('/results/{task_id}')
async def get_evaluation_results(task_id: str):
    if task_id not in eval_task_storage:
        raise HTTPException(status_code=404, detail='任务不存在')
    task = eval_task_storage[task_id]
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail='任务尚未完成')
    return {
        'success': True,
        'task_id': task_id,
        'llm_name': task.get('llm_name'),
        'evaluation_type': task.get('evaluation_type'),
        'description': task.get('description'),
        'created_at': task.get('created_at'),
        'completed_at': task.get('completed_at'),
        'config': task.get('config'),
        'files': task.get('files'),
        'results': task.get('results'),
        'stage_progress': task.get('stage_progress'),
    }


@router.get('/downloads/{task_id}')
async def get_download_links(task_id: str):
    """获取任务的可下载资源"""
    if task_id not in eval_task_storage:
        raise HTTPException(status_code=404, detail='任务不存在')
    task = eval_task_storage[task_id]
    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail='任务尚未完成')
    return _build_download_metadata(task)


@router.get('/downloads/{task_id}/file/{file_name}')
async def download_task_file(task_id: str, file_name: str, format: str = 'json'):
    if task_id not in eval_task_storage:
        raise HTTPException(status_code=404, detail='任务不存在')
    task = eval_task_storage[task_id]
    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail='任务尚未完成')
    safe_name = Path(file_name).name
    analysis_data = _load_analysis_payload(task, safe_name)
    if not analysis_data:
        raise HTTPException(status_code=404, detail='未找到分析数据')
    if format == 'json':
        content = json.dumps(analysis_data, ensure_ascii=False, indent=2)
        filename = f"{safe_name}_analysis.json"
        headers = {
            'Content-Disposition': f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}",
        }
        return Response(content=content, media_type='application/json', headers=headers)
    if format == 'html':
        if not html_report_generator:
            raise HTTPException(status_code=500, detail='HTML报告生成器不可用')
        html_content = html_report_generator.generate_report(analysis_data, task.get('config'))
        filename = f"{safe_name}_evaluation.html"
        headers = {
            'Content-Disposition': f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}",
        }
        return Response(content=html_content, media_type='text/html', headers=headers)
    raise HTTPException(status_code=400, detail='不支持的格式')


@router.get('/downloads/{task_id}/package')
async def download_task_package(task_id: str):
    if task_id not in eval_task_storage:
        raise HTTPException(status_code=404, detail='任务不存在')
    task = eval_task_storage[task_id]
    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail='任务尚未完成')
    buffer = _create_download_package(task)
    llm_name = task.get('llm_name') or 'evaluation'
    filename = f"{llm_name}_{task_id}.zip"
    headers = {
        'Content-Disposition': f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}",
    }
    return StreamingResponse(buffer, media_type='application/zip', headers=headers)


@router.get('/history/{model_name}/{timestamp}/package')
async def download_history_package(model_name: str, timestamp: str):
    buffer = _create_history_package(model_name, timestamp)
    filename = f"{model_name}_{timestamp}.zip"
    headers = {
        'Content-Disposition': f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}",
    }
    return StreamingResponse(buffer, media_type='application/zip', headers=headers)


@router.get('/stats')
async def get_evaluation_stats():
    total_tasks = len(eval_task_storage)
    completed = sum(1 for t in eval_task_storage.values() if t['status'] == 'completed')
    processing = sum(1 for t in eval_task_storage.values() if t['status'] == 'processing')
    failed = sum(1 for t in eval_task_storage.values() if t['status'] == 'failed')
    pending = sum(1 for t in eval_task_storage.values() if t['status'] == 'pending')
    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed,
        'processing_tasks': processing,
        'failed_tasks': failed,
        'pending_tasks': pending,
        'success_rate': (completed / total_tasks * 100) if total_tasks > 0 else 0,
    }


@router.get('/history')
async def list_history_runs(llm_name: Optional[str] = None):
    """列出历史评估目录"""
    history = _collect_history_entries(llm_name)
    return {'history': history}
