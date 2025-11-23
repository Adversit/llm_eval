import os
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from .file_manager_singleton import get_file_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataVisualizer:
    """数据可视化类 - 生成柱状图和饼图"""
    
    def __init__(self):
        """初始化可视化器"""
        self.file_manager = get_file_manager()
        self._setup_chinese_font()
        logger.info("DataVisualizer初始化完成")
    
    def _setup_chinese_font(self):
        """设置中文字体支持"""
        try:
            # 尝试设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            logger.info("中文字体设置完成")
        except Exception as e:
            logger.warning(f"中文字体设置失败: {e}")
    
    def visualize_single_file(self, model_name: str, file_name: str, 
                             save_path: Optional[str] = None) -> Dict[str, str]:
        """可视化单个文件的分析结果
        
        Args:
            model_name: 模型名称
            file_name: 文件名称
            save_path: 保存路径，如果为None则保存到默认位置
            
        Returns:
            Dict: 包含生成图片路径的字典
        """
        logger.info(f"开始可视化单文件结果 - 模型: {model_name}, 文件: {file_name}")
        
        # 使用FileManager查找时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        # 读取分析数据
        analysis_path = timestamped_dir / file_name / f"{file_name}_analysis.json"
        data = self._load_analysis_data(analysis_path)
        
        if not data:
            raise FileNotFoundError(f"分析文件不存在: {analysis_path}")
        
        # 设置保存路径
        if save_path is None:
            save_dir = timestamped_dir / file_name / "visualizations"
        else:
            save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成图表
        bar_chart_path = self._create_bar_chart(data, save_dir, f"{file_name}_柱状图")
        pie_chart_path = self._create_pie_chart(data, save_dir, f"{file_name}_饼图")
        
        result = {
            "bar_chart": str(bar_chart_path),
            "pie_chart": str(pie_chart_path)
        }
        
        logger.info(f"单文件可视化完成 - 柱状图: {bar_chart_path}, 饼图: {pie_chart_path}")
        return result
    
    def visualize_multi_file(self, model_name: str, 
                           save_path: Optional[str] = None) -> Dict[str, str]:
        """可视化多文件汇总的分析结果
        
        Args:
            model_name: 模型名称
            save_path: 保存路径，如果为None则保存到默认位置
            
        Returns:
            Dict: 包含生成图片路径的字典
        """
        logger.info(f"开始可视化多文件汇总结果 - 模型: {model_name}")
        
        # 使用FileManager查找时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        # 读取多文件汇总数据
        analysis_path = timestamped_dir / "multi_file" / "multi_analysis.json"
        data = self._load_analysis_data(analysis_path)
        
        if not data:
            raise FileNotFoundError(f"多文件汇总分析文件不存在: {analysis_path}")
        
        # 设置保存路径
        if save_path is None:
            save_dir = timestamped_dir / "multi_file" / "visualizations"
        else:
            save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成图表
        bar_chart_path = self._create_bar_chart(data, save_dir, "多文件汇总_柱状图")
        pie_chart_path = self._create_pie_chart(data, save_dir, "多文件汇总_饼图")
        
        result = {
            "bar_chart": str(bar_chart_path),
            "pie_chart": str(pie_chart_path)
        }
        
        logger.info(f"多文件可视化完成 - 柱状图: {bar_chart_path}, 饼图: {pie_chart_path}")
        return result
    
    def visualize_files(self, model_name: str, file_names: List[str], 
                       save_path: Optional[str] = None) -> Dict[str, Any]:
        """根据文件数量自动选择可视化方式
        
        Args:
            model_name: 模型名称
            file_names: 文件名列表
            save_path: 保存路径
            
        Returns:
            Dict: 可视化结果
        """
        logger.info(f"开始可视化文件: {file_names}")
        
        results = {
            "model_name": model_name,
            "file_count": len(file_names),
            "single_file_results": [],
            "multi_file_result": None
        }
        
        # 处理单文件可视化
        for file_name in file_names:
            try:
                single_result = self.visualize_single_file(model_name, file_name, save_path)
                results["single_file_results"].append({
                    "file_name": file_name,
                    "visualizations": single_result
                })
            except Exception as e:
                logger.error(f"单文件 {file_name} 可视化失败: {e}")
        
        # 如果文件数量大于1，生成多文件汇总可视化
        if len(file_names) > 1:
            try:
                multi_result = self.visualize_multi_file(model_name, save_path)
                results["multi_file_result"] = multi_result
            except Exception as e:
                logger.error(f"多文件汇总可视化失败: {e}")
        
        return results
    
    def _load_analysis_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载分析数据文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 分析数据，如果加载失败返回None
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"分析文件不存在: {file_path}")
                return None
        except Exception as e:
            logger.error(f"读取分析文件失败 {file_path}: {e}")
            return None
    
    def _create_bar_chart(self, data: Dict[str, Any], save_dir: Path, 
                         filename: str) -> Path:
        """创建柱状图
        
        Args:
            data: 分析数据
            save_dir: 保存目录
            filename: 文件名（不含扩展名）
            
        Returns:
            Path: 保存的图片路径
        """
        # 提取数据
        categories = ['正确回答', '推理错误', '知识缺失', '能力不足']
        values = [
            data.get('final_correct_answers', 0),
            data.get('final_reasoning_errors', 0),
            data.get('final_knowledge_deficiency', 0),
            data.get('final_capability_insufficient', 0)
        ]
        
        # 设置差距较大的暖色调颜色
        colors = ['#FFD700', '#32CD32', '#FF69B4', '#FF4500']  # 黄色、绿色、粉色、红色
        
        # 创建图表 - 与饼图保持一致的尺寸
        plt.figure(figsize=(8, 8))
        bars = plt.bar(categories, values, color=colors, alpha=0.8)
        
        # 设置标题和标签
        model_name = data.get('model_name', '未知模型')
        if 'analysis_type' in data and data['analysis_type'] == 'multi_file_aggregation':
            title = f'{model_name} - 多文件汇总结果'
            file_info = f"文件数量: {data.get('file_count', 0)}"
        else:
            file_name = data.get('file_name', '未知文件')
            title = f'{model_name} - {file_name} 评估结果'
            file_info = f"文件: {file_name}"
        
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('问题分类', fontsize=12)
        plt.ylabel('问题数量', fontsize=12)
        
        # 在柱子上显示数值
        for bar, value in zip(bars, values):
            if value > 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        str(int(value)), ha='center', va='bottom', fontsize=10)
        
        # 添加网格
        plt.grid(axis='y', alpha=0.3)
        
        # 添加文件信息
        #plt.figtext(0.02, 0.02, file_info, fontsize=8, alpha=0.7)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图片
        save_path = save_dir / f"{filename}.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def _create_pie_chart(self, data: Dict[str, Any], save_dir: Path, 
                         filename: str) -> Path:
        """创建饼图
        
        Args:
            data: 分析数据
            save_dir: 保存目录
            filename: 文件名（不含扩展名）
            
        Returns:
            Path: 保存的图片路径
        """
        # 提取数据
        categories = ['正确回答', '推理错误', '知识缺失', '能力不足']
        values = [
            data.get('final_correct_answers', 0),
            data.get('final_reasoning_errors', 0),
            data.get('final_knowledge_deficiency', 0),
            data.get('final_capability_insufficient', 0)
        ]
        
        # 过滤掉值为0的类别
        filtered_data = [(cat, val) for cat, val in zip(categories, values) if val > 0]
        if not filtered_data:
            # 如果所有值都为0，创建一个空图表
            plt.figure(figsize=(8, 8))
            plt.text(0.5, 0.5, '暂无数据', ha='center', va='center', 
                    fontsize=20, transform=plt.gca().transAxes)
            plt.axis('off')
        else:
            filtered_categories, filtered_values = zip(*filtered_data)
            
            # 设置差距较大的暖色调颜色
            color_map = {
                '正确回答': '#FFD700',  # 金黄色 - 代表成功
                '推理错误': '#32CD32',  # 绿色 - 代表部分正确但推理有误
                '知识缺失': '#FF69B4',  # 粉色 - 代表知识不足
                '能力不足': '#FF4500'   # 红橙色 - 代表能力不足
            }
            colors = [color_map[cat] for cat in filtered_categories]
            
            # 创建饼图
            plt.figure(figsize=(8, 8))
            wedges, texts, autotexts = plt.pie(filtered_values, labels=filtered_categories, 
                                             colors=colors, autopct='%1.1f%%',
                                             startangle=90, textprops={'fontsize': 10})
            
            # 美化百分比文字
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        # 设置标题
        model_name = data.get('model_name', '未知模型')
        if 'analysis_type' in data and data['analysis_type'] == 'multi_file_aggregation':
            title = f'{model_name} - 多文件汇总分布'
            file_info = f"文件数量: {data.get('file_count', 0)}"
        else:
            file_name = data.get('file_name', '未知文件')
            title = f'{model_name} - {file_name} 结果分布'
            file_info = f"文件: {file_name}"
        
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        
        # 添加文件信息
        #plt.figtext(0.02, 0.02, file_info, fontsize=8, alpha=0.7)
        
        # 确保饼图是圆形
        plt.axis('equal')
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图片
        save_path = save_dir / f"{filename}.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def create_comparison_charts(self, model_name: str, file_names: List[str],
                               save_path: Optional[str] = None) -> Dict[str, str]:
        """创建多文件对比图表
        
        Args:
            model_name: 模型名称
            file_names: 文件名列表
            save_path: 保存路径
            
        Returns:
            Dict: 生成的对比图表路径
        """
        logger.info(f"开始创建多文件对比图表: {file_names}")
        
        # 使用FileManager查找时间戳目录
        timestamped_dir = self.file_manager.find_latest_timestamp_dir(model_name)
        if not timestamped_dir:
            raise FileNotFoundError(f"未找到模型 {model_name} 的时间戳目录")
        
        # 收集所有文件的数据
        all_data = []
        valid_file_names = []
        
        for file_name in file_names:
            analysis_path = timestamped_dir / file_name / f"{file_name}_analysis.json"
            data = self._load_analysis_data(analysis_path)
            if data:
                all_data.append(data)
                valid_file_names.append(file_name)
        
        if not all_data:
            raise ValueError("没有找到有效的分析数据文件")
        
        # 设置保存路径
        if save_path is None:
            save_dir = timestamped_dir / "comparisons"
        else:
            save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建对比柱状图
        comparison_bar_path = self._create_comparison_bar_chart(
            all_data, valid_file_names, model_name, save_dir
        )
        
        # 创建对比饼图（显示总体分布）
        comparison_pie_path = self._create_total_pie_chart(
            all_data, valid_file_names, model_name, save_dir
        )
        
        result = {
            "comparison_bar_chart": str(comparison_bar_path),
            "total_pie_chart": str(comparison_pie_path)
        }
        
        logger.info(f"多文件对比图表创建完成")
        return result
    
    def _create_comparison_bar_chart(self, all_data: List[Dict], file_names: List[str],
                                   model_name: str, save_dir: Path) -> Path:
        """创建多文件对比柱状图"""
        import numpy as np
        
        categories = ['正确回答', '推理错误', '知识缺失', '能力不足']
        n_files = len(file_names)
        n_categories = len(categories)
        
        # 准备数据
        data_matrix = []
        for data in all_data:
            values = [
                data.get('final_correct_answers', 0),
                data.get('final_reasoning_errors', 0),
                data.get('final_knowledge_deficiency', 0),
                data.get('final_capability_insufficient', 0)
            ]
            data_matrix.append(values)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 设置柱子的位置
        x = np.arange(n_categories)
        width = 0.8 / n_files
        
        # 使用差距较大的暖色调色板
        warm_colors = ['#FFD700', '#32CD32', '#FF69B4', '#FF4500', '#FFA500', '#FF1493', '#ADFF2F', '#FF6347']
        colors = [warm_colors[i % len(warm_colors)] for i in range(n_files)]
        
        # 绘制每个文件的柱子
        for i, (data_values, file_name) in enumerate(zip(data_matrix, file_names)):
            offset = (i - n_files/2 + 0.5) * width
            bars = ax.bar(x + offset, data_values, width, label=file_name, 
                         color=colors[i], alpha=0.8)
            
            # 在柱子上显示数值
            for bar, value in zip(bars, data_values):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           str(int(value)), ha='center', va='bottom', fontsize=8)
        
        # 设置标签和标题
        ax.set_xlabel('问题分类', fontsize=12)
        ax.set_ylabel('问题数量', fontsize=12)
        ax.set_title(f'{model_name} - 多文件对比分析', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图片
        save_path = save_dir / "多文件对比_柱状图.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def _create_total_pie_chart(self, all_data: List[Dict], file_names: List[str],
                              model_name: str, save_dir: Path) -> Path:
        """创建总体分布饼图"""
        # 汇总所有文件的数据
        total_values = [0, 0, 0, 0]  # [正确回答, 推理错误, 知识缺失, 能力不足]
        
        for data in all_data:
            total_values[0] += data.get('final_correct_answers', 0)
            total_values[1] += data.get('final_reasoning_errors', 0)
            total_values[2] += data.get('final_knowledge_deficiency', 0)
            total_values[3] += data.get('final_capability_insufficient', 0)
        
        # 创建总体数据字典
        total_data = {
            'model_name': model_name,
            'analysis_type': 'multi_file_total',
            'file_count': len(file_names),
            'final_correct_answers': total_values[0],
            'final_reasoning_errors': total_values[1],
            'final_knowledge_deficiency': total_values[2],
            'final_capability_insufficient': total_values[3]
        }
        
        # 使用现有的饼图创建方法
        return self._create_pie_chart(total_data, save_dir, "多文件总体分布_饼图")


