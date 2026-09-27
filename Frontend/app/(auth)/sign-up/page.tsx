'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/contexts/auth-context'
import {
  Sparkles, Loader2, Mail, Lock, User, Eye, EyeOff,
  ArrowLeft, Check, X, BookOpen, Target, Zap, KeyRound,
} from 'lucide-react'

// ── Password validation ────────────────────────────────────────
// Rule: ≥ 6 chars, 1 uppercase, 1 lowercase, 1 symbol (no number required)
interface Reqs {
  minLength: boolean
  uppercase: boolean
  lowercase: boolean
  special: boolean
}

function checkPassword(pw: string): Reqs {
  return {
    minLength: pw.length >= 6,
    uppercase: /[A-Z]/.test(pw),
    lowercase: /[a-z]/.test(pw),
    special:   /[^A-Za-z0-9]/.test(pw),
  }
}

const REQUIREMENTS: { key: keyof Reqs; label: string }[] = [
  { key: 'minLength', label: 'At least 6 characters' },
  { key: 'uppercase', label: 'One uppercase letter (A–Z)' },
  { key: 'lowercase', label: 'One lowercase letter (a–z)' },
  { key: 'special',   label: 'One symbol (@, #, $, %…)' },
]

function strengthInfo(count: number) {
  if (count === 0) return { label: '', textCls: '' }
  if (count === 1) return { label: 'Weak',   textCls: 'text-red-500' }
  if (count <= 3)  return { label: 'Medium', textCls: 'text-amber-500' }
  return               { label: 'Strong', textCls: 'text-emerald-500' }
}

const BRAND_FEATURES = [
  { icon: BookOpen, text: '6 structured chapters with practice sessions' },
  { icon: Target,   text: 'Live AI evaluation and instant scoring' },
  { icon: Zap,      text: 'One-click prompt enhancement with AI' },
]

