"""
数据持久化工具类
支持将内存数据持久化到JSON文件
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class DataPersistence:
    """数据持久化管理器"""

    def __init__(self, storage_dir: str, filename: str):
        """
        初始化持久化管理器

        Args:
            storage_dir: 存储目录路径
            filename: JSON文件名
        """
        self.storage_dir = Path(storage_dir)
        self.filepath = self.storage_dir / filename

        # 确保目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 加载数据
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """从文件加载数据"""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载数据文件失败: {e}, 使用空字典")
                return {}
        return {}

    def _save(self):
        """保存数据到文件"""
        try:
            # 创建临时文件
            temp_file = self.filepath.with_suffix('.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)

            # 原子性替换
            temp_file.replace(self.filepath)

        except Exception as e:
            print(f"保存数据文件失败: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """设置数据并持久化"""
        self._data[key] = value
        self._save()

    def delete(self, key: str):
        """删除数据并持久化"""
        if key in self._data:
            del self._data[key]
            self._save()

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._data

    def keys(self):
        """获取所有键"""
        return self._data.keys()

    def values(self):
        """获取所有值"""
        return self._data.values()

    def items(self):
        """获取所有键值对"""
        return self._data.items()

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self._data[key]

    def __setitem__(self, key: str, value: Any):
        """支持字典式赋值"""
        self.set(key, value)

    def __delitem__(self, key: str):
        """支持字典式删除"""
        self.delete(key)

    def __len__(self) -> int:
        """返回数据数量"""
        return len(self._data)

    def clear(self):
        """清空所有数据"""
        self._data.clear()
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """获取所有数据的副本"""
        return self._data.copy()
