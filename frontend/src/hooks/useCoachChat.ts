import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { coachApi } from '@/lib/api'
import type { CoachMessage, ConversationSummary, QuickQuestion } from '@/types'

const API_PORT = import.meta.env.VITE_API_PORT || '8000'
const API_BASE = `${window.location.protocol}//${window.location.hostname}:${API_PORT}/api/v1`

interface StreamToken {
  type: 'token'
  content: string
}

interface StreamDone {
  type: 'done'
  conversation_id: string
  message_id: string
}

type StreamEvent = StreamToken | StreamDone

export interface UseCoachChatReturn {
  messages: CoachMessage[]
  conversations: ConversationSummary[]
  quickQuestions: QuickQuestion[]
  conversationId: string | null
  streamingContent: string
  isStreaming: boolean
  sendMessage: (message: string, conversationId?: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  loadConversation: (id: string) => Promise<void>
  startNewConversation: () => void
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token')
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    }
  }
  return {
    'Content-Type': 'application/json',
  }
}

export function useCoachChat(): UseCoachChatReturn {
  const queryClient = useQueryClient()
  const abortControllerRef = useRef<AbortController | null>(null)

  const [messages, setMessages] = useState<CoachMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => coachApi.getConversations(20).then(r => r.items),
  })

  const { data: quickQuestions = [] } = useQuery({
    queryKey: ['quick-questions'],
    queryFn: () => coachApi.getQuickQuestions(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => coachApi.deleteConversation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const loadConversation = useCallback(async (id: string) => {
    try {
      const conversation = await coachApi.getConversation(id)
      setMessages(conversation.messages)
      setConversationId(id)
    } catch (error) {
      console.error('Failed to load conversation:', error)
    }
  }, [])

  const startNewConversation = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setStreamingContent('')
  }, [])

  const sendMessage = useCallback(async (message: string, convId?: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const userMessage: CoachMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsStreaming(true)
    setStreamingContent('')

    const currentConvId = convId || conversationId

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch(`${API_BASE}/coach/chat/stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message,
          conversation_id: currentConvId,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No reader available')
      }

      let buffer = ''
      let accumulatedContent = ''
      let finalConversationId = currentConvId
      let finalMessageId = ''

      while (true) {
        if (controller.signal.aborted) {
          break
        }

        const { done, value } = await reader.read()
        if (done || controller.signal.aborted) break

        buffer += decoder.decode(value, { stream: true })

        const parts = buffer.split('\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue

          const data = line.slice(6)
          if (!data.trim()) continue

          try {
            const event: StreamEvent = JSON.parse(data)

            if (event.type === 'token') {
              accumulatedContent += event.content
              setStreamingContent(accumulatedContent)
            } else if (event.type === 'done') {
              finalConversationId = event.conversation_id
              finalMessageId = event.message_id
            }
          } catch {
            console.error('Failed to parse SSE event:', data)
          }
        }
      }

      const assistantMessage: CoachMessage = {
        id: finalMessageId || `assistant-${Date.now()}`,
        role: 'assistant',
        content: accumulatedContent,
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, assistantMessage])
      setConversationId(finalConversationId)
      setStreamingContent('')
      setIsStreaming(false)

      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        setIsStreaming(false)
        setStreamingContent('')
        return
      }
      console.error('Chat error:', error)
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          created_at: new Date().toISOString(),
        },
      ])
      setStreamingContent('')
      setIsStreaming(false)
    }
  }, [conversationId, queryClient])

  const deleteConversation = useCallback(async (id: string) => {
    await deleteMutation.mutateAsync(id)
    if (conversationId === id) {
      startNewConversation()
    }
  }, [conversationId, deleteMutation, startNewConversation])

  return {
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
  }
}
