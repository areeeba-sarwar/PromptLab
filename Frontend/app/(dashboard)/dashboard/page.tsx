'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import {
  BookOpen, Zap, Sparkles, Target, Clock, ArrowRight,
  Award, CheckCircle, TrendingUp, BarChart2, RefreshCw,
  ChevronRight, Flame
} from 'lucide-react'
import { useAuth, getAuthToken } from '@/contexts/auth-context'

const AREEBA_API = process.env.NEXT_PUBLIC_AREEBA_API || 'https://laiba52.pythonanywhere.com'
const FATIMA_API = process.env.NEXT_PUBLIC_FATIMA_API || 'https://laiba52.pythonanywhere.com'

// ── Types ─────────────────────────────────────────────────────────
interface DashboardStats {
  total_prompts: number
  total_chats: number
  learning_count: number
  direct_prompt_count: number
  total_activity: number
  last_activity: string
}
interface LearningStats {
  total_chapters: number
  chapters_completed: number
  chapters_remaining: number
  completion_percentage: number
  practice_sessions: number
  practice_submissions: number
  average_score: number
  best_score: number
  chat_messages: number
}
interface ChapterProgress {
  chapter_id: string
  completed: boolean
  completed_questions: number
  total_questions: number
  best_score: number
  average_score: number
  attempt_count: number
  completion_percentage: number
}
interface StreakData {
  current_streak: number
  longest_streak: number
  status: 'active' | 'at_risk' | 'broken'
  last_activity_date: string | null
}
interface ActivityItem {
  activity_type: string
  detail: string | null
  created_at: string
}
interface PracticeSession {
  id: number
  chapter_id: string
  chapter_title: string | null
  session_title: string | null
  question?: { title?: string; scenario?: string } | null
  latest_score: number | null
  created_at: string
  updated_at: string
}
interface Certificate { score: number; issued_at: string }

// ── Constants ─────────────────────────────────────────────────────
const CHAPTER_NAMES: Record<string, string> = {
  "1": "Intro to PE",
  "2": "Clarity & Specificity",
  "3": "Context & Background",
  "4": "Role-Based Prompting",
  "5": "Chain of Thought",
  "6": "Advanced Techniques",
}
const CHAPTER_IDS = ["1", "2", "3", "4", "5", "6"]

// ── Helpers ───────────────────────────────────────────────────────
function formatDate(dateText: string) {
  if (!dateText) return 'No activity yet'
  const iso = dateText.includes('T') ? dateText : dateText.replace(' ', 'T') + 'Z'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return dateText
  return d.toLocaleString()
}

function activityTitle(type: string) {
  const map: Record<string, string> = {
    signup: 'Created account', login: 'Logged in',
    learning: 'Used Learning Module', direct_prompt: 'Enhanced a prompt',
    chat: 'Used Chatbot', practice_attempt: 'Submitted practice prompt',
    chapter_completed: 'Completed chapter',
  }
  return map[type] || type
}

function isMeaningfulActivity(a: ActivityItem) {
  return !['active', 'dashboard', 'dashboard_view', 'session_check'].includes(a.activity_type) &&
    !['Checked session', 'Used dashboard'].includes(a.detail || '')
}

function practiceSessionToActivity(session: PracticeSession): ActivityItem {
  const chapterName = session.chapter_title || `Chapter ${session.chapter_id}`
  const questionText = session.question?.title || session.question?.scenario || session.session_title || 'Practice'
  const scoreText = session.latest_score != null ? `Score: ${session.latest_score}` : 'In progress'
  return {
    activity_type: 'practice_attempt',
    detail: `${chapterName}: ${questionText} — ${scoreText}`,
    created_at: session.updated_at || session.created_at,
  }
}

function sortActivities(items: ActivityItem[]) {
  return items
    .filter(isMeaningfulActivity)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 12)
}

