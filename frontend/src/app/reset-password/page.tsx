'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { BookOpen, Loader2, Lock } from 'lucide-react'

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '')

export default function ResetPasswordPage() {
  const [token] = useState(() => (
    typeof window === 'undefined'
      ? ''
      : (() => {
          const url = new URL(window.location.href)
          return new URLSearchParams(url.hash.slice(1)).get('token')
            || url.searchParams.get('token')
            || ''
        })()
  ))
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (token) {
      window.history.replaceState(null, '', '/reset-password')
    }
  }, [token])

  const handleUpdatePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    if (password !== confirmPassword) {
      setError('The passwords do not match.')
      return
    }
    if (!token) {
      setError('This reset link is invalid or has expired. Request a new one.')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })
      const result = await response.json().catch(() => null) as { detail?: string } | null
      if (!response.ok) {
        throw new Error(result?.detail || 'Could not update your password.')
      }
      setSuccess(true)
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Could not update your password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <Link href="/" className="mx-auto flex w-fit items-center gap-2 text-indigo-600">
          <BookOpen className="h-9 w-9" />
          <span className="text-2xl font-bold tracking-tight text-slate-900">Basira</span>
        </Link>
        <h1 className="mt-7 text-center text-2xl font-semibold text-slate-900">Choose a new password</h1>
        <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          {error && <p role="alert" className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {success ? (
            <div role="status" className="space-y-4 text-sm text-emerald-700">
              <p>Your password has been updated.</p>
              <Link href="/login" className="inline-block font-semibold text-indigo-600 hover:text-indigo-700">
                Continue to sign in
              </Link>
            </div>
          ) : (
          <form onSubmit={handleUpdatePassword} className="space-y-5">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">New password</label>
              <div className="relative mt-1">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input id="password" type="password" autoComplete="new-password" minLength={10} required value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
            </div>
            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700">Confirm password</label>
              <input id="confirm-password" type="password" autoComplete="new-password" minLength={10} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            </div>
            <button type="submit" disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Update password
            </button>
          </form>
          )}
        </section>
      </div>
    </main>
  )
}
