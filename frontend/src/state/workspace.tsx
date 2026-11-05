import { createContext, useCallback, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react'
import type { Appearance, DemoVault, PreviewActivity, ToastMessage, VaultDialog } from '../models'
import { initialDemoVault } from '../services/demo'

interface WorkspaceState {
  vault: DemoVault | null
  setVault: (vault: DemoVault | null) => void
  activities: PreviewActivity[]
  addActivity: (activity: Omit<PreviewActivity, 'id' | 'at'>) => void
  clearActivity: () => void
  dialog: VaultDialog | null
  setDialog: (dialog: VaultDialog | null) => void
  appearance: Appearance
  setAppearance: (appearance: Appearance) => void
  reducedMotion: boolean
  setReducedMotion: (value: boolean) => void
  toasts: ToastMessage[]
  notify: (title: string, detail?: string, tone?: ToastMessage['tone']) => void
  dismissToast: (id: number) => void
  reset: () => void
}

const WorkspaceContext = createContext<WorkspaceState | null>(null)

export function WorkspaceProvider({ children }: PropsWithChildren) {
  const [vault, setVault] = useState<DemoVault | null>(initialDemoVault)
  const [activities, setActivities] = useState<PreviewActivity[]>([])
  const [dialog, setDialog] = useState<VaultDialog | null>(null)
  const [appearance, setAppearance] = useState<Appearance>('light')
  const [reducedMotion, setReducedMotion] = useState(false)
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const counter = useRef(0)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => {
      document.documentElement.dataset.theme = appearance === 'system' ? media.matches ? 'dark' : 'light' : appearance
    }
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [appearance])

  useEffect(() => {
    document.documentElement.classList.toggle('reduce-motion', reducedMotion)
  }, [reducedMotion])

  const notify = useCallback<WorkspaceState['notify']>((title, detail, tone = 'info') => {
    setToasts(current => [...current.slice(-2), { id: ++counter.current, title, detail, tone }])
  }, [])
  const dismissToast = useCallback((id: number) => setToasts(current => current.filter(toast => toast.id !== id)), [])
  const addActivity: WorkspaceState['addActivity'] = activity => {
    setActivities(current => [{ ...activity, id: `preview-event-${++counter.current}`, at: Date.now() }, ...current].slice(0, 8))
  }

  return <WorkspaceContext.Provider value={{ vault, setVault, activities, addActivity,
    clearActivity: () => setActivities([]), dialog, setDialog, appearance, setAppearance,
    reducedMotion, setReducedMotion, toasts, notify,
    dismissToast,
    reset: () => { setVault(initialDemoVault()); setActivities([]); notify('UI preview reset', 'Demo vault and activity have been reset. No files were changed.') },
  }}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace(): WorkspaceState {
  const context = useContext(WorkspaceContext)
  if (!context) throw new Error('Workspace provider is missing')
  return context
}
