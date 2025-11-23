/**
 * 工作流状态管理
 * 确保各模块的步骤按顺序执行
 */

// 本地存储键名
const STORAGE_KEY = 'llm_eval_workflow_state'

export type EvaluationStageKey = 'init' | 'stage1' | 'stage2' | 'result'

export interface WorkflowStageSnapshot {
  key: EvaluationStageKey
  label: string
  progress: number
  status: 'pending' | 'active' | 'completed' | 'failed' | 'disabled'
  enabled: boolean
  message?: string | null
  updatedAt?: string | null
}

export interface EvaluationParamsState {
  stage1_answer_threshold: number
  stage1_reasoning_threshold: number
  stage2_answer_threshold: number
  stage2_reasoning_threshold: number
  evaluation_rounds: number
}

export interface QAParamsState {
  numPairs: number
  useSuggested: boolean
  includeReason: boolean
  minDensityScore: number
  minQualityScore: number
  skipExtract: boolean
  skipEvaluate: boolean
  skipQA: boolean
  skipQAEvaluate: boolean
  enableQAEvaluation: boolean
  minFactualScore: number
  minOverallScore: number
  samplePercentage: number
}

const defaultEvaluationParams: EvaluationParamsState = {
  stage1_answer_threshold: 60,
  stage1_reasoning_threshold: 60,
  stage2_answer_threshold: 60,
  stage2_reasoning_threshold: 60,
  evaluation_rounds: 1,
}

const defaultQAParams: QAParamsState = {
  numPairs: 5,
  useSuggested: false,
  includeReason: true,
  minDensityScore: 5,
  minQualityScore: 5,
  skipExtract: false,
  skipEvaluate: false,
  skipQA: false,
  skipQAEvaluate: false,
  enableQAEvaluation: true,
  minFactualScore: 7,
  minOverallScore: 7,
  samplePercentage: 100,
}

const createDefaultEvaluationStages = (): Record<EvaluationStageKey, WorkflowStageSnapshot> => ({
  init: { key: 'init', label: '初始化', progress: 0, status: 'active', enabled: true, message: null, updatedAt: undefined },
  stage1: { key: 'stage1', label: '第一阶段评估', progress: 0, status: 'pending', enabled: true, message: null, updatedAt: undefined },
  stage2: { key: 'stage2', label: '第二阶段评估', progress: 0, status: 'pending', enabled: true, message: null, updatedAt: undefined },
  result: { key: 'result', label: '结果处理', progress: 0, status: 'pending', enabled: true, message: null, updatedAt: undefined },
})

// 工作流状态接口
export interface WorkflowState {
  // FLMM问卷平台
  flmm: {
    processCompleted: boolean
    projectId?: string
  }

  // 问答管理模块
  qa: {
    processCompleted: boolean
    taskId?: string
    generateTaskId?: string
    evaluateTaskId?: string
    step?: number
    params: QAParamsState
  }

  // 双阶段评测系统
  evaluation: {
    workflowCompleted: boolean
    evaluationId?: string
    stages: Record<EvaluationStageKey, WorkflowStageSnapshot>
    params: EvaluationParamsState
  }
}

// 默认状态
const defaultState: WorkflowState = {
  flmm: {
    processCompleted: false,
  },
  qa: {
    processCompleted: false,
    step: 0,
    params: { ...defaultQAParams },
  },
  evaluation: {
    workflowCompleted: false,
    stages: createDefaultEvaluationStages(),
    params: { ...defaultEvaluationParams },
  },
}

// 工作流存储类
class WorkflowStore {
  private state: WorkflowState
  private listeners: Set<(state: WorkflowState) => void> = new Set()
  private hasStorage = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'

  constructor() {
    this.state = this.loadState()
  }

  // 订阅状态变化
  subscribe(listener: (state: WorkflowState) => void): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  // 通知所有监听器
  private notify(): void {
    this.listeners.forEach(listener => listener(this.getState()))
  }

