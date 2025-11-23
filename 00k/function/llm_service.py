import json
import os
from openai import OpenAI

CONFIG_FILE = 'model_config.json'

def load_llm_config():
    """从JSON文件加载LLM配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None

def get_llm_analysis(prompt, api_key, base_url, model_name):
    """
    调用大模型API进行分析。
    
    Args:
        prompt (str): 发送给大模型的提示。
        api_key (str): API密钥。
        base_url (str): API基础URL。
        model_name (str): 模型名称。
        
    Returns:
        str: 包含分析结果的字符串，或错误信息。
    """
    if not all([api_key, base_url, model_name]) or api_key == "YOUR_API_KEY_HERE":
        return "错误：AI服务配置不完整。请在侧边栏中提供有效的API密钥、基础URL和模型名称。"
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一名资深的数据分析师，擅长从看似分散的调研数据中洞察深层的关联、模式与结论。你的分析需要逻辑严谨、语言专业。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用大模型API时出错: {e}"

def get_llm_analysis_stream(prompt, api_key, base_url, model_name):
    """
    调用大模型API进行流式分析。
    
    Args:
        prompt (str): 发送给大模型的提示。
        api_key (str): API密钥。
        base_url (str): API基础URL。
        model_name (str): 模型名称。
        
    Yields:
        str: 分析结果的文本块。
    """
    if not all([api_key, base_url, model_name]) or api_key == "YOUR_API_KEY_HERE":
        yield "错误：AI服务配置不完整。请在侧边栏中提供有效的API密钥、基础URL和模型名称。"
        return
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一名资深的数据分析师，擅长从看似分散的调研数据中洞察深层的关联、模式与结论。你的分析需要逻辑严谨、语言专业。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"调用大模型API时出错: {e}" 