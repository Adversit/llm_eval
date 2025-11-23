import os
import json
import requests
import glob
from docx import Document
from config import API_KEY, MODEL, API_BASE_URL

def identify_headings_in_document(doc_path):
    """
    使用大模型读取Word文档并识别所有一级标题的行号

    参数:
        doc_path (str): Word文档路径

    返回:
        dict: 包含所有识别出的一级标题行号
    """
    # 使用统一的API配置
    api_key = API_KEY
    model = MODEL
    api_base_url = API_BASE_URL
    
    try:
        # 读取Word文档内容
        doc = Document(doc_path)
        
        # 收集所有段落及其位置
        paragraphs = []
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if text:
                paragraphs.append({
                    'index': i,
                    'text': text,
                    'style': para.style.name if para.style else "Normal"
                })
        
        # 将段落组合成完整文本，包括行号和样式信息
        doc_lines = []
        for i, para in enumerate(paragraphs):
            doc_lines.append(f"[行号:{para['index']}] [样式:{para['style']}] {para['text']}")
        
        full_text_with_lines = "\n".join(doc_lines)
        
        # 准备提示词
        prompt = f"""
请分析以下带有行号和样式标记的文档内容，结合文章内容分析出，哪些是真正的标题。

文档通常遵循特定层次结构：
1. 一级标题 - 文档的主要章节，可能有以下格式:
   - 数字编号: "1."、"2."等
   - 中文数字编号: "一、"、"二、"、"三、"等
   - 章节标识: "第一章"、"第二章"等
   - 无编号但样式明显的主要章节标题: "简介"、"测试环境配置"等

注意：
- 一级标题通常格式明显（字体较大，有明确的编号前缀）
- 文档中真正的一级标题数量通常不会很多，可能只有几个
- 标题的字数都非常少，不会超过15个字

请以JSON格式返回，格式为：
{{
    "heading_lines": [行号1, 行号2, 行号3, ...]
}}

只需要返回行号，不需要返回标题内容。

文档内容:
{full_text_with_lines}
"""
        
        # 调用API
        url = f"{api_base_url}/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个专业的文档结构分析专家，擅长识别文档中的标题层级。请准确区分一级标题与二级及以下标题，只返回真正的一级标题的行号。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 2000,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        # 发送请求
        response = requests.request("POST", url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            
            # 解析JSON响应
            try:
                result = json.loads(content)
                
                # 确保结果包含预期的字段
                if 'heading_lines' not in result:
                    result['heading_lines'] = []
                
                return {
                    'success': True,
                    'heading_lines': result['heading_lines'],
                    'paragraphs': paragraphs  # 返回段落列表以便后续处理
                }
                
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': '无法解析API响应为JSON',
                    'raw_response': content,
                    'heading_lines': [],
                    'paragraphs': paragraphs
                }
        else:
            return {
                'success': False,
                'error': f'API调用失败: {response.status_code} - {response.text}',
                'heading_lines': [],
                'paragraphs': paragraphs
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'识别一级标题时出错: {str(e)}',
            'heading_lines': [],
            'paragraphs': []
        }