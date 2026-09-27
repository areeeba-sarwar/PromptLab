'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { getAuthToken, useAuth } from '@/contexts/auth-context'
import {
  ArrowLeft, Award, CheckCircle, Clock, Loader2,
  XCircle, AlertTriangle, Lock, Download
} from 'lucide-react'

const FATIMA_API = process.env.NEXT_PUBLIC_FATIMA_API || 'https://laiba52.pythonanywhere.com'
const CERTIFYING_AUTHORITY = 'PromptLab'

function parseUtc(value: string): Date {
  if (!value) return new Date(NaN)
  let s = value.includes('T') ? value : value.replace(' ', 'T')
  if (!s.endsWith('Z') && !s.match(/[+-]\d{2}:\d{2}$/)) s += 'Z'
  return new Date(s)
}

interface TestQuestion {
  id: number
  question: string
  options: string[]
}

interface AttemptInfo {
  id: number
  status: string
  started_at: string
  remaining_seconds: number
  score: number | null
  passed: boolean
  timed_out: boolean
}

interface ResultDetail {
  id: number
  question: string
  options: string[]
  your_answer: number | null
  correct_answer: number
  is_correct: boolean
  explanation: string
}

interface TestResult {
  score: number
  passed: boolean
  correct: number
  total: number
  attempted?: number
  timed_out: boolean
  details: ResultDetail[]
  certificate: { issued_at: string; score: number } | null
}

interface TestStatus {
  all_chapters_completed: boolean
  has_certificate: boolean
  certificate: { issued_at: string; score: number } | null
  cooldown_remaining_hours: number
  can_attempt: boolean
  active_attempt: AttemptInfo | null
  pass_score: number
  duration_seconds: number
  total_questions: number
}

// ─── anti-copy handler (Task 8) ───────────────────────────────
function useCopyGuard(active: boolean, onViolation: () => void) {
  useEffect(() => {
    if (!active) return
    const block = (e: Event) => { e.preventDefault(); onViolation() }
    document.addEventListener('copy', block)
    document.addEventListener('cut', block)
    document.addEventListener('contextmenu', block)
    return () => {
      document.removeEventListener('copy', block)
      document.removeEventListener('cut', block)
      document.removeEventListener('contextmenu', block)
    }
  }, [active, onViolation])
}

