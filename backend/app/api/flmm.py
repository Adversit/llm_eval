"""
FLMM问卷平台API - 完整功能版本
支持：数据结构读取、项目创建、证明材料管理、高级分析
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
import os
import json
import shutil
from datetime import datetime
import pandas as pd
import subprocess
import socket

from app.models.flmm import (
    Questionnaire,
    QuestionnaireCreateRequest,
    QuestionnaireResponse,
    QuestionnaireAnalysis,
)
from app.utils.persistence import DataPersistence

# 导入FLMM数据解析器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.utils.flmm_parser import (
    get_flmm_questionnaire_structure,
    get_flmm_evaluation_structure,
    parse_question_content
)

# 导入00k的代码生成函数
OOK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "00k")
sys.path.insert(0, OOK_PATH)
try:
    from function.Admin_create_function_page import (
        generate_questionnaire_page_code,
        generate_evidence_page_code
    )
    CODEGEN_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入00k代码生成函数: {e}")
    CODEGEN_AVAILABLE = False

router = APIRouter()

# 项目数据目录 - 统一存储位置
# 获取项目根目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "flmm")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 端口配置文件
PORT_CONFIG_FILE = os.path.join(DATA_DIR, ".port_config.json")

# ========== Streamlit自动启动辅助函数 ==========

def find_available_port(start_port=8502, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def load_port_config():
    """加载端口配置"""
    if os.path.exists(PORT_CONFIG_FILE):
        try:
            with open(PORT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_port_config(config):
    """保存端口配置"""
    os.makedirs(os.path.dirname(PORT_CONFIG_FILE), exist_ok=True)
    with open(PORT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def start_streamlit_app(project_path, py_filename, port):
    """后台启动Streamlit应用"""
    try:
        script_path = os.path.join(project_path, py_filename)

        # 确定streamlit可执行文件路径
        # 优先使用conda环境中的streamlit
        streamlit_cmd = "D:/Anaconda3/envs/damoxingeval/Scripts/streamlit.exe"
        if not os.path.exists(streamlit_cmd):
            # 如果conda环境不存在，使用系统streamlit
            streamlit_cmd = "streamlit"

        print(f"[Streamlit] 启动参数:")
        print(f"  - 命令: {streamlit_cmd}")
        print(f"  - 脚本: {script_path}")
        print(f"  - 端口: {port}")
        print(f"  - 工作目录: {project_path}")

        # 创建日志文件路径
        log_dir = os.path.join(project_path, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"streamlit_{port}.log")

        # Windows下需要特殊处理
        import sys
        if sys.platform == 'win32':
            # Windows下使用CREATE_NEW_PROCESS_GROUP避免继承父进程
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008

            # 打开日志文件用于输出
            with open(log_file, 'w', encoding='utf-8') as log_f:
                process = subprocess.Popen(
                    [
                        streamlit_cmd, "run", script_path,
                        "--server.port", str(port),
                        "--server.headless", "true",
                        "--server.address", "localhost"
                    ],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,  # 将stderr也重定向到同一个文件
                    cwd=project_path,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    close_fds=True  # 关闭所有文件描述符
                )
        else:
            # Linux/Mac
            with open(log_file, 'w', encoding='utf-8') as log_f:
                process = subprocess.Popen(
                    [
                        streamlit_cmd, "run", script_path,
                        "--server.port", str(port),
                        "--server.headless", "true",
                        "--server.address", "localhost"
                    ],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=project_path,
                    preexec_fn=os.setpgrp if hasattr(os, 'setpgrp') else None  # Unix下创建新进程组
                )

        print(f"[Streamlit] 进程已启动，PID: {process.pid}")
        print(f"[Streamlit] 日志文件: {log_file}")

        # 等待一小会儿，确保进程启动
        import time
        time.sleep(2)

        # 检查进程是否还在运行
        if process.poll() is not None:
            # 进程已退出，读取日志文件
            print(f"[Streamlit] 启动失败！")
            print(f"  - 退出码: {process.returncode}")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    print(f"  - 日志内容:\n{log_content}")
            except:
                pass
            return None

        print(f"[Streamlit] 启动成功！")
        return process.pid
    except Exception as e:
        print(f"启动Streamlit失败: {e}")
        import traceback
        traceback.print_exc()
        import traceback
        traceback.print_exc()
        return None

# 数据存储 - 使用持久化
questionnaire_storage = DataPersistence(DATA_DIR, 'questionnaires.json')
response_storage = DataPersistence(DATA_DIR, 'responses.json')
project_storage = DataPersistence(DATA_DIR, 'projects.json')


# ========== 新增数据模型 ==========

class FunctionModule(BaseModel):
    """功能模块"""
    name: str
    description: str


class ProjectCreateRequest(BaseModel):
    """项目创建请求"""
    company_name: str
    scenario_name: str
    scenario_description: str
    functions_list: List[FunctionModule]
    selected_questionnaire_items: List[Dict[str, Any]]  # 选中的问卷能力项
    selected_evidence_items: Optional[List[Dict[str, Any]]] = []  # 选中的证明材料项
    enable_questionnaire: bool = True
    enable_evidence: bool = False
    auto_generate_account: bool = True
    username: Optional[str] = None
    password: Optional[str] = None


class ProjectInfo(BaseModel):
    """项目信息"""
    project_id: str
    company_name: str
    scenario_name: str
    created_time: str
    status: str
    questionnaire_enabled: bool
    evidence_enabled: bool


# ========== 数据结构API ==========

@router.get("/structure/questionnaire")
async def get_questionnaire_structure():
    """
    获取FLMM调研表数据结构
    返回四层级嵌套结构：能力域 -> 能力子域1 -> 能力子域2 -> 能力项 -> 问题列表
    """
    try:
        structure = get_flmm_questionnaire_structure()

        if not structure:
            raise HTTPException(status_code=404, detail="未找到FLMM调研表数据文件")

        # 计算统计信息
        total_domains = len(structure)
        total_items = 0
        total_questions = 0

        for domain, subdomain1s in structure.items():
            for subdomain1, subdomain2s in subdomain1s.items():
                for subdomain2, items in subdomain2s.items():
                    total_items += len(items)
                    for item, questions in items.items():
                        total_questions += len(questions)

        return {
            'success': True,
            'structure': structure,
            'stats': {
                'total_domains': total_domains,
                'total_items': total_items,
                'total_questions': total_questions
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取问卷结构失败: {str(e)}")


@router.get("/structure/evidence")
async def get_evidence_structure():
    """
    获取FLMM自评表数据结构（用于证明材料收集）
    返回四层级嵌套结构：能力域 -> 能力子域1 -> 能力子域2 -> 能力项列表
    """
    try:
        structure = get_flmm_evaluation_structure()

        if not structure:
            raise HTTPException(status_code=404, detail="未找到FLMM自评表数据文件")

        # 计算统计信息
        total_domains = len(structure)
        total_items = 0

        for domain, subdomain1s in structure.items():
            for subdomain1, subdomain2s in subdomain1s.items():
                for subdomain2, items in subdomain2s.items():
                    total_items += len(items)

        return {
            'success': True,
            'structure': structure,
            'stats': {
                'total_domains': total_domains,
                'total_items': total_items
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取证明材料结构失败: {str(e)}")


# ========== 项目管理API ==========

@router.post("/project/create")
async def create_project(request: ProjectCreateRequest):
    """
    创建FLMM评估项目
    生成项目文件夹、问卷Excel、账号信息等
    """
    try:
        project_id = str(uuid.uuid4())[:8]
        folder_name = f"{request.company_name}_{request.scenario_name}"
        project_path = os.path.join(PROJECTS_DIR, folder_name)

        # 创建项目文件夹
        os.makedirs(project_path, exist_ok=True)

        # 生成账号信息
        if request.auto_generate_account:
            username = f"user_{request.company_name[:4]}_{project_id}"
            password = str(uuid.uuid4())[:12]
        else:
            username = request.username
            password = request.password

        # 创建项目信息JSON
        project_info = {
            "evaluation_info": {
                "project_id": project_id,
                "company_name": request.company_name,
                "scenario_name": request.scenario_name,
                "scenario_description": request.scenario_description,
                "functions_list": [f.dict() for f in request.functions_list],
                "created_time": datetime.now().isoformat(),
                "status": "待评估",
                "questionnaire_enabled": request.enable_questionnaire,
                "evidence_enabled": request.enable_evidence,
                "questionnaire_items_count": len(request.selected_questionnaire_items),
                "evidence_items_count": len(request.selected_evidence_items) if request.selected_evidence_items else 0
            },
            "account_info": {
                "username": username,
                "password": password,
                "company_name": request.company_name,
                "scenario_name": request.scenario_name,
                "created_time": datetime.now().isoformat(),
                "status": "激活"
            }
        }

        json_filename = f"{request.company_name}_{request.scenario_name}.json"
        with open(os.path.join(project_path, json_filename), "w", encoding="utf-8") as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)

        # 生成问卷Excel文件和Python采集页面
        generated_files = [json_filename]
        if request.enable_questionnaire and request.selected_questionnaire_items:
            # 生成Excel问卷
            excel_filename = generate_questionnaire_excel(
                project_path,
                request.company_name,
                request.scenario_name,
                request.selected_questionnaire_items,
                request.functions_list
            )
            generated_files.append(excel_filename)

            # 生成问卷采集Python页面
            if CODEGEN_AVAILABLE:
                py_filename = f"{request.company_name}_{request.scenario_name}.py"
                questionnaire_page_code = generate_questionnaire_page_code(
                    request.company_name,
                    request.scenario_name,
                    excel_filename,
                    json_filename
                )
                with open(os.path.join(project_path, py_filename), "w", encoding="utf-8") as f:
                    f.write(questionnaire_page_code)
                generated_files.append(py_filename)

        # 创建证明材料文件夹和Python上传页面
        if request.enable_evidence and request.selected_evidence_items:
            evidence_folder = os.path.join(project_path, "证明材料")
            os.makedirs(evidence_folder, exist_ok=True)

            for item_info in request.selected_evidence_items:
                item_folder = os.path.join(evidence_folder, item_info['item'])
                os.makedirs(item_folder, exist_ok=True)

            generated_files.append("证明材料/")

            # 生成证明材料上传Python页面
            if CODEGEN_AVAILABLE:
                evidence_py_filename = f"{request.company_name}_{request.scenario_name}_证明材料.py"
                evidence_page_code = generate_evidence_page_code(
                    request.company_name,
                    request.scenario_name,
                    json_filename,
                    {'selected_items_info': request.selected_evidence_items}
                )
                with open(os.path.join(project_path, evidence_py_filename), "w", encoding="utf-8") as f:
                    f.write(evidence_page_code)
                generated_files.append(evidence_py_filename)

        # ========== 不再自动启动Streamlit服务 ==========
        # 改为按需启动：前端点击"启动问卷"按钮时才启动
        questionnaire_url = None
        evidence_url = None

        # 保存到内存存储
        project_storage[project_id] = {
            'project_id': project_id,
            'folder_name': folder_name,
            'project_path': project_path,
            **project_info['evaluation_info']
        }

        return {
            'success': True,
            'message': '项目创建成功',
            'project_id': project_id,
            'folder_name': folder_name,
            'generated_files': generated_files,
            'account': {
                'username': username,
                'password': password,
                'login_url': questionnaire_url or '待部署',
                'evidence_url': evidence_url
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"项目创建失败: {str(e)}")


def generate_questionnaire_excel(
    project_path: str,
    company_name: str,
    scenario_name: str,
    selected_items: List[Dict],
    functions_list: List[FunctionModule]
) -> str:
    """生成问卷Excel文件"""
    excel_filename = f"{company_name}_{scenario_name}_问卷.xlsx"
    excel_data = []

    for item_info in selected_items:
        for question in item_info.get('questions', []):
            # 解析问题内容和选项
            question_stem, options = parse_question_content(question, scenario_name)

            if question_stem:
                # 检查是否包含{function1}占位符
                if "{function1}" in question_stem and functions_list:
                    # 为每个功能生成对应的问题
                    for func in functions_list:
                        function_question = question_stem.replace("{function1}", func.name)
                        options_str = '|'.join(options) if options else '完全不符合|基本不符合|部分符合|基本符合|完全符合'

                        excel_data.append({
                            '能力域': item_info['domain'],
                            '能力子域1': item_info['subdomain1'],
                            '能力子域2': item_info.get('subdomain2', ''),
                            '能力项': item_info['item'],
                            '问题主干': function_question,
                            '答案选项': options_str,
                            '被评估方回答': '',
                            '备注': f"针对功能：{func.name}"
                        })
                else:
                    # 普通问题，直接添加
                    options_str = '|'.join(options) if options else '完全不符合|基本不符合|部分符合|基本符合|完全符合'
                    excel_data.append({
                        '能力域': item_info['domain'],
                        '能力子域1': item_info['subdomain1'],
                        '能力子域2': item_info.get('subdomain2', ''),
                        '能力项': item_info['item'],
                        '问题主干': question_stem,
                        '答案选项': options_str,
                        '被评估方回答': '',
                        '备注': ''
                    })

    # 保存Excel
    df = pd.DataFrame(excel_data)
    excel_path = os.path.join(project_path, excel_filename)
    df.to_excel(excel_path, index=False, engine='openpyxl')

    return excel_filename


@router.get("/projects")
async def list_projects():
    """获取所有评估项目列表"""
    try:
        projects = []

        # 扫描项目目录
        if os.path.exists(PROJECTS_DIR):
            for item in os.listdir(PROJECTS_DIR):
                item_path = os.path.join(PROJECTS_DIR, item)
                if os.path.isdir(item_path):
                    # 查找项目信息JSON文件
                    json_files = [f for f in os.listdir(item_path)
                                if f.endswith('.json') and not f.endswith('_评估结果.json')
                                and not f.endswith('_证明材料上传记录.json')]

                    if json_files:
                        try:
                            with open(os.path.join(item_path, json_files[0]), 'r', encoding='utf-8') as f:
                                project_info = json.load(f)
                                eval_info = project_info.get('evaluation_info', {})

                                # 检查是否有Python文件
                                py_files = [f for f in os.listdir(item_path)
                                          if f.endswith('.py') and not f.endswith('_证明材料.py')]
                                has_questionnaire_file = len(py_files) > 0

                                evidence_files = [f for f in os.listdir(item_path)
                                                if f.endswith('_证明材料.py')]
                                has_evidence_file = len(evidence_files) > 0

                                projects.append({
                                    'folder_name': item,
                                    'project_id': eval_info.get('project_id', ''),
                                    'company_name': eval_info.get('company_name', ''),
                                    'scenario_name': eval_info.get('scenario_name', ''),
                                    'created_time': eval_info.get('created_time', ''),
                                    'status': eval_info.get('status', ''),
                                    'questionnaire_enabled': eval_info.get('questionnaire_enabled', False),
                                    'evidence_enabled': eval_info.get('evidence_enabled', False),
                                    'has_questionnaire_file': has_questionnaire_file,
                                    'has_evidence_file': has_evidence_file
                                })
                        except:
                            continue

        return {
            'success': True,
            'projects': projects,
            'total': len(projects)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """获取项目详情"""
    if project_id in project_storage:
        return {
            'success': True,
            'project': project_storage[project_id]
        }

    raise HTTPException(status_code=404, detail="项目不存在")


@router.get("/project/{project_folder}/details")
async def get_project_details(project_folder: str):
    """
    获取项目完整详情（包含账号密码）
    从项目JSON文件中读取
    """
    try:
        project_path = os.path.join(PROJECTS_DIR, project_folder)

        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail="项目不存在")

        # 查找项目JSON文件
        json_files = [f for f in os.listdir(project_path)
                     if f.endswith('.json') and not f.endswith('_评估结果.json')
                     and not f.endswith('_证明材料上传记录.json')]

        if not json_files:
            raise HTTPException(status_code=404, detail="项目配置文件不存在")

        # 读取JSON文件
        json_path = os.path.join(project_path, json_files[0])
        with open(json_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)

        return project_info

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


# ========== 证明材料上传API ==========

@router.post("/evidence/upload")
async def upload_evidence_files(
    project_folder: str = Form(...),
    capability_item: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    上传证明材料文件
    """
    try:
        project_path = os.path.join(PROJECTS_DIR, project_folder)
        evidence_folder = os.path.join(project_path, "证明材料", capability_item)

        # 确保目录存在
        os.makedirs(evidence_folder, exist_ok=True)

        uploaded_files = []
        for file in files:
            file_path = os.path.join(evidence_folder, file.filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({
                'filename': file.filename,
                'size': os.path.getsize(file_path)
            })

        # 保存上传记录
        record = {
            "capability_item": capability_item,
            "file_names": [f['filename'] for f in uploaded_files],
            "upload_time": datetime.now().isoformat(),
            "upload_id": str(uuid.uuid4())[:8]
        }

        record_file = os.path.join(project_path, f"{project_folder}_证明材料上传记录.json")
        records = []
        if os.path.exists(record_file):
            with open(record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
                if not isinstance(records, list):
                    records = [records]

        records.append(record)

        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        return {
            'success': True,
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


# ========== 保留原有基础API ==========

@router.post("/questionnaire")
async def create_questionnaire(request: QuestionnaireCreateRequest):
    """创建问卷（基础功能）"""
    try:
        questionnaire_id = str(uuid.uuid4())
        questionnaire = Questionnaire(
            questionnaire_id=questionnaire_id,
            title=request.title,
            description=request.description,
            questions=request.questions,
            created_at=datetime.now(),
            status='draft',
        )
        questionnaire_storage[questionnaire_id] = questionnaire.dict()

        return {
            'success': True,
            'message': '问卷创建成功',
            'questionnaire_id': questionnaire_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'创建问卷失败: {str(e)}')


@router.get("/questionnaire/{questionnaire_id}")
async def get_questionnaire(questionnaire_id: str):
    """获取问卷详情"""
    if questionnaire_id not in questionnaire_storage:
        raise HTTPException(status_code=404, detail='问卷不存在')
    return questionnaire_storage[questionnaire_id]


@router.get("/questionnaires")
async def list_questionnaires():
    """获取所有问卷列表"""
    return {
        'success': True,
        'questionnaires': list(questionnaire_storage.values()),
    }


@router.post("/response")
async def submit_response(response: QuestionnaireResponse):
    """提交问卷回答"""
    try:
        if response.questionnaire_id not in questionnaire_storage:
            raise HTTPException(status_code=404, detail='问卷不存在')

        response_id = str(uuid.uuid4())
        response_data = response.dict()
        response_data['response_id'] = response_id

        # 获取该问卷的所有回复
        responses = response_storage.get(response.questionnaire_id, [])
        responses.append(response_data)
        response_storage[response.questionnaire_id] = responses

        return {
            'success': True,
            'message': '提交成功',
            'response_id': response_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'提交失败: {str(e)}')


@router.get("/stats")
async def get_flmm_stats():
    """获取FLMM平台统计信息"""
    total_questionnaires = len(questionnaire_storage)
    total_responses = sum(len(responses) for responses in response_storage.values())
    published = sum(1 for q in questionnaire_storage.values() if q['status'] == 'published')

    return {
        'total_questionnaires': total_questionnaires,
        'total_responses': total_responses,
        'published_questionnaires': published,
        'total_projects': len(project_storage),
        'avg_responses_per_questionnaire': (
            total_responses / total_questionnaires if total_questionnaires > 0 else 0
        ),
    }


# ========== 高级分析API（调用00k中的分析函数）==========

# 导入分析工具
from app.utils.flmm_analyzer import (
    get_projects_list,
    get_basic_statistics,
    analyze_project_questions,
    calculate_five_ratings
)


@router.get("/analysis/projects")
async def get_analysis_projects():
    """
    获取所有可分析的FLMM评估项目
    调用00k中的get_available_projects函数
    """
    try:
        projects = get_projects_list()
        return {
            'success': True,
            'projects': projects,
            'total': len(projects)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/analysis/project/{project_folder}/statistics")
async def get_project_statistics(project_folder: str):
    """
    获取项目的基本统计信息
    调用00k中的generate_overall_statistics函数
    """
    try:
        stats = get_basic_statistics(project_folder)

        if stats is None:
            raise HTTPException(status_code=404, detail="项目数据不存在或加载失败")

        return {
            'success': True,
            'statistics': stats
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/analysis/project/{project_folder}/questions")
async def get_project_question_analysis(project_folder: str):
    """
    获取项目的逐题分析结果
    调用00k中的分析函数
    """
    try:
        questions = analyze_project_questions(project_folder)

        if questions is None:
            raise HTTPException(status_code=404, detail="项目数据不存在或加载失败")

        return {
            'success': True,
            'questions': questions,
            'total': len(questions)
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取问题分析失败: {str(e)}")


@router.get("/analysis/project/{project_folder}/ratings")
async def get_project_ratings(project_folder: str):
    """
    获取项目的5个维度评级
    调用00k中的评级计算函数
    """
    try:
        ratings = calculate_five_ratings(project_folder)

        if ratings is None:
            raise HTTPException(status_code=404, detail="项目数据不存在或评级计算失败")

        return {
            'success': True,
            'ratings': ratings
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取评级失败: {str(e)}")


# ========== 按需启动Streamlit服务 ==========

@router.post("/project/{folder_name}/launch-questionnaire")
async def launch_questionnaire_service(folder_name: str):
    """
    按需启动问卷采集Streamlit服务
    前端点击"启动问卷"时调用此接口
    """
    try:
        project_path = os.path.join(PROJECTS_DIR, folder_name)
        print(f"[Questionnaire] 请求启动项目: {folder_name}")
        print(f"[Questionnaire] 项目路径: {project_path}")
        
        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail="项目不存在")

        # 查找Python文件
        py_files = [f for f in os.listdir(project_path)
                   if f.endswith('.py') and not f.endswith('_证明材料.py')]

        if not py_files:
            raise HTTPException(status_code=404, detail="问卷采集文件不存在")

        py_filename = py_files[0]
        print(f"[Questionnaire] 找到问卷文件: {py_filename}")
        
        port_config = load_port_config()
        service_key = f"{folder_name}_questionnaire"

        # 检查是否已经在运行
        if service_key in port_config:
            existing_port = port_config[service_key]["port"]
            existing_pid = port_config[service_key]["pid"]

            # 检查进程是否还存在且是Streamlit进程
            try:
                import psutil
                if psutil.pid_exists(existing_pid):
                    process = psutil.Process(existing_pid)
                    process_name = process.name().lower()
                    # 检查是否是Python/Streamlit进程
                    if 'python' in process_name or 'streamlit' in process_name:
                        print(f"[Questionnaire] 服务已在运行 - PID: {existing_pid}, Port: {existing_port}")
                        return {
                            'success': True,
                            'message': '服务已在运行',
                            'url': f"http://localhost:{existing_port}",
                            'pid': existing_pid
                        }
                    else:
                        # PID被其他进程占用，清理配置
                        print(f"[Questionnaire] PID {existing_pid} 已被其他进程占用 ({process_name})，清理配置")
                        del port_config[service_key]
                        save_port_config(port_config)
                else:
                    # 进程不存在，清理配置
                    print(f"[Questionnaire] 进程 {existing_pid} 已不存在，清理配置")
                    del port_config[service_key]
                    save_port_config(port_config)
            except Exception as e:
                print(f"[Questionnaire] 检查进程失败: {e}")
                # 清理无效配置
                del port_config[service_key]
                save_port_config(port_config)

        # 查找可用端口并启动
        port = find_available_port()
        if not port:
            raise HTTPException(status_code=500, detail="没有可用端口（8502-8601都被占用）")

        print(f"[Questionnaire] 找到可用端口: {port}")
        pid = start_streamlit_app(project_path, py_filename, port)
        if not pid:
            raise HTTPException(status_code=500, detail="启动Streamlit失败，请查看后端日志")

        # 保存端口配置
        port_config[service_key] = {
            "port": port,
            "pid": pid,
            "file": py_filename,
            "type": "questionnaire",
            "folder_name": folder_name,
            "start_time": datetime.now().isoformat()
        }
        save_port_config(port_config)

        print(f"[Questionnaire] 启动成功 - PID: {pid}, Port: {port}")
        return {
            'success': True,
            'message': '问卷服务已启动',
            'url': f"http://localhost:{port}",
            'pid': pid
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/project/{folder_name}/launch-evidence")
async def launch_evidence_service(folder_name: str):
    """
    按需启动证明材料上传Streamlit服务
    """
    try:
        project_path = os.path.join(PROJECTS_DIR, folder_name)
        print(f"[Evidence] 请求启动项目: {folder_name}")
        print(f"[Evidence] 项目路径: {project_path}")
        
        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail="项目不存在")

        # 查找证明材料Python文件
        py_files = [f for f in os.listdir(project_path)
                   if f.endswith('_证明材料.py')]

        if not py_files:
            raise HTTPException(status_code=404, detail="证明材料上传文件不存在")

        py_filename = py_files[0]
        print(f"[Evidence] 找到证明材料文件: {py_filename}")
        
        port_config = load_port_config()
        service_key = f"{folder_name}_evidence"

        # 检查是否已经在运行
        if service_key in port_config:
            existing_port = port_config[service_key]["port"]
            existing_pid = port_config[service_key]["pid"]

            try:
                import psutil
                if psutil.pid_exists(existing_pid):
                    process = psutil.Process(existing_pid)
                    process_name = process.name().lower()
                    # 检查是否是Python/Streamlit进程
                    if 'python' in process_name or 'streamlit' in process_name:
                        print(f"[Evidence] 服务已在运行 - PID: {existing_pid}, Port: {existing_port}")
                        return {
                            'success': True,
                            'message': '服务已在运行',
                            'url': f"http://localhost:{existing_port}",
                            'pid': existing_pid
                        }
                    else:
                        # PID被其他进程占用，清理配置
                        print(f"[Evidence] PID {existing_pid} 已被其他进程占用 ({process_name})，清理配置")
                        del port_config[service_key]
                        save_port_config(port_config)
                else:
                    # 进程不存在，清理配置
                    print(f"[Evidence] 进程 {existing_pid} 已不存在，清理配置")
                    del port_config[service_key]
                    save_port_config(port_config)
            except Exception as e:
                print(f"[Evidence] 检查进程失败: {e}")
                # 清理无效配置
                del port_config[service_key]
                save_port_config(port_config)

        # 查找可用端口并启动
        port = find_available_port()
        if not port:
            raise HTTPException(status_code=500, detail="没有可用端口（8502-8601都被占用）")

        print(f"[Evidence] 找到可用端口: {port}")
        pid = start_streamlit_app(project_path, py_filename, port)
        if not pid:
            raise HTTPException(status_code=500, detail="启动Streamlit失败，请查看后端日志")

        # 保存端口配置
        port_config[service_key] = {
            "port": port,
            "pid": pid,
            "file": py_filename,
            "type": "evidence",
            "folder_name": folder_name,
            "start_time": datetime.now().isoformat()
        }
        save_port_config(port_config)

        print(f"[Evidence] 启动成功 - PID: {pid}, Port: {port}")
        return {
            'success': True,
            'message': '证明材料服务已启动',
            'url': f"http://localhost:{port}",
            'pid': pid
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/project/{folder_name}/stop/{service_type}")
async def stop_streamlit_service(folder_name: str, service_type: str):
    """
    停止Streamlit服务
    service_type: questionnaire 或 evidence
    """
    try:
        port_config = load_port_config()
        service_key = f"{folder_name}_{service_type}"

        if service_key not in port_config:
            raise HTTPException(status_code=404, detail="服务不存在或未启动")

        pid = port_config[service_key]["pid"]

        # 停止进程
        try:
            import psutil
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)  # 等待最多5秒
        except psutil.NoSuchProcess:
            pass  # 进程已经不存在
        except Exception as e:
            # 强制kill
            try:
                import signal
                os.kill(pid, signal.SIGTERM)
            except:
                pass

        # 从配置中删除
        del port_config[service_key]
        save_port_config(port_config)

        return {
            'success': True,
            'message': f'{service_type}服务已停止'
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")


@router.post("/services/cleanup")
async def cleanup_dead_services():
    """
    清理所有已死亡的服务进程配置
    """
    try:
        port_config = load_port_config()
        cleaned = []
        
        import psutil
        for service_key, service_info in list(port_config.items()):
            pid = service_info.get("pid")
            should_clean = False
            reason = ""
            
            if not pid:
                should_clean = True
                reason = "无PID"
            elif not psutil.pid_exists(pid):
                should_clean = True
                reason = "进程不存在"
            else:
                # 检查进程名称
                try:
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    if 'python' not in process_name and 'streamlit' not in process_name:
                        should_clean = True
                        reason = f"PID被其他进程占用 ({process_name})"
                except:
                    should_clean = True
                    reason = "无法访问进程"
            
            if should_clean:
                cleaned.append({
                    "service": service_key,
                    "pid": pid,
                    "port": service_info.get("port"),
                    "reason": reason
                })
                del port_config[service_key]
        
        save_port_config(port_config)
        
        return {
            'success': True,
            'message': f'清理了 {len(cleaned)} 个僵尸服务',
            'cleaned': cleaned
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/services/list")
async def list_running_services():
    """
    列出所有正在运行的服务
    """
    try:
        port_config = load_port_config()
        services = []
        
        import psutil
        for service_key, service_info in port_config.items():
            pid = service_info.get("pid")
            is_running = False
            process_name = None
            
            if pid and psutil.pid_exists(pid):
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    # 只有Python/Streamlit进程才算运行中
                    if 'python' in process_name.lower() or 'streamlit' in process_name.lower():
                        is_running = True
                except:
                    pass
            
            services.append({
                "service_key": service_key,
                "folder_name": service_info.get("folder_name"),
                "type": service_info.get("type"),
                "port": service_info.get("port"),
                "pid": pid,
                "is_running": is_running,
                "process_name": process_name,
                "start_time": service_info.get("start_time"),
                "file": service_info.get("file")
            })
        
        return {
            'success': True,
            'services': services,
            'total': len(services)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取服务列表失败: {str(e)}")
