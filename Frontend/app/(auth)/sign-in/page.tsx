'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/contexts/auth-context'
import { PromptLabIcon } from '@/components/promptlab-logo'
import {
  Loader2, Mail, Lock, Eye, EyeOff,
  ArrowLeft, BookOpen, Target, Zap,
} from 'lucide-react'

const BRAND_FEATURES = [
  { icon: BookOpen, text: '6 structured chapters with practice sessions' },
  { icon: Target,   text: 'Live AI evaluation and instant scoring' },
  { icon: Zap,      text: 'One-click prompt enhancement with AI' },
]

export default function SignInPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const { login, isLoading } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email || !password) { setError('Please fill in all fields'); return }
    const ok = await login(email, password)
    if (ok) router.push('/dashboard')
    else setError('Invalid email or password. Please try again.')
  }

  return (
    <div className="min-h-screen flex bg-background">

      {/* ── Left panel — branding (desktop only) ── */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between p-10 xl:p-14 bg-gradient-to-br from-primary/8 via-primary/4 to-background border-r border-border relative overflow-hidden">
        {/* Decorative blobs */}
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-12 w-64 h-64 bg-primary/8 rounded-full blur-3xl pointer-events-none" />

        {/* Back link */}
        <Link href="/" className="relative flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit group">
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          Back to home
        </Link>

        {/* Brand content */}
        <div className="relative space-y-8">
          <div className="flex items-center gap-3">
            <PromptLabIcon size={40} className="w-10 h-10 object-contain [filter:brightness(0)_saturate(100%)_invert(21%)_sepia(98%)_saturate(1515%)_hue-rotate(139deg)_brightness(87%)_contrast(101%)]" />
            <span className="text-xl font-bold text-foreground">PromptLab</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl xl:text-4xl font-bold text-foreground leading-tight">
              Master the art of<br />
              <span className="text-primary">prompt engineering</span>
            </h1>
            <p className="text-muted-foreground leading-relaxed">
              Structured courses, real-time AI feedback, and hands-on practice — everything you need to write better prompts.
            </p>
          </div>

          <div className="space-y-3">
            {BRAND_FEATURES.map(f => (
              <div key={f.text} className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="w-7 h-7 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <f.icon className="w-3.5 h-3.5 text-primary" />
                </div>
                {f.text}
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-muted-foreground/60">© 2025 PromptLab. All rights reserved.</p>
      </div>

      {/* ── Right panel — form ── */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">

        {/* Mobile: back + logo */}
        <div className="w-full max-w-sm mb-8 lg:hidden flex items-center justify-between">
          <Link href="/" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors group">
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            Back
          </Link>
          <div className="flex items-center gap-2">
            <PromptLabIcon size={28} className="w-7 h-7 object-contain [filter:brightness(0)_saturate(100%)_invert(21%)_sepia(98%)_saturate(1515%)_hue-rotate(139deg)_brightness(87%)_contrast(101%)]" />
            <span className="font-semibold text-foreground text-sm">PromptLab</span>
          </div>
        </div>

        {/* Form card */}
        <div className="w-full max-w-sm animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both">
          <div className="mb-7">
            <h2 className="text-2xl font-bold text-foreground">Welcome back</h2>
            <p className="text-muted-foreground mt-1 text-sm">Sign in to continue your journey</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm animate-in fade-in duration-200">
                {error}
              </div>
            )}

            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="email">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-11 bg-input border-border focus:border-primary transition-colors"
                  disabled={isLoading}
                  autoComplete="email"
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-foreground" htmlFor="password">Password</label>
                <Link href="/forgot-password" className="text-xs text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-11 h-11 bg-input border-border focus:border-primary transition-colors"
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-0.5"
                  tabIndex={-1}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium transition-all active:scale-[0.98]"
              disabled={isLoading}
            >
              {isLoading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...</>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <p className="mt-6 text-sm text-center text-muted-foreground">
            {"Don't have an account?"}{' '}
            <Link href="/sign-up" className="text-primary hover:underline font-medium">
              Sign up free
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
