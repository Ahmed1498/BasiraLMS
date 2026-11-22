'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { apiFetch } from '@/lib/api'
import { Calendar as CalendarIcon, Loader2 } from 'lucide-react'

type CalendarEvent = {
  id: string
  title: string
  course: string
  course_id: string | null
  date: string
  type: 'assignment' | 'quiz' | 'event'
  target: string | null
}

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<{ events: CalendarEvent[] }>('/calendar')
      .then((data) => setEvents(data.events))
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Could not load the calendar.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <CanvasSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center"><h1 className="text-xl font-bold text-slate-900">Course Calendar & Deadlines</h1></header>
        <main className="flex-1 p-8 max-w-5xl w-full mx-auto space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center gap-3 mb-6"><CalendarIcon className="w-6 h-6 text-indigo-600" /><h2 className="text-lg font-bold text-slate-900">Upcoming schedule</h2></div>
            {loading && <div className="flex justify-center py-12"><Loader2 className="w-7 h-7 animate-spin text-indigo-600" /></div>}
            {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            {!loading && !error && !events.length && <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No deadlines or events are scheduled.</p>}
            <div className="space-y-3">
              {events.map((event) => {
                const date = new Date(event.date)
                const content = (
                  <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between gap-4 hover:border-indigo-200 hover:bg-indigo-50/30 transition-colors">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-14 h-14 shrink-0 rounded-xl bg-indigo-50 text-indigo-700 flex flex-col items-center justify-center font-bold text-xs">
                        <span className="text-[10px] uppercase">{date.toLocaleString(undefined, { month: 'short' })}</span>
                        <span className="text-lg">{date.getDate()}</span>
                      </div>
                      <div className="min-w-0"><h3 className="font-semibold text-slate-900 truncate">{event.title}</h3><p className="text-xs text-slate-500">{event.course} • {date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</p></div>
                    </div>
                    <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold uppercase ${event.type === 'quiz' ? 'bg-purple-100 text-purple-700' : event.type === 'assignment' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-700'}`}>{event.type}</span>
                  </div>
                )
                return event.target ? <Link key={event.id} href={event.target}>{content}</Link> : <div key={event.id}>{content}</div>
              })}
            </div>
          </div>
        </main>
      </div>
      <AIAssistantWidget userRole="student" />
    </div>
  )
}
