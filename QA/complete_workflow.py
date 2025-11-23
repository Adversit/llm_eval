import os
import sys
import argparse

# Support both package imports (when used via `import QA...`) and direct script execution.
try:
    from .process_document import process_document  # type: ignore
    from .evaluate_qa import process_qa_and_evaluate  # type: ignore
except ImportError:  # pragma: no cover - fallback for script usage
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from process_document import process_document
    from evaluate_qa import process_qa_and_evaluate

def run_complete_workflow(document_path, output_dir=None, 
                         min_density_score=5, min_quality_score=5,
                         num_pairs=3, include_reason=False, 
                         suggest_qa_count=True, use_suggested_count=True,
                         min_factual_score=7, min_overall_score=7,
                         qa_sample_percentage=100,
                         skip_extract=False, skip_evaluate=False, 
                         skip_qa=False, skip_qa_evaluate=False,
                         progress_callback=None):
    """
    运行完整的工作流程：文档处理 + 问答质量评估
    
    参数:
        document_path (str): 文档路径
        output_dir (str): 输出目录路径
        min_density_score (int): 最低信息密度分数
        min_quality_score (int): 最低信息质量分数
        num_pairs (int): 每个内容段落生成的问答对数量
        include_reason (bool): 是否包含评估理由
        suggest_qa_count (bool): 是否建议问答对数量
        use_suggested_count (bool): 是否使用建议的问答对数量
        min_factual_score (int): 最低事实依据分数
        min_overall_score (int): 最低总体质量分数
        qa_sample_percentage (float): 问答质量评估的抽查百分比，范围1-100
        skip_extract (bool): 是否跳过内容提取步骤
        skip_evaluate (bool): 是否跳过内容评估步骤
        skip_qa (bool): 是否跳过问答对生成步骤
        skip_qa_evaluate (bool): 是否跳过问答对质量评估步骤
        progress_callback (callable): 进度回调函数，接收(步骤名称, 进度百分比, 消息)参数
    
    返回:
        dict: 包含处理结果的字典
    """
    result = {
        'success': False,
        'files': {},
        'error': None
    }
    
    try:
        # 进度回调函数封装，确保仅在提供回调时调用
        def update_progress(step_name, progress, message=None):
            if progress_callback:
                progress_callback(step_name, progress, message)
                
        update_progress("初始化", 0.0, "正在准备处理文档...")
        
        # 设置输出目录
        output_dir = output_dir or os.path.dirname(document_path) or '.'
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取文档名称和基础名称
        document_name = os.path.basename(document_path)
        base_name = os.path.splitext(document_name)[0]
        
        # 设置输出文件路径
        qa_excel = os.path.join(output_dir, f"{base_name}_问答对.xlsx")
        qa_evaluated_excel = os.path.join(output_dir, f"{base_name}_问答对_evaluated.xlsx")
        
        # 步骤1: 文档处理（提取内容、评估内容质量、生成问答对）
        if not skip_extract or not skip_evaluate or not skip_qa:
            print("\n===== 步骤1: 文档处理 =====")
            update_progress("文档处理", 0.1, "开始处理文档...")
            
            sub_steps = 3 - sum([skip_extract, skip_evaluate, skip_qa])
            current_sub_step = 0
            
            # 计算文档处理阶段的进度占总进度的比例
            doc_process_weight = 0.7  # 文档处理阶段占总进度的70%
            
            # 创建子进度回调，将阶段1的进度映射到总进度的0.1-0.7
            def doc_progress_callback(step_name, progress, message=None):
                # 将 process_document 的 0-0.7 映射到总进度的 0.1-0.7
                scaled_progress = 0.1 + progress * (0.7 - 0.1) / 0.7
                update_progress(step_name, scaled_progress, message)

            doc_result = process_document(
                document_path=document_path,
                output_dir=output_dir,
                min_density_score=min_density_score,
                min_quality_score=min_quality_score,
                num_pairs=num_pairs,
                include_reason=include_reason,
                suggest_qa_count=suggest_qa_count,
                use_suggested_count=use_suggested_count,
                skip_extract=skip_extract,
                skip_evaluate=skip_evaluate,
                skip_qa=skip_qa,
                progress_callback=doc_progress_callback
            )
            
            # 更新文档处理完成的进度
            update_progress("文档处理", doc_process_weight, "文档处理完成")
            
            if not doc_result['success']:
                result['error'] = doc_result['error']
                update_progress("处理失败", 1.0, f"文档处理失败: {doc_result['error']}")
                return result
            
            # 更新文件路径
            result['files'].update(doc_result['files'])
            
            # 获取问答对文件路径
            if 'qa_excel' in doc_result['files']:
                qa_excel = doc_result['files']['qa_excel']
        
        # 步骤2: 问答质量评估
        if not skip_qa_evaluate:
            print("\n===== 步骤2: 问答质量评估 =====")
            print(f"评估参数: 事实依据≥{min_factual_score}, 总体质量≥{min_overall_score}, 抽查{qa_sample_percentage}%")
            update_progress("问答质量评估", 0.8,
                          f"开始评估问答对质量... (阈值: 事实≥{min_factual_score}, 质量≥{min_overall_score}, 抽查{qa_sample_percentage}%)")

            # 检查问答对文件是否存在
            if not os.path.exists(qa_excel):
                error_msg = f"错误: 问答对文件不存在: {qa_excel}"
                result['error'] = error_msg
                update_progress("处理失败", 1.0, error_msg)
                return result

            # 评估问答对质量
            eval_start = 0.8
            eval_weight = 0.15

            def evaluation_progress(step_name, progress, message=None):
                scaled_progress = eval_start + max(0.0, min(1.0, progress)) * eval_weight
                update_progress(step_name, scaled_progress, message)

            qa_eval_success = process_qa_and_evaluate(
                qa_excel=qa_excel,
                output_excel=qa_evaluated_excel,
                min_factual_score=min_factual_score,
                min_overall_score=min_overall_score,
                sample_percentage=qa_sample_percentage,
                progress_callback=evaluation_progress
            )

            if not qa_eval_success:
                error_msg = "问答对质量评估失败"
                result['error'] = error_msg
                update_progress("处理失败", 1.0, error_msg)
                return result
            
            result['files']['qa_evaluated_excel'] = qa_evaluated_excel
            update_progress("问答质量评估", 0.95, "问答质量评估完成")
        else:
            print("\n===== 步骤2: 跳过问答质量评估 =====")
            update_progress("跳过问答评估", 0.95, "已跳过问答质量评估")
        
        # 输出处理结果
        print("\n===== 处理完成 =====")
        for file_type, file_path in result['files'].items():
            print(f"- {file_type}: {file_path}")
        
        result['success'] = True
        update_progress("处理完成", 1.0, "文档完整处理流程成功完成")
        return result
        
    except Exception as e:
        error_msg = f"处理过程中出错: {str(e)}"
        result['error'] = error_msg
        if progress_callback:
            update_progress("处理失败", 1.0, error_msg)
        return result

