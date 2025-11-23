"""
文件上传API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Set
import os
import shutil
from pathlib import Path

router = APIRouter()

# 数据持久化目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'data', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型（文件扩展名）
ALLOWED_EXTENSIONS: Set[str] = {
    # 文档类型
    '.txt', '.md', '.pdf', '.doc', '.docx',
    # 表格类型
    '.xls', '.xlsx', '.csv',
    # 数据类型
    '.json', '.xml', '.yaml', '.yml',
    # 图片类型
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    # 压缩包类型
    '.zip', '.rar', '.7z', '.tar', '.gz',
}

def validate_file_type(filename: str) -> bool:
    """
    验证文件类型是否允许

    Args:
        filename: 文件名

    Returns:
        bool: 是否允许上传
    """
    file_ext = Path(filename).suffix.lower()
    return file_ext in ALLOWED_EXTENSIONS

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower()

@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文件

    支持的文件类型：
    - 文档：.txt, .md, .pdf, .doc, .docx
    - 表格：.xls, .xlsx, .csv
    - 数据：.json, .xml, .yaml, .yml
    - 图片：.jpg, .jpeg, .png, .gif, .bmp, .svg, .webp
    - 压缩包：.zip, .rar, .7z, .tar, .gz
    """
    try:
        # 验证文件类型
        if not validate_file_type(file.filename):
            file_ext = get_file_extension(file.filename)
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。允许的文件类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "success": True,
            "message": "文件上传成功",
            "filename": file.filename,
            "file_path": file_path,
            "file_type": get_file_extension(file.filename)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/files")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    上传多个文件

    支持的文件类型：
    - 文档：.txt, .md, .pdf, .doc, .docx
    - 表格：.xls, .xlsx, .csv
    - 数据：.json, .xml, .yaml, .yml
    - 图片：.jpg, .jpeg, .png, .gif, .bmp, .svg, .webp
    - 压缩包：.zip, .rar, .7z, .tar, .gz
    """
    uploaded_files = []
    failed_files = []

    for file in files:
        try:
            # 验证文件类型
            if not validate_file_type(file.filename):
                file_ext = get_file_extension(file.filename)
                failed_files.append({
                    'filename': file.filename,
                    'reason': f'不支持的文件类型: {file_ext}'
                })
                continue

            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({
                'filename': file.filename,
                'file_path': file_path,
                'file_type': get_file_extension(file.filename)
            })
        except Exception as e:
            failed_files.append({
                'filename': file.filename,
                'reason': str(e)
            })

    # 如果所有文件都失败了
    if not uploaded_files and failed_files:
        raise HTTPException(
            status_code=400,
            detail=f"所有文件上传失败。失败详情: {failed_files}"
        )

    return {
        "success": True,
        "message": f"成功上传 {len(uploaded_files)} 个文件" + (f"，{len(failed_files)} 个文件失败" if failed_files else ""),
        "uploaded_files": uploaded_files,
        "failed_files": failed_files if failed_files else []
    }


@router.get("/allowed-types")
async def get_allowed_file_types():
    """
    获取允许的文件类型列表
    """
    return {
        "success": True,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "categories": {
            "文档": ['.txt', '.md', '.pdf', '.doc', '.docx'],
            "表格": ['.xls', '.xlsx', '.csv'],
            "数据": ['.json', '.xml', '.yaml', '.yml'],
            "图片": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            "压缩包": ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
    }
