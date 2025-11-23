/**
 * 工作流权限守卫Hook
 * 带防抖保护，避免重复弹窗
 */
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal } from 'antd'

interface GuardOptions {
  canAccess: () => boolean
  title: string
  content: string
  redirectPath: string
  redirectLabel: string
}

export const useWorkflowGuard = ({
  canAccess,
  title,
  content,
  redirectPath,
  redirectLabel,
}: GuardOptions) => {
  const navigate = useNavigate()
  const hasShownModal = useRef(false)
  const modalInstance = useRef<ReturnType<typeof Modal.warning> | null>(null)

  useEffect(() => {
    // 如果已经显示过弹窗，不再重复显示
    if (hasShownModal.current) {
      return
    }

    // 检查访问权限
    if (!canAccess()) {
      hasShownModal.current = true

      modalInstance.current = Modal.warning({
        title,
        content,
        okText: redirectLabel,
        onOk: () => {
          navigate(redirectPath)
        },
        onCancel: () => {
          // 如果用户取消，也返回到重定向页面
          navigate(redirectPath)
        },
      })
    }

    // 清理函数
    return () => {
      if (modalInstance.current) {
        modalInstance.current.destroy()
      }
    }
  }, [canAccess, title, content, redirectPath, redirectLabel, navigate])

  return {
    canAccess: canAccess(),
    hasShownModal: hasShownModal.current,
  }
}