// Streak quote logic
function getStreakQuote(streak: StreakData): string {
  const { status, current_streak } = streak
  if (status === 'broken' || current_streak === 0) {
    const opts = [
      "New day, new streak — let's start again!",
      "Every expert was once a beginner. Start fresh today!",
      "Streaks can always be rebuilt. What matters is showing up.",
    ]
    return opts[new Date().getDate() % opts.length]
  }
  if (status === 'at_risk') {
    const opts = [
      "Don't lose your streak — a quick practice session will save it!",
      "Your streak is at risk! A few minutes today keeps it going.",
      "Almost through the day — log a practice and keep your streak alive!",
    ]
    return opts[new Date().getDate() % opts.length]
  }
  // active
  if (current_streak >= 30) return "30+ days of learning! That's true dedication — incredible work!"
  if (current_streak >= 14) return "Two weeks strong! You're becoming a prompt engineering pro!"
  if (current_streak >= 7) return "A full week! You're building a real habit — keep it coming!"
  if (current_streak >= 5) return "Five days and counting! You're on fire, keep going!"
  if (current_streak >= 3) return "Three in a row! Great momentum — consistency is the secret!"
  if (current_streak >= 2) return "Two days strong! You're building something great."
  return "You've started a streak! Come back tomorrow to keep it going."
}

// Color + label logic for chapter performance bars
function barStyle(avg: number, completed: boolean, hasAttempts: boolean) {
  if (!hasAttempts)
    return { bar: 'bg-muted', badge: 'bg-muted text-muted-foreground', label: 'Not started' }
  if (completed || avg >= 70)
    return { bar: 'bg-emerald-500', badge: 'bg-emerald-500/15 text-emerald-600', label: completed ? 'Complete!' : 'On Track' }
  if (avg >= 50)
    return { bar: 'bg-amber-400', badge: 'bg-amber-400/15 text-amber-600', label: 'Needs Practice' }
  return { bar: 'bg-red-500', badge: 'bg-red-500/15 text-red-600', label: 'Needs Attention' }
}

