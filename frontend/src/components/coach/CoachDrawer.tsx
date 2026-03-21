import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, History, Plus } from 'lucide-react'
import { coachApi } from '@/lib/api'
import { ChatMessage } from './ChatMessage'
import type { CoachMessage, ConversationSummary } from '@/types'

interface CoachDrawerProps {
  trigger?: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function CoachDrawer({ trigger, open, onOpenChange }: CoachDrawerProps) {
  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const loadConversations = async () => {
    try {
      const result = await coachApi.getConversations(10)
      setConversations(result.items)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  const loadConversation = async (id: string) => {
    try {
      const conversation = await coachApi.getConversation(id)
      setMessages(conversation.messages)
      setConversationId(id)
      setShowHistory(false)
    } catch (error) {
      console.error('Failed to load conversation:', error)
    }
  }

  const handleSend = async () => {
    const message = input.trim()
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
    setShowHistory(false)
  }

  const handleShowHistory = () => {
    loadConversations()
    setShowHistory(true)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-medium">Financial Coach</h3>
        <div className="flex gap-2">
          <button 
            className="p-2 hover:bg-muted rounded-md"
            onClick={handleShowHistory}
            title="View history"
          >
            <History className="h-4 w-4" />
          </button>
          <button 
            className="p-2 hover:bg-muted rounded-md"
            onClick={handleNewConversation}
            title="New conversation"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {showHistory ? (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {conversations.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No previous conversations
                </p>
              ) : (
                conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className="w-full text-left p-3 rounded-lg hover:bg-muted transition-colors"
                  >
                    <p className="font-medium text-sm truncate">
                      {conv.title || 'Untitled conversation'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(conv.last_message_at).toLocaleDateString()} · {conv.message_count} messages
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto" ref={scrollRef}>
              <div className="p-4">
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">
                      Ask me anything about your finances!
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))
                )}
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
            </div>

            <div className="pt-4 border-t p-4">
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
                  className="p-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
                  disabled={isLoading || !input.trim()}
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
