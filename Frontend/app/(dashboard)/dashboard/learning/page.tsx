'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { BookOpen, Clock, CheckCircle, PlayCircle, ChevronRight, Loader2, Award, Lock } from 'lucide-react'
import { getAuthToken } from '@/contexts/auth-context'

const FATIMA_API = process.env.NEXT_PUBLIC_FATIMA_API || 'https://laiba52.pythonanywhere.com'

interface LearningChapter {
  id: string
  title: string
  description: string
  duration: string
  lessons: number
  content: string
  progress: number
  completed: boolean
  completed_questions: number
  total_questions: number
  best_score: number
  average_score: number
  attempt_count: number
}

export default function LearningPage() {
  const router = useRouter()
  const [chapters, setChapters] = useState<LearningChapter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      router.push('/sign-in')
      return
    }

    async function loadChapters() {
      try {
        const response = await fetch(`${FATIMA_API}/api/fatima/chapters`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        const data = await response.json()
        if (!response.ok) throw new Error(data.error || 'Could not load learning chapters')
        setChapters(data.chapters || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load learning module')
      } finally {
        setLoading(false)
      }
    }

    loadChapters()
  }, [router])

  const completedCount = chapters.filter(chapter => chapter.completed).length
  const totalCount = chapters.length
  const completionPercentage = totalCount ? Math.round((completedCount / totalCount) * 100) : 0
  const totalAttempts = chapters.reduce((sum, chapter) => sum + chapter.attempt_count, 0)
  const nextChapter = useMemo(() => chapters.find(chapter => !chapter.completed) || chapters[0], [chapters])

  return (
    <div className="p-4 lg:p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="pt-12 lg:pt-0">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-primary" />
            </div>
            <h1 className="text-3xl font-bold text-foreground">Learning Path</h1>
          </div>
          <p className="text-muted-foreground">
            Master prompt engineering through structured lessons, real practice questions, saved sessions, and progress tracking.
          </p>
        </div>

        <Card className="bg-card border-border animate-in fade-in slide-in-from-bottom-2 duration-300">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-muted-foreground">Overall Progress</p>
                <p className="text-2xl font-bold text-foreground">
                  {loading ? 'Loading...' : `${completedCount} of ${totalCount} chapters`}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Practice Attempts</p>
                <p className="text-2xl font-bold text-foreground">{loading ? '...' : totalAttempts}</p>
              </div>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
              <div className="bg-primary h-2 rounded-full transition-all duration-700" style={{ width: `${completionPercentage}%` }} />
            </div>
            <p className="text-xs text-muted-foreground mt-2">{completionPercentage}% completed</p>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-4 text-sm text-destructive">
              {error}. Make sure the deployed backend is reachable at https://laiba52.pythonanywhere.com and that the frontend is configured with the correct environment variables.
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading chapters...
          </div>
        ) : (
          <div className="space-y-4">

            {/* ── Final Exam card — locked/unlocked dynamically ── */}
            {(() => {
              const unlocked = completedCount === totalCount && totalCount > 0
              const remaining = totalCount - completedCount

              const inner = (
                <div className={`rounded-xl border-2 p-5 transition-all duration-300 ${
                  unlocked
                    ? 'border-primary bg-primary/5 hover:bg-primary/10 cursor-pointer group'
                    : 'border-border bg-muted/30'
                }`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform duration-200 ${
                      unlocked
                        ? 'bg-primary text-primary-foreground group-hover:scale-110'
                        : 'bg-muted text-muted-foreground'
                    }`}>
                      {unlocked
                        ? <Award className="w-7 h-7" />
                        : <Lock className="w-7 h-7" />
                      }
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <h3 className={`font-semibold text-lg ${unlocked ? 'text-foreground group-hover:text-primary transition-colors' : 'text-muted-foreground'}`}>
                          Final Certification Exam
                        </h3>
                        {!unlocked && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-muted border border-border text-muted-foreground font-medium">
                            Locked
                          </span>
                        )}
                        {unlocked && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 font-medium">
                            Unlocked
                          </span>
                        )}
                      </div>

                      {unlocked ? (
                        <p className="text-sm text-muted-foreground">
                          All chapters complete — you are ready to take the exam.
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Unlock by completing all chapters.{' '}
                          <span className="text-foreground font-medium">
                            {completedCount}/{totalCount} done
                            {remaining > 0 && ` — ${remaining} remaining`}.
                          </span>
                        </p>
                      )}

                      {!unlocked && totalCount > 0 && (
                        <div className="mt-3 w-full max-w-xs">
                          <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-primary h-1.5 rounded-full transition-all duration-700"
                              style={{ width: `${completionPercentage}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {unlocked && (
                      <ChevronRight className="w-5 h-5 text-primary opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-150 flex-shrink-0" />
                    )}
                  </div>
                </div>
              )

              return unlocked
                ? <Link href="/dashboard/learning/final-test">{inner}</Link>
                : inner
            })()}

            <h2 className="text-xl font-semibold text-foreground pt-2">Chapters</h2>

            {chapters.map((chapter, index) => {
              const isCompleted = chapter.completed
              const isCurrent = !isCompleted && chapter.id === nextChapter?.id

              return (
                <Link key={chapter.id} href={`/dashboard/learning/${chapter.id}`}
                  style={{ animationDelay: `${index * 60}ms` }}
                  className="block animate-in fade-in slide-in-from-bottom-2 duration-300 fill-mode-both"
                >
                  <Card className={`bg-card border-border hover:border-primary/50 hover:shadow-md transition-all duration-200 group cursor-pointer ${isCurrent ? 'ring-1 ring-primary/50' : ''}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                          isCompleted
                            ? 'bg-primary text-primary-foreground'
                            : isCurrent
                              ? 'bg-primary/10 text-primary'
                              : 'bg-muted text-muted-foreground'
                        }`}>
                          {isCompleted ? <CheckCircle className="w-6 h-6" /> : <span className="text-lg font-bold">{index + 1}</span>}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors duration-150">
                                {chapter.title}
                              </h3>
                              <p className="text-sm text-muted-foreground mt-1">{chapter.description}</p>

                              <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {chapter.duration}
                                </span>
                                <span>{chapter.completed_questions}/{chapter.total_questions} practice questions completed</span>
                                <span>Best score: {chapter.best_score || 0}</span>
                              </div>

                              <div className="w-full bg-muted rounded-full h-2 mt-4 overflow-hidden">
                                <div
                                  className="bg-primary h-2 rounded-full transition-all duration-700"
                                  style={{ width: `${chapter.progress}%` }}
                                />
                              </div>
                            </div>

                            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all duration-150 flex-shrink-0" />
                          </div>

                          {isCurrent && (
                            <div className="mt-4">
                              <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 transition-all hover:scale-105 active:scale-95">
                                Continue Learning
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              )
            })}

            {nextChapter && (
              <div className="pt-4 flex justify-end">
                <Link href={`/dashboard/learning/${nextChapter.id}/practice`}>
                  <Button
                    size="lg"
                    variant="outline"
                    className="active:scale-95"
                  >
                    <PlayCircle className="w-5 h-5 mr-2" />
                    Start Practice
                  </Button>
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
