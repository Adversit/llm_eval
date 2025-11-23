from stract_extract import identify_headings_in_document
import pandas as pd
import os

def extract_content_from_document(document_path, output_excel=None):
    """
    从文档中提取标题和内容，并保存到Excel文件
    
    参数:
        document_path (str): 文档路径
        output_excel (str, optional): 输出Excel文件路径
        
    返回:
        bool: 操作是否成功
    """
    try:
        # 设置默认输出路径
        if output_excel is None:
            base_name = os.path.splitext(os.path.basename(document_path))[0]
            output_excel = f"{base_name}_内容提取结果.xlsx"
        
        print(f"正在处理文档: {document_path}")
        
        # 调用函数获取文档中的标题
        content = identify_headings_in_document(document_path)
        
        # 处理结果
        if content['success']:
            # 从结果中提取标题信息和段落
            heading_lines = content['heading_lines']
            paragraphs = content['paragraphs']
            
            # 创建输出数据
            output_data = []
            
            # 如果没有找到标题，直接返回
            if not heading_lines:
                print("未找到任何标题")
                return False
            else:
                # 排序标题行号，确保按顺序处理
                heading_lines.sort()
                
                # 遍历每个标题及其下文本
                for i in range(len(heading_lines)):
                    current_heading_line = heading_lines[i]
                    
                    # 找到当前标题
                    current_heading = next((p for p in paragraphs if p['index'] == current_heading_line), None)
                    
                    if current_heading:
                        # 确定下一个标题行号
                        next_heading_line = heading_lines[i+1] if i < len(heading_lines)-1 else float('inf')
                        
                        # 收集当前标题下的所有段落
                        section_paragraphs = []
                        for p in paragraphs:
                            if current_heading_line < p['index'] < next_heading_line:
                                section_paragraphs.append(p['text'])
                        
                        # 合并段落为一个完整内容
                        section_content = "\n".join(section_paragraphs)
                        
                        # 添加标题和合并后的内容
                        output_data.append({
                            '标题行号': current_heading['index'],
                            '标题': current_heading['text'],
                            '标题样式': current_heading['style'],
                            '内容': section_content
                        })
            
                # 创建DataFrame并保存为Excel
                if output_data:
                    df = pd.DataFrame(output_data)
                    
                    # 调整Excel列宽
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                        worksheet = writer.sheets['Sheet1']
                        
                        # 设置列宽
                        worksheet.column_dimensions['A'].width = 10  # 标题行号列
                        worksheet.column_dimensions['B'].width = 40  # 标题列
                        worksheet.column_dimensions['C'].width = 15  # 标题样式列
                        worksheet.column_dimensions['D'].width = 80  # 内容列
                        
                        # 设置内容列自动换行
                        for row in worksheet.iter_rows(min_row=2, min_col=4, max_col=4):
                            for cell in row:
                                cell.alignment = worksheet.cell(1, 1).alignment.copy(wrapText=True)
                    
                    print(f"已成功将标题和内容保存到Excel文件: {output_excel}")
                    print(f"共提取了 {len(output_data)} 个标题及其内容")
                    return True
                else:
                    print("没有可输出的数据")
                    return False
        else:
            # 处理失败情况
            print(f"错误: {content.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"提取内容时出错: {str(e)}")
        return False

# 如果直接运行此脚本
if __name__ == "__main__":
    # 设置输入文件路径
    document_path = "data/NeonSAN RoCE流控指南.docx"
    
    # 提取文档内容
    extract_content_from_document(document_path)