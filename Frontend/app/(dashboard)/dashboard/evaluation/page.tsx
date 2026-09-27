'use client'

import { useState, useEffect, useRef } from 'react'
import { 
  PenLine, BarChart2, Lightbulb,
  Plus, Trash2, X
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useAuth } from '@/contexts/auth-context'

const LAIBA_API = process.env.NEXT_PUBLIC_LAIBA_API || 'https://laiba52.pythonanywhere.com'

// ── Markdown renderer ──────────────────────────────────────
function preprocessText(text: string): string {
  text = text.replace(/(\.)(\s+)(\d+)\.\s+/g, '.\n\n$3. ')
  text = text.replace(/([^\n])\s+-\s+/g, '$1\n- ')
  return text
}

function renderMarkdown(text: string): string {
  let html = preprocessText(text)
  html = html.replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre style="background:var(--background);border:1px solid var(--border);border-radius:8px;padding:12px;overflow-x:auto;margin:10px 0"><code style="font-family:monospace;font-size:13px;color:var(--chart-2)">$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code style="background:var(--background);border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;color:var(--chart-2)">$1</code>')
  html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:16px;font-weight:700;color:var(--foreground);margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--border)">$1</h2>')
  html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:14px;font-weight:700;color:var(--foreground);margin:14px 0 6px">$1</h3>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--foreground);font-weight:700">$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em style="color:var(--muted-foreground)">$1</em>')
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="md-ol" style="margin:5px 0;color:var(--foreground)">$2</li>')
  html = html.replace(/^[-*•] (.+)$/gm, '<li class="md-ul" style="margin:5px 0;color:var(--foreground)">$1</li>')
  html = html.replace(/(<li class="md-ol"[^>]*>.*?<\/li>\n?)+/g, (m) => `<ol style="margin:10px 0;padding-left:22px;list-style-type:decimal">${m}</ol>`)
  html = html.replace(/(<li class="md-ul"[^>]*>.*?<\/li>\n?)+/g, (m) => `<ul style="margin:10px 0;padding-left:22px;list-style-type:disc">${m}</ul>`)
  html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--border);margin:16px 0"/>')
  html = html.replace(/\n/g, '<br/>')
  return html
}

// ── Types ──────────────────────────────────────────────────
interface ChatMessage {
  role:           'user' | 'assistant'
  content:        string
  eval_data?:     EvalData | null
  is_related?:    boolean
  relation_note?: string
}

interface EvalData {
  scores:          { total: number; clarity: number; context: number; specificity: number; constraints: number; format: number }
  grade:           string
  feedback:        string[]
  improved_prompt: string
  security?:       { threat_level: string; threat_type: string }
  difficulty?:     { difficulty: string; next_level_tips: string[] }
  prompt_type?:    string
}

interface Session {
  session_id: number
  title:      string
  updated_at: string
}

interface Analytics {
  total_attempts:       number
  average_score:        number
  best_score:           number
  worst_score:          number
  most_common_weakness: string
  improvement_rate:     string
}

interface Progress {
  history:       { attempt_number: number; score: number; grade: string }[]
  first_score:   number
  latest_score:  number
  improvement:   string
}

// ── Grade helpers ──────────────────────────────────────────
const gradeColor = (g: string) => {
  if (g === 'A+' || g === 'A') return '#22c55e'
  if (g === 'B')  return '#3b82f6'
  if (g === 'C')  return '#10b981'
  if (g === 'D')  return '#f97316'
  return '#ef4444'
}

const threatBadge = (level: string) => {
  if (level === 'SAFE')    return { bg: 'rgba(34,197,94,0.15)',  color: '#22c55e', text: '🛡 SAFE'      }
  if (level === 'WARNING') return { bg: 'rgba(16,185,129,0.15)', color: '#10b981', text: '⚠ WARNING'   }
  return                          { bg: 'rgba(239,68,68,0.15)',  color: '#ef4444', text: '🚨 DANGEROUS' }
}

