'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { BookOpen, Loader2, Lock, Mail, User } from 'lucide-react'
import { setAccessToken } from '@/lib/api'

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '')

export default function SignupPage() {
  const router = useRouter()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'student' | 'teacher'>('student')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSignup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName.trim(),
          role,
        }),
      })
      const result = await response.json().catch(() => null) as
        | { detail?: string; message?: string; access_token?: string; dashboard?: string }
        | null
      if (!response.ok) {
        throw new Error(result?.detail || result?.message || 'Could not create your account.')
      }

      if (result?.access_token) {
        setAccessToken(result.access_token)
        router.push(result.dashboard || `/${role}/dashboard`)
        return
      }
      setSuccess('Account created. Check your email to confirm your address, then sign in.')
    } catch (signupError) {
      setError(signupError instanceof Error ? signupError.message : 'Could not create your account.')
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
        <h1 className="mt-7 text-center text-2xl font-semibold text-slate-900">Create your account</h1>
        <p className="mt-2 text-center text-sm text-slate-600">
          Choose whether you will use Basira as a student or a teacher.
        </p>

        <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          {error && <p role="alert" className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {success && <p role="status" className="mb-5 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{success}</p>}
          <form className="space-y-5" onSubmit={handleSignup}>
            <div>
              <label htmlFor="full-name" className="block text-sm font-medium text-slate-700">Full name</label>
              <div className="relative mt-1">
                <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input id="full-name" type="text" autoComplete="name" required minLength={2} maxLength={200} value={fullName} onChange={(event) => setFullName(event.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700">Email address</label>
              <div className="relative mt-1">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">Password</label>
              <div className="relative mt-1">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input id="password" type="password" autoComplete="new-password" required minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
              <p className="mt-1 text-xs text-slate-500">Use at least 10 characters.</p>
            </div>
            <fieldset>
              <legend className="block text-sm font-medium text-slate-700">I am joining as</legend>
              <div className="mt-2 grid grid-cols-2 gap-3">
                {(['student', 'teacher'] as const).map((option) => (
                  <label key={option} className={`cursor-pointer rounded-lg border px-3 py-3 text-center text-sm font-semibold capitalize transition ${role === option ? 'border-indigo-600 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600' : 'border-slate-300 text-slate-700 hover:border-slate-400'}`}>
                    <input
                      type="radio"
                      name="role"
                      value={option}
                      checked={role === option}
                      onChange={() => setRole(option)}
                      className="sr-only"
                    />
                    {option}
                  </label>
                ))}
              </div>
            </fieldset>
            <button type="submit" disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Create account
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">Sign in</Link>
          </p>
        </section>
      </div>
    </main>
  )
}
