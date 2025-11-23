import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class HTMLReportGenerator:
    """HTML评估报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        pass

    def generate_report(self, analysis_data: Dict[str, Any],
                       evaluation_params: Optional[Dict[str, Any]] = None) -> str:
        """生成HTML评估报告

        Args:
            analysis_data: 分析数据（包含最终统计结果）
            evaluation_params: 评估参数（包含模型名称等），可选

        Returns:
            str: HTML报告内容
        """
        # 提取数据
        model_name = analysis_data.get('model_name', '未知模型')

        # 尝试从多个来源获取评估模型名称
        eval_model_name = '未知评估模型'
        if evaluation_params:
            eval_model_name = evaluation_params.get('eval_model_name', '未知评估模型')
        elif 'evaluation_info' in analysis_data:
            eval_info = analysis_data['evaluation_info']
            if isinstance(eval_info, dict):
                eval_model_name = eval_info.get('eval_model_name', '未知评估模型')

        # 计算知识能力得分（正确率）
        knowledge_score = analysis_data.get('final_accuracy_rate', 0)

        # 计算推理能力得分（需要从评估结果中获取平均推理分数）
        reasoning_score = self._calculate_reasoning_score(analysis_data)

        # 生成标准要求
        knowledge_standard = "综合正确率 ≥ 60分"
        reasoning_standard = "推理得分 ≥ 60分"

        # 生成检验结果（具体分数）
        knowledge_result = f"{knowledge_score:.2f}"
        reasoning_result = f"{reasoning_score:.2f}"

        # 生成检验结论
        knowledge_conclusion = self._get_conclusion(knowledge_score)
        reasoning_conclusion = self._get_conclusion(reasoning_score)

        # 生成HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>大模型能力评估表（知识与推理能力）</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; margin: 24px; color:#111; }}
    h1 {{ font-size: 20px; margin: 0 0 16px; }}
    .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
    .table-wrap {{ overflow-x:auto; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; }}
    thead th {{ background:#f5f5f7; text-align:center; font-weight:600; }}
    th, td {{ border:1px solid #ddd; padding:10px 12px; }}
    tbody td {{ text-align:center; }}
    .item {{ text-align:left; font-weight:600; }}
    .pass {{ color: #52c41a; font-weight: 600; }}
    .basic-pass {{ color: #faad14; font-weight: 600; }}
    .fail {{ color: #f5222d; font-weight: 600; }}
    .hint {{ color:#666; font-size:12px; margin-top:12px; }}
    @media print {{
      body {{ margin: 0; }}
      h1 {{ margin: 0 0 8px; }}
    }}
  </style>
</head>
<body>
  <h1>大模型能力评估表（知识与推理能力）</h1>

  <div class="meta">
    生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>序号</th>
          <th>被评估模型</th>
          <th>评估模型</th>
          <th>能力项</th>
          <th>标准要求</th>
          <th>检验结果</th>
          <th>检验结论</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td>{model_name}</td>
          <td>{eval_model_name}</td>
          <td class="item">大模型内部知识能力</td>
          <td>{knowledge_standard}</td>
          <td>实际得分: {knowledge_result}</td>
          <td class="{self._get_conclusion_class(knowledge_score)}">{knowledge_conclusion}</td>
        </tr>
        <tr>
          <td>2</td>
          <td>{model_name}</td>
          <td>{eval_model_name}</td>
          <td class="item">大模型推理能力</td>
          <td>{reasoning_standard}</td>
          <td>实际得分: {reasoning_result}</td>
          <td class="{self._get_conclusion_class(reasoning_score)}">{reasoning_conclusion}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <p class="hint">
    <strong>填写说明：</strong><br>
    • 被评估模型：待测试的大语言模型<br>
    • 评估模型：用于对模型输出进行评分的参考模型<br>
    • 标准要求：基于百分制评分体系，60分为合格线<br>
    • 检验结果：实际测评得分，采用百分制（0-100分）<br>
    • 检验结论标准：通过（≥80分）/ 基本通过（60-80分）/ 不通过（<60分）<br>
    <br>
    <strong>评估说明：</strong><br>
    • 知识能力：基于Stage1评估，衡量模型在无外部参考内容情况下的知识储备和问答准确性<br>
    • 推理能力：综合Stage1和Stage2评估，衡量模型的逻辑推理、分析和内容理解能力<br>
    • 评分体系：采用百分制（0-100分），基础分0-60分，卓越加分0-40分
  </p>
</body>
</html>"""

        return html_content

    def _calculate_reasoning_score(self, analysis_data: Dict[str, Any]) -> float:
        """计算推理能力得分

        Args:
            analysis_data: 分析数据

        Returns:
            float: 推理能力得分
        """
        # 方法1: 尝试从statistics中直接获取（最可靠）
        statistics = analysis_data.get('statistics', {})
        if statistics:
            # 获取推理错误率，反推推理能力得分
            reasoning_error_rate = statistics.get('reasoning_error_rate', 0)
            accuracy_rate = statistics.get('accuracy_rate', 0)

            # 推理能力 = 100 - 推理错误率（简化计算）
            # 或者使用准确率作为参考
            if reasoning_error_rate > 0 or accuracy_rate > 0:
                # 推理能力得分 = 准确率 (因为准确的回答需要正确的推理)
                return accuracy_rate

        # 方法2: 从评估信息中获取平均推理分数
        eval_info = analysis_data.get('evaluation_info', {})

        # 检查是否为多轮评估
        is_multi_round = eval_info.get('is_multi_round_evaluation', False)

        if is_multi_round:
            # 多轮评估：从汇总数据中获取
            stage1_info = eval_info.get('stage1_round_summary', {})
            stage2_info = eval_info.get('stage2_round_summary', {})

            # 获取Stage1平均推理分数
            stage1_stats = stage1_info.get('aggregated_statistics', {})
            stage1_reasoning = stage1_stats.get('avg_reasoning_score', 0)

            # 获取Stage2平均推理分数
            stage2_stats = stage2_info.get('aggregated_statistics', {}) if stage2_info else {}
            stage2_reasoning = stage2_stats.get('avg_reasoning_score', 0)

            # 如果有Stage2，取加权平均；否则只用Stage1
            if stage2_reasoning > 0:
                return (stage1_reasoning + stage2_reasoning) / 2
            elif stage1_reasoning > 0:
                return stage1_reasoning
        else:
            # 单轮评估：从单轮数据中获取
            stage1_info = eval_info.get('stage1_info', {})
            stage2_info = eval_info.get('stage2_info')

            # 获取Stage1分数分布
            if stage1_info:
                stage1_score_dist = stage1_info.get('score_distribution', {})
                stage1_reasoning = stage1_score_dist.get('avg_reasoning_score', 0)
            else:
                stage1_reasoning = 0

            # 如果有Stage2，也获取其推理分数
            if stage2_info:
                stage2_score_dist = stage2_info.get('score_distribution', {})
                stage2_reasoning = stage2_score_dist.get('avg_reasoning_score', 0)
                if stage2_reasoning > 0 and stage1_reasoning > 0:
                    return (stage1_reasoning + stage2_reasoning) / 2
                elif stage2_reasoning > 0:
                    return stage2_reasoning
                elif stage1_reasoning > 0:
                    return stage1_reasoning
            else:
                if stage1_reasoning > 0:
                    return stage1_reasoning

        # 如果以上都没有获取到，返回准确率作为替代（知识能力的得分）
        return analysis_data.get('final_accuracy_rate', 0)

    def _get_conclusion(self, score: float) -> str:
        """根据分数获取结论

        Args:
            score: 分数（百分制或百分比）

        Returns:
            str: 结论文本
        """
        if score >= 80:
            return "通过"
        elif score >= 60:
            return "基本通过"
        else:
            return "不通过"

    def _get_conclusion_class(self, score: float) -> str:
        """根据分数获取CSS类名

        Args:
            score: 分数

        Returns:
            str: CSS类名
        """
        if score >= 80:
            return "pass"
        elif score >= 60:
            return "basic-pass"
        else:
            return "fail"

    def save_report(self, html_content: str, output_path: Path) -> None:
        """保存HTML报告到文件

        Args:
            html_content: HTML内容
            output_path: 输出路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """测试HTML报告生成器"""
    # 模拟分析数据
    analysis_data = {
        "model_name": "FinLLM-A",
        "final_accuracy_rate": 75.5,
        "evaluation_info": {
            "is_multi_round_evaluation": False,
            "stage1_info": {
                "score_distribution": {
                    "avg_reasoning_score": 68.3
                }
            },
            "stage2_info": {
                "score_distribution": {
                    "avg_reasoning_score": 72.1
                }
            }
        }
    }

    evaluation_info = {
        "eval_model_name": "GPT-4"
    }

    # 生成报告
    generator = HTMLReportGenerator()
    html_content = generator.generate_report(analysis_data, evaluation_info)

    # 保存报告
    output_path = Path("test_report.html")
    generator.save_report(html_content, output_path)

    print(f"测试报告已生成：{output_path}")


if __name__ == "__main__":
    main()
