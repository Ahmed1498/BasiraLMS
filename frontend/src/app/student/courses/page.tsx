'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { apiFetch } from '@/lib/api'
import { BookOpen, Search, Loader2 } from 'lucide-react'

type CourseSummary = {
  id: string
  title: string
  description: string
  category_id: string
}

export default function CoursesCatalogPage() {
  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    async function loadCourses() {
      try {
        const data = await apiFetch<{ courses: CourseSummary[] }>('/courses')
        setCourses(data.courses || [])
      } catch {
        // Fallback demo courses
        setCourses([
          { id: '1', title: 'Python Programming Masterclass', description: 'Master Python from scratch with hands-on projects and quizzes.', category_id: 'programming' },
          { id: '2', title: 'Full-Stack Web Development with Next.js', description: 'Build modern full-stack web applications.', category_id: 'web-development' },
        ])
      } finally {
        setLoading(false)
      }
    }
    loadCourses()
  }, [])

  const filteredCourses = courses.filter(c => c.title.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <CanvasSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900">Courses Catalog</h1>
          <div className="relative w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search courses..."
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </header>

        <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-6">
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-indigo-600 animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredCourses.map((course) => (
                <div key={course.id} className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col justify-between">
                  <div>
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
                      <BookOpen className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-lg text-slate-900 mb-2">{course.title}</h3>
                    <p className="text-xs text-slate-500 line-clamp-3">{course.description}</p>
                  </div>
                  <div className="mt-6 pt-4 border-t border-slate-100 flex justify-between items-center">
                    <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full uppercase font-semibold">{course.category_id}</span>
                    <Link
                      href={`/student/courses/${course.id}`}
                      className="text-sm font-semibold text-indigo-600 hover:text-indigo-700"
                    >
                      View Course &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      <AIAssistantWidget userRole="student" />
    </div>
  )
}