// ── Component ─────────────────────────────────────────────────
export default function SignUpPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'details' | 'verify'>('details')
  const [code, setCode] = useState('')
  const [cooldown, setCooldown] = useState(0)
  const [notice, setNotice] = useState('')
  const { register, verifyRegistration, resendRegistrationCode, isLoading } = useAuth()
  const router = useRouter()

  const reqs = checkPassword(password)
  const metCount = Object.values(reqs).filter(Boolean).length
  const strength = strengthInfo(metCount)
  const allMet = metCount === 4
  const confirmMismatch = confirm !== '' && password !== confirm
  const confirmMatch = confirm !== '' && password === confirm

  // Strength bar segments
  const seg1 = metCount >= 1  // red
  const seg2 = metCount >= 2  // amber
  const seg3 = metCount === 4 // green

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown(value => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name || !email || !password || !confirm) { setError('Please fill in all fields'); return }
    if (!allMet) { setError('Your password does not meet the strength requirements below'); return }
    if (password !== confirm) { setError('Passwords do not match'); return }
    const result = await register(name, email, password)
    if (result.ok) {
      setStep('verify')
      setCooldown(45)
      setNotice(`We sent a 6-digit verification code to ${email}.`)
    } else {
      setError(result.error || 'Registration failed.')
    }
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setNotice('')
    if (code.length !== 6) { setError('Enter the 6-digit verification code.'); return }
    const result = await verifyRegistration(email, code)
    if (result.ok) router.push('/dashboard')
    else setError(result.error || 'Invalid code, please try again.')
  }

  const handleResend = async () => {
    if (cooldown > 0 || isLoading) return
    setError('')
    setNotice('')
    const result = await resendRegistrationCode(email)
    if (result.ok) {
      setCooldown(45)
      setNotice('A new verification code was sent.')
    } else {
      if (result.retryAfter) setCooldown(result.retryAfter)
      setError(result.error || 'Could not resend code.')
    }
  }

  return (
    <div className="min-h-screen flex bg-background">

      {/* ── Left panel — branding (desktop only) ── */}
      <div className="hidden lg:flex lg:w-[42%] flex-col justify-between p-10 xl:p-14 bg-gradient-to-br from-primary/8 via-primary/4 to-background border-r border-border relative overflow-hidden">
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-12 w-64 h-64 bg-primary/8 rounded-full blur-3xl pointer-events-none" />

        <Link href="/" className="relative flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit group">
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          Back to home
        </Link>

        <div className="relative space-y-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">PromptLab</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl xl:text-4xl font-bold text-foreground leading-tight">
              Start your journey<br />
              <span className="text-primary">today — it's free</span>
            </h1>
            <p className="text-muted-foreground leading-relaxed">
              Join learners who are improving their AI skills with structured courses and real-time feedback.
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
            <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-primary-foreground" />
            </div>
            <span className="font-semibold text-foreground text-sm">PromptLab</span>
          </div>
        </div>

        {/* Form */}
        <div className="w-full max-w-sm animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both">
          <div className="mb-7">
            <h2 className="text-2xl font-bold text-foreground">
              {step === 'details' ? 'Create your account' : 'Verify your email'}
            </h2>
            <p className="text-muted-foreground mt-1 text-sm">
              {step === 'details' ? 'Start mastering prompt engineering today' : `Enter the verification code sent to ${email}`}
            </p>
          </div>

          {step === 'details' ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm animate-in fade-in duration-200">
                {error}
              </div>
            )}

            {/* Name */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="name">Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="pl-10 h-11 bg-input border-border focus:border-primary transition-colors"
                  disabled={isLoading}
                  autoComplete="name"
                />
              </div>
            </div>

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

            {/* Create Password */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="password">Create Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  placeholder="Create a strong password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-11 h-11 bg-input border-border focus:border-primary transition-colors"
                  disabled={isLoading}
                  autoComplete="new-password"
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

              {/* Strength meter — appears as soon as typing starts */}
              {password.length > 0 && (
                <div className="space-y-2 animate-in fade-in duration-200">
                  {/* Three-segment bar */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 flex gap-1">
                      <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg1 ? 'bg-red-500' : 'bg-muted'}`} />
                      <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg2 ? 'bg-amber-400' : 'bg-muted'}`} />
                      <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg3 ? 'bg-emerald-500' : 'bg-muted'}`} />
                    </div>
                    {strength.label && (
                      <span className={`text-xs font-semibold w-11 text-right shrink-0 ${strength.textCls}`}>
                        {strength.label}
                      </span>
                    )}
                  </div>

                  {/* Requirements checklist */}
                  <div className="p-3 bg-muted/40 rounded-lg border border-border space-y-1.5">
                    <p className="text-xs text-muted-foreground font-medium mb-1">
                      Password must include:
                    </p>
                    {REQUIREMENTS.map(({ key, label }) => (
                      <div key={key} className="flex items-center gap-2 text-xs">
                        {reqs[key]
                          ? <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                          : <X className="w-3.5 h-3.5 text-muted-foreground/50 flex-shrink-0" />
                        }
                        <span className={reqs[key] ? 'text-emerald-600' : 'text-muted-foreground'}>
                          {label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Static hint shown before typing */}
              {password.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Must be at least 6 characters and include uppercase, lowercase, and a symbol (@, #, $, %).
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="confirm">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="confirm"
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="Retype your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={`pl-10 pr-11 h-11 bg-input border-border focus:border-primary transition-colors ${
                    confirmMismatch ? 'border-destructive focus:border-destructive' :
                    confirmMatch    ? 'border-emerald-500 focus:border-emerald-500' : ''
                  }`}
                  disabled={isLoading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-0.5"
                  tabIndex={-1}
                  aria-label={showConfirm ? 'Hide password' : 'Show password'}
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {confirmMismatch && (
                <p className="text-xs text-destructive flex items-center gap-1 animate-in fade-in duration-150">
                  <X className="w-3 h-3 flex-shrink-0" /> Passwords do not match
                </p>
              )}
              {confirmMatch && (
                <p className="text-xs text-emerald-600 flex items-center gap-1 animate-in fade-in duration-150">
                  <Check className="w-3 h-3 flex-shrink-0" /> Passwords match
                </p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium transition-all active:scale-[0.98]"
              disabled={isLoading || (password.length > 0 && !allMet) || confirmMismatch}
            >
              {isLoading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating account...</>
              ) : (
                'Create Account'
              )}
            </Button>
          </form>
          ) : (
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <KeyRound className="w-6 h-6 text-primary" />
            </div>
            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {error}
              </div>
            )}
            {notice && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 text-sm">
                {notice}
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="verification-code">
                Verification code
              </label>
              <Input
                id="verification-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                className="h-12 text-center text-xl tracking-[0.4em] font-mono"
                disabled={isLoading}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">The code expires in 10 minutes.</p>
            </div>
            <Button type="submit" className="w-full h-11" disabled={isLoading || code.length !== 6}>
              {isLoading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Verifying...</> : 'Verify & Create Account'}
            </Button>
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => { setStep('details'); setCode(''); setError(''); setNotice('') }}
                className="text-muted-foreground hover:text-foreground"
              >
                Change details
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || isLoading}
                className="text-primary hover:underline disabled:text-muted-foreground disabled:no-underline"
              >
                {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Code'}
              </button>
            </div>
          </form>
          )}

          <p className="mt-6 text-sm text-center text-muted-foreground">
            Already have an account?{' '}
            <Link href="/sign-in" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