function formatTime(secs: number) {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function certificateDate(value: string) {
  return parseUtc(value).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

function safeFileName(value: string) {
  return value.trim().replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '') || 'User'
}

function escapeXml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function buildCertificateSvg(userName: string, issuedAt: string, score: number) {
  const name = escapeXml(userName)
  const date = escapeXml(certificateDate(issuedAt))
  const signature = escapeXml(CERTIFYING_AUTHORITY)

  return `
<svg xmlns="http://www.w3.org/2000/svg" width="1123" height="794" viewBox="0 0 1123 794">
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fffdf7"/><stop offset="1" stop-color="#f8f0df"/></linearGradient>
    <radialGradient id="seal" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#f6d36a"/><stop offset="1" stop-color="#b88722"/></radialGradient>
    <pattern id="pattern" width="54" height="54" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 27 H54" stroke="#d8b86a" stroke-opacity="0.12" stroke-width="1"/></pattern>
  </defs>
  <rect width="1123" height="794" fill="url(#paper)"/>
  <rect width="1123" height="794" fill="url(#pattern)"/>
  <rect x="42" y="42" width="1039" height="710" rx="10" fill="none" stroke="#bd8f2f" stroke-width="5"/>
  <rect x="62" y="62" width="999" height="670" rx="8" fill="none" stroke="#d7b766" stroke-width="2"/>
  <text x="561.5" y="128" text-anchor="middle" font-family="Georgia, serif" font-size="28" fill="#775018" letter-spacing="7">PROMPTLAB</text>
  <text x="561.5" y="194" text-anchor="middle" font-family="Georgia, serif" font-size="54" fill="#1f2937">Certificate of Completion</text>
  <text x="561.5" y="245" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="#6b5a38">This certifies that</text>
  <text x="561.5" y="329" text-anchor="middle" font-family="Georgia, serif" font-size="58" font-weight="700" fill="#111827">${name}</text>
  <line x1="250" y1="352" x2="873" y2="352" stroke="#bd8f2f" stroke-width="2"/>
  <text x="561.5" y="402" text-anchor="middle" font-family="Arial, sans-serif" font-size="21" fill="#4b5563">has successfully completed the</text>
  <text x="561.5" y="446" text-anchor="middle" font-family="Georgia, serif" font-size="31" font-weight="700" fill="#7a4f12">Prompt Engineering Course</text>
  <text x="561.5" y="493" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="#4b5563">Final exam score: ${score}% - Completed on ${date}</text>
  <circle cx="562" cy="582" r="62" fill="url(#seal)" opacity="0.96"/>
  <circle cx="562" cy="582" r="48" fill="none" stroke="#fff6d5" stroke-width="3"/>
  <text x="562" y="575" text-anchor="middle" font-family="Georgia, serif" font-size="18" font-weight="700" fill="#fff8db">CERTIFIED</text>
  <text x="562" y="604" text-anchor="middle" font-family="Georgia, serif" font-size="16" fill="#fff8db">PROMPTLAB</text>
  <text x="302" y="641" text-anchor="middle" font-family="'Brush Script MT', 'Segoe Script', cursive" font-size="44" fill="#182033">${signature}</text>
  <line x1="180" y1="662" x2="424" y2="662" stroke="#6b7280" stroke-width="1.5"/>
  <text x="302" y="689" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#6b7280">Certifying Authority</text>
  <text x="821" y="641" text-anchor="middle" font-family="Georgia, serif" font-size="24" fill="#1f2937">${date}</text>
  <line x1="699" y1="662" x2="943" y2="662" stroke="#6b7280" stroke-width="1.5"/>
  <text x="821" y="689" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#6b7280">Completion Date</text>
</svg>`.trim()
}

async function svgToJpegDataUrl(svg: string) {
  const image = new Image()
  const svgUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = reject
      image.src = svgUrl
    })
    const canvas = document.createElement('canvas')
    canvas.width = 1123
    canvas.height = 794
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas is not available')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.94)
  } finally {
    URL.revokeObjectURL(svgUrl)
  }
}

function makePdfFromJpegDataUrl(jpegDataUrl: string) {
  const binary = atob(jpegDataUrl.split(',')[1])
  const imageBytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) imageBytes[i] = binary.charCodeAt(i)

  const encoder = new TextEncoder()
  const chunks: Uint8Array[] = []
  const offsets: number[] = []
  let length = 0
  const add = (part: string | Uint8Array) => {
    const bytes = typeof part === 'string' ? encoder.encode(part) : part
    chunks.push(bytes)
    length += bytes.length
  }
  const object = (id: number, content: string | Uint8Array, prefix = '', suffix = '') => {
    offsets[id] = length
    add(`${id} 0 obj\n${prefix}`)
    add(content)
    add(`${suffix}\nendobj\n`)
  }

  add('%PDF-1.4\n')
  object(1, '<< /Type /Catalog /Pages 2 0 R >>')
  object(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
  object(3, '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>')
  object(4, imageBytes, `<< /Type /XObject /Subtype /Image /Width 1123 /Height 794 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${imageBytes.length} >>\nstream\n`, '\nendstream')
  const content = 'q\n842 0 0 595 0 0 cm\n/Im0 Do\nQ'
  object(5, content, `<< /Length ${content.length} >>\nstream\n`, '\nendstream')

  const xref = length
  add('xref\n0 6\n0000000000 65535 f \n')
  for (let i = 1; i <= 5; i++) add(`${String(offsets[i]).padStart(10, '0')} 00000 n \n`)
  add(`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`)

  return new Blob(chunks, { type: 'application/pdf' })
}

