'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { apiFetch, setAccessToken } from '@/lib/api'
import { Activity, BookOpen, Loader2, LogOut, Plus, Shield, Users } from 'lucide-react'

type AdminUser = {
  id: string
  full_name: string
  email: string
  role: 'student' | 'teacher' | 'admin'
  is_active: boolean
}

type Overview = {
  user_count: number
  course_count: number
  pending_submissions: number
}

export default function AdminDashboard() {
  const router = useRouter()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [overview, setOverview] = useState<Overview | null>(null)
  const [adminId, setAdminId] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'student' | 'teacher'>('student')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const loadAdminData = useCallback(async () => {
    try {
      const [overviewData, userData, profile] = await Promise.all([
        apiFetch<Overview>('/admin/overview'),
        apiFetch<{ users: AdminUser[] }>('/admin/users'),
        apiFetch<{ id: string; role: 'student' | 'teacher' | 'admin' }>('/users/me'),
      ])
      if (profile.role !== 'admin') {
        router.replace(`/${profile.role}/dashboard`)
        return
      }
      setOverview(overviewData)
      setUsers(userData.users)
      setAdminId(profile.id)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load administration data.')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    void Promise.resolve().then(() => loadAdminData())
  }, [loadAdminData])

  const handleInvite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      await apiFetch('/admin/users/invite', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), full_name: fullName.trim(), role }),
      })
      setFullName('')
      setEmail('')
      setMessage('Invitation sent. The user will appear here after accepting it.')
      await loadAdminData()
    } catch (inviteError) {
      setError(inviteError instanceof Error ? inviteError.message : 'Could not invite this user.')
    } finally {
      setSaving(false)
    }
  }

  const handleRoleChange = async (user: AdminUser, nextRole: AdminUser['role']) => {
    setError(null)
    try {
      const updated = await apiFetch<Pick<AdminUser, 'role'>>(`/admin/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ role: nextRole }),
      })
      setUsers((current) => current.map((item) => item.id === user.id ? { ...item, role: updated.role } : item))
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Could not update this account role.')
    }
  }

  const handleStatusChange = async (user: AdminUser) => {
    setError(null)
    try {
      const updated = await apiFetch<Pick<AdminUser, 'is_active'>>(`/admin/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !user.is_active }),
      })
      setUsers((current) => current.map((item) => item.id === user.id ? { ...item, is_active: updated.is_active } : item))
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Could not update this account status.')
    }
  }

  const handleSignOut = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
      setAccessToken(null)
      router.replace('/login')
    } catch (signOutError) {
      setError(signOutError instanceof Error ? signOutError.message : 'Could not sign out.')
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
  }

  const cards = [
    { title: 'Total users', value: overview?.user_count ?? 0, icon: Users, tone: 'bg-indigo-50 text-indigo-600' },
    { title: 'Active courses', value: overview?.course_count ?? 0, icon: BookOpen, tone: 'bg-emerald-50 text-emerald-600' },
    { title: 'Pending submissions', value: overview?.pending_submissions ?? 0, icon: Activity, tone: 'bg-amber-50 text-amber-600' },
  ]

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3"><Shield className="h-8 w-8 text-indigo-600" /><span className="text-xl font-bold text-slate-900">Basira — Administration</span></Link>
          <button onClick={handleSignOut} aria-label="Sign out" className="text-slate-500 hover:text-slate-800"><LogOut className="h-5 w-5" /></button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-8 px-4 py-8 sm:px-6 lg:px-8">
        {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {message && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
        <section>
          <p className="text-xs font-bold uppercase tracking-widest text-indigo-600">Platform overview</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Administration dashboard</h1>
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            {cards.map(({ title, value, icon: Icon, tone }) => (
              <article key={title} className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${tone}`}><Icon className="h-6 w-6" /></span>
                <div><p className="text-xs text-slate-500">{title}</p><p className="text-2xl font-bold text-slate-900">{value}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">Invite a user</h2>
          <p className="mt-1 text-sm text-slate-500">The authentication provider sends the invitation email.</p>
          <form onSubmit={handleInvite} className="mt-4 grid gap-3 md:grid-cols-[1fr_1.5fr_160px_auto]">
            <input required minLength={2} maxLength={200} value={fullName} onChange={(event) => setFullName(event.target.value)} aria-label="Full name" placeholder="Full name" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} aria-label="Email" placeholder="Email address" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <select value={role} onChange={(event) => setRole(event.target.value as 'student' | 'teacher')} aria-label="Role" className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
            <button type="submit" disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Invite
            </button>
          </form>
        </section>

        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5">
            <h2 className="text-lg font-bold text-slate-900">User management</h2>
            <p className="mt-1 text-sm text-slate-500">Manage roles and account access for registered users.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <tr><th className="px-5 py-3">Name</th><th className="px-5 py-3">Email</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Access</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-5 py-4 font-medium text-slate-900">{user.full_name}</td>
                    <td className="px-5 py-4 text-slate-500">{user.email}</td>
                    <td className="px-5 py-4">
                      <select value={user.role} disabled={user.id === adminId} onChange={(event) => void handleRoleChange(user, event.target.value as AdminUser['role'])} aria-label={`Role for ${user.full_name}`} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs capitalize disabled:cursor-not-allowed disabled:opacity-60">
                        <option value="student">Student</option><option value="teacher">Teacher</option><option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${user.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{user.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td className="px-5 py-4">
                      <button disabled={user.id === adminId} onClick={() => void handleStatusChange(user)} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 disabled:cursor-not-allowed disabled:opacity-50">
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
                {!users.length && <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">No users have registered yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  )
}
