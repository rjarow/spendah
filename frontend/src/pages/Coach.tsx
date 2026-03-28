import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, Plus, Trash2 } from 'lucide-react'
import { useCoachChat } from '@/hooks/useCoachChat'
import { ChatMessage } from '@/components/coach/ChatMessage'

export default function CoachPage() {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    conversations,
    quickQuestions,
    conversationId,
    streamingContent,
    isStreaming,
    sendMessage,
    deleteConversation,
    loadConversation,
    startNewConversation,
  } = useCoachChat()

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  const handleSend = async (text?: string) => {
    const message = text || input.trim()
    if (!message || isStreaming) return
    setInput('')
    await sendMessage(message, conversationId || undefined)
  }

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await deleteConversation(id)
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      <div className="w-80 flex-shrink-0 border rounded-lg flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-medium">Conversations</h2>
          <button 
            className="p-2 hover:bg-muted rounded-md border"
            onClick={startNewConversation}
            title="New conversation"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="space-y-1 p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => loadConversation(conv.id)}
                className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                  conversationId === conv.id ? 'bg-primary/10' : 'hover:bg-muted'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">
                    {conv.title || 'Untitled conversation'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(conv.last_message_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 rounded transition-opacity"
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col border rounded-lg">
        <div className="flex-shrink-0 p-4 border-b">
          <h2 className="text-lg font-medium">Financial Coach</h2>
        </div>
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4" ref={scrollRef}>
            {messages.length === 0 && !streamingContent ? (
              <div className="h-full flex flex-col items-center justify-center text-center py-12">
                <h3 className="text-xl font-semibold mb-2">
                  How can I help you today?
                </h3>
                <p className="text-muted-foreground mb-6 max-w-md">
                  I can answer questions about your spending, help review subscriptions, 
                  explain trends, and provide insights about your finances.
                </p>
                <div className="grid grid-cols-2 gap-3 max-w-lg">
                  {quickQuestions.map((q) => (
                    <button
                      key={q.id}
                      className="h-auto py-3 px-4 text-left border rounded-lg hover:bg-muted transition-colors"
                      onClick={() => handleSend(q.text)}
                    >
                      {q.text}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
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
            )}
          </div>

          <div className="p-4 border-t">
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
                disabled={isStreaming || !input.trim()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 disabled:opacity-50"
              >
                <Send className="h-4 w-4 mr-2" />
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
