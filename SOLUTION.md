# QA模块进度显示优化方案

## 问题分析

### 当前状态
1. **问答对生成任务（generation）**：包含3个阶段
   - 内容提取
   - 内容质量评估（前评估）
   - 问答对生成
   - ✅ 有 progress_callback，实时更新进度和日志

2. **问答对质量评估任务（evaluation）**：单一阶段
   - 问答对质量评估（后评估）
   - ❌ **没有 progress_callback**，只在开始和结束更新

### 具体问题
1. 评估任务进度跳跃：5% → 100%（中间没有细粒度更新）
2. 评估日志缺失：评估过程中的详细日志（如"正在评估 10/50"）只打印到终端
3. 前端显示不够直观：日志列表只显示最新一条

## 解决方案

### 方案A：完整方案（推荐）

#### 1. 后端修改

**修改 `QA/evaluate_qa.py` - 添加 progress_callback 支持**

```python
def process_qa_and_evaluate(
    qa_excel,
    output_excel=None,
    min_factual_score=7,
    min_overall_score=7,
    sample_percentage=100,
    progress_callback=None  # 新增参数
):
    """
    处理问答Excel文件并评估每个问答对的质量

    参数:
        ...
        progress_callback (callable, optional): 进度回调函数，接收 (step_name, progress, message)
    """
    try:
        # ... existing code ...

        # 在开始时调用回调
        if progress_callback:
            progress_callback("初始化", 0.05, "开始读取问答Excel文件")

        # 读取Excel文件
        df = pd.read_excel(qa_excel)

        # ... validation code ...

        if progress_callback:
            progress_callback("准备评估", 0.10, f"将评估 {sample_size}/{total_rows} 个问答对")

        # 遍历选中的问答对
        evaluated_count = 0
        for index in sample_indices:
            row = df.loc[index]
            question = row['问题']
            answer = row['答案']
            content = row['内容']

            evaluated_count += 1

            # 计算当前进度（10% - 90%）
            current_progress = 0.10 + (evaluated_count / sample_size) * 0.80
            message = f"正在评估 [{evaluated_count}/{sample_size}]: {question[:30]}..."

            if progress_callback:
                progress_callback("问答对质量评估", current_progress, message)

            print(message)

            # ... evaluation code ...

        # 保存结果
        if progress_callback:
            progress_callback("保存结果", 0.95, "正在保存评估结果")

        df.to_excel(output_excel, index=False)

        if progress_callback:
            progress_callback("完成", 1.0, "评估完成")

        return True

    except Exception as e:
        if progress_callback:
            progress_callback("错误", 0, f"评估失败: {str(e)}")
        raise
```

**修改 `backend/app/api/qa.py` - 传递 progress_callback**

```python
def process_qa_evaluation(task_id: str, file_path: str, output_path: str, min_factual: int, min_overall: int, sample_pct: float):
    """后台任务：评估问答对"""
    try:
        # 定义进度回调
        def progress_callback(step_name, step_progress, message=None):
            progress_percent = max(0, min(100, round(step_progress * 100, 2)))
            _update_task(
                task_id,
                status='processing',
                message=message or '处理中',
                progress=progress_percent,
                current_step=step_name
            )
            _append_task_log(task_id, f"[{step_name}] {message}" if message else step_name)

        # 初始化
        progress_callback('初始化', 0.01, '开始问答质量评估')

        # 调用评估函数，传入回调
        success = process_qa_and_evaluate(
            qa_excel=file_path,
            output_excel=output_path,
            min_factual_score=min_factual,
            min_overall_score=min_overall,
            sample_percentage=sample_pct,
            progress_callback=progress_callback  # 传递回调
        )

        if success:
            _update_task(
                task_id,
                status='completed',
                progress=100,
                message='问答对评估完成',
                result_file=output_path,
                completed_at=datetime.now(),
                current_step='完成'
            )
            _append_task_log(task_id, '评估完成')
        else:
            # ... error handling ...
    except Exception as e:
        # ... error handling ...
```

#### 2. 前端修改

**修改 `frontend/src/pages/QA/Process.tsx` - 显示完整日志列表**

在任务详情中添加日志展开功能：

