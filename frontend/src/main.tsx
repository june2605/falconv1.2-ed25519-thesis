import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import './styles.css'
import './desktop.css'
import App from './App'
import { WorkspaceProvider } from './state/workspace'
import { DesktopProvider } from './native/status'
import { NativeVaultProvider } from './native/vault'

createRoot(document.getElementById('root')!).render(<StrictMode><DesktopProvider><WorkspaceProvider><NativeVaultProvider><App /></NativeVaultProvider></WorkspaceProvider></DesktopProvider></StrictMode>)
