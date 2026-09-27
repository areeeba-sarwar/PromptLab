'use client'

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { User } from '@/lib/types'

const AREEBA_API = process.env.NEXT_PUBLIC_AREEBA_API || 'https://laiba52.pythonanywhere.com'
const TOKEN_KEY = 'promptlab_token'
const USER_KEY = 'promptlab_user'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<boolean>
  register: (name: string, email: string, password: string) => Promise<AuthResult>
  verifyRegistration: (email: string, code: string) => Promise<AuthResult>
  resendRegistrationCode: (email: string) => Promise<AuthResult>
  logout: () => void
}

interface AuthResult {
  ok: boolean
  error?: string
  retryAfter?: number
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const savedUser = localStorage.getItem(USER_KEY)
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem(USER_KEY)
      }
    }
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true)
    try {
      const response = await fetch(`${AREEBA_API}/api/areeba/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()
      if (!response.ok) return false

      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      setUser(data.user)
      return true
    } catch (error) {
      console.error('Login error:', error)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  const register = useCallback(async (name: string, email: string, password: string): Promise<AuthResult> => {
    setIsLoading(true)
    try {
      const response = await fetch(`${AREEBA_API}/api/areeba/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: name, email, password })
      })

      const data = await response.json()
      if (!response.ok) return { ok: false, error: data.error || 'Registration failed.' }
      return { ok: true }
    } catch (error) {
      console.error('Register error:', error)
      return { ok: false, error: 'Could not reach the server.' }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const verifyRegistration = useCallback(async (email: string, code: string): Promise<AuthResult> => {
    setIsLoading(true)
    try {
      const response = await fetch(`${AREEBA_API}/api/areeba/verify-registration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code })
      })
      const data = await response.json()
      if (!response.ok) return { ok: false, error: data.error || 'Verification failed.' }

      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      setUser(data.user)
      return { ok: true }
    } catch {
      return { ok: false, error: 'Could not reach the server.' }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const resendRegistrationCode = useCallback(async (email: string): Promise<AuthResult> => {
    setIsLoading(true)
    try {
      const response = await fetch(`${AREEBA_API}/api/areeba/resend-registration-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })
      const data = await response.json()
      if (!response.ok) {
        return { ok: false, error: data.error || 'Could not resend code.', retryAfter: data.retry_after }
      }
      return { ok: true }
    } catch {
      return { ok: false, error: 'Could not reach the server.' }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY)

    if (token) {
      fetch(`${AREEBA_API}/api/areeba/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {})
    }

    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, verifyRegistration, resendRegistrationCode, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function getAuthToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}
