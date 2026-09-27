'use client'

import { use, useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChatMessage } from '@/components/chat/chat-message'
import { ChatInput } from '@/components/chat/chat-input'
import type { Message } from '@/lib/types'
import { ArrowLeft, Target, RefreshCw, CheckCircle, XCircle, Lightbulb, TrendingUp, Loader2, History, ShieldAlert, Award } from 'lucide-react'
import Link from 'next/link'
import { getAuthToken } from '@/contexts/auth-context'

const FATIMA_API = process.env.NEXT_PUBLIC_FATIMA_API || 'https://laiba52.pythonanywhere.com'
const AREEBA_API = process.env.NEXT_PUBLIC_AREEBA_API || 'https://laiba52.pythonanywhere.com'

interface PracticeQuestion {
  id: number
  chapter_id: string
  title: string
  statement: string
  scenario: string
  hints: string[]
  expected_elements: string[]
  difficulty: string
}

interface PracticeEvaluation {
  score: number
  clarity: number
  structure: number
  specificity: number
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  detailed_feedback: string
  prompt_quality_analysis: string
  improvement_recommendations: string[]
  passed?: boolean
}

interface PracticeAttempt extends PracticeEvaluation {
  id: number
  attempt_number: number
  prompt_text: string
  created_at: string
}

interface PracticeSession {
  id: number
  chapter_id: string
  chapter_title?: string
  question_id: number
  question: PracticeQuestion
  status: string
  session_title: string
  latest_score?: number | null
  messages?: Message[]
  attempts?: PracticeAttempt[]
  created_at: string
  updated_at: string
}

function toUtcDate(value: string): Date {
  if (!value) return new Date()
  const iso = value.includes('T') ? value : value.replace(' ', 'T') + 'Z'
  return new Date(iso)
}

function toMessage(apiMessage: any): Message {
  return {
    id: String(apiMessage.id),
    role: apiMessage.role,
    content: apiMessage.content,
    timestamp: toUtcDate(apiMessage.timestamp || apiMessage.created_at)
  }
}

function formatShortDate(value: string) {
  if (!value) return ''
  const iso = value.includes('T') ? value : value.replace(' ', 'T') + 'Z'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return value
  return d.toLocaleString()
}

