import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime
from contextlib import contextmanager
from .json_serializer import safe_json_dump

# 跨平台导入
if os.name != 'nt':  # Unix/Linux/Mac
    import fcntl
else:  # Windows
    import msvcrt

class FileManager:
    """文件管理类，用于保存和读取评估相关的文件

    改进:
    - 添加文件锁机制防止并发写入冲突
    - 增强错误恢复能力
    - 优化内存使用（使用流式I/O）
    """

    def __init__(self, base_dir='data'):
        """初始化文件管理器

        Args:
            base_dir: 基础目录，默认为'data'
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self._current_timestamp = None  # 当前会话的时间戳
        self._lock_dir = self.base_dir / '.locks'
        self._lock_dir.mkdir(exist_ok=True)
    
    @contextmanager
    def _file_lock(self, file_path: Path):
        """文件锁上下文管理器，支持跨平台

        Args:
            file_path: 要锁定的文件路径

        Yields:
            None
        """
        lock_file = self._lock_dir / f"{file_path.name}.lock"
        lock_handle = None
        try:
            lock_handle = open(lock_file, 'w')
            # 跨平台文件锁
            if os.name == 'nt':  # Windows
                # Windows文件锁
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # Unix/Linux/Mac
                # Unix文件锁
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            yield
        except IOError:
            # 锁定失败，可能其他进程正在使用
            raise Exception("文件正在被其他进程使用，请稍后重试")
        finally:
            if lock_handle:
                try:
                    if os.name == 'nt':
                        # Windows解锁
                        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        # Unix解锁
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                except:
                    pass
                try:
                    lock_handle.close()
                except:
                    pass
            # 清理锁文件
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except:
                pass

    def _get_model_dir(self, model_name: str) -> Path:
        """获取模型目录路径（不带时间戳）
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            Path: 模型目录路径
        """
        model_dir = self.base_dir / model_name
        model_dir.mkdir(exist_ok=True)
        return model_dir
    
    def _get_or_create_timestamp(self, model_name: str, for_new_test: bool = False) -> str:
        """获取或创建当前会话的时间戳
        
        Args:
            model_name: 被评估模型的名称
            for_new_test: 是否为新测试（强制生成新时间戳）
            
        Returns:
            str: 时间戳字符串
        """
        if self._current_timestamp is None or for_new_test:
            if for_new_test:
                # 强制生成新的时间戳（新测试开始）
                self._current_timestamp = datetime.now().strftime("%Y%m%d%H%M")
            else:
                # 第一次访问，生成新的时间戳
                self._current_timestamp = datetime.now().strftime("%Y%m%d%H%M")
        
        return self._current_timestamp
    
    def _get_timestamped_model_dir(self, model_name: str) -> Path:
        """获取带时间戳的模型目录路径
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            Path: 带时间戳的模型目录路径
        """
        timestamp = self._get_or_create_timestamp(model_name)
        model_dir_with_timestamp = f"{model_name}{timestamp}"
        
        # 创建带时间戳的模型目录
        timestamped_model_dir = self.base_dir / model_dir_with_timestamp
        timestamped_model_dir.mkdir(exist_ok=True)
        return timestamped_model_dir
    
    def _get_file_dir(self, model_name: str, file_name: str) -> Path:
        """获取文件存储目录路径
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            
        Returns:
            Path: 文件存储目录路径
        """
        # 使用带时间戳的模型目录
        timestamped_model_dir = self._get_timestamped_model_dir(model_name)
        
        file_dir = timestamped_model_dir / file_name
        file_dir.mkdir(exist_ok=True)
        return file_dir
    
    def _get_result_dir(self, model_name: str) -> Path:
        """获取结果分析目录路径
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            Path: 结果分析目录路径
        """
        # 使用带时间戳的模型目录
        timestamped_model_dir = self._get_timestamped_model_dir(model_name)
        result_dir = timestamped_model_dir / "结果分析"
        result_dir.mkdir(exist_ok=True)
        return result_dir
    
    def save_file(self, model_name: str, file_name: str, input_name: str,
                  content: Union[str, bytes], file_type: str = 'text') -> str:
        """保存文件到指定位置（使用原子写入和文件锁）

        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            input_name: 需要输入的名称
            content: 文件内容
            file_type: 文件类型，'text' 或 'binary'

        Returns:
            str: 保存的文件路径
        """
        file_dir = self._get_file_dir(model_name, file_name)
        file_path = file_dir / input_name

        # 使用原子写入：先写入临时文件，成功后重命名
        temp_file = None
        try:
            with self._file_lock(file_path):
                # 创建临时文件
                fd, temp_path = tempfile.mkstemp(dir=file_dir, suffix='.tmp')
                temp_file = Path(temp_path)

                try:
                    if file_type == 'text':
                        with os.fdopen(fd, 'w', encoding='utf-8') as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())  # 确保写入磁盘
                    else:  # binary
                        with os.fdopen(fd, 'wb') as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())  # 确保写入磁盘

                    # 原子替换目标文件
                    if os.name == 'nt':  # Windows需要先删除
                        if file_path.exists():
                            file_path.unlink()
                    temp_file.replace(file_path)
                    temp_file = None  # 标记已完成，避免finally中删除

                except Exception as e:
                    # 关闭文件描述符（如果还没关闭）
                    try:
                        os.close(fd)
                    except:
                        pass
                    raise e

            return str(file_path)

        except Exception as e:
            raise Exception(f"文件保存失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
    
    def read_file(self, model_name: str, file_name: str, input_name: str, 
                  file_type: str = 'text') -> Union[str, bytes]:
        """读取指定位置的文件
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            input_name: 需要输入的名称
            file_type: 文件类型，'text' 或 'binary'
            
        Returns:
            Union[str, bytes]: 文件内容
        """
        file_dir = self._get_file_dir(model_name, file_name)
        file_path = file_dir / input_name
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            if file_type == 'text':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:  # binary
                with open(file_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"文件读取失败: {e}")
    
    def save_result(self, model_name: str, result_name: str, 
                    content: Union[str, dict]) -> str:
        """保存结果分析文件
        
        Args:
            model_name: 被评估模型的名称
            result_name: 结果文件名称
            content: 结果内容
            
        Returns:
            str: 保存的文件路径
        """
        result_dir = self._get_result_dir(model_name)
        file_path = result_dir / result_name
        
        try:
            if isinstance(content, dict):
                # 如果是字典，保存为JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    safe_json_dump(content, f)
            else:
                # 否则保存为文本
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            return str(file_path)
        except Exception as e:
            raise Exception(f"结果保存失败: {e}")
    
    def read_result(self, model_name: str, result_name: str) -> Union[str, dict]:
        """读取结果分析文件
        
        Args:
            model_name: 被评估模型的名称
            result_name: 结果文件名称
            
        Returns:
            Union[str, dict]: 结果内容
        """
        result_dir = self._get_result_dir(model_name)
        file_path = result_dir / result_name
        
        if not file_path.exists():
            raise FileNotFoundError(f"结果文件不存在: {file_path}")
        
        try:
            # 尝试读取为JSON
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 否则读取为文本
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"结果读取失败: {e}")
    
    def upload_file(self, model_name: str, file_name: str, input_name: str, 
                    uploaded_file) -> str:
        """处理上传的文件（适用于Streamlit）
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            input_name: 需要输入的名称
            uploaded_file: Streamlit上传的文件对象
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 读取上传文件的内容
            content = uploaded_file.read()
            
            # 根据文件类型决定保存方式
            if uploaded_file.type.startswith('text/') or uploaded_file.name.endswith(('.txt', '.csv', '.json')):
                # 文本文件
                content = content.decode('utf-8')
                return self.save_file(model_name, file_name, input_name, content, 'text')
            else:
                # 二进制文件
                return self.save_file(model_name, file_name, input_name, content, 'binary')
        except Exception as e:
            raise Exception(f"文件上传失败: {e}")
    
    def list_files(self, model_name: str, file_name: Optional[str] = None) -> List[str]:
        """列出指定目录下的文件
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称，如果为None则列出模型目录下所有文件
            
        Returns:
            List[str]: 文件列表
        """
        if file_name:
            file_dir = self._get_file_dir(model_name, file_name)
        else:
            file_dir = self._get_model_dir(model_name)
        
        if not file_dir.exists():
            return []
        
        files = []
        for item in file_dir.iterdir():
            if item.is_file():
                files.append(item.name)
        
        return sorted(files)
    
    def list_results(self, model_name: str) -> List[str]:
        """列出结果分析目录下的文件
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            List[str]: 结果文件列表
        """
        result_dir = self._get_result_dir(model_name)
        
        if not result_dir.exists():
            return []
        
        files = []
        for item in result_dir.iterdir():
            if item.is_file():
                files.append(item.name)
        
        return sorted(files)
    
    def delete_file(self, model_name: str, file_name: str, input_name: str) -> bool:
        """删除指定文件
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            input_name: 需要输入的名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            file_dir = self._get_file_dir(model_name, file_name)
            file_path = file_dir / input_name
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def delete_result(self, model_name: str, result_name: str) -> bool:
        """删除结果文件
        
        Args:
            model_name: 被评估模型的名称
            result_name: 结果文件名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result_dir = self._get_result_dir(model_name)
            file_path = result_dir / result_name
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_path(self, model_name: str, file_name: str, input_name: str) -> str:
        """获取文件的完整路径
        
        Args:
            model_name: 被评估模型的名称
            file_name: 文件名称
            input_name: 需要输入的名称
            
        Returns:
            str: 文件完整路径
        """
        file_dir = self._get_file_dir(model_name, file_name)
        return str(file_dir / input_name)
    
    def get_result_path(self, model_name: str, result_name: str) -> str:
        """获取结果文件的完整路径
        
        Args:
            model_name: 被评估模型的名称
            result_name: 结果文件名称
            
        Returns:
            str: 结果文件完整路径
        """
        result_dir = self._get_result_dir(model_name)
        return str(result_dir / result_name)
    
    def start_new_test(self, model_name: str) -> str:
        """开始新的测试，生成新的时间戳
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            str: 新生成的时间戳
        """
        self._current_timestamp = datetime.now().strftime("%Y%m%d%H%M")
        return self._current_timestamp
    
    def find_latest_timestamp_dir(self, model_name: str) -> Optional[Path]:
        """查找模型的最新时间戳目录
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            Optional[Path]: 最新的时间戳目录路径，如果没有找到则返回None
        """
        import re
        
        # 查找所有匹配的时间戳目录
        pattern = f"{model_name}(\\d{{12}})"
        timestamp_dirs = []
        
        for item in self.base_dir.iterdir():
            if item.is_dir():
                match = re.match(pattern, item.name)
                if match:
                    timestamp_dirs.append((match.group(1), item))
        
        # 返回最新的时间戳目录
        if timestamp_dirs:
            latest_timestamp, latest_dir = max(timestamp_dirs, key=lambda x: x[0])
            self._current_timestamp = latest_timestamp  # 设置为当前时间戳
            return latest_dir
        
        return None
    
    def get_current_timestamp(self, model_name: str) -> Optional[str]:
        """获取当前会话的时间戳
        
        Args:
            model_name: 被评估模型的名称
            
        Returns:
            Optional[str]: 当前时间戳，如果没有则返回None
        """
        return self._current_timestamp
    
    def set_timestamp(self, timestamp: str):
        """设置当前时间戳（用于确保一致性）
        
        Args:
            timestamp: 要设置的时间戳
        """
        self._current_timestamp = timestamp