// ── Safe fetch helper — never throws, always returns a value ──
async function safeFetch(url: string, options: RequestInit): Promise<any> {
  try {
    const res = await fetch(url, { ...options, signal: AbortSignal.timeout(30000) })
    if (!res.ok) return null
    return await res.json()
  } catch (e) {
    console.error('safeFetch failed:', url, e)
    return null
  }
}

// ── Main Component ─────────────────────────────────────────
export default function EvaluationPage() {
  const { user } = useAuth()
  const USER_ID = user?.id || 1

  // Chat state
  const [messages,     setMessages]     = useState<ChatMessage[]>([])
  const [input,        setInput]        = useState('')
  const [loading,      setLoading]      = useState(false)
  const [evalLoading,  setEvalLoading]  = useState(false)
  const [expandedEval, setExpandedEval] = useState<number | null>(null)

  // Sessions
  const [sessions,      setSessions]      = useState<Session[]>([])
  const [activeSession, setActiveSession] = useState<number | null>(null)
  const [sessionTitle,  setSessionTitle]  = useState('New Chat')

  // Panels
  const [activePanel, setActivePanel] = useState<string | null>(null)
  const [analytics,   setAnalytics]   = useState<Analytics | null>(null)
  const [progress,    setProgress]    = useState<Progress | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])
  useEffect(() => { fetchSessions() }, [])

  // ── Session helpers ────────────────────────────────────
  const fetchSessions = async () => {
    const d = await safeFetch(`${LAIBA_API}/api/sessions?user_id=${USER_ID}`, {})
    if (Array.isArray(d)) setSessions(d)
  }

  const fetchAnalytics = async () => {
    const [ad, pd] = await Promise.all([
      safeFetch(`${LAIBA_API}/api/analytics/${USER_ID}`, {}),
      safeFetch(`${LAIBA_API}/api/progress/${USER_ID}`, {})
    ])
    if (ad && !ad.message) setAnalytics(ad)
    if (pd && !pd.message) setProgress(pd)
  }

  const newChat = async () => {
    const d = await safeFetch(`${LAIBA_API}/api/sessions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, title: 'New Chat' })
    })
    if (d?.session_id) {
      setActiveSession(d.session_id)
      setSessionTitle('New Chat')
      setMessages([])
      setExpandedEval(null)
      setSessions(prev => [{ session_id: d.session_id, title: 'New Chat', updated_at: new Date().toISOString() }, ...prev])
    }
  }

  const loadSession = async (sid: number, title: string) => {
    setActiveSession(sid)
    setSessionTitle(title)
    setExpandedEval(null)
    const d = await safeFetch(`${LAIBA_API}/api/sessions/${sid}/messages`, {})
    if (Array.isArray(d)) setMessages(d.filter((m: any) => m.role === 'user' || m.role === 'assistant'))
  }

  const deleteSession = async (e: React.MouseEvent, sid: number) => {
    e.stopPropagation()
    await safeFetch(`${LAIBA_API}/api/sessions/${sid}`, { method: 'DELETE' })
    setSessions(prev => prev.filter(s => s.session_id !== sid))
    if (activeSession === sid) { setActiveSession(null); setMessages([]); setSessionTitle('New Chat') }
  }

  // ── Send message — FIXED: sequential, robust, never "Sorry" ──
  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')

    // Ensure we have a session
    let sid = activeSession
    if (!sid) {
      const d = await safeFetch(`${LAIBA_API}/api/sessions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID, title: 'New Chat' })
      })
      if (d?.session_id) {
        sid = d.session_id
        setActiveSession(sid)
        setSessions(prev => [{ session_id: sid!, title: 'New Chat', updated_at: new Date().toISOString() }, ...prev])
      }
    }

    // Optimistically add user message
    const userMsg: ChatMessage = { role: 'user', content: text, eval_data: null }
    const newMsgs = [...messages, userMsg]
    setMessages(newMsgs)
    setLoading(true)
    setEvalLoading(false)

    // Save user message (fire and forget)
    if (sid) {
      safeFetch(`${LAIBA_API}/api/sessions/${sid}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text })
      })
    }

    // ── STEP 1: Get the chat answer FIRST (primary) ──
    const chatData = await safeFetch(`${LAIBA_API}/api/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: newMsgs.map(m => ({ role: m.role, content: m.content }))
      })
    })

    // Extract answer — chat is the primary source
    let finalAnswer = chatData?.answer || ''

    // ── STEP 2: Evaluate — 3 second delay to avoid Groq rate limit ──
    await new Promise(resolve => setTimeout(resolve, 3000))
    setEvalLoading(true)
    const evalData = await safeFetch(`${LAIBA_API}/api/evaluate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, prompt_text: text })
    })
    setEvalLoading(false)

    // If chat gave no answer, use evaluate's answer as fallback
    if (!finalAnswer && evalData?.answer) {
      finalAnswer = evalData.answer
    }

    // Last resort: explicit, helpful error
    if (!finalAnswer) {
      finalAnswer = `**Backend not reachable** ⚠️

Make sure:
1. Your deployed backend is reachable at https://laiba52.pythonanywhere.com
2. The frontend is configured with NEXT_PUBLIC_LAIBA_API and the request origin is allowed by the backend
3. The remote backend can be slow on cold starts; wait a few seconds and retry.

Open https://laiba52.pythonanywhere.com/api/health in browser to verify.`
    }

    // Attach eval data to the user message
    if (evalData?.success) {
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 && m.role === 'user'
          ? { ...m, eval_data: evalData as EvalData }
          : m
      ))
    }

    // Add assistant message
    const assistantMsg: ChatMessage = {
      role:          'assistant',
      content:       finalAnswer,
      is_related:    chatData?.is_related   || false,
      relation_note: chatData?.relation_note || ''
    }
    setMessages(prev => [...prev, assistantMsg])

    // Save assistant message + update session title
    if (sid) {
      safeFetch(`${LAIBA_API}/api/sessions/${sid}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'assistant', content: finalAnswer })
      })
      if (messages.length === 0) {
        const newTitle = text.length > 35 ? text.slice(0, 35) + '...' : text
        setSessionTitle(newTitle)
        setSessions(prev => prev.map(s => s.session_id === sid ? { ...s, title: newTitle } : s))
      }
      fetchSessions()
    }

    setLoading(false)
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const togglePanel = (panel: string) => {
    if (panel === 'progress' && activePanel !== 'progress') fetchAnalytics()
    setActivePanel(prev => prev === panel ? null : panel)
  }

  // ── Render ─────────────────────────────────────────────
  return (
    <div className="font-sans" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--background)', color: 'var(--foreground)' }}>

      {/* ── TOP BAR ── */}
      <div style={{ height: '56px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', flexShrink: 0, position: 'relative', zIndex: 20 }}>
        <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--foreground)' }}>
          {sessionTitle}
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { key: 'notes',    icon: <PenLine size={15} />,   title: 'Score History'  },
            { key: 'progress', icon: <BarChart2 size={15} />, title: 'Your Progress'  },
            { key: 'tips',     icon: <Lightbulb size={15} />, title: 'Prompt Tips'    },
          ].map(btn => (
            <button
              key={btn.key}
              title={btn.title}
              onClick={() => togglePanel(btn.key)}
              style={{
                width: '34px', height: '34px', borderRadius: '8px',
                border: activePanel === btn.key ? '1px solid var(--primary)' : '1px solid var(--border)',
                background: activePanel === btn.key ? 'rgba(5,150,105,0.15)' : 'var(--card)',
                color: activePanel === btn.key ? 'var(--primary)' : 'var(--muted-foreground)',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s'
              }}
            >
              {btn.icon}
            </button>
          ))}
        </div>

        {/* ── PANEL: Progress ── */}
        {activePanel === 'progress' && (
          <div style={{ position: 'absolute', top: '56px', right: '12px', width: '320px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 100, overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--foreground)' }}>📊 Your Progress</span>
              <button onClick={() => setActivePanel(null)} style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer' }}><X size={14} /></button>
            </div>
            <div style={{ padding: '14px 18px 18px' }}>
              {!analytics ? (
                <p style={{ fontSize: '13px', color: 'var(--muted-foreground)', textAlign: 'center', padding: '20px 0' }}>No data yet — start chatting!</p>
              ) : (
                <>
                  {[
                    { label: 'Total Prompts',    value: `${analytics.total_attempts}`   },
                    { label: 'Average Score',    value: `${analytics.average_score}/10` },
                    { label: 'Best Score',       value: `${analytics.best_score}/10`    },
                    { label: 'Improvement Rate', value: analytics.improvement_rate      },
                  ].map((s, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
                      <span style={{ fontSize: '13px', color: 'var(--muted-foreground)' }}>{s.label}</span>
                      <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--primary)' }}>{s.value}</span>
                    </div>
                  ))}
                  {analytics.most_common_weakness && (
                    <div style={{ marginTop: '12px', background: 'rgba(5,150,105,0.1)', border: '1px solid rgba(5,150,105,0.25)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'var(--primary)' }}>
                      💡 Focus on: {analytics.most_common_weakness}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* ── PANEL: Score Chart ── */}
        {activePanel === 'notes' && (
          <div style={{ position: 'absolute', top: '56px', right: '12px', width: '340px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 100, overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--foreground)' }}>📈 Score History</span>
              <button onClick={() => setActivePanel(null)} style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer' }}><X size={14} /></button>
            </div>
            <div style={{ padding: '14px 18px 18px' }}>
              {!progress ? (
                <p style={{ fontSize: '13px', color: 'var(--muted-foreground)', textAlign: 'center', padding: '20px 0' }}>No score history yet</p>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
                    {[
                      { label: 'First',  value: progress.first_score  },
                      { label: 'Latest', value: progress.latest_score },
                      { label: 'Change', value: progress.improvement  },
                    ].map((s, i) => (
                      <div key={i} style={{ flex: 1, textAlign: 'center', background: 'var(--background)', borderRadius: '8px', padding: '10px 6px' }}>
                        <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary)' }}>{s.value}</div>
                        <div style={{ fontSize: '10px', color: 'var(--muted-foreground)', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{s.label}</div>
                      </div>
                    ))}
                  </div>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={progress.history}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="attempt_number" tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} stroke="var(--border)" />
                      <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} stroke="var(--border)" />
                      <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid var(--primary)', borderRadius: '8px', fontSize: '12px', color: 'var(--foreground)' }} formatter={(v: any) => [`${v}/10`, 'Score']} />
                      <Line type="monotone" dataKey="score" stroke="var(--primary)" strokeWidth={2} dot={{ fill: 'var(--primary)', r: 3, strokeWidth: 0 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── PANEL: Tips ── */}
        {activePanel === 'tips' && (
          <div style={{ position: 'absolute', top: '56px', right: '12px', width: '300px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 100, overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--foreground)' }}>💡 Prompt Tips</span>
              <button onClick={() => setActivePanel(null)} style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer' }}><X size={14} /></button>
            </div>
            <div style={{ padding: '12px 14px 16px' }}>
              {[
                { tip: 'Add your audience', ex: '...for a high school student' },
                { tip: 'Specify a format',  ex: '...in bullet points'          },
                { tip: 'Set constraints',   ex: '...in under 200 words'        },
                { tip: 'Give context',      ex: 'I am learning Python...'      },
                { tip: 'Assign a role',     ex: 'Act as a math teacher...'     },
              ].map((t, i) => (
                <div key={i} style={{ padding: '9px 12px', background: 'var(--background)', borderRadius: '8px', marginBottom: '8px', borderLeft: '3px solid var(--primary)' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--foreground)', marginBottom: '2px' }}>{t.tip}</div>
                  <div style={{ fontSize: '11px', color: 'var(--muted-foreground)', fontStyle: 'italic' }}>{t.ex}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── BODY ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── SESSION SIDEBAR ── */}
        <div style={{ width: '220px', background: 'var(--background)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
          <button
            onClick={newChat}
            style={{ margin: '12px 10px 8px', background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.25)', color: 'var(--primary)', padding: '9px 14px', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s' }}
          >
            <Plus size={14} /> New Chat
          </button>

          <div style={{ padding: '4px 14px 4px', fontSize: '10px', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--muted-foreground)' }}>
            Recent
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '2px 8px' }}>
            {sessions.length === 0 ? (
              <div style={{ padding: '16px 8px', fontSize: '12px', color: 'var(--muted-foreground)', textAlign: 'center' }}>No chats yet</div>
            ) : (
              sessions.map(s => (
                <div
                  key={s.session_id}
                  onClick={() => loadSession(s.session_id, s.title)}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderRadius: '8px', cursor: 'pointer', marginBottom: '2px', background: activeSession === s.session_id ? 'rgba(5,150,105,0.12)' : 'transparent', transition: 'background 0.2s' }}
                  onMouseEnter={e => { if (activeSession !== s.session_id) (e.currentTarget as HTMLDivElement).style.background = 'var(--card)' }}
                  onMouseLeave={e => { if (activeSession !== s.session_id) (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
                >
                  <span style={{ fontSize: '12px', color: activeSession === s.session_id ? 'var(--primary)' : 'var(--muted-foreground)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                    {s.title}
                  </span>
                  <button
                    onClick={(e) => deleteSession(e, s.session_id)}
                    className="delete-btn"
                    style={{ background: 'none', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer', padding: '2px', borderRadius: '4px', flexShrink: 0, opacity: 0 }}
                    onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.color = 'var(--destructive)'}
                    onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.color = 'var(--muted-foreground)'}
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              ))
            )}
          </div>

          <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)', fontSize: '10px', color: 'var(--muted-foreground)' }}>
            PromptIQ · FYP 2025
          </div>
        </div>

        {/* ── CHAT AREA ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          <div style={{ flex: 1, overflowY: 'auto', padding: '24px 40px', display: 'flex', flexDirection: 'column', gap: '0' }}>
            {messages.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '40px', marginBottom: '16px' }}>✦</div>
                <div style={{ fontSize: '40px', fontWeight: 700, color: 'var(--foreground)', marginBottom: '20px', fontFamily: 'sans-serif' }}>
                  How can I help you today?
                </div>
                <div style={{ fontSize: '14px', color: 'var(--muted-foreground)', maxWidth: '360px', lineHeight: 1.7 }}>
                  Ask me anything. Every message you send will be automatically evaluated for prompt quality — helping you improve as you chat.
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} style={{ marginBottom: '20px', animation: 'fadeIn 0.3s ease' }}>

                  {/* ── User message ── */}
                  {msg.role === 'user' && (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '6px' }}>
                        <div style={{ background: 'var(--secondary)', color: 'var(--secondary-foreground)', padding: '10px 16px', borderRadius: '16px', borderBottomRightRadius: '4px', fontSize: '14px', lineHeight: 1.7, maxWidth: '70%', whiteSpace: 'pre-wrap' }}>
                          {msg.content}
                        </div>
                      </div>

                      {/* Eval strip */}
                      {msg.eval_data ? (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '6px' }}>
                          <div
                            onClick={() => setExpandedEval(expandedEval === i ? null : i)}
                            style={{ background: 'rgba(5,150,105,0.08)', border: '1px solid rgba(5,150,105,0.2)', borderRadius: '12px', padding: '10px 14px', maxWidth: '80%', cursor: 'pointer', transition: 'all 0.2s' }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontFamily: 'serif', fontSize: '18px', fontWeight: 800, color: 'var(--primary)' }}>
                                {msg.eval_data.scores.total}/10
                              </span>
                              <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '20px', background: `${gradeColor(msg.eval_data.grade)}20`, color: gradeColor(msg.eval_data.grade), border: `1px solid ${gradeColor(msg.eval_data.grade)}40` }}>
                                {msg.eval_data.grade}
                              </span>
                              {msg.eval_data.security && (() => {
                                const tb = threatBadge(msg.eval_data.security!.threat_level)
                                return <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '20px', background: tb.bg, color: tb.color }}>{tb.text}</span>
                              })()}
                              {msg.eval_data.difficulty?.difficulty && (
                                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--muted-foreground)' }}>
                                  📊 {msg.eval_data.difficulty.difficulty}
                                </span>
                              )}
                              {msg.eval_data.prompt_type && (
                                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '20px', background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--muted-foreground)' }}>
                                  {msg.eval_data.prompt_type}
                                </span>
                              )}
                            </div>

                            <div style={{ marginTop: '8px' }}>
                              {[
                                { label: 'Clarity',     v: msg.eval_data.scores.clarity     },
                                { label: 'Context',     v: msg.eval_data.scores.context     },
                                { label: 'Specificity', v: msg.eval_data.scores.specificity },
                                { label: 'Constraints', v: msg.eval_data.scores.constraints },
                                { label: 'Format',      v: msg.eval_data.scores.format      },
                              ].map(b => (
                                <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                  <div style={{ width: '70px', fontSize: '10px', color: 'var(--muted-foreground)', flexShrink: 0 }}>{b.label}</div>
                                  <div style={{ flex: 1, background: 'var(--secondary)', borderRadius: '20px', height: '5px', overflow: 'hidden' }}>
                                    <div style={{ width: `${(b.v / 2) * 100}%`, height: '100%', background: 'var(--primary)', borderRadius: '20px' }} />
                                  </div>
                                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--primary)', width: '24px', textAlign: 'right' }}>{b.v}/2</div>
                                </div>
                              ))}
                            </div>

                            <div style={{ fontSize: '10px', color: 'var(--muted-foreground)', marginTop: '6px', textAlign: 'center' }}>
                              {expandedEval === i ? '▲ collapse' : '▼ click for details'}
                            </div>

                            {expandedEval === i && (
                              <div style={{ marginTop: '12px', borderTop: '1px solid rgba(5,150,105,0.2)', paddingTop: '12px' }}>
                                {msg.eval_data.feedback?.length > 0 && (
                                  <div style={{ marginBottom: '10px' }}>
                                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '6px' }}>Feedback</div>
                                    {msg.eval_data.feedback.map((f, fi) => (
                                      <div key={fi} style={{ display: 'flex', gap: '8px', fontSize: '12px', color: 'var(--muted-foreground)', padding: '7px 10px', background: 'var(--background)', borderLeft: '2px solid var(--primary)', borderRadius: '4px', marginBottom: '5px', lineHeight: 1.5 }}>
                                        <span style={{ color: 'var(--primary)', fontWeight: 700 }}>→</span>{f}
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {msg.eval_data.improved_prompt && (
                                  <div>
                                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '6px' }}>Improved Version</div>
                                    <div style={{ background: 'rgba(5,150,105,0.08)', border: '1px solid rgba(5,150,105,0.2)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'var(--foreground)', lineHeight: 1.7 }}>
                                      {msg.eval_data.improved_prompt}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ) : evalLoading && i === messages.length - 1 ? (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '6px' }}>
                          <div style={{ background: 'rgba(5,150,105,0.05)', border: '1px dashed rgba(5,150,105,0.2)', borderRadius: '10px', padding: '8px 14px', fontSize: '12px', color: 'var(--primary)' }}>
                            ◈ Evaluating prompt...
                          </div>
                        </div>
                      ) : null}
                    </>
                  )}

                  {/* Relation tag */}
                  {msg.role === 'assistant' && msg.is_related && msg.relation_note && (
                    <div style={{ marginLeft: '38px', marginBottom: '5px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 600, padding: '2px 10px', background: 'rgba(5,150,105,0.1)', borderRadius: '20px', border: '1px solid rgba(5,150,105,0.2)' }}>
                        🔗 Related to: {msg.relation_note}
                      </span>
                    </div>
                  )}

                  {/* ── Assistant message ── */}
                  {msg.role === 'assistant' && (
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg,var(--primary),var(--primary))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0, marginTop: '2px' }}>✦</div>
                      <div
                        className="markdown-body"
                        style={{ background: 'var(--card)', border: '1px solid var(--border)', borderTopLeftRadius: '4px', borderTopRightRadius: '16px', borderBottomRightRadius: '16px', borderBottomLeftRadius: '16px', padding: '12px 16px', fontSize: '14px', lineHeight: 1.8, color: 'var(--foreground)', maxWidth: '75%' }}
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                      />
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Typing indicator */}
            {loading && (
              <div style={{ display: 'flex', gap: '10px', animation: 'fadeIn 0.3s ease' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg,var(--primary),var(--primary))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0 }}>✦</div>
                <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderTopLeftRadius: '4px', borderTopRightRadius: '16px', borderBottomRightRadius: '16px', borderBottomLeftRadius: '16px', padding: '14px 18px', display: 'flex', gap: '5px', alignItems: 'center' }}>
                  {[0, 150, 300].map(d => (
                    <span key={d} style={{ width: '6px', height: '6px', background: 'var(--muted-foreground)', borderRadius: '50%', display: 'inline-block', animation: `bounce 1.2s ${d}ms infinite` }} />
                  ))}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ── INPUT ── */}
          <div style={{ padding: '14px 40px 18px', borderTop: '1px solid var(--border)', background: 'var(--background)', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', background: 'var(--card)', border: '1.5px solid var(--border)', borderRadius: '14px', padding: '10px 10px 10px 18px', transition: 'border-color 0.2s' }}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask anything — your prompt will be evaluated automatically..."
                rows={1}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontSize: '14px', color: 'var(--foreground)', resize: 'none', minHeight: '24px', maxHeight: '120px', lineHeight: 1.6, fontFamily: 'inherit' }}
                onFocus={e => { (e.currentTarget.closest('div') as HTMLDivElement).style.borderColor = '#a16207' }}
                onBlur={e  => { (e.currentTarget.closest('div') as HTMLDivElement).style.borderColor = 'var(--border)' }}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                style={{ width: '36px', height: '36px', borderRadius: '10px', background: loading || !input.trim() ? 'var(--secondary)' : '#ca8a04', border: 'none', color: loading || !input.trim() ? 'var(--muted-foreground)' : '#09090b', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', transition: 'all 0.2s', flexShrink: 0 }}
              >
                →
              </button>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted-foreground)', textAlign: 'center', marginTop: '8px' }}>
              Enter to send · Shift+Enter for new line · Prompt quality evaluated automatically
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity:0; transform:translateY(-4px) } to { opacity:1; transform:translateY(0) } }
        @keyframes bounce { 0%,60%,100% { transform:translateY(0) } 30% { transform:translateY(-5px) } }
        ::-webkit-scrollbar { width: 4px }
        ::-webkit-scrollbar-track { background: transparent }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px }
        .delete-btn { opacity: 0 !important }
        div:hover > .delete-btn { opacity: 1 !important }
      `}</style>
    </div>
  )
}