// ── Component ─────────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [learningStats, setLearningStats] = useState<LearningStats | null>(null)
  const [chapterProgress, setChapterProgress] = useState<ChapterProgress[]>([])
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])
  const [certificate, setCertificate] = useState<Certificate | null>(null)
  const [streak, setStreak] = useState<StreakData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activityTab, setActivityTab] = useState<'all' | 'practice'>('all')
  const [barsVisible, setBarsVisible] = useState(false)

  async function loadDashboard(silent = false) {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    setError(null)
    const token = getAuthToken()
    if (!token) { router.push('/sign-in'); return }

    try {
      const [aRes, fRes, pRes, cRes] = await Promise.all([
        fetch(`${AREEBA_API}/api/areeba/dashboard/me`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null),
        fetch(`${FATIMA_API}/api/fatima/dashboard/me`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null),
        fetch(`${FATIMA_API}/api/fatima/progress/me`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null),
        fetch(`${FATIMA_API}/api/fatima/certificate/me`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => null),
      ])

      if (!aRes) {
        setError(`Cannot connect to the account service at ${AREEBA_API}. Make sure the deployed backend is reachable at https://laiba52.pythonanywhere.com.`)
        return
      }

      if (aRes.status === 401) { router.push('/sign-in'); return }
      if (!aRes.ok) {
        setError(`Account service returned ${aRes.status}. Please try again after the backend is ready.`)
        return
      }

      const aData = await aRes.json()
      setStats(aData.stats)
      if (aData.streak) setStreak(aData.streak)
      const accountActs: ActivityItem[] = (aData.recent_activity || []).filter(isMeaningfulActivity)
      let practiceActs: ActivityItem[] = []

      if (fRes?.ok) {
        const fData = await fRes.json()
        setLearningStats(fData.stats)
        practiceActs = (fData.recent_sessions || []).map((s: PracticeSession) => practiceSessionToActivity(s))
      }
      if (pRes?.ok) {
        const pData = await pRes.json()
        setChapterProgress(pData.progress || [])
        // Trigger bar animation after data arrives
        setTimeout(() => setBarsVisible(true), 100)
      }
      if (cRes?.ok) {
        const cData = await cRes.json()
        if (cData.has_certificate) setCertificate(cData.certificate)
      }
      setRecentActivity(sortActivities([...practiceActs, ...accountActs]))
    } catch (e) {
      console.error('Dashboard error:', e)
      setError('Dashboard could not load. Please make sure the backend services are running and try again.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadDashboard()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Build a progress map keyed by chapter_id
  const progressMap: Record<string, ChapterProgress> = {}
  chapterProgress.forEach(p => { progressMap[p.chapter_id] = p })

  // Stat cards — each links to a relevant page
  const statCards = [
    {
      title: 'Chapters Completed',
      value: loading ? '—' : learningStats ? `${learningStats.chapters_completed}/${learningStats.total_chapters}` : '0',
      sub: learningStats ? `${learningStats.completion_percentage}% of course done` : 'Learning module',
      icon: BookOpen, color: 'bg-blue-500/10 text-blue-500', href: '/dashboard/learning',
    },
    {
      title: 'Practice Attempts',
      value: loading ? '—' : String(learningStats?.practice_submissions ?? 0),
      sub: learningStats ? `Across ${learningStats.practice_sessions} sessions` : 'Practice evaluation',
      icon: Target, color: 'bg-violet-500/10 text-violet-500', href: '/dashboard/learning',
    },
    {
      title: 'Best Score',
      value: loading ? '—' : learningStats ? `${learningStats.best_score}/100` : '—',
      sub: learningStats ? `Avg: ${learningStats.average_score}/100` : 'Practice scores',
      icon: TrendingUp, color: 'bg-emerald-500/10 text-emerald-500', href: '/dashboard/learning',
    },
    {
      title: 'Last Active',
      value: loading ? '—' : formatDate(stats?.last_activity || '').split(',')[0],
      sub: 'Keep the streak going!',
      icon: Flame, color: 'bg-orange-500/10 text-orange-500', href: '/dashboard',
    },
  ]

  const filteredActivity = activityTab === 'practice'
    ? recentActivity.filter(a => ['practice_attempt', 'chapter_completed'].includes(a.activity_type))
    : recentActivity

  const activityIconColor: Record<string, string> = {
    practice_attempt: 'bg-violet-500/10 text-violet-500',
    chapter_completed: 'bg-emerald-500/10 text-emerald-600',
    login: 'bg-blue-500/10 text-blue-500',
    signup: 'bg-blue-500/10 text-blue-500',
    direct_prompt: 'bg-amber-500/10 text-amber-500',
    learning: 'bg-blue-500/10 text-blue-500',
  }

  return (
    <div className="p-4 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* ── Header ── */}
        <div className="pt-12 lg:pt-0 flex items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Welcome back{user?.name ? `, ${user.name}` : ''}
            </h1>
            <p className="text-muted-foreground mt-1">Here's how your prompt engineering journey is going</p>
          </div>
          <Button
            variant="outline" size="sm"
            onClick={() => loadDashboard(true)}
            disabled={refreshing}
            className="flex-shrink-0 gap-1.5 hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
              <div>
                <p className="font-semibold text-foreground">Dashboard is waiting for the backend</p>
                <p className="text-sm text-muted-foreground mt-1">{error}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadDashboard(true)}
                disabled={refreshing}
                className="flex-shrink-0 gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        {/* ── Certificate banner ── */}
        {certificate && (
          <Card className="border-2 border-primary/40 bg-primary/5">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Award className="w-6 h-6 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-foreground">You earned a Certificate of Completion!</p>
                <p className="text-sm text-muted-foreground">
                  Final test score: <span className="text-primary font-medium">{certificate.score}%</span> ·
                  Issued {formatDate(certificate.issued_at).split(',')[0]}
                </p>
              </div>
              <Link href="/dashboard/learning/final-test">
                <Button size="sm" variant="outline" className="hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors">
                  View Certificate
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}

        {/* ── Streak widget ── */}
        {streak && (() => {
          const isActive = streak.status === 'active'
          const isAtRisk = streak.status === 'at_risk'

          const cardCls = isActive
            ? 'border-orange-400/50 bg-gradient-to-r from-orange-400/8 to-orange-300/5'
            : isAtRisk
              ? 'border-amber-400/50 bg-gradient-to-r from-amber-400/8 to-amber-300/5'
              : 'border-border bg-muted/20'

          const flameCls = isActive
            ? 'text-orange-400'
            : isAtRisk
              ? 'text-amber-400'
              : 'text-muted-foreground/50'

          const flameWrapCls = isActive
            ? 'bg-orange-400/15'
            : isAtRisk
              ? 'bg-amber-400/15'
              : 'bg-muted'

          const countCls = isActive
            ? 'text-orange-400'
            : isAtRisk
              ? 'text-amber-500'
              : 'text-muted-foreground'

          const badgeLabel = isActive ? 'Active' : isAtRisk ? 'At Risk' : 'Start Fresh'
          const badgeCls = isActive
            ? 'bg-orange-400/15 text-orange-500 border border-orange-400/30'
            : isAtRisk
              ? 'bg-amber-400/15 text-amber-600 border border-amber-400/30'
              : 'bg-muted text-muted-foreground border border-border'

          return (
            <Card className={`border-2 overflow-hidden ${cardCls}`}>
              <CardContent className="p-5">
                <div className="flex items-center gap-4">
                  {/* Flame icon */}
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 ${flameWrapCls}`}>
                    <Flame className={`w-7 h-7 transition-all duration-500 ${flameCls} ${isActive ? 'drop-shadow-[0_0_8px_rgba(251,146,60,0.6)]' : ''}`} />
                  </div>

                  {/* Streak count + quote */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <span className={`text-4xl font-black leading-none ${countCls}`}>
                        {streak.current_streak}
                      </span>
                      <span className="text-base font-semibold text-muted-foreground">
                        {streak.current_streak === 1 ? 'day streak' : 'day streak'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 leading-snug">
                      {getStreakQuote(streak)}
                    </p>
                    <p className="text-xs text-muted-foreground/70 mt-1.5">
                      Personal best: <span className="font-semibold text-muted-foreground">{streak.longest_streak} days</span>
                    </p>
                  </div>

                  {/* Badge */}
                  <span className={`text-xs px-2.5 py-1 rounded-full font-semibold flex-shrink-0 self-start ${badgeCls}`}>
                    {badgeLabel}
                  </span>
                </div>

                {/* Mini progress bar for "at risk" state — shows how much of the day has passed */}
                {isAtRisk && (() => {
                  const now = new Date()
                  const pct = Math.round(((now.getUTCHours() * 60 + now.getUTCMinutes()) / 1440) * 100)
                  return (
                    <div className="mt-4 space-y-1">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Day progress (UTC)</span>
                        <span>{pct}% of day elapsed — practice now to save your streak!</span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div className="h-full bg-amber-400 rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })()}
              </CardContent>
            </Card>
          )
        })()}

        {/* ── Stat cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {statCards.map(stat => (
            <Link key={stat.title} href={stat.href}>
              <Card className="bg-card border-border hover:border-primary/40 hover:shadow-md transition-all duration-200 cursor-pointer group h-full">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-muted-foreground">{stat.title}</p>
                      <p className="text-2xl font-bold text-foreground mt-1 group-hover:text-primary transition-colors">{stat.value}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 leading-tight">{stat.sub}</p>
                    </div>
                    <div className={`p-2.5 rounded-lg flex-shrink-0 ${stat.color}`}>
                      <stat.icon className="h-4 w-4" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* ── Course progress bar ── */}
        {learningStats && (
          <Card className="bg-card border-border">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h2 className="font-semibold text-foreground">Course Progress</h2>
                  <p className="text-sm text-muted-foreground">
                    {learningStats.chapters_completed} of {learningStats.total_chapters} chapters completed
                    {!certificate && learningStats.chapters_completed === learningStats.total_chapters && (
                      <Link href="/dashboard/learning/final-test" className="ml-2 text-primary hover:underline font-medium">
                        Take final exam →
                      </Link>
                    )}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-primary">{learningStats.completion_percentage}%</p>
                  <p className="text-xs text-muted-foreground">complete</p>
                </div>
              </div>
              <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                <div
                  className="bg-primary h-3 rounded-full transition-all duration-1000"
                  style={{ width: `${learningStats.completion_percentage}%` }}
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Chapter Performance (replaces Score Insights) ── */}
        {chapterProgress.length > 0 && (
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-5 h-5 text-primary" />
                  <CardTitle className="text-base text-foreground">Chapter Performance</CardTitle>
                </div>
                <Link href="/dashboard/learning">
                  <Button variant="ghost" size="sm" className="text-xs text-muted-foreground hover:text-primary gap-1">
                    View all <ChevronRight className="w-3 h-3" />
                  </Button>
                </Link>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Click a row to jump straight to practice</p>
            </CardHeader>
            <CardContent className="pt-0">

              {/* Legend */}
              <div className="flex flex-wrap gap-4 mb-4 text-xs text-muted-foreground">
                {[
                  { dot: 'bg-emerald-500', label: 'On Track / Complete (≥70)' },
                  { dot: 'bg-amber-400',   label: 'Needs Practice (50–69)' },
                  { dot: 'bg-red-500',     label: 'Needs Attention (<50)' },
                  { dot: 'bg-muted',       label: 'Not started' },
                ].map(l => (
                  <span key={l.label} className="flex items-center gap-1.5">
                    <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${l.dot}`} />
                    {l.label}
                  </span>
                ))}
              </div>

              {/* Rows */}
              <div className="space-y-1">
                {CHAPTER_IDS.map((id, index) => {
                  const p = progressMap[id]
                  const avg = p ? Math.round(p.average_score) : 0
                  const best = p?.best_score ?? 0
                  const hasAttempts = (p?.attempt_count ?? 0) > 0
                  const completed = p?.completed ?? false
                  const style = barStyle(avg, completed, hasAttempts)

                  return (
                    <Link key={id} href={`/dashboard/learning/${id}/practice`}>
                      <div className="flex items-center gap-3 py-2.5 px-3 -mx-3 rounded-xl hover:bg-muted/60 transition-colors cursor-pointer group">

                        {/* Chapter number */}
                        <span className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0 transition-colors ${
                          completed ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'
                        }`}>
                          {completed ? <CheckCircle className="w-3.5 h-3.5" /> : index + 1}
                        </span>

                        {/* Chapter name */}
                        <span className="w-36 text-sm font-medium text-foreground truncate flex-shrink-0 group-hover:text-primary transition-colors">
                          {CHAPTER_NAMES[id] || `Chapter ${id}`}
                        </span>

                        {/* Bar track */}
                        <div className="flex-1 h-5 bg-muted rounded-full overflow-hidden relative">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ease-out ${style.bar}`}
                            style={{ width: barsVisible && hasAttempts ? `${avg}%` : '0%', transitionDelay: `${index * 80}ms` }}
                          />
                          {/* Best-score tick */}
                          {hasAttempts && best > avg && (
                            <div
                              className="absolute top-1 bottom-1 w-0.5 bg-white/70 rounded-full"
                              style={{ left: `${best}%`, transitionDelay: `${index * 80 + 300}ms` }}
                            />
                          )}
                        </div>

                        {/* Score */}
                        <span className="w-12 text-right text-sm font-bold text-foreground flex-shrink-0">
                          {hasAttempts ? `${avg}/100` : '—'}
                        </span>

                        {/* Status badge */}
                        <span className={`hidden sm:inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${style.badge}`}>
                          {style.label}
                        </span>

                        {/* Arrow hint */}
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </div>
                    </Link>
                  )
                })}
              </div>

              {/* Summary callout */}
              {chapterProgress.some(p => p.attempt_count > 0) && (() => {
                const attempted = chapterProgress.filter(p => p.attempt_count > 0)
                const best = attempted.reduce((b, c) => c.average_score > b.average_score ? c : b)
                const weak = attempted.reduce((w, c) => c.average_score < w.average_score ? c : w)
                return (
                  <div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-border">
                    <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 font-medium">
                      <Award className="w-3 h-3" />
                      Strongest: {CHAPTER_NAMES[best.chapter_id] || `Ch ${best.chapter_id}`} ({Math.round(best.average_score)}/100)
                    </span>
                    {weak.chapter_id !== best.chapter_id && weak.average_score < 70 && (
                      <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-600 font-medium">
                        <Target className="w-3 h-3" />
                        Focus: {CHAPTER_NAMES[weak.chapter_id] || `Ch ${weak.chapter_id}`} ({Math.round(weak.average_score)}/100)
                      </span>
                    )}
                  </div>
                )
              })()}
            </CardContent>
          </Card>
        )}

        {/* ── Quick actions ── */}
        <div>
          <h2 className="text-base font-semibold text-foreground mb-3">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { title: 'Continue Learning', desc: 'Pick up where you left off', href: '/dashboard/learning', icon: BookOpen, color: 'bg-blue-500/10 text-blue-500' },
              { title: 'Live Evaluation', desc: 'Get AI feedback on any prompt', href: '/dashboard/evaluation', icon: Zap, color: 'bg-violet-500/10 text-violet-500' },
              { title: 'Enhance Prompts', desc: 'Transform your prompts with AI', href: '/dashboard/enhancer', icon: Sparkles, color: 'bg-amber-500/10 text-amber-500' },
            ].map(a => (
              <Link key={a.href} href={a.href}>
                <Card className="bg-card border-border hover:border-primary/50 hover:shadow-md transition-all duration-200 cursor-pointer group h-full">
                  <CardContent className="p-5 flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl ${a.color} flex items-center justify-center flex-shrink-0 transition-transform duration-200 group-hover:scale-110`}>
                      <a.icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground group-hover:text-primary transition-colors text-sm">{a.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{a.desc}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all flex-shrink-0" />
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>

        {/* ── Recent Activity (with filter tabs) ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-foreground">Recent Activity</h2>
            <div className="flex rounded-lg border border-border overflow-hidden text-xs">
              {(['all', 'practice'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActivityTab(tab)}
                  className={`px-3 py-1.5 font-medium transition-colors capitalize ${
                    activityTab === tab
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {tab === 'all' ? 'All' : 'Practice only'}
                </button>
              ))}
            </div>
          </div>

          <Card className="bg-card border-border">
            <CardContent className="p-0">
              {filteredActivity.length === 0 ? (
                <div className="p-6 text-sm text-muted-foreground text-center">
                  {activityTab === 'practice' ? 'No practice sessions yet. Start a chapter to begin.' : 'No activity yet.'}
                </div>
              ) : (
                <div>
                  {filteredActivity.map((activity, i) => {
                    const colorCls = activityIconColor[activity.activity_type] || 'bg-muted text-muted-foreground'
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-4 border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                      >
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${colorCls}`}>
                          {activity.activity_type === 'practice_attempt' ? <Target className="w-3.5 h-3.5" /> :
                           activity.activity_type === 'chapter_completed' ? <CheckCircle className="w-3.5 h-3.5" /> :
                           activity.activity_type === 'direct_prompt' ? <Sparkles className="w-3.5 h-3.5" /> :
                           <BookOpen className="w-3.5 h-3.5" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground">{activityTitle(activity.activity_type)}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{activity.detail || 'No details'}</p>
                        </div>
                        <p className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">{formatDate(activity.created_at)}</p>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  )
}
