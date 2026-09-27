'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkles, Loader2, Mail, Lock, Eye, EyeOff, Check, X, ArrowLeft, KeyRound } from 'lucide-react'

const AREEBA_API = process.env.NEXT_PUBLIC_AREEBA_API || 'https://laiba52.pythonanywhere.com'

// ── Password strength — 6 chars, uppercase, lowercase, symbol ─
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

// ── Component ─────────────────────────────────────────────────
type Step = 'email' | 'otp' | 'success'

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const reqs = checkPassword(newPassword)
  const metCount = Object.values(reqs).filter(Boolean).length
  const strength = strengthInfo(metCount)
  const allMet = metCount === 4
  const confirmMismatch = confirmPassword !== '' && newPassword !== confirmPassword
  const confirmMatch = confirmPassword !== '' && newPassword === confirmPassword
  const seg1 = metCount >= 1  // red
  const seg2 = metCount >= 2  // amber
  const seg3 = metCount === 4 // green

  // ── Step 1: Send OTP ────────────────────────────────────────
  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!email) { setError('Please enter your email address'); return }
    setLoading(true)
    try {
      const res = await fetch(`${AREEBA_API}/api/areeba/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Something went wrong'); return }
      setStep('otp')
    } catch {
      setError('Could not reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: Verify OTP + set new password ──────────────────
  async function handleReset(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!otp) { setError('Please enter the reset code'); return }
    if (!allMet) { setError('Your password does not meet the strength requirements'); return }
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return }
    setLoading(true)
    try {
      const res = await fetch(`${AREEBA_API}/api/areeba/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp, new_password: newPassword }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Reset failed'); return }
      setStep('success')
    } catch {
      setError('Could not reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      </div>

      <Card className="w-full max-w-md bg-card/80 backdrop-blur-sm border-border">

        {/* ── Step 1: Enter email ── */}
        {step === 'email' && (
          <>
            <CardHeader className="space-y-4 text-center">
              <div className="mx-auto w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <KeyRound className="w-6 h-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-foreground">Forgot your password?</CardTitle>
                <CardDescription className="text-muted-foreground mt-2">
                  Enter your email and we'll send you a 6-digit reset code.
                </CardDescription>
              </div>
            </CardHeader>

            <form onSubmit={handleSendOtp}>
              <CardContent className="space-y-4">
                {error && (
                  <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                    {error}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground" htmlFor="email">
                    Email address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 bg-input border-border focus:border-primary"
                      disabled={loading}
                    />
                  </div>
                </div>
              </CardContent>

              <CardFooter className="flex flex-col space-y-4">
                <Button
                  type="submit"
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  disabled={loading}
                >
                  {loading ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending code...</>
                  ) : (
                    'Send Reset Code'
                  )}
                </Button>
                <Link
                  href="/sign-in"
                  className="flex items-center justify-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Back to sign in
                </Link>
              </CardFooter>
            </form>
          </>
        )}

        {/* ── Step 2: Enter OTP + new password ── */}
        {step === 'otp' && (
          <>
            <CardHeader className="space-y-4 text-center">
              <div className="mx-auto w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <KeyRound className="w-6 h-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-foreground">Enter reset code</CardTitle>
                <CardDescription className="text-muted-foreground mt-2">
                  A 6-digit code was sent to <span className="text-foreground font-medium">{email}</span>.
                  Enter it below along with your new password. The code expires in 15 minutes.
                </CardDescription>
              </div>
            </CardHeader>

            <form onSubmit={handleReset}>
              <CardContent className="space-y-4">
                {error && (
                  <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                    {error}
                  </div>
                )}

                {/* OTP input */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground" htmlFor="otp">
                    6-digit reset code
                  </label>
                  <Input
                    id="otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    className="bg-input border-border focus:border-primary text-center text-xl tracking-[0.4em] font-mono"
                    disabled={loading}
                  />
                </div>

                {/* New password */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground" htmlFor="newpw">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="newpw"
                      type={showPw ? 'text' : 'password'}
                      placeholder="Create a strong password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="pl-10 pr-10 bg-input border-border focus:border-primary"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                      aria-label={showPw ? 'Hide password' : 'Show password'}
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {newPassword.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex gap-1.5 items-center">
                        <div className="flex-1 flex gap-1">
                          <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg1 ? 'bg-red-500' : 'bg-muted'}`} />
                          <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg2 ? 'bg-amber-400' : 'bg-muted'}`} />
                          <div className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${seg3 ? 'bg-emerald-500' : 'bg-muted'}`} />
                        </div>
                        <span className={`text-xs font-semibold w-12 text-right ${strength.textCls}`}>
                          {strength.label}
                        </span>
                      </div>
                      <div className="p-3 bg-muted/40 rounded-lg border border-border space-y-1.5">
                        {REQUIREMENTS.map(({ key, label }) => (
                          <div key={key} className="flex items-center gap-2 text-xs">
                            {reqs[key]
                              ? <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                              : <X className="w-3.5 h-3.5 text-muted-foreground/60 flex-shrink-0" />
                            }
                            <span className={reqs[key] ? 'text-emerald-600' : 'text-muted-foreground'}>{label}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Confirm password */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground" htmlFor="confirmpw">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="confirmpw"
                      type={showConfirm ? 'text' : 'password'}
                      placeholder="Retype your new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`pl-10 pr-10 bg-input border-border focus:border-primary ${confirmMismatch ? 'border-destructive' : confirmMatch ? 'border-emerald-500' : ''}`}
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                      aria-label={showConfirm ? 'Hide password' : 'Show password'}
                    >
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {confirmMismatch && (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <X className="w-3 h-3" /> Passwords do not match
                    </p>
                  )}
                  {confirmMatch && (
                    <p className="text-xs text-emerald-600 flex items-center gap-1">
                      <Check className="w-3 h-3" /> Passwords match
                    </p>
                  )}
                </div>
              </CardContent>

              <CardFooter className="flex flex-col space-y-3">
                <Button
                  type="submit"
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  disabled={loading || (newPassword.length > 0 && !allMet) || confirmMismatch}
                >
                  {loading ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Resetting password...</>
                  ) : (
                    'Reset Password'
                  )}
                </Button>
                <button
                  type="button"
                  onClick={() => { setStep('email'); setError('') }}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Try a different email
                </button>
              </CardFooter>
            </form>
          </>
        )}

        {/* ── Step 3: Success ── */}
        {step === 'success' && (
          <>
            <CardHeader className="space-y-4 text-center">
              <div className="mx-auto w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                <Check className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-foreground">Password reset!</CardTitle>
                <CardDescription className="text-muted-foreground mt-2">
                  Your password has been changed successfully. Sign in with your new password to continue.
                </CardDescription>
              </div>
            </CardHeader>

            <CardFooter className="flex flex-col space-y-4 pt-0">
              <Link href="/sign-in" className="w-full">
                <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                  Go to Sign In
                </Button>
              </Link>
            </CardFooter>
          </>
        )}
      </Card>
    </div>
  )
}