def main():
    """测试DataVisualizer功能"""
    try:
        visualizer = DataVisualizer()
        
        # 测试模型名称
        model_name = "deepseek"
        
        print("=== 数据可视化器测试 ===")
        
        # 测试单文件可视化
        print("\n=== 单文件可视化测试 ===")
        try:
            single_result = visualizer.visualize_single_file(model_name, "test")
            print(f"单文件可视化成功")
            print(f"柱状图: {single_result['bar_chart']}")
            print(f"饼图: {single_result['pie_chart']}")
        except Exception as e:
            print(f"单文件可视化失败: {e}")
        
        # 测试多文件可视化
        print("\n=== 多文件汇总可视化测试 ===")
        try:
            multi_result = visualizer.visualize_multi_file(model_name)
            print(f"多文件可视化成功")
            print(f"柱状图: {multi_result['bar_chart']}")
            print(f"饼图: {multi_result['pie_chart']}")
        except Exception as e:
            print(f"多文件可视化失败: {e}")
        
        # 测试自动选择可视化
        print("\n=== 自动选择可视化测试 ===")
        try:
            file_names = ["test"]  # 可以添加更多文件名进行测试
            auto_result = visualizer.visualize_files(model_name, file_names)
            print(f"自动可视化成功")
            print(f"文件数量: {auto_result['file_count']}")
            print(f"单文件结果数: {len(auto_result['single_file_results'])}")
            print(f"多文件汇总: {'有' if auto_result['multi_file_result'] else '无'}")
        except Exception as e:
            print(f"自动可视化失败: {e}")
        
        # 测试对比图表（如果有多个文件）
        print("\n=== 多文件对比图表测试 ===")
        try:
            file_names = ["test"]  # 如果有多个文件，可以添加更多
            if len(file_names) > 1:
                comparison_result = visualizer.create_comparison_charts(model_name, file_names)
                print(f"对比图表创建成功")
                print(f"对比柱状图: {comparison_result['comparison_bar_chart']}")
                print(f"总体饼图: {comparison_result['total_pie_chart']}")
            else:
                print("文件数量不足，跳过对比图表测试")
        except Exception as e:
            print(f"对比图表创建失败: {e}")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()