async function downloadCertificatePdf(userName: string, certificate: { issued_at: string; score: number }) {
  const jpeg = await svgToJpegDataUrl(buildCertificateSvg(userName, certificate.issued_at, certificate.score))
  const url = URL.createObjectURL(makePdfFromJpegDataUrl(jpeg))
  const link = document.createElement('a')
  link.href = url
  link.download = `PromptLab_Certificate_${safeFileName(userName)}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function FinalTestPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [status, setStatus]       = useState<TestStatus | null>(null)
  const [questions, setQuestions] = useState<TestQuestion[]>([])
  const [attempt, setAttempt]     = useState<AttemptInfo | null>(null)
  const [answers, setAnswers]     = useState<Record<number, number>>({})
  const [result, setResult]       = useState<TestResult | null>(null)
  const [loading, setLoading]     = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [timerSecs, setTimerSecs] = useState(0)
  const [copyWarning, setCopyWarning] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const submittedRef = useRef(false)
  const answersRef = useRef<Record<number, number>>({})

  const headers = useCallback(() => {
    const token = getAuthToken()
    return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : null
  }, [])

  // Load test status on mount
  useEffect(() => {
    const h = headers()
    if (!h) { router.push('/sign-in'); return }
    fetch(`${FATIMA_API}/api/fatima/final-test/status`, { headers: h })
      .then(r => r.json())
      .then(d => setStatus(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [headers, router])

  // Start countdown once attempt is set
  useEffect(() => {
    if (!attempt || result) return
    setTimerSecs(attempt.remaining_seconds)
    timerRef.current = setInterval(() => {
      setTimerSecs(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current!)
          if (!submittedRef.current) submitTest(true)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, result])

  useEffect(() => {
    answersRef.current = answers
  }, [answers])

  const handleCopyViolation = useCallback(() => setCopyWarning(true), [])
  useCopyGuard(!!attempt && !result, handleCopyViolation)

  const startTest = async () => {
    const h = headers()
    if (!h) return
    setLoading(true)
    try {
      const res  = await fetch(`${FATIMA_API}/api/fatima/final-test/start`, { method: 'POST', headers: h })
      const data = await res.json()
      if (!res.ok) { alert(data.error || 'Could not start test'); return }
      submittedRef.current = false
      answersRef.current = {}
      setAnswers({})
      setResult(null)
      setCopyWarning(false)
      setAttempt(data.attempt)
      setQuestions(data.questions)
    } finally {
      setLoading(false)
    }
  }

  const submitTest = async (timedOut = false) => {
    if (submittedRef.current) return
    submittedRef.current = true
    if (timerRef.current) clearInterval(timerRef.current)
    const h = headers()
    if (!h) return
    setSubmitting(true)
    try {
      const res  = await fetch(`${FATIMA_API}/api/fatima/final-test/submit`, {
        method: 'POST',
        headers: h,
        body: JSON.stringify({ answers: Object.fromEntries(Object.entries(answersRef.current).map(([k, v]) => [k, v])) })
      })
      const data = await res.json()
      if (!res.ok) { alert(data.error || 'Submission failed'); return }
      setResult(data)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Loading ──────────────────────────────────────────────────
  if (loading) return (
    <div className="h-screen flex items-center justify-center text-muted-foreground">
      <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading…
    </div>
  )

  // ── Status gate ───────────────────────────────────────────────
  if (status && !attempt && !result) {
    if (status.has_certificate && status.certificate) {
      return <CertificateView certificate={status.certificate} userName={user?.name || 'PromptLab Learner'} />
    }

    if (!status.all_chapters_completed) {
      return (
        <GatePage icon={<Lock className="w-10 h-10 text-muted-foreground" />} title="Finish the course first"
          message="You must complete all 6 chapters and their practice questions before taking the final test.">
          <Link href="/dashboard/learning"><Button>Go to Learning</Button></Link>
        </GatePage>
      )
    }

    if (status.cooldown_remaining_hours > 0) {
      return (
        <GatePage icon={<Clock className="w-10 h-10 text-amber-400" />} title="Cooldown active"
          message={`You can retake the test in ${status.cooldown_remaining_hours} hours.`}>
          <Link href="/dashboard/learning"><Button variant="outline">Back</Button></Link>
        </GatePage>
      )
    }

    return (
      <div className="p-4 lg:p-8 max-w-2xl mx-auto space-y-6">
        <div className="pt-12 lg:pt-0">
          <Link href="/dashboard/learning" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="w-4 h-4" /> Back to Learning
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Final Certification Test</h1>
          <p className="text-muted-foreground mt-1">Prove your prompt engineering mastery.</p>
        </div>
        <Card className="bg-card border-border">
          <CardContent className="p-6 space-y-4">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><p className="text-2xl font-bold text-foreground">{status.total_questions}</p><p className="text-xs text-muted-foreground">Questions</p></div>
              <div><p className="text-2xl font-bold text-foreground">30 min</p><p className="text-xs text-muted-foreground">Time limit</p></div>
              <div><p className="text-2xl font-bold text-foreground">{status.pass_score}%</p><p className="text-xs text-muted-foreground">Passing score</p></div>
            </div>
            <ul className="text-sm text-muted-foreground space-y-1 border-t border-border pt-4">
              <li>• Timer starts immediately when you click Start.</li>
              <li>• The test auto-submits when time runs out.</li>
              <li>• You have 1 attempt per 7 days.</li>
              <li>• Copying text is disabled during the test.</li>
            </ul>
            <Button className="w-full" onClick={startTest} disabled={loading}>Start Test</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Result screen ─────────────────────────────────────────────
  if (result) {
    return (
      <div className="p-4 lg:p-8 max-w-3xl mx-auto space-y-6">
        <div className="pt-12 lg:pt-0">
          <Link href="/dashboard/learning" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="w-4 h-4" /> Back to Learning
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Test Results</h1>
        </div>

        {result.timed_out && (
          <Card className="border-amber-400/40 bg-amber-400/5">
            <CardContent className="p-4 text-sm text-amber-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" /> Time ran out — test was auto-submitted.
            </CardContent>
          </Card>
        )}

        <Card className={`border-2 ${result.passed ? 'border-primary/40 bg-primary/5' : 'border-destructive/40 bg-destructive/5'}`}>
          <CardContent className="p-8 text-center space-y-2">
            {result.passed
              ? <Award className="w-16 h-16 text-primary mx-auto" />
              : <XCircle className="w-16 h-16 text-destructive mx-auto" />}
            <p className="text-5xl font-bold text-foreground">{result.score}%</p>
            <p className="text-xl font-semibold text-foreground">{result.passed ? 'Congratulations — you passed!' : 'Not quite — keep practising'}</p>
            <p className="text-sm text-muted-foreground">
              {result.correct} / {result.total} correct
              {result.attempted !== undefined && ` (${result.attempted} attempted)`}
            </p>
            {result.passed && result.certificate && (
              <p className="text-xs text-muted-foreground">Certificate issued {parseUtc(result.certificate.issued_at).toLocaleDateString()}</p>
            )}
          </CardContent>
        </Card>

        {result.passed && result.certificate && (
          <CertificateView certificate={result.certificate} userName={user?.name || 'PromptLab Learner'} />
        )}

        <div className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">Question Review</h2>
          {result.details.map((d, i) => (
            <Card key={d.id} className={`border ${d.is_correct ? 'border-primary/30' : 'border-destructive/30'}`}>
              <CardContent className="p-4 space-y-2">
                <div className="flex items-start gap-2">
                  {d.is_correct
                    ? <CheckCircle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    : <XCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />}
                  <p className="text-sm font-medium text-foreground">{i + 1}. {d.question}</p>
                </div>
                <div className="ml-6 space-y-1">
                  {d.options.map((opt, oi) => (
                    <p key={oi} className={`text-xs px-2 py-1 rounded ${
                      oi === d.correct_answer ? 'bg-primary/10 text-primary font-medium' :
                      oi === d.your_answer && !d.is_correct ? 'bg-destructive/10 text-destructive' :
                      'text-muted-foreground'
                    }`}>{opt}</p>
                  ))}
                </div>
                <p className="ml-6 text-xs text-muted-foreground italic">{d.explanation}</p>
              </CardContent>
            </Card>
          ))}
        </div>

      </div>
    )
  }

  // ── Active test ───────────────────────────────────────────────
  const allAnswered = questions.length > 0 && questions.every(q => answers[q.id] !== undefined)
  const timerRed = timerSecs < 300   // last 5 min
  const timerAmber = timerSecs < 600 // last 10 min

  return (
    <div className="min-h-screen flex flex-col">
      {/* sticky header with countdown */}
      <div className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">Final Certification Test</span>
          <div className={`flex items-center gap-2 font-mono text-lg font-bold ${timerRed ? 'text-destructive animate-pulse' : timerAmber ? 'text-amber-400' : 'text-foreground'}`}>
            <Clock className="w-5 h-5" />
            {formatTime(timerSecs)}
          </div>
          <span className="text-sm text-muted-foreground">{Object.keys(answers).length}/{questions.length} answered</span>
        </div>
      </div>

      {copyWarning && (
        <div className="bg-destructive/90 text-destructive-foreground px-4 py-2 text-sm text-center flex items-center justify-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          Copying is not allowed during this test.
          <button onClick={() => setCopyWarning(false)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      <div className="flex-1 max-w-3xl mx-auto w-full px-4 py-6 space-y-4">
        {questions.map((q, i) => (
          <Card key={q.id} className={`border-border bg-card transition-all ${answers[q.id] !== undefined ? 'ring-1 ring-primary/30' : ''}`}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-foreground">{i + 1}. {q.question}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-2">
              {q.options.map((opt, oi) => (
                <button
                  key={oi}
                  onClick={() => setAnswers(prev => ({ ...prev, [q.id]: oi }))}
                  className={`w-full text-left text-sm rounded-lg border px-4 py-3 transition-all ${
                    answers[q.id] === oi
                      ? 'border-primary bg-primary/10 text-primary font-medium'
                      : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/40 hover:bg-muted/50'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </CardContent>
          </Card>
        ))}

        <div className="sticky bottom-0 bg-background/90 backdrop-blur-sm border-t border-border py-4 flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {allAnswered ? 'All questions answered.' : `${questions.length - Object.keys(answers).length} question(s) unanswered.`}
          </p>
          <Button
            onClick={() => submitTest(false)}
            disabled={submitting || questions.length === 0}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {submitting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Submitting…</> : 'Submit Test'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────

function GatePage({ icon, title, message, children }: { icon: React.ReactNode; title: string; message: string; children?: React.ReactNode }) {
  return (
    <div className="p-4 lg:p-8 max-w-2xl mx-auto flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
      {icon}
      <h1 className="text-2xl font-bold text-foreground">{title}</h1>
      <p className="text-muted-foreground">{message}</p>
      {children}
    </div>
  )
}

function CertificateView({ certificate, userName }: { certificate: { issued_at: string; score: number }; userName: string }) {
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await downloadCertificatePdf(userName, certificate)
    } catch {
      alert('Could not generate the certificate PDF. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="p-4 lg:p-8 max-w-2xl mx-auto space-y-6">
      <Card className="overflow-hidden border-2 border-amber-500/50 bg-gradient-to-br from-amber-50 via-white to-orange-50 text-slate-900 shadow-xl">
        <CardContent className="relative p-10 text-center space-y-4">
          <div className="absolute inset-4 border border-amber-300/80 pointer-events-none" />
          <div className="absolute inset-8 border border-amber-200/80 pointer-events-none" />
          <Award className="w-20 h-20 text-amber-600 mx-auto" />
          <h1 className="text-3xl font-bold text-slate-950">Certificate of Completion</h1>
          <p className="text-4xl font-bold font-serif text-slate-950">{userName}</p>
          <p className="text-muted-foreground">This certifies that you have successfully completed the</p>
          <p className="text-2xl font-semibold text-slate-950">Prompt Engineering Course</p>
          <p className="text-muted-foreground">with a score of <span className="text-primary font-bold">{certificate.score}%</span></p>
          <p className="text-sm text-muted-foreground">Issued on {certificateDate(certificate.issued_at)}</p>
          <div className="grid grid-cols-2 gap-8 pt-6">
            <div>
              <p className="text-3xl text-slate-900" style={{ fontFamily: '"Brush Script MT", "Segoe Script", cursive' }}>{CERTIFYING_AUTHORITY}</p>
              <div className="mx-auto mt-1 h-px w-44 bg-slate-400" />
              <p className="mt-2 text-xs text-muted-foreground">Certifying Authority</p>
            </div>
            <div>
              <p className="text-lg font-serif text-slate-900">{certificateDate(certificate.issued_at)}</p>
              <div className="mx-auto mt-3 h-px w-44 bg-slate-400" />
              <p className="mt-2 text-xs text-muted-foreground">Completion Date</p>
            </div>
          </div>
          <div className="border-t border-primary/20 pt-4">
            <p className="text-xs text-muted-foreground">PromptLab - Prompt Engineering Learning Platform</p>
          </div>
          <Button onClick={handleDownload} disabled={downloading} className="relative z-10">
            {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            Download Certificate
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
