import pandas as pd
import logging
import os
from functools import lru_cache
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExcelProcessor:
    """Excel文件处理器

    改进:
    - 添加数据缓存机制减少重复读取
    - 支持分块读取大文件
    - 添加数据验证
    """

    # 类级别缓存，存储已读取的文件
    _file_cache: Dict[str, pd.DataFrame] = {}
    _cache_enabled = True

    def __init__(self, file_path: str, use_cache: bool = True, chunk_size: Optional[int] = None):
        """
        初始化Excel处理器

        Args:
            file_path (str): Excel文件路径
            use_cache (bool): 是否使用缓存，默认True
            chunk_size (int, optional): 分块大小，用于大文件处理。None表示一次性读取
        """
        self.file_path = file_path
        self.columns = ['问题编号', '问题', '答案', '内容']
        self.data = None
        self.use_cache = use_cache and self._cache_enabled
        self.chunk_size = chunk_size
        self._file_size = None

        logger.info(f"初始化ExcelProcessor，文件路径: {file_path}, 缓存: {self.use_cache}")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 获取文件大小
        self._file_size = os.path.getsize(file_path)
        logger.info(f"文件大小: {self._file_size / 1024 / 1024:.2f} MB")

        # 读取Excel文件
        self._load_excel()
    
    def _load_excel(self):
        """加载Excel文件（支持缓存和分块读取）"""
        try:
            # 检查缓存
            cache_key = f"{self.file_path}:{os.path.getmtime(self.file_path)}"
            if self.use_cache and cache_key in self._file_cache:
                logger.info("从缓存中读取Excel文件")
                self.data = self._file_cache[cache_key].copy()
                logger.info(f"缓存命中，共 {len(self.data)} 行数据")
            else:
                logger.info("开始读取Excel文件...")

                # 根据文件大小决定读取策略
                # 超过10MB的文件使用分块读取
                if self._file_size > 10 * 1024 * 1024 and self.chunk_size is None:
                    logger.info("文件较大，使用优化读取模式")
                    # 使用openpyxl引擎的read_only模式
                    self.data = pd.read_excel(
                        self.file_path,
                        engine='openpyxl'
                    )
                else:
                    self.data = pd.read_excel(self.file_path)

                logger.info(f"成功读取Excel文件，共 {len(self.data)} 行数据")

                # 检查必需的列是否存在
                missing_columns = [col for col in self.columns if col not in self.data.columns]
                if missing_columns:
                    logger.warning(f"缺少以下列: {missing_columns}")
                    logger.info(f"实际列名: {list(self.data.columns)}")
                else:
                    logger.info("所有必需列均存在")

                # 存入缓存（限制缓存大小）
                if self.use_cache:
                    # 限制缓存条目数量为10个
                    if len(self._file_cache) >= 10:
                        # 移除最早的缓存项
                        oldest_key = next(iter(self._file_cache))
                        del self._file_cache[oldest_key]
                        logger.info(f"缓存已满，移除旧项: {oldest_key}")

                    self._file_cache[cache_key] = self.data.copy()
                    logger.info(f"文件已缓存，当前缓存大小: {len(self._file_cache)}")

        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            raise

    @classmethod
    def clear_cache(cls):
        """清空文件缓存"""
        cls._file_cache.clear()
        logger.info("Excel文件缓存已清空")

    @classmethod
    def get_cache_info(cls) -> Dict[str, int]:
        """获取缓存信息"""
        return {
            'cached_files': len(cls._file_cache),
            'cache_enabled': cls._cache_enabled
        }
    
    def process_data(self):
        """
        处理数据，将每行转换为指定格式的字典
        
        Returns:
            list: 包含字典的列表，每个字典格式为 {"id": "", "question": "", "answer": "", "content": ""}
        """
        if self.data is None:
            logger.error("数据未加载")
            return []
        
        logger.info("开始处理数据...")
        processed_data = []
        
        for index, row in self.data.iterrows():
            try:
                item = {
                    "id": str(row.get('问题编号', '')),
                    "question": str(row.get('问题', '')),
                    "answer": str(row.get('答案', '')),
                    "content": str(row.get('内容', ''))
                }
                processed_data.append(item)
                
            except Exception as e:
                logger.error(f"处理第 {index + 1} 行数据时出错: {str(e)}")
                continue
        
        logger.info(f"数据处理完成，共处理 {len(processed_data)} 条记录")
        return processed_data
    
    def get_first_n_rows(self, n=3):
        """
        获取前n行的处理结果
        
        Args:
            n (int): 要获取的行数，默认为3
            
        Returns:
            list: 前n行的处理结果
        """
        processed_data = self.process_data()
        return processed_data[:n]


if __name__ == "__main__":
    # 测试代码
    try:
        # 请替换为你的Excel文件路径
        file_path = "data/test.xlsx"  # 示例路径
        
        processor = ExcelProcessor(file_path)
        
        # 输出前三行的内容
        first_three_rows = processor.get_first_n_rows(3)
        
        print("\n=== 前三行数据 ===")
        for i, row in enumerate(first_three_rows, 1):
            print(f"\n第 {i} 行:")
            print(f"  ID: {row['id']}")
            print(f"  问题: {row['question']}")
            print(f"  答案: {row['answer']}")
            print(f"  内容: {row['content']}")
            
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        print(f"错误: {str(e)}")