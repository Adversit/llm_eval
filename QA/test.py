from complete_workflow import run_complete_workflow
from evaluate_qa import process_qa_and_evaluate

document_path = r"D:\1、信通院\C\8、金融大模型工作\3、金融大模型标准工作\部门-金融大模型应用能力评估模型\00g、生成问答对\V4-完全版\word\xx证券\青云环境整体开关机文档_v1.0(3)(1).docx"

# 测试完整工作流
result = run_complete_workflow(
    document_path=document_path,
    num_pairs=1,  # 每个内容段落生成的问答对数量
    include_reason=False,  # 不包含评估理由，减少token消耗
    suggest_qa_count=True,  # 让模型建议问答对数量
    use_suggested_count=True,  # 使用模型建议的问答对数量
    min_factual_score=7,  # 最低事实依据分数阈值
    min_overall_score=7,  # 最低总体质量分数阈值
    qa_sample_percentage=30,  # 只评估30%的问答对，减少token消耗
    skip_extract=False,  # 是否跳过内容提取步骤
    skip_evaluate=False,  # 是否跳过内容评估步骤
    skip_qa=False,  # 是否跳过问答对生成步骤
    skip_qa_evaluate=True  # 是否跳过问答对质量评估步骤
)

if result['success']:
    print("完整工作流测试成功！")
    print("生成的文件:")
    for file_type, file_path in result['files'].items():
        print(f"- {file_type}: {file_path}")
else:
    print(f"测试失败: {result['error']}") 

# # 单独评估问答对质量
# qa_result = process_qa_and_evaluate(
#     qa_excel=r"D:\1、信通院\C\8、金融大模型工作\3、金融大模型标准工作\部门-金融大模型应用能力评估模型\00g、生成问答对\V3\word\金融智能进化论（二）：DeepSeek-R1对金融业务智能转型影响_问答对.xlsx",
#     min_factual_score=7,
#     min_overall_score=7,
#     sample_percentage=50  # 只评估50%的问答对，减少token消耗
# )

# if qa_result:
#     print("问答质量评估成功")
# else:
#     print("问答质量评估失败")

