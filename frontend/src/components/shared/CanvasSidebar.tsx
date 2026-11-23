'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { User, LayoutDashboard, BookOpen, Calendar, Inbox, GraduationCap } from 'lucide-react'
import { apiFetch } from '@/lib/api'

export default function CanvasSidebar() {
  const pathname = usePathname()
  const [role, setRole] = useState<'student' | 'teacher' | 'admin'>('student')

  useEffect(() => {
    apiFetch<{ role: 'student' | 'teacher' | 'admin' }>('/users/me')
      .then((profile) => setRole(profile.role))
      .catch(() => undefined)
  }, [])

  const base = role === 'student' ? '/student' : role === 'teacher' ? '/teacher' : '/admin'
  const navItems = [
    ...(role === 'student' ? [{ name: 'Account', href: '/student/account', icon: User }] : []),
    { name: 'Dashboard', href: `${base}/dashboard`, icon: LayoutDashboard },
    ...(role === 'student' ? [{ name: 'Courses', href: '/student/courses', icon: BookOpen }] : []),
    { name: 'Calendar', href: '/student/calendar', icon: Calendar },
    { name: 'Inbox', href: '/student/inbox', icon: Inbox },
  ]

  return (
    <aside className="w-24 bg-slate-900 text-white flex flex-col items-center py-6 shrink-0 select-none shadow-xl sticky top-0 h-screen z-50">
      {/* Canvas Logo */}
      <div className="mb-8 flex flex-col items-center">
        <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center shadow-lg">
          <GraduationCap className="w-7 h-7 text-white" />
        </div>
        <span className="text-[11px] font-bold tracking-wider mt-2 text-indigo-300">Basira LMS</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 w-full flex flex-col items-center space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`w-full py-4 px-2 flex flex-col items-center justify-center transition-colors relative group ${
                isActive
                  ? 'bg-indigo-600/25 text-white border-l-4 border-indigo-400'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon className="w-6 h-6 mb-1 group-hover:scale-110 transition-transform" />
              <span className="text-[11px] font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
