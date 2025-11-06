'use client'

import { useState, useRef, useEffect } from 'react'
import api from '@/lib/api-client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
}

interface ChatProps {
  jobId: string
}

export default function Chat({ jobId }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await api.chat.send(jobId, {
        question: input.trim(),
        chat_history: messages.slice(-4), // Últimas 4 mensagens para contexto
      })

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.answer,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="card flex flex-col h-[600px] md:h-[700px]">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <span className="text-xl">💬</span>
          Chat sobre a Transcrição
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Faça perguntas sobre o conteúdo
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <div className="w-16 h-16 mx-auto mb-4 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
                <span className="text-3xl">💭</span>
              </div>
              <p className="text-slate-600 dark:text-slate-400 mb-2">
                Comece fazendo uma pergunta
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-500">
                Exemplo: "Quais foram os principais pontos discutidos?"
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-in-up`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                  }`}
                >
                  <p className="text-sm md:text-base whitespace-pre-wrap break-words">
                    {msg.content}
                  </p>
                  {msg.timestamp && (
                    <p
                      className={`text-xs mt-1 ${
                        msg.role === 'user'
                          ? 'text-blue-100'
                          : 'text-slate-500 dark:text-slate-400'
                      }`}
                    >
                      {msg.timestamp.toLocaleTimeString('pt-BR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="spinner w-4 h-4"></div>
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      Pensando...
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Digite sua pergunta... (Enter para enviar)"
            className="input resize-none h-12 md:h-14"
            disabled={loading}
            rows={1}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-primary px-4 md:px-6 flex-shrink-0 h-12 md:h-14"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
          Shift + Enter para nova linha
        </p>
      </div>
    </div>
  )
}
