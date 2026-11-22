'use client'

import { FormEvent, Suspense, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import { apiFetch } from '@/lib/api'
import { ArrowLeft, Loader2 } from 'lucide-react'

type QuizQuestion = { id: string; question_text: string; options: string[] }
type Quiz = { id: string; title: string; description: string; time_limit_minutes: number; due_date: string | null; questions: QuizQuestion[] }

function QuizContent() {
  const params = useParams<{ id: string }>()
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ score: number; correct_count: number; question_count: number } | null>(null)

  useEffect(() => {
    apiFetch<Quiz>(`/quizzes/${params.id}`)
      .then(setQuiz)
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Could not load the quiz.'))
      .finally(() => setLoading(false))
  }, [params.id])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    const values = new FormData(event.currentTarget)
    const answers: Record<string, string> = {}
    quiz?.questions.forEach((question) => {
      const answer = values.get(question.id)
      if (typeof answer === 'string') answers[question.id] = answer
    })
    try {
      const response = await apiFetch<{ score: number; correct_count: number; question_count: number }>(`/quizzes/${params.id}/attempt`, {
        method: 'POST',
        body: JSON.stringify({ answers }),
      })
      setResult(response)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not submit the quiz.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
  if (!quiz) return <div className="min-h-screen p-8"><Link href="/student/calendar" className="text-indigo-600">Back to calendar</Link><p className="mt-4 text-red-700">{error}</p></div>

  return (
    <div className="flex min-h-screen bg-slate-50">
      <CanvasSidebar />
      <main className="mx-auto w-full max-w-4xl p-8">
        <Link href="/student/calendar" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" />Back to calendar</Link>
        <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-widest text-indigo-600">Quiz</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{quiz.title}</h1>
          <p className="mt-2 text-sm text-slate-600">{quiz.description || 'Answer every question to submit your attempt.'}</p>
          {quiz.due_date && <p className="mt-3 text-sm text-slate-500">Due {new Date(quiz.due_date).toLocaleString()} • {quiz.time_limit_minutes} minutes</p>}
          {error && <p role="alert" className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {result ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
              <p className="text-sm font-semibold text-emerald-700">Quiz submitted</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">{result.score}%</p>
              <p className="mt-1 text-sm text-slate-600">{result.correct_count} correct out of {result.question_count}</p>
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-6">
              {quiz.questions.map((question, index) => (
                <fieldset key={question.id} className="rounded-xl border border-slate-200 p-4">
                  <legend className="px-2 text-sm font-semibold text-slate-900">{index + 1}. {question.question_text}</legend>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {question.options.map((option) => (
                      <label key={option} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
                        <input required type="radio" name={question.id} value={option} className="accent-indigo-600" />
                        {option}
                      </label>
                    ))}
                  </div>
                </fieldset>
              ))}
              <button type="submit" disabled={submitting} className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{submitting ? 'Submitting...' : 'Submit quiz'}</button>
            </form>
          )}
        </section>
      </main>
    </div>
  )
}

export default function QuizPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>}>
      <QuizContent />
    </Suspense>
  )
}
