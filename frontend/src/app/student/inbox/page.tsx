'use client'

import { FormEvent, useEffect, useState } from 'react'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { apiFetch } from '@/lib/api'
import { Inbox as InboxIcon, Loader2, Send } from 'lucide-react'

type Message = {
  id: string
  sender_id: string
  recipient_id: string
  sender_name: string
  recipient_name: string
  subject: string
  body: string
  sent_at: string | null
  is_read: boolean
  direction: 'sent' | 'received'
}
type Contact = { id: string; full_name: string; email: string; role: string }

export default function InboxPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selected, setSelected] = useState<Message | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [composing, setComposing] = useState(false)

  const load = async () => {
    try {
      const [messageData, contactData] = await Promise.all([
        apiFetch<{ messages: Message[] }>('/messages'),
        apiFetch<{ users: Contact[] }>('/users/contacts'),
      ])
      setMessages(messageData.messages)
      setContacts(contactData.users)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load inbox.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => load())
  }, [])

  const openMessage = async (message: Message) => {
    setSelected(message)
    if (message.direction === 'received' && !message.is_read) {
      try {
        await apiFetch(`/messages/${message.id}/read`, { method: 'POST' })
        setMessages((current) => current.map((item) => item.id === message.id ? { ...item, is_read: true } : item))
      } catch {
        // Reading the message is still useful if the read receipt update fails.
      }
    }
  }

  const sendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSending(true)
    setError(null)
    const values = new FormData(event.currentTarget)
    try {
      await apiFetch('/messages', {
        method: 'POST',
        body: JSON.stringify({
          recipient_id: values.get('recipient_id'),
          subject: values.get('subject'),
          body: values.get('body'),
        }),
      })
      setComposing(false)
      await load()
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Could not send the message.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <CanvasSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center justify-between"><h1 className="text-xl font-bold text-slate-900">Inbox & Messages</h1><button onClick={() => setComposing(true)} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"><Send className="h-4 w-4" />Compose</button></header>
        <main className="flex-1 p-8 max-w-7xl w-full mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
          {error && <p role="alert" className="md:col-span-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col min-h-96">
            <div className="p-4 border-b border-slate-200 font-bold text-slate-900 flex items-center gap-2"><InboxIcon className="w-5 h-5 text-indigo-600" /><span>Messages</span></div>
            {loading ? <div className="flex justify-center p-10"><Loader2 className="h-6 w-6 animate-spin text-indigo-600" /></div> : (
              <div className="divide-y divide-slate-100 overflow-y-auto">
                {messages.map((message) => (
                  <button key={message.id} onClick={() => void openMessage(message)} className={`w-full text-left p-4 transition-colors ${selected?.id === message.id ? 'bg-indigo-50/60 border-l-4 border-indigo-600' : 'hover:bg-slate-50'}`}>
                    <div className="flex justify-between items-center mb-1"><span className="font-semibold text-xs text-slate-900">{message.direction === 'received' ? message.sender_name : `To: ${message.recipient_name}`}</span>{message.direction === 'received' && !message.is_read && <span className="h-2 w-2 rounded-full bg-indigo-600" />}</div>
                    <h2 className="text-xs font-medium text-slate-800 truncate">{message.subject}</h2>
                    <p className="mt-1 text-[11px] text-slate-400">{message.sent_at ? new Date(message.sent_at).toLocaleString() : ''}</p>
                  </button>
                ))}
                {!messages.length && <p className="p-6 text-center text-sm text-slate-500">No messages yet.</p>}
              </div>
            )}
          </div>
          <div className="md:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            {selected ? (
              <div className="space-y-5"><div className="border-b border-slate-100 pb-4"><h2 className="text-xl font-bold text-slate-900">{selected.subject}</h2><p className="mt-1 text-xs text-slate-500">From {selected.sender_name} • To {selected.recipient_name}</p></div><pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-5 text-sm leading-6 text-slate-700">{selected.body}</pre></div>
            ) : <div className="flex h-full min-h-64 items-center justify-center text-slate-400">Select a message to read</div>}
          </div>
        </main>
      </div>
      {composing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={sendMessage} className="w-full max-w-lg space-y-4 rounded-2xl bg-white p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-900">New message</h2>
            <div><label htmlFor="recipient" className="mb-1 block text-sm font-medium text-slate-700">Recipient</label><select id="recipient" name="recipient_id" required className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">Choose a recipient</option>{contacts.map((contact) => <option key={contact.id} value={contact.id}>{contact.full_name} ({contact.role})</option>)}</select></div>
            <div><label htmlFor="subject" className="mb-1 block text-sm font-medium text-slate-700">Subject</label><input id="subject" name="subject" required maxLength={200} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
            <div><label htmlFor="body" className="mb-1 block text-sm font-medium text-slate-700">Message</label><textarea id="body" name="body" required rows={6} maxLength={10000} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
            <div className="flex justify-end gap-3"><button type="button" onClick={() => setComposing(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Cancel</button><button type="submit" disabled={sending} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">{sending && <Loader2 className="h-4 w-4 animate-spin" />}Send</button></div>
          </form>
        </div>
      )}
      <AIAssistantWidget userRole="student" />
    </div>
  )
}
