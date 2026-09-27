'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  ArrowRight,
  Award,
  BookOpen,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Facebook,
  Github,
  Instagram,
  Linkedin,
  MessageSquare,
  Mouse,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { PromptLabIcon } from '@/components/promptlab-logo'
import { ThemeToggle } from '@/components/theme-toggle'

const navLinks = [
  { href: '#home', label: 'Home' },
  { href: '#features', label: 'Features' },
  { href: '#faq', label: 'FAQ' },
]

const typingPhrases = [
  'Write Better Prompts',
  'Get Real-Time Feedback',
  'Master AI Communication',
]

const floatingChips = [
  { label: 'Real-time Feedback', className: 'left-5 top-28 hidden border-emerald-400/40 bg-emerald-50 text-emerald-700 dark:border-emerald-300/35 dark:bg-emerald-400/10 dark:text-emerald-100 md:flex' },
  { label: 'AI-Powered', className: 'right-10 top-32 hidden border-cyan-400/40 bg-cyan-50 text-cyan-700 dark:border-cyan-300/35 dark:bg-cyan-400/10 dark:text-cyan-100 lg:flex' },
  { label: 'Track Progress', className: 'left-14 bottom-32 hidden border-lime-400/40 bg-lime-50 text-lime-700 dark:border-lime-300/35 dark:bg-lime-400/10 dark:text-lime-100 lg:flex' },
  { label: 'Smart Practice', className: 'right-14 bottom-36 hidden border-teal-400/40 bg-teal-50 text-teal-700 dark:border-teal-300/35 dark:bg-teal-400/10 dark:text-teal-100 md:flex' },
  { label: '6 Guided Chapters', className: 'right-[12%] top-[31%] hidden border-violet-400/40 bg-violet-50 text-violet-700 dark:border-violet-300/35 dark:bg-violet-400/10 dark:text-violet-100 xl:flex' },
  { label: 'Final Certificate', className: 'left-[8%] top-[61%] hidden border-amber-400/45 bg-amber-50 text-amber-700 dark:border-amber-300/40 dark:bg-amber-400/10 dark:text-amber-100 xl:flex' },
]

const floatingIcons = [
  { icon: Sparkles, className: 'left-[16%] top-[40%] hidden border-emerald-400/35 bg-emerald-50 text-emerald-700 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-200 lg:flex' },
  { icon: Zap, className: 'right-[15%] top-[43%] hidden border-cyan-400/35 bg-cyan-50 text-cyan-700 dark:border-cyan-300/30 dark:bg-cyan-400/10 dark:text-cyan-200 lg:flex' },
  { icon: Target, className: 'left-[29%] bottom-[19%] hidden border-lime-400/35 bg-lime-50 text-lime-700 dark:border-lime-300/30 dark:bg-lime-400/10 dark:text-lime-200 xl:flex' },
  { icon: Award, className: 'right-[31%] bottom-[20%] hidden border-amber-400/35 bg-amber-50 text-amber-700 dark:border-amber-300/30 dark:bg-amber-400/10 dark:text-amber-200 xl:flex' },
]

const features = [
  {
    icon: BookOpen,
    title: 'Structured Learning',
    description: 'Master prompt engineering through 6 comprehensive chapters with hands-on exercises.',
    detail: 'Move through focused lessons, quizzes, and practice tasks that build from beginner basics to confident AI communication.',
  },
  {
    icon: MessageSquare,
    title: 'Practice Mode',
    description: 'ChatGPT-like interface for practicing prompts with real-time AI feedback.',
    detail: 'Try prompts in a guided workspace and improve clarity, specificity, and structure with actionable suggestions.',
  },
  {
    icon: Zap,
    title: 'Live Evaluation',
    description: 'Get instant scores on clarity, structure, and specificity for every prompt.',
    detail: 'See scoring feedback as you practice, so every attempt teaches you exactly what to improve next.',
  },
  {
    icon: Sparkles,
    title: 'Prompt Enhancer',
    description: 'Transform basic prompts into powerful, effective ones with AI assistance.',
    detail: 'Compare your original prompt with an enhanced version and learn why the stronger version works better.',
  },
]

