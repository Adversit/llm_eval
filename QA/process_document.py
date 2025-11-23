import os
import sys
from extract_content import extract_content_from_document
from evaluate_content import process_excel_and_evaluate
from get_qa import process_excel_and_generate_qa

def process_document(document_path, min_density_score=5, min_quality_score=5,
                    output_dir=None, content_excel=None, evaluated_excel=None,
                    filtered_excel=None, qa_excel=None, num_pairs=5,
                    skip_extract=False, skip_evaluate=False, skip_qa=False,
                    include_reason=True, suggest_qa_count=False, use_suggested_count=False,
                    progress_callback=None):
    """
    处理文档并生成问答对

    参数:
        document_path (str): 文档路径
        min_density_score (int): 最低信息密度分数，默认为5
        min_quality_score (int): 最低信息质量分数，默认为5
        output_dir (str): 输出目录路径，默认为文档所在目录
        content_excel (str): 内容提取结果Excel文件路径
        evaluated_excel (str): 内容评估结果Excel文件路径
        filtered_excel (str): 筛选后内容Excel文件路径
        qa_excel (str): 问答对结果Excel文件路径
        num_pairs (int): 每个内容段落生成的问答对数量，默认为5
        skip_extract (bool): 是否跳过内容提取步骤
        skip_evaluate (bool): 是否跳过内容评估步骤
        skip_qa (bool): 是否跳过问答对生成步骤
        include_reason (bool): 是否包含评估理由，默认为True
        suggest_qa_count (bool): 是否建议问答对数量，默认为False
        use_suggested_count (bool): 是否使用建议的问答对数量，默认为False
        progress_callback (callable): 进度回调函数，签名为 callback(step_name, progress, message)

    返回:
        dict: 包含处理结果的字典
    """
    result = {
        'success': False,
        'files': {},
        'error': None
    }
    
    try:
        # 检查文件是否存在
        if not skip_extract and not os.path.exists(document_path):
            result['error'] = f"错误: 文件不存在: {document_path}"
            return result
        
        # 检查参数一致性
        if use_suggested_count and not suggest_qa_count and not skip_evaluate:
            print("警告: 设置了use_suggested_count=True但suggest_qa_count=False，将自动启用suggest_qa_count")
            suggest_qa_count = True
        
        # 设置输出目录
        output_dir = output_dir or os.path.dirname(document_path) or '.'
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取文档名称和基础名称
        document_name = os.path.basename(document_path)
        base_name = os.path.splitext(document_name)[0]
        
        # 设置默认输出文件路径
        content_excel = content_excel or os.path.join(output_dir, f"{base_name}_内容提取结果.xlsx")
        evaluated_excel = evaluated_excel or os.path.join(output_dir, f"{base_name}_内容评估结果.xlsx")
        filtered_excel = filtered_excel or os.path.join(output_dir, f"{base_name}_内容评估结果_filtered.xlsx")
        qa_excel = qa_excel or os.path.join(output_dir, f"{base_name}_问答对.xlsx")
        
        # 步骤1: 提取文档内容
        if not skip_extract:
            print("\n===== 步骤1: 提取文档内容 =====")
            if progress_callback:
                progress_callback("提取文档内容", 0.1, "正在提取文档内容...")

            success = extract_content_from_document(document_path, content_excel)

            if not success:
                result['error'] = "内容提取失败，流程终止"
                return result

            result['files']['content_excel'] = content_excel
            if progress_callback:
                progress_callback("提取文档内容", 0.25, "文档内容提取完成")
        else:
            print("\n===== 步骤1: 跳过内容提取 =====")
            if not os.path.exists(content_excel):
                result['error'] = f"错误: 内容提取结果文件不存在: {content_excel}"
                return result

            result['files']['content_excel'] = content_excel
        
        # 步骤2: 评估内容质量
        if not skip_evaluate:
            print("\n===== 步骤2: 评估内容质量 =====")
            if progress_callback:
                progress_callback("评估内容质量", 0.35, "正在评估内容质量...")

            success = process_excel_and_evaluate(
                content_excel,
                evaluated_excel,
                min_density_score,
                min_quality_score,
                include_reason,
                suggest_qa_count
            )

            if not success:
                result['error'] = "内容评估失败，流程终止"
                return result

            result['files']['evaluated_excel'] = evaluated_excel
            result['files']['filtered_excel'] = filtered_excel
            if progress_callback:
                progress_callback("评估内容质量", 0.50, "内容质量评估完成")
        else:
            print("\n===== 步骤2: 跳过内容评估 =====")
            if not os.path.exists(filtered_excel):
                result['error'] = f"错误: 筛选后的内容文件不存在: {filtered_excel}"
                return result

            result['files']['filtered_excel'] = filtered_excel

        # 步骤3: 生成问答对
        if not skip_qa:
            print("\n===== 步骤3: 生成问答对 =====")
            if progress_callback:
                progress_callback("生成问答对", 0.60, "正在生成问答对...")

            success = process_excel_and_generate_qa(
                filtered_excel,
                qa_excel,
                num_pairs,
                use_suggested_count
            )

            if not success:
                result['error'] = "问答对生成失败，流程终止"
                return result
            
            result['files']['qa_excel'] = qa_excel
            if progress_callback:
                progress_callback("生成问答对", 0.70, "问答对生成完成")
        else:
            print("\n===== 步骤3: 跳过问答对生成 =====")
            if not os.path.exists(qa_excel):
                result['error'] = f"错误: 问答对文件不存在: {qa_excel}"
                return result

            result['files']['qa_excel'] = qa_excel
        
        # 输出处理结果
        print("\n===== 处理完成 =====")
        for file_type, file_path in result['files'].items():
            print(f"- {file_type}: {file_path}")
        
        result['success'] = True
        return result
        
    except Exception as e:
        result['error'] = f"处理过程中出错: {str(e)}"
        return result

def main():
    """
    主函数，处理命令行参数并调用处理函数
    """
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python main.py <文档路径> [最低信息密度分数=5] [最低信息质量分数=5] [包含评估理由=True] [建议问答对数量=False] [使用建议数量=False]")
        return
    
    # 获取文档路径
    document_path = sys.argv[1]
    
    # 获取可选参数
    min_density_score = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    min_quality_score = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    # 获取是否包含评估理由参数
    include_reason = True
    if len(sys.argv) > 4:
        include_reason_str = sys.argv[4].lower()
        include_reason = include_reason_str in ['true', 't', 'yes', 'y', '1']
    
    # 获取是否建议问答对数量参数
    suggest_qa_count = False
    if len(sys.argv) > 5:
        suggest_qa_count_str = sys.argv[5].lower()
        suggest_qa_count = suggest_qa_count_str in ['true', 't', 'yes', 'y', '1']
    
    # 获取是否使用建议的问答对数量参数
    use_suggested_count = False
    if len(sys.argv) > 6:
        use_suggested_count_str = sys.argv[6].lower()
        use_suggested_count = use_suggested_count_str in ['true', 't', 'yes', 'y', '1']
    
    # 调用处理函数
    result = process_document(
        document_path=document_path,
        min_density_score=min_density_score,
        min_quality_score=min_quality_score,
        include_reason=include_reason,
        suggest_qa_count=suggest_qa_count,
        use_suggested_count=use_suggested_count
    )
    
    # 处理结果
    if not result['success']:
        print(f"处理失败: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main() 