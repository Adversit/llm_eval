#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""标记被中断的任务为失败"""
import json
from datetime import datetime

TASKS_FILE = r'D:\work\project\LLM_eval\data\evaluation\tasks.json'
INTERRUPTED_TASK_ID = '4ee336ed-9ce8-4463-9764-4e253b546d60'

# 读取任务数据
with open(TASKS_FILE, 'r', encoding='utf-8') as f:
    tasks = json.load(f)

# 查找并标记被中断的任务
if INTERRUPTED_TASK_ID in tasks:
    task = tasks[INTERRUPTED_TASK_ID]
    if task['status'] == 'processing':
        task['status'] = 'failed'
        task['message'] = '任务被中断（后端重启）'
        task['completed_at'] = datetime.utcnow().isoformat()
        print(f"已将任务 {INTERRUPTED_TASK_ID} 标记为失败")
    else:
        print(f"任务 {INTERRUPTED_TASK_ID} 当前状态: {task['status']}")
else:
    print(f"未找到任务 {INTERRUPTED_TASK_ID}")

# 保存修改后的数据
with open(TASKS_FILE, 'w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print("任务状态已更新")