  // 从本地存储加载状态
  private loadState(): WorkflowState {
    if (!this.hasStorage) return { ...defaultState }
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        return {
          flmm: {
            ...defaultState.flmm,
            ...(parsed.flmm || {}),
          },
          qa: {
            ...defaultState.qa,
            ...(parsed.qa || {}),
            step: parsed.qa?.step ?? defaultState.qa.step,
            params: {
              ...defaultQAParams,
              ...(parsed.qa?.params || {}),
            },
          },
          evaluation: {
            ...defaultState.evaluation,
            ...(parsed.evaluation || {}),
            stages: parsed.evaluation?.stages || createDefaultEvaluationStages(),
            params: {
              ...defaultEvaluationParams,
              ...(parsed.evaluation?.params || {}),
            },
          },
        }
      }
    } catch (e) {
      console.error('Failed to load workflow state:', e)
    }
    return {
      flmm: { ...defaultState.flmm },
      qa: { ...defaultState.qa },
      evaluation: {
        workflowCompleted: false,
        evaluationId: undefined,
        stages: createDefaultEvaluationStages(),
        params: { ...defaultEvaluationParams },
      },
    }
  }

  // 保存状态到本地存储
  private saveState(): void {
    try {
      if (this.hasStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state))
      }
      this.notify()
    } catch (e) {
      console.error('Failed to save workflow state:', e)
    }
  }

  private ensureEvaluationStages(): Record<EvaluationStageKey, WorkflowStageSnapshot> {
    if (!this.state.evaluation.stages) {
      this.state.evaluation.stages = createDefaultEvaluationStages()
    }
    return this.state.evaluation.stages
  }

  // 获取完整状态
  getState(): WorkflowState {
    return { ...this.state }
  }

  // ========== FLMM模块 ==========

  setFLMMProcessCompleted(projectId?: string): void {
    this.state.flmm.processCompleted = true
    this.state.flmm.projectId = projectId
    this.saveState()
  }

  canAccessFLMMAnalysis(): boolean {
    return this.state.flmm.processCompleted
  }

  resetFLMM(): void {
    this.state.flmm = { processCompleted: false }
    this.saveState()
  }

  // ========== QA模块 ==========

  setQAProcessCompleted(taskId?: string): void {
    this.state.qa.processCompleted = true
    this.state.qa.taskId = taskId
    this.saveState()
  }

  setQAGenerateTaskId(taskId: string): void {
    this.state.qa.generateTaskId = taskId
    this.saveState()
  }

  setQAEvaluateTaskId(taskId: string): void {
    this.state.qa.evaluateTaskId = taskId
    this.saveState()
  }

  setQAStep(step: number): void {
    this.state.qa.step = step
    this.saveState()
  }

  saveQAParams(params: Partial<QAParamsState>): void {
    this.state.qa.params = {
      ...this.state.qa.params,
      ...params,
    }
    this.saveState()
  }

  canAccessQAAnalysis(): boolean {
    return this.state.qa.processCompleted
  }

  resetQA(): void {
    this.state.qa = {
      processCompleted: false,
      step: undefined,
      params: { ...defaultQAParams },
    }
    this.saveState()
  }

  // ========== 评测系统模块 ==========

  setEvaluationWorkflowCompleted(evaluationId?: string): void {
    this.state.evaluation.workflowCompleted = true
    this.state.evaluation.evaluationId = evaluationId
    this.saveState()
  }

  canAccessEvaluationAnalysis(): boolean {
    return this.state.evaluation.workflowCompleted
  }

  resetEvaluation(): void {
    this.state.evaluation = {
      workflowCompleted: false,
      evaluationId: undefined,
      stages: createDefaultEvaluationStages(),
      params: { ...defaultEvaluationParams },
    }
    this.saveState()
  }

  saveEvaluationParams(params: Partial<EvaluationParamsState>): void {
    this.state.evaluation.params = {
      ...this.state.evaluation.params,
      ...params,
    }
    this.saveState()
  }

  updateEvaluationStage(stageKey: EvaluationStageKey, snapshot: Partial<WorkflowStageSnapshot>): void {
    const stages = this.ensureEvaluationStages()
    const base = stages[stageKey] || createDefaultEvaluationStages()[stageKey]
    stages[stageKey] = {
      ...base,
      ...snapshot,
    }
    this.state.evaluation.stages = { ...stages }
    this.saveState()
  }

  bulkUpdateEvaluationStages(stageMap: Record<string, Partial<WorkflowStageSnapshot>>): void {
    const stages = this.ensureEvaluationStages()
    const validKeys: EvaluationStageKey[] = ['init', 'stage1', 'stage2', 'result']
    Object.entries(stageMap).forEach(([key, snapshot]) => {
      if (!validKeys.includes(key as EvaluationStageKey)) {
        return
      }
      const typedKey = key as EvaluationStageKey
      if (!stages[typedKey]) {
        stages[typedKey] = createDefaultEvaluationStages()[typedKey]
      }
      const current = stages[typedKey]
      stages[typedKey] = {
        ...current,
        ...snapshot,
      }
    })
    this.state.evaluation.stages = { ...stages }
    this.saveState()
  }

  resetEvaluationStages(): void {
    this.state.evaluation.stages = createDefaultEvaluationStages()
    this.saveState()
  }

  // ========== 全局操作 ==========

  resetAll(): void {
    this.state = {
      flmm: { ...defaultState.flmm },
      qa: { ...defaultState.qa },
      evaluation: {
        workflowCompleted: false,
        evaluationId: undefined,
        stages: createDefaultEvaluationStages(),
        params: { ...defaultEvaluationParams },
      },
    }
    this.saveState()
  }
}

// 导出单例
export const workflowStore = new WorkflowStore()
