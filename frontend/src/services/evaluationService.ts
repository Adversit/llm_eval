/**
 * Evaluation System API Service
 */
import api from './api'

export interface EvaluationUploadResponse {
  success: boolean
  message: string
  files: Array<{
    filename: string
    file_path: string
    size: number
  }>
}

export interface EvaluationTaskResponse {
  success: boolean
  message: string
  task_id: string
}

export interface EvaluationTaskConfig {
  stage1_answer_threshold: number
  stage1_reasoning_threshold: number
  stage2_answer_threshold: number
  stage2_reasoning_threshold: number
  evaluation_rounds: number
  eval_model_name?: string
  stage2_only?: boolean
}

export interface Stage1RoundSummary {
  round_number: number
  statistics?: Record<string, number>
  score_distribution?: Record<string, number>
}

export interface Stage1Summary {
  statistics?: Record<string, number>
  aggregated_statistics?: Record<string, number>
  evaluation_rounds?: number
  thresholds?: Record<string, number>
  score_distribution?: Record<string, number>
  rounds?: Stage1RoundSummary[]
}

export interface Stage2RoundSummary {
  round_number: number
  stage1_statistics?: Record<string, number>
  stage2_statistics?: Record<string, number>
  stage2_thresholds?: Record<string, number>
  need_retest?: number
  stage2_executed?: boolean
}

export interface EvaluationFileResult {
  file_name: string
  source_file: string
  stage1_summary?: Stage1Summary
  stage2_rounds?: Stage2RoundSummary[]
  final_analysis?: {
    final_correct_answers?: number
    final_reasoning_errors?: number
    final_knowledge_deficiency?: number
    final_capability_insufficient?: number
    final_accuracy_rate?: number
    statistics?: Record<string, number>
  }
  stage2_statistics?: Record<string, number>
  analysis?: {
    statistics?: Record<string, number>
    score_distribution?: Record<string, number>
  }
}

export interface EvaluationResultPayload {
  model_name: string
  evaluation_type: string
  files: EvaluationFileResult[]
  summary: {
    total_files: number
    total_questions: number
    final_correct_answers: number
    final_reasoning_errors: number
    final_knowledge_deficiency: number
    final_capability_insufficient: number
    overall_accuracy_rate: number
    files_with_stage2?: number
    multi_file_analysis?: Record<string, any>
  }
  artifacts?: Record<string, string>
}

export interface StageProgressMeta {
  key: string
  label: string
  progress: number
  status: 'pending' | 'active' | 'completed' | 'failed' | 'disabled'
  enabled?: boolean
  message?: string | null
  updated_at?: string | null
}

export interface FileStageProgress {
  stage1?: {
    progress: number
    current_question?: number
    total_questions?: number
  }
  stage2?: {
    progress: number
    current_question?: number
    total_questions?: number
  }
  result?: {
    progress: number
  }
}

export interface FileProgress {
  current_file: number  // 1-based 当前文件索引
  total_files: number
  current_filename?: string  // 当前文件名
  file_stages?: FileStageProgress
}

export type StepKey = 'stage1_infer' | 'stage1_eval' | 'stage2_infer' | 'stage2_eval' | 'analysis'

export interface StepProgress {
  current_step: StepKey  // 当前细分步骤
  step_progress_percent: number  // 当前步骤内的进度 0-100
  current_question?: number  // 当前问题数
  total_questions?: number  // 总问题数
}

export interface EvaluationTaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  current_stage: string
  message: string
  created_at: string
  completed_at?: string
  llm_name?: string
  evaluation_type?: string
  description?: string
  config?: EvaluationTaskConfig
  files?: string[]
  results?: EvaluationResultPayload
  stage_progress?: Record<string, StageProgressMeta>
  file_progress?: FileProgress  // 文件级进度
  step_progress?: StepProgress  // 步骤级进度（细粒度）
  has_stage2?: boolean  // 是否包含第二阶段
}

export interface EvaluationResultsResponse {
  success: boolean
  task_id: string
  llm_name?: string
  evaluation_type?: string
  description?: string
  created_at?: string
  completed_at?: string
  config?: EvaluationTaskConfig
  files?: string[]
  results: EvaluationResultPayload
  stage_progress?: Record<string, StageProgressMeta>
}

export interface EvaluationTaskListItem {
  task_id: string
  llm_name?: string
  status: string
  evaluation_type?: string
  description?: string
  created_at?: string
  completed_at?: string
}

export interface EvaluationTaskListResponse {
  tasks: EvaluationTaskListItem[]
}

export interface EvaluationStats {
  total_tasks: number
  completed_tasks: number
  processing_tasks: number
  failed_tasks: number
  pending_tasks: number
  success_rate: number
}

export interface ServerFileMeta {
  file_name: string
  file_path: string
  size: number
  source: 'upload' | 'history'
  timestamp?: string
  model_name?: string
  updated_at?: string | null
}

