import { createContext, useContext } from 'react'
import type { UserRole } from './types'

export interface SessionState {
  role: UserRole
  entityId: string
}

// Current demo identity (role + reporting entity). Provided by AppLayout and
// consumed by pages via useSession(). Context — not localStorage-at-render —
// so that switching entity in the topbar re-renders the open page immediately
// instead of requiring a manual refresh.
export const SessionContext = createContext<SessionState>({ role: 'hq', entityId: '' })

export const useSession = () => useContext(SessionContext)
