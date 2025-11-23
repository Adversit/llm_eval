import json
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Union

def convert_numpy_types(obj: Any) -> Any:
    """
    递归转换NumPy和pandas数据类型为Python原生类型，以便JSON序列化
    
    Args:
        obj: 要转换的对象
        
    Returns:
        转换后的对象
    """
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj

def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    安全的JSON序列化，自动处理NumPy和pandas数据类型
    
    Args:
        data: 要序列化的数据
        **kwargs: json.dumps的其他参数
        
    Returns:
        JSON字符串
    """
    # 转换数据类型
    converted_data = convert_numpy_types(data)
    
    # 设置默认参数
    default_kwargs = {
        'ensure_ascii': False,
        'indent': 2,
        'default': str  # 对于无法转换的类型，使用str()
    }
    default_kwargs.update(kwargs)
    
    return json.dumps(converted_data, **default_kwargs)

def safe_json_dump(data: Any, fp, **kwargs) -> None:
    """
    安全的JSON文件写入，自动处理NumPy和pandas数据类型
    
    Args:
        data: 要序列化的数据
        fp: 文件对象
        **kwargs: json.dump的其他参数
    """
    # 转换数据类型
    converted_data = convert_numpy_types(data)
    
    # 设置默认参数
    default_kwargs = {
        'ensure_ascii': False,
        'indent': 2,
        'default': str  # 对于无法转换的类型，使用str()
    }
    default_kwargs.update(kwargs)
    
    json.dump(converted_data, fp, **default_kwargs)