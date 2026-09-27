'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Loader2, AlertTriangle, ShieldAlert, Mic } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  isLoading?: boolean
  placeholder?: string
  /** Block copy/cut/right-click and show a warning banner */
  guardCopy?: boolean
  /** Called when pasted text is likely AI-generated */
  onAiPaste?: () => void
}

// ── AI text heuristics ─────────────────────────────────────────
// Patterns common in AI-generated responses.
const AI_PHRASES = [
  /\bcertainly[,!]?\s/i,
  /\bof course[,!]?\s/i,
  /\bas an ai\b/i,
  /\bas a language model\b/i,
  /\bi('m| am) here to help\b/i,
  /\bi('d| would) be happy to\b/i,
  /\bgreat question\b/i,
  /\bsure[,!]?\s+(here|let me|i('ll|'d))\b/i,
  /\bfeel free to\b/i,
  /\bhope this helps\b/i,
  /\bin conclusion\b/i,
  /\bin summary\b/i,
  /\bto summarize\b/i,
  /\bit('s| is) important to note\b/i,
  /\bit('s| is) worth noting\b/i,
  /\bplease note that\b/i,
  /\blet me know if you\b/i,
  /\bdon't hesitate to\b/i,
]

function isLikelyAiGenerated(text: string): boolean {
  if (text.length < 50) return false
  const matched = AI_PHRASES.filter(r => r.test(text)).length
  return matched >= 2
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

export function ChatInput({
  onSend,
  isLoading,
  placeholder = "Type your prompt...",
  guardCopy = false,
  onAiPaste,
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const [copyWarning, setCopyWarning] = useState(false)
  const [pasteWarning, setPasteWarning] = useState(false)
  const [aiWarning, setAiWarning] = useState(false)
  const [speechError, setSpeechError] = useState('')
  const [isListening, setIsListening] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const speechBaseRef = useRef('')
  const finalSpeechRef = useRef('')
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const stopListening = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    recognitionRef.current?.stop()
    setIsListening(false)
  }, [])

  const resetSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(stopListening, 4000)
  }, [stopListening])

  const handleMicClick = useCallback(() => {
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
  }, [input, isListening, resetSilenceTimer, stopListening])

  useEffect(() => {
    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      recognitionRef.current?.abort()
    }
  }, [])

  const handleCopy = useCallback((e: React.ClipboardEvent) => {
    if (!guardCopy) return
    e.preventDefault()
    setCopyWarning(true)
    setTimeout(() => setCopyWarning(false), 4000)
  }, [guardCopy])

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    if (!guardCopy) return
    e.preventDefault()
    setCopyWarning(true)
    setTimeout(() => setCopyWarning(false), 4000)
  }, [guardCopy])

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    if (guardCopy) {
      // Paste is fully blocked during guarded sessions
      e.preventDefault()
      setPasteWarning(true)
      setTimeout(() => setPasteWarning(false), 4000)
      return
    }
    if (!onAiPaste) return
    const pasted = e.clipboardData?.getData('text') || ''
    if (isLikelyAiGenerated(pasted)) {
      setAiWarning(true)
      onAiPaste()
      setTimeout(() => setAiWarning(false), 6000)
    }
  }, [guardCopy, onAiPaste])

  return (
    <div>
      {copyWarning && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/90 text-destructive-foreground text-xs animate-in fade-in slide-in-from-bottom-1 duration-200">
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
          Copying is not allowed during practice sessions.
          <button onClick={() => setCopyWarning(false)} className="ml-auto underline opacity-80 hover:opacity-100">Dismiss</button>
        </div>
      )}
      {pasteWarning && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/90 text-destructive-foreground text-xs animate-in fade-in slide-in-from-bottom-1 duration-200">
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
          Pasting is not allowed during practice sessions. Type your own answer.
          <button onClick={() => setPasteWarning(false)} className="ml-auto underline opacity-80 hover:opacity-100">Dismiss</button>
        </div>
      )}
      {aiWarning && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 text-amber-400 border-t border-amber-500/30 text-xs animate-in fade-in slide-in-from-bottom-1 duration-200">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          This response appears to be AI-generated. Your own words make better practice!
          <button onClick={() => setAiWarning(false)} className="ml-auto underline opacity-80 hover:opacity-100">Dismiss</button>
        </div>
      )}
      {speechError && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/90 text-destructive-foreground text-xs animate-in fade-in slide-in-from-bottom-1 duration-200">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          {speechError}
          <button onClick={() => setSpeechError('')} className="ml-auto underline opacity-80 hover:opacity-100">Dismiss</button>
        </div>
      )}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border bg-card">
        <div className="flex gap-3 items-end max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onCopy={handleCopy}
              onCut={handleCopy}
              onContextMenu={handleContextMenu}
              onPaste={handlePaste}
              placeholder={placeholder}
              disabled={isLoading}
              rows={1}
              className="w-full resize-none bg-input border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary disabled:opacity-50"
            />
          </div>
          <Button
            type="button"
            size="icon"
            variant="outline"
            onClick={handleMicClick}
            disabled={isLoading}
            className="h-11 w-11 flex-shrink-0"
            title={isListening ? 'Stop listening' : 'Start voice input'}
          >
            <Mic className={`h-4 w-4 ${isListening ? 'animate-pulse text-primary' : ''}`} />
          </Button>
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isLoading}
            className="h-11 w-11 bg-primary hover:bg-primary/90 text-primary-foreground flex-shrink-0 transition-transform active:scale-95"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          {isListening ? 'Listening...' : 'Press Enter to send, Shift+Enter for new line'}
        </p>
      </form>
    </div>
  )
}
