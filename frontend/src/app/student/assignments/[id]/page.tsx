'use client'

import { FormEvent, Suspense, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import { apiFetch } from '@/lib/api'
import { ArrowLeft, Loader2 } from 'lucide-react'

type Assignment = {
  id: string
  title: string
  description: string
  due_date: string | null
  total_points: number
  my_submission: null | { status: string; grade: number | null; feedback: string | null; file_url: string | null; submission_text: string | null }
}

function AssignmentContent() {
  const params = useParams<{ id: string }>()
  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [role, setRole] = useState<'student' | 'teacher' | 'admin'>('student')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      apiFetch<Assignment>(`/assignments/${params.id}`),
      apiFetch<{ role: 'student' | 'teacher' | 'admin' }>('/users/me'),
    ]).then(([detail, profile]) => {
      setAssignment(detail)
      setRole(profile.role)
    }).catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Could not load the assignment.'))
      .finally(() => setLoading(false))
  }, [params.id])

  const submitForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    const values = new FormData(event.currentTarget)
    try {
      await apiFetch(`/assignments/${params.id}/submit`, {
        method: 'POST',
        body: JSON.stringify({
          file_url: String(values.get('file_url') || '') || null,
          submission_text: String(values.get('submission_text') || '') || null,
        }),
      })
      setSuccess('Assignment submitted successfully.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not submit the assignment.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
  if (!assignment) return <div className="min-h-screen p-8"><Link href="/student/calendar" className="text-indigo-600">Back to calendar</Link><p className="mt-4 text-red-700">{error}</p></div>

  return (
    <div className="flex min-h-screen bg-slate-50">
      <CanvasSidebar />
      <main className="mx-auto w-full max-w-4xl p-8">
        <Link href="/student/calendar" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" />Back to calendar</Link>
        <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-widest text-indigo-600">Assignment</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{assignment.title}</h1>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{assignment.description || 'No additional instructions.'}</p>
          <div className="mt-5 flex gap-4 text-sm text-slate-500"><span>{assignment.total_points} points</span>{assignment.due_date && <span>Due {new Date(assignment.due_date).toLocaleString()}</span>}</div>
          {error && <p role="alert" className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {success && <p role="status" className="mt-5 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{success}</p>}
          {role === 'student' && (
            assignment.my_submission ? (
              <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-5">
                <h2 className="font-bold text-slate-900">Your submission</h2>
                <p className="mt-2 text-sm text-slate-600">Status: {assignment.my_submission.status}</p>
                {assignment.my_submission.grade !== null && <p className="mt-1 text-sm font-medium text-slate-900">Grade: {assignment.my_submission.grade}/{assignment.total_points}</p>}
                {assignment.my_submission.feedback && <p className="mt-2 text-sm text-slate-600">{assignment.my_submission.feedback}</p>}
              </div>
            ) : (
              <form onSubmit={submitForm} className="mt-6 space-y-4 border-t border-slate-100 pt-6">
                <div><label htmlFor="file_url" className="mb-1 block text-sm font-medium text-slate-700">Submission link</label><input id="file_url" name="file_url" type="url" placeholder="https://..." className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="submission_text" className="mb-1 block text-sm font-medium text-slate-700">Written answer</label><textarea id="submission_text" name="submission_text" rows={6} maxLength={50000} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{saving ? 'Submitting...' : 'Submit assignment'}</button>
              </form>
            )
          )}
        </section>
      </main>
    </div>
  )
}

export default function AssignmentPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>}>
      <AssignmentContent />
    </Suspense>
  )
}