def main():
    """
    主函数，处理命令行参数并调用完整工作流程
    """
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='运行完整的文档处理和问答质量评估工作流')
    
    # 添加参数
    parser.add_argument('document_path', help='文档路径')
    parser.add_argument('--output-dir', '-o', help='输出目录路径')
    parser.add_argument('--min-density', '-d', type=int, default=5, help='最低信息密度分数，默认为5')
    parser.add_argument('--min-quality', '-q', type=int, default=5, help='最低信息质量分数，默认为5')
    parser.add_argument('--num-pairs', '-n', type=int, default=3, help='每个内容段落生成的问答对数量，默认为3')
    parser.add_argument('--include-reason', '-r', action='store_true', help='是否包含评估理由')
    parser.add_argument('--suggest-qa-count', '-s', action='store_true', help='是否建议问答对数量')
    parser.add_argument('--use-suggested-count', '-u', action='store_true', help='是否使用建议的问答对数量')
    parser.add_argument('--min-factual', '-f', type=int, default=7, help='最低事实依据分数，默认为7')
    parser.add_argument('--min-overall', '-v', type=int, default=7, help='最低总体质量分数，默认为7')
    parser.add_argument('--qa-sample', '-p', type=float, default=100, help='问答质量评估的抽查百分比，范围1-100，默认为100（全部评估）')
    parser.add_argument('--skip-extract', action='store_true', help='跳过内容提取步骤')
    parser.add_argument('--skip-evaluate', action='store_true', help='跳过内容评估步骤')
    parser.add_argument('--skip-qa', action='store_true', help='跳过问答对生成步骤')
    parser.add_argument('--skip-qa-evaluate', action='store_true', help='跳过问答对质量评估步骤')
    
    # 解析参数
    args = parser.parse_args()
    
    # 调用完整工作流程
    result = run_complete_workflow(
        document_path=args.document_path,
        output_dir=args.output_dir,
        min_density_score=args.min_density,
        min_quality_score=args.min_quality,
        num_pairs=args.num_pairs,
        include_reason=args.include_reason,
        suggest_qa_count=args.suggest_qa_count,
        use_suggested_count=args.use_suggested_count,
        min_factual_score=args.min_factual,
        min_overall_score=args.min_overall,
        qa_sample_percentage=args.qa_sample,
        skip_extract=args.skip_extract,
        skip_evaluate=args.skip_evaluate,
        skip_qa=args.skip_qa,
        skip_qa_evaluate=args.skip_qa_evaluate
    )
    
    # 处理结果
    if not result['success']:
        print(f"处理失败: {result['error']}")
        sys.exit(1)
    else:
        print("完整工作流程执行成功！")

if __name__ == "__main__":
    main() 