export interface ServerHistoryGroup {
  model_name: string
  timestamp: string
  display_name: string
  created_at?: string | null
  result_dir?: string
  files: ServerFileMeta[]
}

export interface ServerFileInventory {
  uploads: ServerFileMeta[]
  history: ServerHistoryGroup[]
}

export interface EvaluationDownloadMetadata {
  task_id: string
  files: Array<{
    file_name: string
    display_name?: string
    formats: Array<{
      format: string
      label: string
      url: string
    }>
  }>
  package: {
    label: string
    url: string
  }
  result_dir?: string | null
  timestamp?: string | null
  timestamp_display?: string | null
}

export interface EvaluationHistoryResponse {
  history: ServerHistoryGroup[]
}

export interface ModelInfo {
  key: string
  display_name: string
  description: string
  model: string
}

export interface ModelsResponse {
  test_models: ModelInfo[]
  eval_models: ModelInfo[]
  default_test_model: string | null
  default_eval_model: string
}

export const evaluationService = {
  /**
   * Upload evaluation files
   */
  uploadFiles: async (files: File[]): Promise<EvaluationUploadResponse> => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const response = await api.post<EvaluationUploadResponse>(
      '/eval/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    return response as any as EvaluationUploadResponse
  },

  /**
   * Create evaluation task
   */
  createTask: async (params: {
    llm_name: string
    evaluation_type: string
    description?: string
    file_paths: string[]
    stage1_answer_threshold: number
    stage1_reasoning_threshold: number
    stage2_answer_threshold: number
    stage2_reasoning_threshold: number
    evaluation_rounds: number
    eval_model_name?: string
  }): Promise<EvaluationTaskResponse> => {
    const formData = new FormData()
    formData.append('llm_name', params.llm_name)
    formData.append('evaluation_type', params.evaluation_type)
    if (params.description) {
      formData.append('description', params.description)
    }
    formData.append('file_paths', JSON.stringify(params.file_paths))
    formData.append('stage1_answer_threshold', params.stage1_answer_threshold.toString())
    formData.append('stage1_reasoning_threshold', params.stage1_reasoning_threshold.toString())
    formData.append('stage2_answer_threshold', params.stage2_answer_threshold.toString())
    formData.append('stage2_reasoning_threshold', params.stage2_reasoning_threshold.toString())
    formData.append('evaluation_rounds', params.evaluation_rounds.toString())
    if (params.eval_model_name) {
      formData.append('eval_model_name', params.eval_model_name)
    }

    const response = await api.post<EvaluationTaskResponse>(
      '/eval/create',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    return response as any as EvaluationTaskResponse
  },

  /**
   * Get task status
   */
  getTaskStatus: async (taskId: string): Promise<EvaluationTaskStatus> => {
    const response = await api.get<EvaluationTaskStatus>(`/eval/task/${taskId}`)
    return response as any as EvaluationTaskStatus
  },

  /**
   * Get evaluation results
   */
  getResults: async (taskId: string): Promise<EvaluationResultsResponse> => {
    const response = await api.get<EvaluationResultsResponse>(`/eval/results/${taskId}`)
    return response as any as EvaluationResultsResponse
  },

  /**
   * List evaluation tasks
   */
  listTasks: async (): Promise<EvaluationTaskListResponse> => {
    const response = await api.get<EvaluationTaskListResponse>('/eval/tasks')
    return response as any as EvaluationTaskListResponse
  },

  /**
   * Get evaluation statistics
   */
  getStats: async (): Promise<EvaluationStats> => {
    const response = await api.get<EvaluationStats>('/eval/stats')
    return response as any as EvaluationStats
  },

  /**
   * 获取服务器端文件信息
   */
  listServerFiles: async (llmName?: string): Promise<ServerFileInventory> => {
    const response = await api.get<ServerFileInventory>('/eval/files', {
      params: llmName ? { llm_name: llmName } : undefined,
    })
    return response as any as ServerFileInventory
  },

  /**
   * 获取下载链接
   */
  getDownloadLinks: async (taskId: string): Promise<EvaluationDownloadMetadata> => {
    const response = await api.get<EvaluationDownloadMetadata>(`/eval/downloads/${taskId}`)
    return response as any as EvaluationDownloadMetadata
  },

  /**
   * 历史时间戳目录
   */
  listHistory: async (llmName?: string): Promise<EvaluationHistoryResponse> => {
    const response = await api.get<EvaluationHistoryResponse>('/eval/history', {
      params: llmName ? { llm_name: llmName } : undefined,
    })
    return response as any as EvaluationHistoryResponse
  },

  /**
   * 获取可用的模型列表
   */
  getAvailableModels: async (): Promise<ModelsResponse> => {
    const response = await api.get<ModelsResponse>('/eval/models')
    return response as any as ModelsResponse
  },

  /**
   * 获取所有任务（用于工作台）
   */
  getAllTasks: async (): Promise<{ tasks: any[] }> => {
    return api.get('/eval/tasks')
  },
}
