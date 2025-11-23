import api from './api'

// 类型定义
interface QATask {
  task_id: string
  filename: string
  task_type: 'generation' | 'evaluation'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  created_at: string
}

interface AllTasksResponse {
  tasks: QATask[]
}

export const qaService = {
  /**
   * 生成问答对
   */
  generateQA: async (
    files: File[],
    options: {
      numPairs: number
      useSuggested: boolean
      suggestQACount?: boolean
      includeReason: boolean
      minDensityScore: number
      minQualityScore: number
      skipExtract?: boolean
      skipEvaluate?: boolean
      skipQA?: boolean
      skipQAEvaluate?: boolean
      minFactualScore?: number
      minOverallScore?: number
      samplePercentage?: number
    }
  ) => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })

    // 根据useSuggested自动推导suggest_qa_count（如果未提供）
    const suggestQaCount = options.suggestQACount ?? options.useSuggested

    const params = new URLSearchParams({
      num_pairs_per_section: String(options.numPairs ?? 5),
      use_suggested_count: String(options.useSuggested),
      include_reason: String(options.includeReason),
      suggest_qa_count: String(suggestQaCount),
      min_density_score: String(options.minDensityScore ?? 5),
      min_quality_score: String(options.minQualityScore ?? 5),
      skip_extract: String(options.skipExtract ?? false),
      skip_evaluate: String(options.skipEvaluate ?? false),
      skip_qa: String(options.skipQA ?? false),
      skip_qa_evaluate: String(options.skipQAEvaluate ?? false),
      min_factual_score: String(options.minFactualScore ?? 7),
      min_overall_score: String(options.minOverallScore ?? 7),
      qa_sample_percentage: String(options.samplePercentage ?? 100),
    })

    const { data } = await api.post(`/qa/generate?${params.toString()}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * 评估问答对
   */
  evaluateQA: async (
    sourceTaskId: string,
    minFactual: number = 7,
    minOverall: number = 7,
    samplePercentage: number = 100
  ) => {
    const { data } = await api.post(`/qa/evaluate-task`, {
      source_task_id: sourceTaskId,
      min_factual_score: minFactual,
      min_overall_score: minOverall,
      sample_percentage: samplePercentage,
    })
    return data
  },

  /**
   * 获取任务状态
   */
  getTaskStatus: async (taskId: string) => {
    return api.get(`/qa/task/${taskId}`)
  },

  /**
   * 下载结果文件
   */
  downloadResult: async (taskId: string) => {
    const response = await fetch(`/api/qa/download/${taskId}`)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `result_${taskId}.xlsx`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  },

  /**
   * 获取统计信息
   */
  getStats: async () => {
    const { data } = await api.get('/qa/stats')
    return data
  },

  /**
   * 获取所有任务（用于结果分析）
   */
  getAllTasks: async (): Promise<AllTasksResponse> => {
    return api.get('/qa/tasks/all')
  },

  /**
   * 预览结果文件
   */
  previewResult: async (taskId: string, limit: number = 100) => {
    return api.get(`/qa/preview/${taskId}`, {
      params: { limit }
    })
  },
}
