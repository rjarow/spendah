import { useState } from 'react'
import { MessageCircle, Send, X, Loader2 } from 'lucide-react'
import { coachApi } from '@/lib/api'
import { ChatMessage } from './ChatMessage'
import type { CoachMessage, QuickQuestion } from '@/types'

interface CoachWidgetProps {
  onExpand?: () => void
}

export function CoachWidget({ onExpand }: CoachWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [quickQuestions, setQuickQuestions] = useState<QuickQuestion[]>([])

  const loadQuickQuestions = async () => {
    try {
      const questions = await coachApi.getQuickQuestions()
      setQuickQuestions(questions)
    } catch (error) {
      console.error('Failed to load quick questions:', error)
    }
  }

  const handleOpen = () => {
    setIsOpen(true)
    if (quickQuestions.length === 0) {
      loadQuickQuestions()
    }
  }

  const handleSend = async (text?: string) => {
    const message = text || input.trim()
    if (!message || isLoading) return

    const userMessage: CoachMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await coachApi.chat(message, conversationId || undefined)
      
      if (!conversationId) {
        setConversationId(response.conversation_id)
      }

      const assistantMessage: CoachMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewConversation = () => {
    setMessages([])
    setConversationId(null)
  }

  if (!isOpen) {
    return (
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 transition-opacity"
        title="Open Financial Coach"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] shadow-xl flex flex-col bg-background border rounded-lg">
      <div className="flex-shrink-0 flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-medium">
          Financial Coach
        </h3>
        <div className="flex gap-1">
          {onExpand && (
            <button 
              className="p-2 hover:bg-muted rounded-md"
              onClick={onExpand}
              title="Open full page"
            >
              <span className="text-xs">↗️</span>
            </button>
          )}
          <button 
            className="p-2 hover:bg-muted rounded-md"
            onClick={() => setIsOpen(false)}
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="p-4 space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Ask me anything about your finances!
            </p>
            <div className="space-y-2">
              {quickQuestions.slice(0, 4).map((q) => (
                <button
                  key={q.id}
                  className="w-full text-left p-3 border rounded-lg hover:bg-muted transition-colors text-sm"
                  onClick={() => handleSend(q.text)}
                >
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-2">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex gap-3 p-4">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-2">
                  <p className="text-sm text-muted-foreground">Thinking...</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-4 border-t flex-shrink-0">
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your finances..."
            disabled={isLoading}
            className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            className="p-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
        {messages.length > 0 && (
          <button 
            className="w-full text-xs text-muted-foreground hover:text-foreground mt-2"
            onClick={handleNewConversation}
          >
            Start new conversation
          </button>
        )}
      </div>
    </div>
  )
}
