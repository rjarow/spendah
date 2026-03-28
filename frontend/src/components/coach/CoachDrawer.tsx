import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, History, Plus } from 'lucide-react'
import { useCoachChat } from '@/hooks/useCoachChat'
import { ChatMessage } from './ChatMessage'

interface CoachDrawerProps {
  trigger?: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function CoachDrawer(_props: CoachDrawerProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    conversations,
    conversationId,
    streamingContent,
    isStreaming,
    sendMessage,
    loadConversation,
    startNewConversation,
  } = useCoachChat()

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isStreaming) return
    setInput('')
    await sendMessage(message, conversationId || undefined)
  }

  const handleNewConversation = () => {
    startNewConversation()
    setShowHistory(false)
  }

  const handleShowHistory = () => {
    setShowHistory(true)
  }

  const handleLoadConversation = (id: string) => {
    loadConversation(id)
    setShowHistory(false)
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
                    onClick={() => handleLoadConversation(conv.id)}
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
                {messages.length === 0 && !streamingContent ? (
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
                {isStreaming && streamingContent && (
                  <ChatMessage 
                    message={{
                      id: 'streaming',
                      role: 'assistant',
                      content: streamingContent,
                      created_at: new Date().toISOString(),
                    }} 
                    isStreaming={true}
                  />
                )}
                {isStreaming && !streamingContent && (
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
                  disabled={isStreaming}
                  className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <button 
                  type="submit" 
                  className="p-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
                  disabled={isStreaming || !input.trim()}
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
