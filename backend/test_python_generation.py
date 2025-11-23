"""
测试Python文件生成功能
"""
import sys
import os

# 添加路径
BACKEND_DIR = os.path.dirname(__file__)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'app'))

OOK_PATH = os.path.join(os.path.dirname(BACKEND_DIR), "00k")
sys.path.insert(0, OOK_PATH)

print("=" * 60)
print("测试Python文件生成功能")
print("=" * 60)
print()

# 测试1: 导入代码生成函数
print("测试1: 导入00k代码生成函数")
try:
    from function.Admin_create_function_page import (
        generate_questionnaire_page_code,
        generate_evidence_page_code
    )
    print("✅ 成功导入代码生成函数")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

print()

# 测试2: 生成问卷页面代码
print("测试2: 生成问卷页面代码")
try:
    code = generate_questionnaire_page_code(
        company_name="测试公司",
        scenario_name="测试场景",
        excel_filename="测试公司_测试场景_问卷.xlsx",
        json_filename="测试公司_测试场景.json"
    )
    print(f"✅ 成功生成问卷页面代码 ({len(code)} 字符)")
    print(f"   前50个字符: {code[:50]}")
except Exception as e:
    print(f"❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试3: 生成证明材料页面代码
print("测试3: 生成证明材料页面代码")
try:
    evidence_data = {
        'selected_items_info': [
            {'item': '测试能力项1'},
            {'item': '测试能力项2'}
        ]
    }
    code = generate_evidence_page_code(
        company_name="测试公司",
        scenario_name="测试场景",
        json_filename="测试公司_测试场景.json",
        evidence_data=evidence_data
    )
    print(f"✅ 成功生成证明材料页面代码 ({len(code)} 字符)")
    print(f"   前50个字符: {code[:50]}")
except Exception as e:
    print(f"❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试4: 写入文件测试
print("测试4: 写入文件测试")
try:
    test_dir = os.path.join(BACKEND_DIR, "test_output")
    os.makedirs(test_dir, exist_ok=True)

    test_file = os.path.join(test_dir, "test_questionnaire.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"✅ 成功写入测试文件: {test_file}")
    print(f"   文件大小: {os.path.getsize(test_file)} 字节")

    # 清理
    os.remove(test_file)
    os.rmdir(test_dir)
    print("✅ 清理完成")
except Exception as e:
    print(f"❌ 写入失败: {e}")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