```typescript
// 在 renderStep2 中，任务详情卡片内
{item.status?.logs && item.status.logs.length > 0 && (
  <div style={{ marginTop: 8 }}>
    <Collapse
      ghost
      items={[{
        key: 'logs',
        label: (
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              查看完整日志 ({item.status.logs.length} 条)
            </Text>
          </Space>
        ),
        children: (
          <List
            size="small"
            dataSource={item.status.logs}
            renderItem={(log: any, idx: number) => (
              <List.Item key={idx} style={{ padding: '4px 0', borderBottom: 'none' }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  [{log.timestamp}] {log.message}
                </Text>
              </List.Item>
            )}
            style={{
              maxHeight: 200,
              overflowY: 'auto',
              background: '#fafafa',
              padding: 8,
              borderRadius: 4
            }}
          />
        )
      }]}
    />
  </div>
)}
```

**优化轮询频率（可选）**

```typescript
// 将轮询间隔改为500ms，获得更流畅的体验
refetchInterval: (query) => {
  const status = query?.state?.data?.status
  if (status === 'completed' || status === 'failed') {
    return false
  }
  return 500  // 从1000改为500
}
```

### 方案B：简化方案（快速实现）

如果暂时不修改 `evaluate_qa.py`，可以只修改后端API：

**修改 `backend/app/api/qa.py`**

```python
def process_qa_evaluation(task_id: str, file_path: str, output_path: str, min_factual: int, min_overall: int, sample_pct: float):
    """后台任务：评估问答对"""
    try:
        # 读取文件获取总数
        df = pd.read_excel(file_path)
        total_rows = len(df)
        sample_size = max(1, int(total_rows * sample_pct / 100))

        _update_task(task_id, status='processing', message=f'准备评估 {sample_size}/{total_rows} 个问答对', progress=5, current_step='准备评估')
        _append_task_log(task_id, f'开始评估，总数: {sample_size}')

        # 模拟中间进度（粗粒度）
        import threading
        import time

        # 在子线程中模拟进度更新
        stop_progress = False
        def update_progress():
            progress = 10
            while not stop_progress and progress < 90:
                time.sleep(3)  # 每3秒更新一次
                if not stop_progress:
                    progress = min(progress + 10, 90)
                    _update_task(
                        task_id,
                        status='processing',
                        message=f'正在评估问答对质量...',
                        progress=progress,
                        current_step='问答对质量评估'
                    )

        progress_thread = threading.Thread(target=update_progress)
        progress_thread.start()

        try:
            success = process_qa_and_evaluate(
                qa_excel=file_path,
                output_excel=output_path,
                min_factual_score=min_factual,
                min_overall_score=min_overall,
                sample_percentage=sample_pct
            )
        finally:
            stop_progress = True
            progress_thread.join()

        # ... rest of the code ...
```

## 推荐实施顺序

1. **第一阶段（2小时）**：
   - 实施方案A的后端修改
   - 测试评估任务的进度更新

2. **第二阶段（1小时）**：
   - 实施前端的日志展开功能
   - 优化轮询频率

3. **第三阶段（测试）**：
   - 上传文档测试完整流程
   - 验证进度条和日志是否实时更新

## 预期效果

### 优化前
- 生成任务：✅ 实时进度，✅ 详细日志
- 评估任务：❌ 跳跃进度（5% → 100%），❌ 缺少日志

### 优化后
- 生成任务：✅ 实时进度，✅ 详细日志
- 评估任务：✅ 实时进度（5% → 10% → 20% → ... → 100%），✅ 详细日志（"正在评估 10/50"）
- 前端显示：✅ 可展开查看完整日志，✅ 更流畅的进度更新

## 技术细节

### 进度计算公式
```
评估任务进度 = 10% + (已评估数 / 总数) * 80%
- 0-10%: 初始化和准备
- 10-90%: 评估过程（线性增长）
- 90-100%: 保存结果和完成
```

### 日志格式
```
[步骤名称] 详细信息
例如：
[初始化] 开始读取问答Excel文件
[准备评估] 将评估 50/100 个问答对
[问答对质量评估] 正在评估 [10/50]: 什么是机器学习？...
[保存结果] 正在保存评估结果
[完成] 评估完成
```