export default function PracticePage({ params }: { params: Promise<{ chapterId: string }> }) {
  const { chapterId } = use(params)
  const router = useRouter()
  const [session, setSession] = useState<PracticeSession | null>(null)
  const [sessions, setSessions] = useState<PracticeSession[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentFeedback, setCurrentFeedback] = useState<PracticeEvaluation | null>(null)
  const [allCompleted, setAllCompleted] = useState(false)
  const [questionCopyWarning, setQuestionCopyWarning] = useState(false)
  const [historyLimit, setHistoryLimit] = useState(5)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasStarted = useRef(false)

  const currentProblem = session?.question
  const visibleMessages = messages.filter(message => message.role !== 'system')

  const authHeaders = useCallback(() => {
    const token = getAuthToken()
    return token ? { Authorization: `Bearer ${token}` } : null
  }, [])

  const loadSessions = useCallback(async () => {
    const headers = authHeaders()
    if (!headers) return
    const response = await fetch(`${FATIMA_API}/api/fatima/practice/sessions`, { headers })
    const data = await response.json()
    if (response.ok) setSessions(data.sessions || [])
  }, [authHeaders])

  const applySession = (nextSession: PracticeSession) => {
    setSession(nextSession)
    setMessages((nextSession.messages || []).map(toMessage))
    const attempts = nextSession.attempts || []
    const latestAttempt = attempts[attempts.length - 1]
    setCurrentFeedback(latestAttempt || null)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (hasStarted.current) return
    hasStarted.current = true

    const headers = authHeaders()
    if (!headers) {
      router.push('/sign-in')
      return
    }

    async function startPractice() {
      try {
        const response = await fetch(`${FATIMA_API}/api/fatima/practice/start`, {
          method: 'POST',
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify({ chapter_id: chapterId })
        })
        const data = await response.json()
        if (data.all_completed) {
          setAllCompleted(true)
          await loadSessions()
          return
        }
        if (!response.ok) throw new Error(data.error || 'Could not start practice session')
        applySession(data.session)
        await loadSessions()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not start practice')
      } finally {
        setInitialLoading(false)
      }
    }

    startPractice()
  }, [authHeaders, chapterId, loadSessions, router])

  const handleSend = async (content: string) => {
    if (!session) return
    const headers = authHeaders()
    if (!headers) {
      router.push('/sign-in')
      return
    }

    const optimisticUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, optimisticUserMessage])
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${FATIMA_API}/api/fatima/practice/${session.id}/submit`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt_text: content })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not evaluate prompt')

      setCurrentFeedback(data.evaluation)
      applySession(data.session)
      await loadSessions()

      // Keep Areeba dashboard activity updated without changing Areeba auth code.
      fetch(`${AREEBA_API}/api/areeba/prompt-history`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module_type: 'learning',
          original_prompt: content,
          ai_response: data.evaluation?.detailed_feedback,
          explanation: data.evaluation?.prompt_quality_analysis,
          resources: JSON.stringify(data.evaluation?.suggestions || [])
        })
      }).catch(() => {})
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangeQuestion = async () => {
    if (!session) return
    const headers = authHeaders()
    if (!headers) {
      router.push('/sign-in')
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(`${FATIMA_API}/api/fatima/practice/${session.id}/change-question`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      if (data.all_completed) {
        setAllCompleted(true)
        return
      }
      if (!response.ok) throw new Error(data.error || 'Could not change question')
      applySession(data.session)
      await loadSessions()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change question')
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuestionCopy = useCallback((e: React.ClipboardEvent | React.MouseEvent) => {
    e.preventDefault()
    setQuestionCopyWarning(true)
    setTimeout(() => setQuestionCopyWarning(false), 4000)
  }, [])

  const loadSession = async (sessionId: number) => {
    const headers = authHeaders()
    if (!headers) {
      router.push('/sign-in')
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(`${FATIMA_API}/api/fatima/practice/sessions/${sessionId}`, { headers })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not load session')
      applySession(data.session)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load session')
    } finally {
      setIsLoading(false)
    }
  }

  if (initialLoading) {
    return (
      <div className="h-screen flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Starting practice session...
      </div>
    )
  }

  if (allCompleted) {
    return (
      <div className="h-screen flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <Award className="w-10 h-10 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">All Questions Attempted!</h1>
          <p className="text-muted-foreground mb-2">
            You have attempted all practice questions for this chapter.
          </p>
          <p className="text-sm text-muted-foreground mb-8">
            Keep reviewing your previous sessions to improve your scores, or move on to the next chapter.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button variant="outline" onClick={() => router.push(`/dashboard/learning/${chapterId}`)}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Chapter
            </Button>
            <Button onClick={() => router.push('/dashboard/learning')}>
              Go to Learning
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (error && !session) {
    return (
      <div className="p-4 lg:p-8">
        <div className="max-w-4xl mx-auto text-center py-12">
          <h1 className="text-2xl font-bold text-foreground">Practice could not start</h1>
          <p className="text-sm text-muted-foreground mt-2">{error}</p>
          <Button variant="link" onClick={() => router.push('/dashboard/learning')} className="mt-4 text-primary">
            Back to Learning
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b border-border bg-card/50 flex-shrink-0">
        <div className="max-w-6xl mx-auto p-4">
          <div className="flex items-center justify-between pt-8 lg:pt-0">
            <div className="flex items-center gap-4">
              <Link href={`/dashboard/learning/${chapterId}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ArrowLeft className="w-4 h-4" />
                Back to Chapter
              </Link>
              <div className="hidden sm:block h-4 w-px bg-border" />
              <div className="hidden sm:flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-foreground">Practice Evaluation</span>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={handleChangeQuestion} disabled={isLoading} className="border-border text-foreground">
              <RefreshCw className="w-4 h-4 mr-2" />
              Change Question
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="border-b border-destructive/40 bg-destructive/5 px-4 py-2 text-sm text-destructive flex-shrink-0">
          {error}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/*
          LEFT COLUMN (chat)
          - flex flex-col + min-h-0: required so the overflow-y-auto child below
            is actually allowed to shrink/scroll inside a flex column instead of
            stretching the column past the viewport (which was dragging ChatInput
            off-screen on scroll).
        */}
        <div className="flex-1 flex flex-col min-h-0">
          {currentProblem && (
            <div
              className="p-4 border-b border-border bg-muted/30 select-none flex-shrink-0"
              onCopy={handleQuestionCopy as any}
              onCut={handleQuestionCopy as any}
              onContextMenu={handleQuestionCopy as any}
            >
              {questionCopyWarning && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-destructive/90 text-destructive-foreground text-xs rounded-md animate-in fade-in slide-in-from-top-1 duration-200">
                  <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
                  Copying the practice question is not allowed.
                  <button onClick={() => setQuestionCopyWarning(false)} className="ml-auto underline opacity-80 hover:opacity-100">Dismiss</button>
                </div>
              )}
              <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <h3 className="text-sm font-medium text-primary">Practice Scenario</h3>
                  <span className="text-xs rounded-full bg-muted px-2 py-1 text-muted-foreground capitalize">{currentProblem.difficulty}</span>
                </div>
                <p className="text-foreground font-medium">{currentProblem.title}</p>
                <p className="text-foreground mt-1">{currentProblem.statement}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {currentProblem.hints.map((hint, i) => (
                    <span key={i} className="inline-flex items-center gap-1 text-xs bg-primary/10 text-primary px-2 py-1 rounded-md">
                      <Lightbulb className="w-3 h-3" />
                      {hint}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Scrollable region: only this area scrolls, ChatInput below stays put */}
          <div className="flex-1 overflow-y-auto min-h-0">
            {visibleMessages.length === 0 ? (
              <div className="h-full flex items-center justify-center p-4">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Target className="w-8 h-8 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">Ready to Practice</h3>
                  <p className="text-muted-foreground text-sm">
                    Write a prompt for the scenario above. Your answer will be scored and saved in this practice session.
                  </p>
                </div>
              </div>
            ) : (
              <div className="pb-2">
                {visibleMessages.map(message => <ChatMessage key={message.id} message={message} />)}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/*
            Sticky input bar.
            - flex-shrink-0 keeps it from being compressed by the flex column.
            - sticky bottom-0 pins it to the bottom of the scrolling viewport
              it belongs to; combined with min-h-0/overflow-y-auto above, the
              messages list scrolls underneath while this bar stays anchored.
            - solid bg + top border + z-index stop message content from
              showing through or visually overlapping the input.
            - safe-area padding keeps it clear of mobile home-indicator/notch
              areas (iOS) without affecting desktop.
          */}
          <div
            className="flex-shrink-0 sticky bottom-0 z-10 bg-background border-t border-border"
            style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
          >
            <ChatInput
              onSend={handleSend}
              isLoading={isLoading}
              placeholder="Write and improve your prompt here..."
              guardCopy={true}
              onAiPaste={() => {}}
            />
          </div>
        </div>

        <div className="hidden lg:block w-96 border-l border-border bg-card overflow-y-auto">
          <div className="p-4 space-y-4">
            <h3 className="font-semibold text-foreground">Evaluation</h3>

            {currentFeedback ? (
              <>
                <Card className="bg-muted/50 border-border">
                  <CardContent className="p-4 text-center">
                    <div className="text-4xl font-bold text-primary">{currentFeedback.score}</div>
                    <p className="text-sm text-muted-foreground">Overall Score</p>
                    <p className="text-xs text-muted-foreground mt-1">{currentFeedback.passed ? 'Passed this question' : 'Improve and resubmit'}</p>
                  </CardContent>
                </Card>

                <div className="space-y-3">
                  {([
                    ['Clarity', currentFeedback.clarity],
                    ['Structure', currentFeedback.structure],
                    ['Specificity', currentFeedback.specificity]
                  ] as [string, number][]).map(([label, value]) => (
                    <div key={label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-muted-foreground">{label}</span>
                        <span className="text-foreground">{value}%</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div className="bg-primary h-2 rounded-full transition-all" style={{ width: `${value}%` }} />
                      </div>
                    </div>
                  ))}
                </div>

                {currentFeedback.strengths.length > 0 && (
                  <Card className="bg-muted/50 border-border">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2 text-foreground">
                        <CheckCircle className="w-4 h-4 text-primary" /> Strengths
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <ul className="space-y-1">{currentFeedback.strengths.map((s, i) => <li key={i} className="text-xs text-muted-foreground">{s}</li>)}</ul>
                    </CardContent>
                  </Card>
                )}

                {currentFeedback.weaknesses.length > 0 && (
                  <Card className="bg-muted/50 border-border">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2 text-foreground">
                        <XCircle className="w-4 h-4 text-destructive" /> Areas to Improve
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <ul className="space-y-1">{currentFeedback.weaknesses.map((w, i) => <li key={i} className="text-xs text-muted-foreground">{w}</li>)}</ul>
                    </CardContent>
                  </Card>
                )}

                <Card className="bg-primary/5 border-primary/20">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <TrendingUp className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                      <div className="space-y-2">
                        <p className="text-xs text-muted-foreground">{currentFeedback.detailed_feedback}</p>
                        <ul className="space-y-1">
                          {currentFeedback.improvement_recommendations.map((item, i) => <li key={i} className="text-xs text-muted-foreground">• {item}</li>)}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-muted/50 border-border">
                <CardContent className="p-4 text-sm text-muted-foreground">
                  Submit your first prompt to see score, strengths, weaknesses, suggestions, and detailed feedback.
                </CardContent>
              </Card>
            )}

            <Card className="bg-card border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2 text-foreground">
                  <History className="w-4 h-4 text-primary" /> Practice History
                  {sessions.length > 0 && (
                    <span className="ml-auto text-xs font-normal text-muted-foreground">{sessions.length} session{sessions.length !== 1 ? 's' : ''}</span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                {sessions.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No previous sessions yet.</p>
                ) : (
                  <>
                    {sessions.slice(0, historyLimit).map(item => (
                      <button
                        key={item.id}
                        onClick={() => loadSession(item.id)}
                        className={`w-full text-left rounded-md border p-2 transition-colors hover:border-primary/50 ${item.id === session?.id ? 'border-primary/60 bg-primary/5' : 'border-border bg-muted/30'}`}
                      >
                        <p className="text-xs font-medium text-foreground line-clamp-1">{item.session_title}</p>
                        <p className="text-xs text-muted-foreground">Score: {item.latest_score ?? 'No attempt'} • {formatShortDate(item.updated_at)}</p>
                      </button>
                    ))}
                    {sessions.length > historyLimit && (
                      <button
                        onClick={() => setHistoryLimit(l => l + 5)}
                        className="w-full text-xs text-primary hover:underline py-1 text-center"
                      >
                        Load more ({sessions.length - historyLimit} remaining)
                      </button>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}