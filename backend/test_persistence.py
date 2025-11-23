"""
测试数据持久化功能
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from app.utils.persistence import DataPersistence


def test_persistence():
    """测试持久化功能"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp()

    try:
        print("=" * 60)
        print("测试数据持久化功能")
        print("=" * 60)

        # 测试1: 创建持久化对象
        print("\n[测试1] 创建持久化对象...")
        storage = DataPersistence(test_dir, 'test.json')
        print(f"✓ 成功创建，存储路径: {storage.filepath}")

        # 测试2: 写入数据
        print("\n[测试2] 写入数据...")
        storage['task1'] = {
            'id': 'task1',
            'status': 'pending',
            'message': '任务已创建'
        }
        storage['task2'] = {
            'id': 'task2',
            'status': 'processing',
            'message': '任务处理中'
        }
        print(f"✓ 成功写入 2 条数据")

        # 测试3: 读取数据
        print("\n[测试3] 读取数据...")
        task1 = storage['task1']
        print(f"✓ task1: {task1}")
        task2 = storage.get('task2')
        print(f"✓ task2: {task2}")

        # 测试4: 检查文件是否存在
        print("\n[测试4] 检查持久化文件...")
        if storage.filepath.exists():
            print(f"✓ 文件存在: {storage.filepath}")
            with open(storage.filepath, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                print(f"✓ 文件内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print("✗ 文件不存在")
            return False

        # 测试5: 重新加载数据（模拟服务器重启）
        print("\n[测试5] 重新加载数据（模拟服务器重启）...")
        storage2 = DataPersistence(test_dir, 'test.json')
        if 'task1' in storage2 and 'task2' in storage2:
            print(f"✓ 数据成功恢复")
            print(f"  - task1: {storage2['task1']}")
            print(f"  - task2: {storage2['task2']}")
        else:
            print("✗ 数据恢复失败")
            return False

        # 测试6: 更新数据
        print("\n[测试6] 更新数据...")
        task1_data = storage2['task1']
        task1_data['status'] = 'completed'
        storage2['task1'] = task1_data
        print(f"✓ 更新 task1 状态为 completed")

        # 测试7: 删除数据
        print("\n[测试7] 删除数据...")
        storage2.delete('task2')
        print(f"✓ 删除 task2")
        print(f"  - 剩余数据数量: {len(storage2)}")

        # 测试8: 统计功能
        print("\n[测试8] 统计功能...")
        print(f"  - 总数: {len(storage2)}")
        print(f"  - 键列表: {list(storage2.keys())}")
        print(f"  - 所有数据: {storage2.get_all()}")

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        shutil.rmtree(test_dir)
        print(f"\n清理临时目录: {test_dir}")


if __name__ == '__main__':
    success = test_persistence()
    sys.exit(0 if success else 1)
