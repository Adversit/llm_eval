"""
FileManager单例模式管理器
确保整个应用使用同一个FileManager实例，保持时间戳一致性
"""

from .dir_rs import FileManager

class FileManagerSingleton:
    """FileManager单例管理器"""
    
    _instance = None
    _file_manager = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileManagerSingleton, cls).__new__(cls)
            cls._file_manager = FileManager()
        return cls._instance
    
    def get_file_manager(self) -> FileManager:
        """获取FileManager实例"""
        return self._file_manager
    
    def reset_for_new_test(self, model_name: str):
        """为新测试重置时间戳"""
        if self._file_manager:
            self._file_manager.start_new_test(model_name)

# 全局函数，方便其他模块使用
def get_file_manager() -> FileManager:
    """获取全局FileManager实例"""
    singleton = FileManagerSingleton()
    return singleton.get_file_manager()

def reset_file_manager_for_new_test(model_name: str):
    """为新测试重置FileManager"""
    singleton = FileManagerSingleton()
    singleton.reset_for_new_test(model_name)

def ensure_timestamp_consistency(model_name: str, session_timestamp: str = None):
    """确保FileManager使用与session state一致的时间戳"""
    file_manager = get_file_manager()
    if session_timestamp:
        # 如果提供了session时间戳，强制使用它
        file_manager.set_timestamp(session_timestamp)
    return file_manager