'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BookOpen, Loader2 } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { supabase } from '@/lib/supabaseClient'

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '')

export default function ConfirmAccountPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    let active = true

    async function completeConfirmation() {
      try {
        const url = new URL(window.location.href)
        const tokenHash = url.searchParams.get('token_hash')
        let dashboard: string | null = null

        if (tokenHash) {
          const response = await fetch(`${API_BASE_URL}/auth/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              token_hash: tokenHash,
              type: url.searchParams.get('type') || 'email',
            }),
          })
          const result = await response.json().catch(() => null) as
            | { detail?: string; access_token?: string; refresh_token?: string; dashboard?: string }
            | null
          if (!response.ok) {
            throw new Error(result?.detail || 'Could not confirm this account. The link may have expired.')
          }
          if (!result?.access_token || !result.refresh_token) {
            throw new Error('The authentication provider did not return a valid session.')
          }
          const { error: sessionError } = await supabase.auth.setSession({
            access_token: result.access_token,
            refresh_token: result.refresh_token,
          })
          if (sessionError) throw sessionError
          dashboard = result.dashboard || null
        }

        if (dashboard) {
          if (active) router.replace(dashboard)
          return
        }

        let { data, error: sessionError } = await supabase.auth.getSession()
        if (sessionError) throw sessionError
        if (!data.session) {
          const code = url.searchParams.get('code')
          if (code) {
            const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
            if (exchangeError) throw exchangeError
            const refreshedSession = await supabase.auth.getSession()
            data = refreshedSession.data
            sessionError = refreshedSession.error
            if (sessionError) throw sessionError
          }
        }
        if (!data.session) {
          const providerError = url.searchParams.get('error_description')
          throw new Error(providerError || 'The confirmation link is invalid or has expired.')
        }

        const profile = await apiFetch<{ role: 'student' | 'teacher' | 'admin' }>('/users/me')
        if (active) router.replace(`/${profile.role}/dashboard`)
      } catch (confirmationError) {
        if (active) {
          setError(
            confirmationError instanceof Error
              ? confirmationError.message
              : 'Could not confirm this account. Please request a new email.',
          )
        }
      }
    }

    void completeConfirmation()
    return () => {
      active = false
    }
  }, [router])

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <BookOpen className="mx-auto h-10 w-10 text-indigo-600" />
        <h1 className="mt-4 text-xl font-bold text-slate-900">Confirming your account</h1>
        {error ? (
          <>
            <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
            <a href="/login" className="mt-5 inline-block text-sm font-semibold text-indigo-600 hover:text-indigo-700">Back to sign in</a>
          </>
        ) : (
          <div className="mt-5 flex items-center justify-center gap-2 text-sm text-slate-600">
            <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
            <span>Please wait while we finish signing you in.</span>
          </div>
        )}
      </section>
    </main>
  )
}