const stats = [
  { value: 500, suffix: '+', label: 'Learners' },
  { value: 6, suffix: '', label: 'Chapters' },
  { value: 10000, suffix: '+', label: 'Prompts Practiced' },
  { value: 50, suffix: '+', label: 'Practice Problems' },
]

const steps = [
  {
    step: '01',
    title: 'Learn the Fundamentals',
    description: 'Start with structured chapters covering prompt clarity, context, constraints, and examples.',
    icon: BookOpen,
  },
  {
    step: '02',
    title: 'Practice with Feedback',
    description: 'Apply each concept in realistic exercises and get direct AI-powered evaluation.',
    icon: Target,
  },
  {
    step: '03',
    title: 'Improve and Certify',
    description: 'Refine weak prompts, complete the final test, and earn your completion certificate.',
    icon: Award,
  },
]

const faqs = [
  {
    question: 'What is PromptLab?',
    answer: 'PromptLab is an interactive learning platform that helps you learn, practice, evaluate, and improve AI prompts through guided lessons and hands-on feedback.',
  },
  {
    question: 'Do I need any prior experience?',
    answer: 'No. PromptLab starts with beginner-friendly fundamentals and gradually moves into more advanced prompt engineering techniques.',
  },
  {
    question: 'How does the scoring system work?',
    answer: 'Your prompts are evaluated on practical quality signals such as clarity, structure, specificity, and usefulness. The score helps you see what to improve next.',
  },
  {
    question: 'How do I earn my certificate?',
    answer: 'Complete the learning chapters, practice activities, and final assessment. When you meet the completion criteria, your certificate can be unlocked.',
  },
  {
    question: 'Can I retake the final exam?',
    answer: 'Yes. You can review the material and retake the final exam so your result reflects your improved understanding.',
  },
  {
    question: 'Is PromptLab free to use?',
    answer: 'The landing page links users into the learning flow without requiring payment details. Any future paid features can be added without changing the core learning path.',
  },
  {
    question: 'How does the streak system work?',
    answer: 'The streak system rewards consistent practice by tracking learning activity over time and encouraging regular progress.',
  },
  {
    question: 'What is the AI detection feature?',
    answer: 'The AI detection feature helps analyze prompt quality and feedback signals so learners can understand how their input may be interpreted by AI systems.',
  },
]

function useScrollReveal() {
  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>('[data-reveal]')
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.16 },
    )

    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])
}

function useTypewriter(words: string[]) {
  const [wordIndex, setWordIndex] = useState(0)
  const [letterCount, setLetterCount] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const current = words[wordIndex]
    const finishedTyping = !deleting && letterCount === current.length
    const finishedDeleting = deleting && letterCount === 0
    const delay = finishedTyping ? 1200 : deleting ? 42 : 82

    const timer = window.setTimeout(() => {
      if (finishedTyping) {
        setDeleting(true)
        return
      }
      if (finishedDeleting) {
        setDeleting(false)
        setWordIndex((index) => (index + 1) % words.length)
        return
      }
      setLetterCount((count) => count + (deleting ? -1 : 1))
    }, delay)

    return () => window.clearTimeout(timer)
  }, [deleting, letterCount, wordIndex, words])

  return words[wordIndex].slice(0, letterCount)
}

function CountUp({ value, suffix, active }: { value: number; suffix: string; active: boolean }) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!active) return
    let frame = 0
    const totalFrames = 90
    const timer = window.setInterval(() => {
      frame += 1
      const progress = 1 - Math.pow(1 - frame / totalFrames, 3)
      setCount(Math.round(value * progress))
      if (frame >= totalFrames) {
        setCount(value)
        window.clearInterval(timer)
      }
    }, 16)

    return () => window.clearInterval(timer)
  }, [active, value])

  return (
    <>
      {count.toLocaleString()}
      {suffix}
    </>
  )
}

