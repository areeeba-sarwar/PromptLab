'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Sparkles,
  Send,
  Mic,
  Loader2,
  Copy,
  Check,
  RefreshCw,
  Wand2,
  History,
  Plus,
  MessageSquare,
  Trash2,
  AlertCircle
} from 'lucide-react'
import { getAuthToken } from '@/contexts/auth-context'

const RABIA_API = process.env.NEXT_PUBLIC_RABIA_API || 'https://laiba52.pythonanywhere.com'

interface MessageMeta {
  version_id?: number
}

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  iteration: number
  metadata?: MessageMeta | null
  created_at: string
}

interface EnhancementVersion {
  id: number
  version_number: number
  input_prompt: string
  enhanced_prompt: string
  created_at: string
}

interface EnhancementSession {
  id: number
  title: string
  original_prompt: string
  status: string
  created_at: string
  updated_at: string
  latest_version?: EnhancementVersion | null
  messages?: ChatMessage[]
  versions?: EnhancementVersion[]
}

function formatDate(value: string) {
  if (!value) return ''
  let normalized = value.includes('T') ? value : value.replace(' ', 'T')
  if (!normalized.endsWith('Z') && !normalized.match(/[+-]\d{2}:\d{2}$/)) normalized += 'Z'
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function shortText(text: string, length = 70) {
  if (!text) return 'New enhancement'
  return text.length > length ? `${text.slice(0, length)}...` : text
}

function isContinuationRequest(text: string) {
  const value = text.trim().toLowerCase()
  return [
    'enhance again',
    'improve further',
    'refine',
    'refine this',
    'create another version',
    'another version',
    'version 2',
    'version 3',
    'expand this',
    'make it better'
  ].includes(value)
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance

interface SpeechRecognitionResultItem {
  transcript: string
}

interface SpeechRecognitionResult {
  isFinal: boolean
  [index: number]: SpeechRecognitionResultItem
}

interface SpeechRecognitionEventLike {
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResult
  }
}

interface SpeechRecognitionErrorEventLike {
  error: string
}

interface SpeechRecognitionInstance {
  continuous: boolean
  interimResults: boolean
  lang: string
  onstart: (() => void) | null
  onend: (() => void) | null
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onspeechstart: (() => void) | null
  onsoundstart: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

function appendSpeechText(current: string, speech: string) {
  if (!current.trim()) return speech
  return `${current.trimEnd()} ${speech}`
}

export default function EnhancerPage() {
  const router = useRouter()
  const [input, setInput] = useState('')
  const [sessions, setSessions] = useState<EnhancementSession[]>([])
  const [activeSession, setActiveSession] = useState<EnhancementSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [error, setError] = useState('')
  const [speechError, setSpeechError] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const speechBaseRef = useRef('')
  const finalSpeechRef = useRef('')
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      router.push('/sign-in')
      return
    }
    fetchSessions()
  }, [router])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 180) + 'px'
    }
  }, [input])

  const apiHeaders = () => {
    const token = getAuthToken()
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  }

  const fetchSessions = async () => {
    const token = getAuthToken()
    if (!token) return

    setSessionsLoading(true)
    try {
      const response = await fetch(`${RABIA_API}/api/rabia/enhancer/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.status === 401) {
        router.push('/sign-in')
        return
      }

      const data = await response.json()
      setSessions(data.sessions || [])
    } catch {
      setError('Unable to load enhancement history. Make sure the backend is reachable at https://laiba52.pythonanywhere.com.')
    } finally {
      setSessionsLoading(false)
    }
  }

  const loadSession = async (sessionId: number) => {
    const token = getAuthToken()
    if (!token) return

    setError('')
    setIsLoading(true)
    try {
      const response = await fetch(`${RABIA_API}/api/rabia/enhancer/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const data = await response.json()

      if (!response.ok) {
        setError(data.error || 'Unable to load this session.')
        return
      }

      setActiveSession(data.session)
      setMessages(data.session.messages || [])
    } catch {
      setError('Unable to load session.')
    } finally {
      setIsLoading(false)
    }
  }

  const startNewChat = () => {
    setActiveSession(null)
    setMessages([])
    setInput('')
    setError('')
  }

  const syncSessionFromResponse = (session: EnhancementSession) => {
    setActiveSession(session)
    setMessages(session.messages || [])
    setInput('')
    fetchSessions()
  }

  const handleEnhance = async () => {
    const prompt = input.trim()
    if (!prompt || isLoading) return

    // Context isolation: typing a new prompt always starts an independent
    // enhancement session. Only explicit continuation commands use the latest
    // enhanced prompt from the active session.
    if (activeSession && latestAssistantMessage && isContinuationRequest(prompt)) {
      setInput('')
      await handleEnhanceAgain()
      return
    }

    setActiveSession(null)
    setMessages([])
    setError('')
    setIsLoading(true)

    const temporaryMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: prompt,
      iteration: (activeSession?.versions?.length || 0) + 1,
      created_at: new Date().toISOString()
    }

    setMessages(prev => [...prev, temporaryMessage])
    setInput('')

    try {
      const response = await fetch(`${RABIA_API}/api/rabia/enhancer/enhance`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          prompt
        })
      })

      const data = await response.json()

      if (response.status === 401) {
        router.push('/sign-in')
        return
      }

      if (!response.ok) {
        setError(data.error || 'Enhancement failed.')
        setMessages(prev => prev.filter(msg => msg.id !== temporaryMessage.id))
        return
      }

      syncSessionFromResponse(data.session)
    } catch {
      setError('Enhancement failed. Make sure the backend is reachable at https://laiba52.pythonanywhere.com and that the request origin is allowed.')
      setMessages(prev => prev.filter(msg => msg.id !== temporaryMessage.id))
    } finally {
      setIsLoading(false)
    }
  }

  const handleEnhanceAgain = async () => {
    if (!activeSession || isLoading) return

    setError('')
    setIsLoading(true)

    try {
      const response = await fetch(`${RABIA_API}/api/rabia/enhancer/sessions/${activeSession.id}/enhance-again`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({})
      })

      const data = await response.json()

      if (response.status === 401) {
        router.push('/sign-in')
        return
      }

      if (!response.ok) {
        setError(data.error || 'Enhance Again failed.')
        return
      }

      syncSessionFromResponse(data.session)
    } catch {
      setError('Enhance Again failed. Check that Rabia backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const deleteSession = async (sessionId: number) => {
    const token = getAuthToken()
    if (!token) return

    try {
      await fetch(`${RABIA_API}/api/rabia/enhancer/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })

      if (activeSession?.id === sessionId) {
        startNewChat()
      }
      fetchSessions()
    } catch {
      setError('Unable to delete session.')
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEnhance()
    }
  }

  const stopListening = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  const resetSilenceTimer = () => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(stopListening, 4000)
  }

  const handleMicClick = () => {
    if (isListening) {
      stopListening()
      return
    }

    const SpeechRecognition =
      (window as typeof window & {
        SpeechRecognition?: SpeechRecognitionConstructor
        webkitSpeechRecognition?: SpeechRecognitionConstructor
      }).SpeechRecognition ||
      (window as typeof window & {
        SpeechRecognition?: SpeechRecognitionConstructor
        webkitSpeechRecognition?: SpeechRecognitionConstructor
      }).webkitSpeechRecognition

    if (!SpeechRecognition) {
      setSpeechError('Voice input is not supported in this browser.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'
    recognitionRef.current = recognition
    speechBaseRef.current = input
    finalSpeechRef.current = ''
    setSpeechError('')

    recognition.onstart = () => {
      setIsListening(true)
      resetSilenceTimer()
    }

    recognition.onspeechstart = resetSilenceTimer
    recognition.onsoundstart = resetSilenceTimer

    recognition.onresult = (event) => {
      resetSilenceTimer()
      let interimTranscript = ''

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript
        if (event.results[index].isFinal) {
          finalSpeechRef.current = appendSpeechText(finalSpeechRef.current, transcript.trim())
        } else {
          interimTranscript = appendSpeechText(interimTranscript, transcript.trim())
        }
      }

      const speechText = appendSpeechText(finalSpeechRef.current, interimTranscript.trim())
      setInput(appendSpeechText(speechBaseRef.current, speechText))
    }

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setSpeechError('Microphone permission was denied. Please allow microphone access to use voice input.')
      } else {
        setSpeechError('Voice input stopped unexpectedly. Please try again.')
      }
      stopListening()
    }

    recognition.onend = () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }
      setIsListening(false)
    }

    try {
      recognition.start()
    } catch {
      setSpeechError('Voice input could not be started. Please try again.')
      setIsListening(false)
    }
  }

  useEffect(() => {
    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      recognitionRef.current?.abort()
    }
  }, [])

  const latestAssistantMessage = [...messages].reverse().find(message => message.role === 'assistant')

  return (
    <div className="h-screen overflow-hidden flex flex-col">
      <div className="border-b border-border bg-card/50 shrink-0">
        <div className="max-w-7xl mx-auto p-4 lg:px-8 lg:py-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Prompt Enhancement Workspace</h1>
              <p className="text-sm text-muted-foreground">
                Convert simple prompts into complete, polished, ready-to-use prompts.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto w-full flex-1 min-h-0 p-4 lg:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6 h-full min-h-0">
          <aside className="h-full min-h-0 overflow-hidden">
            <Card className="bg-card border-border h-full flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2 text-foreground">
                  <History className="w-4 h-4 text-muted-foreground" />
                  Enhancement Sessions
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={startNewChat}
                  className="border-border text-foreground"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  New
                </Button>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-hidden">
                {sessionsLoading ? (
                  <div className="flex items-center justify-center py-8 text-muted-foreground">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Loading...
                  </div>
                ) : sessions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">
                    No saved sessions yet. History appears after you submit a prompt.
                  </p>
                ) : (
                  <div className="space-y-2 h-full overflow-y-auto pr-1">
                    {sessions.map(session => (
                      <div
                        key={session.id}
                        className={`group rounded-lg border p-3 transition-colors cursor-pointer ${
                          activeSession?.id === session.id
                            ? 'border-primary/40 bg-primary/10'
                            : 'border-border bg-muted/20 hover:bg-muted/40'
                        }`}
                        onClick={() => loadSession(session.id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground line-clamp-2">
                              {session.title}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {formatDate(session.updated_at)}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteSession(session.id)
                            }}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                            aria-label="Delete session"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        {session.latest_version && (
                          <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
                            <Sparkles className="w-3 h-3 text-primary" />
                            <span>{session.latest_version.version_number} enhanced version{session.latest_version.version_number > 1 ? 's' : ''}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </aside>

          <main className="h-full min-h-0 flex flex-col space-y-4">
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="w-4 h-4 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
            {speechError && (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="w-4 h-4 mt-0.5" />
                <span>{speechError}</span>
              </div>
            )}

            <Card className="bg-card border-border flex-1 min-h-0 flex flex-col overflow-hidden">
              <CardHeader className="border-b border-border shrink-0 bg-card z-10">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2 text-foreground">
                      <MessageSquare className="w-5 h-5 text-primary" />
                      {activeSession ? activeSession.title : 'New Enhancement Chat'}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">
                      {activeSession
                        ? `Last updated ${formatDate(activeSession.updated_at)}`
                        : 'Type a prompt below to start a saved enhancement session.'}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEnhanceAgain}
                    disabled={!latestAssistantMessage || isLoading}
                    className="border-border text-foreground shrink-0"
                    title={latestAssistantMessage ? 'Refine the latest enhanced prompt' : 'Submit a prompt first'}
                  >
                    <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                    Enhance Again
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="flex-1 min-h-0 flex flex-col p-0">
                <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6 space-y-5">
                  {messages.length === 0 && !isLoading ? (
                    <div className="h-full min-h-[360px] flex items-center justify-center text-center">
                      <div className="max-w-md">
                        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                          <Wand2 className="w-8 h-8 text-primary" />
                        </div>
                        <h3 className="text-lg font-semibold text-foreground mb-2">Ready to Enhance</h3>
                        <p className="text-sm text-muted-foreground">
                          Enter any weak or simple prompt. The engine will return only the final enhanced prompt.
                        </p>
                      </div>
                    </div>
                  ) : (
                    messages.map(message => (
                      <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[90%] rounded-2xl p-4 ${
                            message.role === 'user'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted/40 border border-border text-foreground'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-medium opacity-70 mb-2">
                                {message.role === 'user'
                                  ? 'Your prompt'
                                  : `Enhanced prompt${message.iteration ? ` - Version ${message.iteration}` : ''}`}
                              </p>
                              <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                            </div>
                            {message.role === 'assistant' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => copyToClipboard(message.content, `message-${message.id}`)}
                                className="shrink-0 h-8 px-2"
                              >
                                {copiedId === `message-${message.id}` ? (
                                  <Check className="w-4 h-4 text-primary" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}

                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="rounded-2xl bg-muted/40 border border-border p-4 text-sm text-muted-foreground flex items-center">
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Enhancing prompt...
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                <div className="border-t border-border p-4 shrink-0 bg-card">
                  <div className="flex gap-3">
                    <textarea
                      ref={textareaRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Enter a prompt to improve, e.g. 'Tell me about AI'"
                      rows={1}
                      className="flex-1 resize-none bg-input border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleMicClick}
                      disabled={isLoading}
                      className="self-end"
                      title={isListening ? 'Stop listening' : 'Start voice input'}
                    >
                      <Mic className={`w-4 h-4 ${isListening ? 'animate-pulse text-primary' : ''}`} />
                    </Button>
                    <Button
                      onClick={handleEnhance}
                      disabled={!input.trim() || isLoading}
                      className="bg-primary text-primary-foreground hover:bg-primary/90 self-end"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <p className="text-xs text-muted-foreground">{isListening ? 'Listening...' : 'Press Cmd/Ctrl + Enter to enhance'}</p>
                    <p className="text-xs text-muted-foreground">Returns one enhanced prompt only</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </main>
        </div>
      </div>
    </div>
  )
}
