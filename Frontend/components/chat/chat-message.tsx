'use client'

import { cn } from '@/lib/utils'
import { Bot, User } from 'lucide-react'
import type { Message } from '@/lib/types'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className={cn(
      "flex gap-4 p-4",
      isUser ? "bg-transparent" : "bg-muted/30"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
        isUser ? "bg-primary/10" : "bg-primary"
      )}>
        {isUser ? (
          <User className="h-4 w-4 text-primary" />
        ) : (
          <Bot className="h-4 w-4 text-primary-foreground" />
        )}
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <p className="text-sm font-medium text-foreground">
          {isUser ? 'You' : 'PromptLab AI'}
        </p>
        <div className="text-sm text-foreground/90 whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
    </div>
  )
}
