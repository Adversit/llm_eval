"""
基础LLM服务模块
包含LLM客户端配置和通用工具函数
"""

import json
import os
from openai import OpenAI
import streamlit as st
import pandas as pd


def get_llm_client():
    """
    从 model_config.json 加载配置并返回 OpenAI 客户端。
    """
    config_path = "model_config.json"
    selected_config_key = None
    api_key, base_url, model_name_inflection = None, None, None
    model_name_summary = None

    try:
        if not os.path.exists(config_path):
            st.error(f"错误: LLM 配置文件 '{config_path}' 未找到。请创建该文件并填入API配置。")
            example_json_config = '''
            {
              "MyLLM": {
                "name": "MyLLM (Example)",
                "api_key": "sk-your_api_key_here",
                "base_url": "https://api.example.com",
                "model": "your-model-name"
              }
            }
            '''
            st.info(f"示例 model_config.json 内容:\n{example_json_config}\n请确保 base_url 指向API服务根目录，程序会自动添加 /v1 后缀 (如果需要)")
            return None, None, None

        with open(config_path, 'r', encoding='utf-8') as f:
            all_configs = json.load(f)

        if not all_configs:
            st.error(f"错误: LLM 配置文件 '{config_path}' 为空或格式不正确。")
            return None, None, None

        config_keys = list(all_configs.keys())
        
        # 使用第一个配置作为主配置
        primary_config_key = config_keys[0]
        config_to_use = all_configs[primary_config_key]

        api_key = config_to_use.get("api_key")
        base_url = config_to_use.get("base_url")
        model_name_inflection = config_to_use.get("model")

        # 如果有第二个配置，使用它的模型作为总结模型
        if len(config_keys) > 1:
            summary_config_key = config_keys[1]
            # 假设第二个模型的api_key和base_url与第一个相同
            model_name_summary = all_configs[summary_config_key].get("model", model_name_inflection)
        else:
            # 否则，回退到主配置中定义的summary_model，或主模型本身
            model_name_summary = config_to_use.get("summary_model", model_name_inflection)


        if not all([api_key, base_url, model_name_inflection]):
            st.error(f"错误: LLM 配置 '{primary_config_key}' 中缺少 api_key, base_url, 或 model。")
            return None, None, None

        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip('/') + "/v1"

        client = OpenAI(api_key=api_key, base_url=base_url)
        return client, model_name_inflection, model_name_summary
    except FileNotFoundError:
        st.error(f"错误: LLM 配置文件 '{config_path}' 未找到。")
        return None, None, None
    except json.JSONDecodeError:
        st.error(f"错误: 解析 LLM 配置文件 '{config_path}' 出错。请检查其 JSON 格式。")
        return None, None, None
    except Exception as e:
        st.error(f"加载或初始化LLM客户端时发生未知错误: {e}")
        return None, None, None


def format_value_for_ai(value):
    """
    格式化数值供AI处理，统一处理缺失值和数值格式
    """
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        float_value = float(value)
        # Format to a string with 2 decimal places, and a sign for changes.
        # No thousands separator for AI to simplify parsing if it needs to.
        return f"{float_value:+.2f}" # No currency symbol for AI
    except (ValueError, TypeError):
        return "N/A" 