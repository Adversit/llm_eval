"""
测试numpy类型转换是否正常工作
"""
import sys
import os

# 添加app目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.flmm_analyzer import (
    convert_numpy_types,
    get_basic_statistics,
    analyze_project_questions,
    calculate_five_ratings
)
import numpy as np
import json

def test_convert_function():
    """测试转换函数"""
    print("测试1: 基本类型转换")
    test_data = {
        'int64': np.int64(42),
        'float64': np.float64(3.14),
        'nested': {
            'score': np.int64(5),
            'value': np.float64(2.5)
        },
        'list': [np.int64(1), np.int64(2), np.int64(3)],
        'normal_int': 10,
        'normal_str': 'test'
    }

    result = convert_numpy_types(test_data)
    print("原始数据:", test_data)
    print("转换结果:", result)

    # 尝试JSON序列化
    try:
        json_str = json.dumps(result)
        print("✅ JSON序列化成功")
        print("JSON:", json_str[:100])
    except Exception as e:
        print(f"❌ JSON序列化失败: {e}")

    print()

def test_real_data():
    """测试真实数据"""
    project_folder = "中金公司_投研大模型"

    print("测试2: 基本统计信息")
    try:
        stats = get_basic_statistics(project_folder)
        if stats:
            print("统计信息:", stats)
            json_str = json.dumps(stats)
            print("✅ 基本统计信息序列化成功")
        else:
            print("⚠️ 未找到统计数据")
    except Exception as e:
        print(f"❌ 基本统计信息失败: {e}")

    print()

    print("测试3: 问题分析")
    try:
        questions = analyze_project_questions(project_folder)
        if questions and len(questions) > 0:
            print(f"找到 {len(questions)} 个问题")
            print("第一个问题:", questions[0])
            json_str = json.dumps(questions[0])
            print("✅ 问题分析序列化成功")
        else:
            print("⚠️ 未找到问题数据")
    except Exception as e:
        print(f"❌ 问题分析失败: {e}")

    print()

    print("测试4: 五个维度评级")
    try:
        ratings = calculate_five_ratings(project_folder)
        if ratings:
            print(f"找到 {len(ratings)} 个评级")
            for key, value in ratings.items():
                print(f"  {key}: score={value['score']}")
            json_str = json.dumps(ratings)
            print("✅ 评级数据序列化成功")
            print("JSON长度:", len(json_str))
        else:
            print("⚠️ 未找到评级数据")
    except Exception as e:
        print(f"❌ 评级计算失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("Numpy类型转换测试")
    print("=" * 60)
    print()

    test_convert_function()
    test_real_data()

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