export default function HomePage() {
  const typedText = useTypewriter(typingPhrases)
  const [activeSection, setActiveSection] = useState('home')
  const [statsActive, setStatsActive] = useState(false)
  const [openFaq, setOpenFaq] = useState(0)
  const [showTop, setShowTop] = useState(false)

  useScrollReveal()

  useEffect(() => {
    const sections = ['home', 'features', 'how-it-works', 'stats', 'faq']
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id)
            if (entry.target.id === 'stats') setStatsActive(true)
          }
        })
      },
      { rootMargin: '-35% 0px -55% 0px', threshold: 0 },
    )

    sections.forEach((id) => {
      const element = document.getElementById(id)
      if (element) observer.observe(element)
    })

    const onScroll = () => setShowTop(window.scrollY > window.innerHeight * 0.7)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })

    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  const activeNav = useMemo(() => {
    if (activeSection === 'faq') return 'faq'
    if (activeSection === 'features' || activeSection === 'how-it-works' || activeSection === 'stats') return 'features'
    return 'home'
  }, [activeSection])

  return (
    <div id="top" className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border/80 bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
          <Link href="#home" className="flex items-center gap-2 transition-transform hover:scale-[1.02]">
            <PromptLabIcon size={40} className="h-10 w-10 object-contain" />
            <span className="text-lg font-semibold text-foreground">PromptLab</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary navigation">
            {navLinks.map((link) => {
              const id = link.href.replace('#', '')
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-full px-4 py-2 text-sm transition-colors hover:bg-primary/10 hover:text-primary ${
                    activeNav === id ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
                  }`}
                >
                  {link.label}
                </Link>
              )
            })}
          </nav>
          <div className="flex items-center gap-2 sm:gap-4">
            <ThemeToggle />
            <Link href="/sign-in">
              <Button variant="ghost" className="text-foreground hover:text-primary">
                Sign In
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button className="bg-primary text-primary-foreground transition-transform hover:scale-[1.02] hover:bg-primary/90">
                Sign Up
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section id="home" className="relative min-h-[calc(100vh-4rem)] overflow-hidden">
          <div
            aria-hidden="true"
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'var(--hero-gradient)',
              backgroundSize: '300% 300%',
              animation: 'heroGradientMove 8s ease infinite',
            }}
          />

          {floatingChips.map((chip, index) => (
            <div
              key={chip.label}
              className={`floating-chip absolute z-10 items-center rounded-full border px-4 py-2 text-sm font-medium shadow-lg shadow-black/20 backdrop-blur ${chip.className}`}
              style={{ animationDelay: `${index * 0.45}s` }}
            >
              {chip.label}
            </div>
          ))}

          {floatingIcons.map((item, index) => (
            <div
              key={index}
              className={`floating-chip absolute z-10 h-11 w-11 items-center justify-center rounded-2xl border shadow-lg shadow-black/20 backdrop-blur ${item.className}`}
              style={{ animationDelay: `${index * 0.55 + 0.25}s` }}
              aria-hidden="true"
            >
              <item.icon className="h-5 w-5" />
            </div>
          ))}

          <div className="relative z-20 mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl items-center px-4 py-20">
            <div className="mx-auto max-w-3xl text-center" data-reveal>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
                <Sparkles className="h-4 w-4" />
                AI-Powered Learning Platform
              </div>
              <h1 className="mb-6 text-balance text-4xl font-bold text-foreground lg:text-6xl">
                <span className="block">Master Prompt</span>
                <span className="block">Engineering to</span>
                <span className="mt-3 block min-h-[1.15em] text-primary">
                  {typedText}
                  <span className="typewriter-caret" aria-hidden="true" />
                </span>
              </h1>
              <p className="mx-auto mb-8 max-w-2xl text-pretty text-lg text-muted-foreground">
                Learn, practice, and perfect your AI prompts with structured lessons, real-time feedback,
                and AI-powered enhancements.
              </p>
              <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
                <Link href="/sign-up">
                  <Button size="lg" className="w-full bg-primary text-primary-foreground transition-transform hover:scale-[1.02] hover:bg-primary/90 sm:w-auto">
                    Start Learning Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
                <Link href="#features">
                  <Button size="lg" variant="outline" className="w-full border-border text-foreground hover:border-primary hover:text-primary-foreground sm:w-auto">
                    Explore Features
                  </Button>
                </Link>
              </div>
            </div>
          </div>

          <Link
            href="#features"
            aria-label="Scroll to features"
            className="scroll-indicator absolute bottom-6 left-1/2 z-30 flex -translate-x-1/2 flex-col items-center gap-2 text-primary transition-colors hover:text-foreground"
          >
            <Mouse className="h-6 w-6" />
            <ChevronDown className="h-5 w-5" />
          </Link>
        </section>

        <section id="features" className="py-20 lg:py-28">
          <div className="mx-auto max-w-7xl px-4">
            <div className="mb-12 text-center" data-reveal>
              <h2 className="mb-4 text-3xl font-bold text-foreground lg:text-4xl">Everything You Need to Excel</h2>
              <p className="mx-auto max-w-2xl text-muted-foreground">
                Learning, practice, and AI assistance work together so every prompt gets sharper.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {features.map((feature) => (
                <Card
                  key={feature.title}
                  data-reveal
                  className="feature-card group min-h-64 overflow-hidden border-border bg-card transition-all duration-300 hover:-translate-y-1 hover:border-primary/60 hover:shadow-xl hover:shadow-primary/10"
                >
                  <CardContent className="relative h-full p-6">
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 transition-colors group-hover:bg-primary/20">
                      <feature.icon className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="mb-2 text-xl font-semibold text-foreground">{feature.title}</h3>
                    <p className="text-muted-foreground">{feature.description}</p>
                    <div className="mt-5 max-h-0 overflow-hidden border-t border-transparent pt-0 text-sm leading-6 text-muted-foreground transition-all duration-300 group-hover:max-h-32 group-hover:border-border group-hover:pt-4">
                      {feature.detail}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="bg-muted/30 py-20 lg:py-28">
          <div className="mx-auto max-w-7xl px-4">
            <div className="mb-14 text-center" data-reveal>
              <h2 className="mb-4 text-3xl font-bold text-foreground lg:text-4xl">How It Works</h2>
              <p className="mx-auto max-w-2xl text-muted-foreground">
                A clear path from first lesson to confident prompt engineering.
              </p>
            </div>
            <div className="relative grid grid-cols-1 gap-8 md:grid-cols-3">
              <div className="step-line absolute left-[16.5%] top-8 hidden h-px w-[67%] bg-border md:block" aria-hidden="true" />
              {steps.map((item) => (
                <div key={item.step} className="relative text-center" data-reveal>
                  <div className="relative z-10 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-primary/30 bg-background shadow-lg shadow-black/10">
                    <item.icon className="h-8 w-8 text-primary" />
                  </div>
                  <div className="mb-2 text-sm font-medium text-primary">Step {item.step}</div>
                  <h3 className="mb-2 text-xl font-semibold text-foreground">{item.title}</h3>
                  <p className="text-muted-foreground">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="stats" className="border-y border-border bg-background py-14">
          <div className="mx-auto max-w-7xl px-4">
            <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center" data-reveal>
                  <p className="text-3xl font-bold text-primary lg:text-4xl">
                    <CountUp value={stat.value} suffix={stat.suffix} active={statsActive} />
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 lg:py-28">
          <div className="mx-auto max-w-4xl px-4 text-center" data-reveal>
            <div className="rounded-2xl border border-border bg-card p-8 lg:p-12">
              <PromptLabIcon size={80} className="mx-auto mb-6 h-20 w-20 object-contain" />
              <h2 className="mb-4 text-3xl font-bold text-foreground lg:text-4xl">
                Ready to Master Prompt Engineering?
              </h2>
              <p className="mx-auto mb-8 max-w-xl text-muted-foreground">
                Join learners improving their AI communication skills with guided practice and instant feedback.
              </p>
              <Link href="/sign-up">
                <Button size="lg" className="bg-primary text-primary-foreground transition-transform hover:scale-[1.02] hover:bg-primary/90">
                  Get Started for Free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground sm:flex-row sm:gap-6">
                <span className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-primary" />
                  No credit card required
                </span>
                <span className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-primary" />
                  Start learning instantly
                </span>
              </div>
            </div>
          </div>
        </section>

        <section id="faq" className="bg-muted/30 py-20 lg:py-28">
          <div className="mx-auto max-w-4xl px-4">
            <div className="mb-10 text-center" data-reveal>
              <h2 className="mb-4 text-3xl font-bold text-foreground lg:text-4xl">Frequently Asked Questions</h2>
              <p className="text-muted-foreground">Quick answers about learning, scoring, certification, and practice.</p>
            </div>
            <div className="space-y-3">
              {faqs.map((faq, index) => {
                const isOpen = openFaq === index
                return (
                  <div
                    key={faq.question}
                    className={`overflow-hidden rounded-lg border bg-card transition-colors ${
                      isOpen ? 'border-primary/60' : 'border-border hover:border-primary/30'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setOpenFaq(isOpen ? -1 : index)}
                      className="flex w-full cursor-pointer items-center justify-between gap-4 px-5 py-4 text-left text-foreground transition-colors hover:text-primary"
                      aria-expanded={isOpen}
                    >
                      <span className="font-medium">{faq.question}</span>
                      <ChevronDown className={`h-5 w-5 shrink-0 text-primary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </button>
                    <div className={`grid transition-all duration-300 ${isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
                      <div className="overflow-hidden">
                        <p className="px-5 pb-5 text-sm leading-6 text-muted-foreground">{faq.answer}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-background">
        <div className="mx-auto max-w-7xl px-4 py-10">
          <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr] md:items-start">
            <div className="flex flex-col items-center text-center md:items-start md:text-left">
              <div className="mb-4 flex items-center gap-3">
                <PromptLabIcon size={40} className="h-10 w-10 object-contain" />
                <span className="text-xl font-semibold text-foreground">PromptLab</span>
              </div>
              <p className="max-w-sm text-sm leading-6 text-muted-foreground">
                Build stronger prompts, practice with feedback, and communicate better with AI.
              </p>
            </div>

            <nav className="flex flex-col items-center text-center md:items-start md:text-left" aria-label="Footer navigation">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">Navigation</h3>
              <div className="grid min-w-48 grid-cols-2 gap-x-10 gap-y-3 text-sm text-muted-foreground">
                <Link className="transition-colors hover:text-primary" href="#home">Home</Link>
                <Link className="transition-colors hover:text-primary" href="#features">Features</Link>
                <Link className="transition-colors hover:text-primary" href="#faq">FAQ</Link>
                <Link className="transition-colors hover:text-primary" href="/sign-in">Sign In</Link>
                <Link className="transition-colors hover:text-primary" href="/sign-up">Sign Up</Link>
              </div>
            </nav>

            <div className="flex flex-col items-center text-center md:items-end md:text-right">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">Connect</h3>
              <div className="flex gap-3">
                {[
                  { href: 'https://github.com/', label: 'GitHub', icon: Github },
                  { href: 'https://www.linkedin.com/', label: 'LinkedIn', icon: Linkedin },
                  { href: 'https://www.instagram.com/', label: 'Instagram', icon: Instagram },
                  { href: 'https://www.facebook.com/', label: 'Facebook', icon: Facebook },
                ].map((social) => (
                  <Link
                    key={social.label}
                    href={social.href}
                    aria-label={social.label}
                    className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary hover:text-primary"
                  >
                    <social.icon className="h-4 w-4" />
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-center text-sm text-muted-foreground md:flex-row md:text-left">
            <p>© 2025 PromptLab. All rights reserved.</p>
            <p>Built for learning, practice, and better AI communication.</p>
          </div>
        </div>
      </footer>

      <button
        type="button"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        aria-label="Back to top"
        className={`fixed bottom-5 right-5 z-50 flex h-11 w-11 items-center justify-center rounded-full border border-primary/40 bg-background/90 text-primary shadow-lg backdrop-blur transition-all hover:-translate-y-1 hover:bg-primary hover:text-primary-foreground ${
          showTop ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'
        }`}
      >
        <ChevronUp className="h-5 w-5" />
      </button>
    </div>
  )
}
