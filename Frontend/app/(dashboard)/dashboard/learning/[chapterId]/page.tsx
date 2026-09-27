'use client'

import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Clock, CheckCircle, Target, Loader2, PlayCircle } from 'lucide-react'
import Link from 'next/link'
import { getAuthToken } from '@/contexts/auth-context'

const FATIMA_API = process.env.NEXT_PUBLIC_FATIMA_API || 'https://laiba52.pythonanywhere.com'

interface LearningChapter {
  id: string
  title: string
  description: string
  duration: string
  lessons: number
  content: string
  videoUrl: string | null
  progress: number
  completed: boolean
  completed_questions: number
  total_questions: number
  best_score: number
  average_score: number
  attempt_count: number
}

interface PracticeQuestion {
  id: number
  title: string
  scenario: string
  difficulty: string
}

export default function ChapterPage({ params }: { params: Promise<{ chapterId: string }> }) {
  const { chapterId } = use(params)
  const router = useRouter()
  const [chapter, setChapter] = useState<LearningChapter | null>(null)
  const [questions, setQuestions] = useState<PracticeQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      router.push('/sign-in')
      return
    }

    async function loadChapter() {
      try {
        const response = await fetch(`${FATIMA_API}/api/fatima/chapters/${chapterId}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        const data = await response.json()
        if (!response.ok) throw new Error(data.error || 'Could not load chapter')
        setChapter(data.chapter)
        setQuestions(data.questions || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load chapter')
      } finally {
        setLoading(false)
      }
    }

    loadChapter()
  }, [chapterId, router])

  if (loading) {
    return (
      <div className="p-4 lg:p-8">
        <div className="max-w-4xl mx-auto flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading chapter...
        </div>
      </div>
    )
  }

  if (error || !chapter) {
    return (
      <div className="p-4 lg:p-8">
        <div className="max-w-4xl mx-auto text-center py-12">
          <h1 className="text-2xl font-bold text-foreground">Chapter not found</h1>
          <p className="text-sm text-muted-foreground mt-2">{error}</p>
          <Button variant="link" onClick={() => router.push('/dashboard/learning')} className="mt-4 text-primary">
            Back to Learning
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto p-4 lg:p-8">
          <div className="pt-8 lg:pt-0">
            <Link href="/dashboard/learning" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4">
              <ArrowLeft className="w-4 h-4" />
              Back to Learning
            </Link>

            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground">{chapter.title}</h1>
                <p className="text-muted-foreground mt-2">{chapter.description}</p>
                <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="w-4 h-4" />{chapter.duration}</span>
                  <span className="flex items-center gap-1"><Target className="w-4 h-4" />{chapter.completed_questions}/{chapter.total_questions} practice questions completed</span>
                  {chapter.completed && <span className="flex items-center gap-1 text-primary"><CheckCircle className="w-4 h-4" />Completed</span>}
                </div>
              </div>
              <Link href={`/dashboard/learning/${chapterId}/practice`}>
                <Button className="bg-primary text-primary-foreground hover:bg-primary/90">Start Practice</Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 lg:p-8 space-y-8">
        <Card className="bg-card border-border">
          <CardContent className="p-6 lg:p-8">
            <div className="prose prose-invert max-w-none">
              {chapter.content.split('\n').map((line, i) => {
                if (line.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold mb-4">{line.slice(2)}</h1>
                if (line.startsWith('## ')) return <h2 key={i} className="text-xl font-semibold mt-8 mb-3">{line.slice(3)}</h2>
                if (line.startsWith('### ')) return <h3 key={i} className="text-lg font-medium mt-6 mb-2">{line.slice(4)}</h3>
                if (line.startsWith('- ')) return <li key={i} className="ml-4 list-disc">{line.slice(2)}</li>
                if (line.trim() === '') return <div key={i} className="h-4" />
                return <p key={i} className="leading-relaxed">{line}</p>
              })}
            </div>
          </CardContent>
        </Card>

        {chapter.videoUrl && (
          <Card className="bg-card border-border">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <PlayCircle className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold text-foreground">Chapter Video</h2>
              </div>
              <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-black">
                <iframe
                  src={`${chapter.videoUrl}?rel=0&modestbranding=1`}
                  title={`${chapter.title} — video`}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                  className="absolute inset-0 w-full h-full"
                />
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="bg-card border-border">
          <CardContent className="p-6">
            <h2 className="text-xl font-semibold text-foreground mb-4">Practice Questions</h2>
            <div className="space-y-3">
              {questions.map((question, index) => (
                <div key={question.id} className="flex items-start justify-between gap-4 rounded-lg border border-border p-4">
                  <div>
                    <p className="text-sm font-medium text-foreground">{index + 1}. {question.title}</p>
                    <p className="text-sm text-muted-foreground mt-1">{question.scenario}</p>
                  </div>
                  <span className="text-xs rounded-full bg-muted px-2 py-1 text-muted-foreground capitalize">{question.difficulty}</span>
                </div>
              ))}
            </div>
            <p className="text-sm text-muted-foreground mt-4">
              Chapter completion is automatic. Complete all practice questions with a passing score to mark this chapter as completed.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
