'use client'

import { useEffect, useState, Suspense } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import AIAssistantWidget from '@/components/ai-assistant/AIAssistantWidget'
import { BookOpen, ArrowLeft, Loader2, PlayCircle, FileText, CheckCircle, HelpCircle } from 'lucide-react'

type CourseLesson = {
  id: string
  title: string
  content_type: 'text' | 'video' | 'file'
  content_body: string
  video_url?: string
}

type CourseModule = {
  id: string
  title: string
  lessons: CourseLesson[]
}

type CourseData = {
  id: string
  title: string
  description: string
  category_id: string
  modules: CourseModule[]
}

function CourseDetailContent() {
  const params = useParams()
  const courseId = params?.courseId as string

  const [course, setCourse] = useState<CourseData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedLesson, setSelectedLesson] = useState<CourseLesson | null>(null)
  const [completedLessons, setCompletedLessons] = useState<Record<string, boolean>>({})

  useEffect(() => {
    async function fetchCourse() {
      if (!courseId) return
      try {
        const data = await apiFetch<CourseData>(`/courses/${courseId}`)
        setCourse(data)
        if (data.modules && data.modules.length > 0 && data.modules[0].lessons?.length > 0) {
          setSelectedLesson(data.modules[0].lessons[0])
        }
      } catch {
        // Fallback mock course data for preview
        const mockCourse: CourseData = {
          id: courseId,
          title: 'Python Programming Masterclass: From Zero to Hero',
          description: 'A comprehensive beginner-friendly course covering Python programming fundamentals, algorithms, and data structures with embedded video lectures and quizzes.',
          category_id: 'programming',
          modules: [
            {
              id: 'm1',
              title: 'Module 1: Python Fundamentals & Syntax',
              lessons: [
                {
                  id: 'l1',
                  title: '1.1 Introduction to Variables & Data Types',
                  content_type: 'text',
                  content_body: 'Welcome to Python Programming!\nIn this foundational lesson, we explore how data is stored, manipulated, and represented in computer memory.\n\n• Slide 1: What is Computer Science?\n• Slide 2: Variables and Data Types\n• Slide 3: Control Flow (If/Else Statements)',
                },
                {
                  id: 'l2',
                  title: '1.2 Video Lecture: Python Syntax & Operators',
                  content_type: 'video',
                  video_url: 'https://www.youtube.com/embed/_uQrJ0TkZlc',
                  content_body: 'Watch this comprehensive video lecture explaining operators, precedence, and basic input/output operations in Python.',
                },
              ],
            },
            {
              id: 'm2',
              title: 'Module 2: Control Flow & Functions',
              lessons: [
                {
                  id: 'l3',
                  title: '2.1 Conditional Statements (if/elif/else)',
                  content_type: 'text',
                  content_body: 'Conditional statements allow your program to execute different blocks of code based on whether a boolean expression evaluates to True or False.',
                },
              ],
            },
          ],
        }
        setCourse(mockCourse)
        setSelectedLesson(mockCourse.modules[0].lessons[0])
      } finally {
        setLoading(false)
      }
    }
    fetchCourse()
  }, [courseId])

  const toggleComplete = (lessonId: string) => {
    setCompletedLessons(prev => ({
      ...prev,
      [lessonId]: !prev[lessonId]
    }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    )
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <h2 className="text-xl font-bold text-slate-900 mb-2">Course Not Found</h2>
        <p className="text-slate-600 mb-6">The requested course does not exist.</p>
        <Link
          href="/student/dashboard"
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Canvas Global Sidebar */}
      <CanvasSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 h-16 px-8 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <div className="flex items-center gap-3">
            <Link href="/student/dashboard" className="text-slate-500 hover:text-slate-700">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <BookOpen className="w-6 h-6 text-indigo-600" />
            <span className="text-lg font-bold text-slate-900">{course.title}</span>
          </div>
        </header>

        {/* Main Content Layout */}
        <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar Curriculum */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <h3 className="font-bold text-slate-900 mb-3 text-sm uppercase tracking-wider">Course Curriculum</h3>
              <div className="space-y-4">
                {course.modules?.map((mod) => (
                  <div key={mod.id} className="space-y-2">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase">{mod.title}</h4>
                    <div className="space-y-1">
                      {mod.lessons?.map((les) => {
                        const isDone = completedLessons[les.id]
                        return (
                          <button
                            key={les.id}
                            onClick={() => setSelectedLesson(les)}
                            className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between transition-colors ${
                              selectedLesson?.id === les.id
                                ? 'bg-indigo-50 text-indigo-700 border border-indigo-100'
                                : 'text-slate-700 hover:bg-slate-50'
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate">
                              {les.content_type === 'video' ? (
                                <PlayCircle className="w-4 h-4 text-indigo-600 shrink-0" />
                              ) : (
                                <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                              )}
                              <span className="truncate">{les.title}</span>
                            </div>
                            {isDone && <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0" />}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Lesson Viewer Main Area */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
              {selectedLesson ? (
                <>
                  <div className="border-b border-slate-100 pb-4 flex justify-between items-center">
                    <div>
                      <h1 className="text-2xl font-bold text-slate-900">{selectedLesson.title}</h1>
                      <p className="text-xs text-indigo-600 font-medium mt-1 uppercase">
                        {selectedLesson.content_type === 'video' ? 'Video Lecture' : 'Lesson Material & Slides'}
                      </p>
                    </div>
                    {/* Mark as Complete Button */}
                    <button
                      onClick={() => toggleComplete(selectedLesson.id)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                        completedLessons[selectedLesson.id]
                          ? 'bg-emerald-600 text-white shadow-sm'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200'
                      }`}
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span>{completedLessons[selectedLesson.id] ? 'Completed' : 'Mark as Complete'}</span>
                    </button>
                  </div>

                  {selectedLesson.content_type === 'video' && selectedLesson.video_url ? (
                    <div className="aspect-video w-full rounded-xl overflow-hidden bg-slate-900 shadow-md">
                      <iframe
                        src={selectedLesson.video_url}
                        title={selectedLesson.title}
                        className="w-full h-full"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      ></iframe>
                    </div>
                  ) : null}

                  <div className="prose max-w-none text-slate-700 whitespace-pre-line leading-relaxed bg-slate-50 p-6 rounded-xl border border-slate-200">
                    {selectedLesson.content_body}
                  </div>

                  {/* Quick Quiz Box */}
                  <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-6 space-y-4">
                    <div className="flex items-center gap-2 text-indigo-900 font-semibold">
                      <HelpCircle className="w-5 h-5 text-indigo-600" />
                      <span>Quick Knowledge Check</span>
                    </div>
                    <p className="text-sm text-slate-700">Which keyword is used to define a function in Python?</p>
                    <div className="grid grid-cols-2 gap-3">
                      {['func', 'def', 'function', 'define'].map((opt) => (
                        <button
                          key={opt}
                          onClick={() => alert(opt === 'def' ? 'Correct!' : 'Incorrect, try again.')}
                          className="bg-white hover:bg-indigo-100/50 border border-indigo-200 text-slate-800 text-sm font-medium py-2 px-4 rounded-lg transition-colors text-center shadow-sm"
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-slate-500 text-center py-12">Select a lesson from the curriculum to begin learning.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI Assistant Widget */}
      <AIAssistantWidget
        userRole="student"
        currentPageContext={{
          courseTitle: course.title,
          courseId: course.id,
          lessonId: selectedLesson?.id,
          lessonTitle: selectedLesson?.title,
          contentBody: selectedLesson?.content_body,
          videoUrl: selectedLesson?.video_url,
        }}
      />
    </div>
  )
}

export default function CourseDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      }
    >
      <CourseDetailContent />
    </Suspense>
  )
}