def main():
    """测试文件管理器功能"""
    # 创建文件管理器实例
    fm = FileManager()
    
    model_name = "deepseek-v3"
    file_name = "test_data"
    input_name = "sample.txt"
    result_name = "analysis_result.json"
    
    print("=== 文件管理器测试 ===")
    
    # 测试保存文件
    print("1. 测试保存文件...")
    content = "这是一个测试文件的内容。"
    saved_path = fm.save_file(model_name, file_name, input_name, content)
    print(f"✓ 文件已保存到: {saved_path}")
    
    # 测试读取文件
    print("2. 测试读取文件...")
    read_content = fm.read_file(model_name, file_name, input_name)
    print(f"✓ 读取内容: {read_content}")
    
    # 测试保存结果
    print("3. 测试保存结果...")
    result_data = {
        "model": model_name,
        "accuracy": 0.95,
        "timestamp": "2025-01-25 10:00:00"
    }
    result_path = fm.save_result(model_name, result_name, result_data)
    print(f"✓ 结果已保存到: {result_path}")
    
    # 测试读取结果
    print("4. 测试读取结果...")
    read_result = fm.read_result(model_name, result_name)
    print(f"✓ 读取结果: {read_result}")
    
    # 测试列出文件
    print("5. 测试列出文件...")
    files = fm.list_files(model_name, file_name)
    print(f"✓ 文件列表: {files}")
    
    results = fm.list_results(model_name)
    print(f"✓ 结果列表: {results}")
    
    # 测试获取路径
    print("6. 测试获取路径...")
    file_path = fm.get_file_path(model_name, file_name, input_name)
    result_path = fm.get_result_path(model_name, result_name)
    print(f"✓ 文件路径: {file_path}")
    print(f"✓ 结果路径: {result_path}")

if __name__ == "__main__":
    main()