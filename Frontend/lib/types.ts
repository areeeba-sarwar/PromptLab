export interface User {
  id: string
  name: string
  email: string
}

export interface Chapter {
  id: string
  title: string
  description: string
  duration: string
  lessons: number
  progress: number
  content: string
  videoUrl?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface Evaluation {
  score: number
  clarity: number
  structure: number
  specificity: number
  suggestions: string[]
  strengths: string[]
  weaknesses: string[]
}

export interface PracticeSession {
  problemStatement: string
  messages: Message[]
  currentFeedback?: Evaluation
}

export interface EnhancedPrompt {
  original: string
  enhanced: string
  improvements: string[]
}
