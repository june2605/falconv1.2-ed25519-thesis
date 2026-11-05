import { createContext, useContext, useEffect, useState, type PropsWithChildren } from 'react'
import { connectDesktop, type DesktopConnection } from './desktop'

const DesktopContext = createContext<DesktopConnection>({ mode: 'preview', reason: 'unavailable' })

export function DesktopProvider({ children }: PropsWithChildren) {
  const [connection, setConnection] = useState<DesktopConnection>({ mode: 'preview', reason: 'unavailable' })
  useEffect(() => {
    const controller = new AbortController()
    void connectDesktop(controller.signal).then(value => { if (!controller.signal.aborted) setConnection(value) })
    return () => controller.abort()
  }, [])
  return <DesktopContext.Provider value={connection}>{children}</DesktopContext.Provider>
}

export function useDesktopConnection(): DesktopConnection { return useContext(DesktopContext) }
