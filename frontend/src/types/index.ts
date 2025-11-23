export interface QAPair {
  question: string
  answer: string
  title?: string
  content?: string
  question_number?: string
}

export interface QAEvaluation {
  question: string
  answer: string
  factual_score: number
  completeness_score: number
  overall_score: number
  key_points: string[]
  supported_points: string[]
  unsupported_points: string[]
  evaluation_reason: string
  is_passed: boolean
}

export interface QATaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  completed_at?: string
  result_file?: string
  current_step?: string
  logs?: TaskLogEntry[]
}

export interface QAStats {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  processing_tasks: number
  success_rate: number
}

export interface TaskLogEntry {
  timestamp: string
  message: string
}
