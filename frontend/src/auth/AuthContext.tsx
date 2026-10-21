import { createContext, useContext, useEffect, useState } from 'react'
import { clearSession, getSession, setSession } from '../api/client'

const AuthCtx = createContext<any>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState(getSession())

  useEffect(() => {
    setSessionState(getSession())
  }, [])

  const login = (access: string, refresh: string, user: any) => {
    setSession(access, refresh, user)
    setSessionState(getSession())
  }

  const logout = () => {
    clearSession()
    setSessionState(getSession())
  }

  return <AuthCtx.Provider value={{ ...session, login, logout }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
