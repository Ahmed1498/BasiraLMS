'use client'

import { useState } from 'react'
import { X, Send, Sparkles, Bot, User, Loader2 } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface AIAssistantWidgetProps {
  userRole?: string
  currentPageContext?: {
    courseTitle?: string
    moduleTitle?: string
    lessonTitle?: string
    contentBody?: string
    videoUrl?: string
    courseId?: string
    lessonId?: string
  }
}

export default function AIAssistantWidget({ userRole = 'student', currentPageContext }: AIAssistantWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    {
      role: 'assistant',
      content: currentPageContext?.lessonTitle
        ? `Hi! Ask me a question about ${currentPageContext.lessonTitle}.`
        : 'Hi! Ask me a question about your courses or lessons.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  if (userRole !== 'student') {
    return null
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const data = await apiFetch<{ response: string }>('/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          prompt: userMessage,
          page_context: currentPageContext || {},
        }),
      })

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
        },
      ])
    } catch (requestError) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: requestError instanceof Error
            ? `I could not get a response from the course assistant: ${requestError.message}`
            : 'I could not get a response from the course assistant. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-full shadow-lg transition-all transform hover:scale-105 font-medium"
        >
          <Sparkles className="w-5 h-5 animate-pulse" />
          <span>AI Learning Assistant</span>
        </button>
      ) : (
        <div className="bg-white w-[400px] h-[550px] rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
          {/* Header */}
          <div className="bg-indigo-600 text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              <div>
                <h3 className="font-semibold text-sm">Basira AI Agent</h3>
                <p className="text-xs text-indigo-200 truncate max-w-[280px]">
                  {currentPageContext?.lessonTitle ? `Page: ${currentPageContext.lessonTitle}` : 'Ready to help'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-indigo-200 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-bl-none shadow-sm'
                  }`}
                >
                  {msg.content}
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-2.5 justify-start">
                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white text-slate-500 border border-slate-200 p-3 rounded-2xl rounded-bl-none shadow-sm flex items-center gap-2 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing page & generating response...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input form */}
          <form onSubmit={handleSendMessage} className="p-3 bg-white border-t border-slate-200 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about this lesson or ask to summarize video..."
              className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
