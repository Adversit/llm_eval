import os
import sys
import argparse
from evaluate_qa import process_qa_and_evaluate

def main():
    """
    主函数，处理命令行参数并调用问答质量评估函数
    """
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='评估问答对质量')
    
    # 添加参数
    parser.add_argument('qa_excel', help='问答Excel文件路径')
    parser.add_argument('--output', '-o', help='输出Excel文件路径')
    parser.add_argument('--min-factual', '-f', type=int, default=7, help='最低事实依据分数阈值，默认为7')
    parser.add_argument('--min-overall', '-v', type=int, default=7, help='最低总体质量分数阈值，默认为7')
    parser.add_argument('--sample', '-s', type=float, default=100, help='抽查的百分比，范围1-100，默认为100（全部评估）')
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置输出路径
    output_excel = args.output
    if not output_excel:
        base_name, ext = os.path.splitext(args.qa_excel)
        output_excel = f"{base_name}_evaluated{ext}"
    
    # 调用评估函数
    print(f"开始评估问答对质量: {args.qa_excel}")
    print(f"最低事实依据分数阈值: {args.min_factual}")
    print(f"最低总体质量分数阈值: {args.min_overall}")
    print(f"抽查百分比: {args.sample}%")
    
    result = process_qa_and_evaluate(
        qa_excel=args.qa_excel,
        output_excel=output_excel,
        min_factual_score=args.min_factual,
        min_overall_score=args.min_overall,
        sample_percentage=args.sample
    )
    
    if result:
        print(f"问答对质量评估完成，结果保存至: {output_excel}")
    else:
        print("问答对质量评估失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 