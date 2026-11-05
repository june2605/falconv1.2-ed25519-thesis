import { createContext, useContext, type PropsWithChildren, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export const TaskFooterHost = createContext<HTMLDivElement | null>(null)

/** Shell-owned action area: stays reachable while the single main area scrolls. */
export function TaskFooter({ label, title, description, children }: PropsWithChildren<{ label: string; title: string; description: ReactNode }>) {
  const host = useContext(TaskFooterHost)
  return host ? createPortal(<section className="task-actions" aria-label={label}>
    <div className="task-action-copy"><strong>{title}</strong><p>{description}</p></div>
    <div className="task-action-buttons">{children}</div>
  </section>, host) : null
}
