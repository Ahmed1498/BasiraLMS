'use client'

import { useRouter } from 'next/navigation'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { User, Mail, Shield, LogOut } from 'lucide-react'
import { apiFetch, setAccessToken } from '@/lib/api'

export default function AccountPage() {
  const router = useRouter()

  const handleSignOut = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
      setAccessToken(null)
      router.push('/login')
    } catch (signOutError) {
      window.alert(
        signOutError instanceof Error ? signOutError.message : 'Could not sign out.',
      )
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <CanvasSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900">User Account Settings</h1>
        </header>

        <main className="flex-1 p-8 max-w-4xl w-full mx-auto space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
            <div className="flex items-center gap-4 border-b border-slate-100 pb-6">
              <div className="w-16 h-16 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-2xl shadow-inner">
                <User className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Student Account</h2>
                <p className="text-xs text-slate-500 mt-1">Basira LMS Enrolled Learner</p>
              </div>
            </div>

            <div className="space-y-4 text-sm text-slate-700">
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <Mail className="w-5 h-5 text-indigo-600" />
                <div>
                  <p className="text-xs text-slate-500">Email Address</p>
                  <p className="font-medium text-slate-900">student@basiralms.com</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <Shield className="w-5 h-5 text-indigo-600" />
                <div>
                  <p className="text-xs text-slate-500">Access Role</p>
                  <p className="font-medium text-slate-900 uppercase">Student</p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={handleSignOut}
                className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-5 py-2.5 rounded-xl font-medium text-sm transition-colors shadow-sm"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </main>
      </div>

      <AIAssistantWidget userRole="student" />
    </div>
  )
}
