/**
 * 工作流状态管理Hook
 */
import { useState, useEffect, useMemo } from 'react'
import { workflowStore, WorkflowState } from '../store/workflowStore'

export const useWorkflow = () => {
  const [state, setState] = useState<WorkflowState>(workflowStore.getState())

  // 订阅状态变化（替代轮询机制）
  useEffect(() => {
    const unsubscribe = workflowStore.subscribe((newState) => {
      setState(newState)
    })

    return unsubscribe
  }, [])

  // 使用 useMemo 固定函数引用,避免每次渲染都生成新的 bind 函数
  const methods = useMemo(() => ({
    // FLMM
    setFLMMProcessCompleted: workflowStore.setFLMMProcessCompleted.bind(workflowStore),
    canAccessFLMMAnalysis: workflowStore.canAccessFLMMAnalysis.bind(workflowStore),
    resetFLMM: workflowStore.resetFLMM.bind(workflowStore),

    // QA
    setQAProcessCompleted: workflowStore.setQAProcessCompleted.bind(workflowStore),
    setQAGenerateTaskId: workflowStore.setQAGenerateTaskId.bind(workflowStore),
    setQAEvaluateTaskId: workflowStore.setQAEvaluateTaskId.bind(workflowStore),
    saveQAParams: workflowStore.saveQAParams.bind(workflowStore),
    canAccessQAAnalysis: workflowStore.canAccessQAAnalysis.bind(workflowStore),
    resetQA: workflowStore.resetQA.bind(workflowStore),
    setQAStep: workflowStore.setQAStep.bind(workflowStore),

    // Evaluation
    setEvaluationWorkflowCompleted: workflowStore.setEvaluationWorkflowCompleted.bind(workflowStore),
    canAccessEvaluationAnalysis: workflowStore.canAccessEvaluationAnalysis.bind(workflowStore),
    resetEvaluation: workflowStore.resetEvaluation.bind(workflowStore),
    saveEvaluationParams: workflowStore.saveEvaluationParams.bind(workflowStore),
    updateEvaluationStage: workflowStore.updateEvaluationStage.bind(workflowStore),
    bulkUpdateEvaluationStages: workflowStore.bulkUpdateEvaluationStages.bind(workflowStore),
    resetEvaluationStages: workflowStore.resetEvaluationStages.bind(workflowStore),

    // Global
    resetAll: workflowStore.resetAll.bind(workflowStore),
  }), [])

  return {
    state,
    ...methods,
  }
}
