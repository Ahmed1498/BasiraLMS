'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { apiFetch, setAccessToken } from '@/lib/api'
import CanvasSidebar from '@/components/shared/CanvasSidebar'
import { BookOpen, FileText, Loader2, LogOut, Plus, Users, X } from 'lucide-react'

type Course = {
  id: string
  title: string
  description: string | null
  student_count: number
  pending_submissions: number
}

type Module = { id: string; title: string }
type Profile = { full_name: string; role: 'student' | 'teacher' | 'admin' }
type Submission = {
  id: string
  assignment_title: string
  student_name: string
  student_email: string
  submitted_at: string | null
  file_url: string | null
  submission_text: string | null
  status: string
  grade: number | null
  feedback: string | null
  total_points: number
}
type CourseAction = 'assignment' | 'module' | 'lesson' | 'quiz' | 'submissions'

export default function TeacherDashboard() {
  const router = useRouter()
  const [courses, setCourses] = useState<Course[]>([])
  const [teacherName, setTeacherName] = useState('Teacher')
  const [loading, setLoading] = useState(true)
  const [signingOut, setSigningOut] = useState(false)
  const [savingCourse, setSavingCourse] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [courseTitle, setCourseTitle] = useState('')
  const [courseDescription, setCourseDescription] = useState('')
  const [activeCourse, setActiveCourse] = useState<Course | null>(null)
  const [activeAction, setActiveAction] = useState<CourseAction | null>(null)
  const [modules, setModules] = useState<Module[]>([])
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [actionError, setActionError] = useState<string | null>(null)
  const [savingAction, setSavingAction] = useState(false)

  const loadDashboard = useCallback(async () => {
    try {
      const [courseData, profile] = await Promise.all([
        apiFetch<{ courses: Course[] }>('/courses'),
        apiFetch<Profile>('/users/me'),
      ])
      if (profile.role !== 'teacher') {
        router.replace(`/${profile.role}/dashboard`)
        return
      }
      setCourses(courseData.courses)
      setTeacherName(profile.full_name || 'Teacher')
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load the teacher dashboard.')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    void Promise.resolve().then(() => loadDashboard())
  }, [loadDashboard])

  const handleSignOut = async () => {
    setSigningOut(true)
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
      setAccessToken(null)
      router.replace('/login')
    } catch (signOutError) {
      setError(signOutError instanceof Error ? signOutError.message : 'Could not sign out.')
      setSigningOut(false)
    }
  }

  const handleCreateCourse = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSavingCourse(true)
    setError(null)
    try {
      await apiFetch('/courses', {
        method: 'POST',
        body: JSON.stringify({ title: courseTitle.trim(), description: courseDescription.trim(), category_id: 'general' }),
      })
      setCourseTitle('')
      setCourseDescription('')
      await loadDashboard()
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Could not create the course.')
    } finally {
      setSavingCourse(false)
    }
  }

  const openAction = async (course: Course, action: CourseAction) => {
    setActiveCourse(course)
    setActiveAction(action)
    setActionError(null)
    setModules([])
    setSubmissions([])
    if (action === 'lesson') {
      try {
        const detail = await apiFetch<{ modules: Module[] }>(`/courses/${course.id}`)
        setModules(detail.modules)
      } catch (loadError) {
        setActionError(loadError instanceof Error ? loadError.message : 'Could not load course modules.')
      }
    }
    if (action === 'submissions') {
      try {
        const result = await apiFetch<{ submissions: Submission[] }>(`/courses/${course.id}/submissions`)
        setSubmissions(result.submissions)
      } catch (loadError) {
        setActionError(loadError instanceof Error ? loadError.message : 'Could not load submissions.')
      }
    }
  }

  const handleCourseAction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!activeCourse || !activeAction) return
    setSavingAction(true)
    setActionError(null)
    const values = new FormData(event.currentTarget)
    try {
      if (activeAction === 'assignment') {
        const dueDate = String(values.get('due_date') || '')
        await apiFetch(`/courses/${activeCourse.id}/assignments`, {
          method: 'POST',
          body: JSON.stringify({
            title: values.get('title'),
            description: values.get('description'),
            total_points: Number(values.get('total_points')),
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
          }),
        })
      } else if (activeAction === 'module') {
        await apiFetch(`/courses/${activeCourse.id}/modules`, {
          method: 'POST',
          body: JSON.stringify({ title: values.get('title'), order_index: modules.length }),
        })
      } else if (activeAction === 'lesson') {
        await apiFetch(`/courses/modules/${String(values.get('module_id'))}/lessons`, {
          method: 'POST',
          body: JSON.stringify({
            title: values.get('title'),
            content_type: values.get('content_type'),
            content_body: values.get('content_body'),
            video_url: values.get('video_url') || null,
            order_index: 0,
          }),
        })
      } else if (activeAction === 'quiz') {
        const options = String(values.get('options')).split('\n').map((option) => option.trim()).filter(Boolean)
        const dueDate = String(values.get('due_date') || '')
        await apiFetch(`/courses/${activeCourse.id}/quizzes`, {
          method: 'POST',
          body: JSON.stringify({
            title: values.get('title'),
            description: values.get('description'),
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
            questions: [{
              question_text: values.get('question_text'),
              options,
              correct_answer: values.get('correct_answer'),
            }],
          }),
        })
      }
      setActiveAction(null)
      setActiveCourse(null)
      await loadDashboard()
    } catch (saveError) {
      setActionError(saveError instanceof Error ? saveError.message : 'Could not save this change.')
    } finally {
      setSavingAction(false)
    }
  }

  const handleGradeSubmission = async (event: FormEvent<HTMLFormElement>, submission: Submission) => {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const grade = Number(values.get('grade'))
    const feedback = String(values.get('feedback') || '')
    try {
      await apiFetch(`/submissions/${submission.id}/grade`, {
        method: 'POST',
        body: JSON.stringify({ grade, feedback }),
      })
      setSubmissions((current) => current.map((item) => item.id === submission.id ? { ...item, grade, feedback, status: 'graded' } : item))
      await loadDashboard()
    } catch (gradeError) {
      setActionError(gradeError instanceof Error ? gradeError.message : 'Could not save this grade.')
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
  }

  const actionTitle: Record<CourseAction, string> = {
    assignment: 'Create assignment',
    module: 'Add course module',
    lesson: 'Add lesson',
    quiz: 'Create quiz',
    submissions: 'Student submissions',
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <CanvasSidebar />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3"><BookOpen className="h-8 w-8 text-indigo-600" /><span className="text-xl font-bold text-slate-900">Basira — Teacher workspace</span></Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm font-medium text-slate-600 sm:inline">{teacherName}</span>
            <button onClick={handleSignOut} disabled={signingOut} aria-label="Sign out" className="text-slate-500 hover:text-slate-800 disabled:opacity-50">
              {signingOut ? <Loader2 className="h-5 w-5 animate-spin" /> : <LogOut className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-8 px-4 py-8 sm:px-6 lg:px-8">
        {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <section className="flex flex-col items-start justify-between gap-4 rounded-2xl bg-slate-900 p-6 text-white shadow-sm sm:flex-row sm:items-center sm:p-8">
          <div>
            <p className="text-sm font-semibold text-indigo-300">Teaching dashboard</p>
            <h1 className="mt-1 text-2xl font-bold sm:text-3xl">Manage your courses</h1>
            <p className="mt-2 text-slate-300">Create course content, publish assignments and quizzes, and review student work.</p>
          </div>
          <span className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm">{courses.length} courses</span>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">Create a course</h2>
          <form onSubmit={handleCreateCourse} className="mt-4 grid gap-3 md:grid-cols-[1fr_2fr_auto]">
            <input required minLength={2} maxLength={200} value={courseTitle} onChange={(event) => setCourseTitle(event.target.value)} aria-label="Course title" placeholder="Course title" className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
            <input maxLength={10000} value={courseDescription} onChange={(event) => setCourseDescription(event.target.value)} aria-label="Course description" placeholder="Short course description" className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
            <button type="submit" disabled={savingCourse} className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {savingCourse ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Create course
            </button>
          </form>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between">
            <div><p className="text-xs font-bold uppercase tracking-widest text-indigo-600">Your teaching</p><h2 className="mt-1 text-xl font-bold text-slate-900">Assigned courses</h2></div>
          </div>
          {courses.length ? (
            <div className="grid gap-6 lg:grid-cols-2">
              {courses.map((course) => (
                <article key={course.id} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900">{course.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">{course.description || 'No description provided.'}</p>
                  <div className="mt-4 flex flex-wrap gap-5 text-sm text-slate-600">
                    <span className="inline-flex items-center gap-2"><Users className="h-4 w-4 text-indigo-600" />{course.student_count} enrolled</span>
                    <span className="inline-flex items-center gap-2"><FileText className="h-4 w-4 text-amber-600" />{course.pending_submissions} to grade</span>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4 sm:grid-cols-3">
                    <button onClick={() => void openAction(course, 'module')} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200">Add module</button>
                    <button onClick={() => void openAction(course, 'lesson')} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200">Add lesson</button>
                    <button onClick={() => void openAction(course, 'assignment')} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200">Add assignment</button>
                    <button onClick={() => void openAction(course, 'quiz')} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200">Create quiz</button>
                    <button onClick={() => void openAction(course, 'submissions')} className="col-span-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 sm:col-span-2">Review submissions</button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">Create your first course to start adding lessons and assignments.</div>
          )}
        </section>
      </main>

      {activeCourse && activeAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <section aria-labelledby="course-action-title" aria-modal="true" role="dialog" className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-start justify-between border-b border-slate-100 pb-4">
              <div><p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">{activeCourse.title}</p><h2 id="course-action-title" className="mt-1 text-lg font-bold text-slate-900">{actionTitle[activeAction]}</h2></div>
              <button onClick={() => { setActiveCourse(null); setActiveAction(null) }} aria-label="Close dialog" className="text-slate-400 hover:text-slate-700"><X className="h-5 w-5" /></button>
            </div>
            {actionError && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{actionError}</p>}
            {activeAction === 'submissions' ? (
              submissions.length ? (
                <div className="space-y-4">
                  {submissions.map((submission) => (
                    <article key={submission.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div><h3 className="font-semibold text-slate-900">{submission.assignment_title}</h3><p className="mt-1 text-xs text-slate-500">{submission.student_name} · {submission.student_email}</p></div>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${submission.status === 'graded' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{submission.status}</span>
                      </div>
                      {submission.file_url && <a href={submission.file_url} target="_blank" rel="noreferrer" className="mt-3 block break-all text-sm text-indigo-600 underline">Open submission link</a>}
                      {submission.submission_text && <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{submission.submission_text}</pre>}
                      {submission.status !== 'graded' && (
                        <form onSubmit={(event) => void handleGradeSubmission(event, submission)} className="mt-4 grid gap-2 sm:grid-cols-[120px_1fr_auto]">
                          <label className="sr-only" htmlFor={`grade-${submission.id}`}>Grade</label>
                          <input id={`grade-${submission.id}`} name="grade" type="number" min="0" max={submission.total_points} step="0.5" required placeholder={`0-${submission.total_points}`} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                          <input name="feedback" maxLength={10000} placeholder="Feedback for the student" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                          <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Save grade</button>
                        </form>
                      )}
                      {submission.status === 'graded' && <p className="mt-3 text-sm text-slate-700">Grade: {submission.grade}/{submission.total_points}{submission.feedback && ` — ${submission.feedback}`}</p>}
                    </article>
                  ))}
                </div>
              ) : <p className="rounded-lg bg-slate-50 p-5 text-sm text-slate-500">No submissions have been received for this course.</p>
            ) : (
              <form onSubmit={handleCourseAction} className="space-y-4">
                {(activeAction === 'assignment' || activeAction === 'module' || activeAction === 'lesson' || activeAction === 'quiz') && (
                  <div>
                    <label htmlFor="title" className="mb-1 block text-sm font-medium text-slate-700">{activeAction === 'assignment' ? 'Assignment title' : activeAction === 'module' ? 'Module title' : activeAction === 'quiz' ? 'Quiz title' : 'Lesson title'}</label>
                    <input id="title" name="title" required minLength={2} maxLength={200} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  </div>
                )}
                {(activeAction === 'assignment' || activeAction === 'quiz') && (
                  <div><label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-700">Description</label><textarea id="description" name="description" rows={2} maxLength={10000} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                )}
                {activeAction === 'assignment' && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div><label htmlFor="due-date" className="mb-1 block text-sm font-medium text-slate-700">Due date</label><input id="due-date" name="due_date" type="datetime-local" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                    <div><label htmlFor="total-points" className="mb-1 block text-sm font-medium text-slate-700">Points</label><input id="total-points" name="total_points" type="number" min="1" max="10000" defaultValue="100" required className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                  </div>
                )}
                {activeAction === 'lesson' && (
                  <>
                    <div><label htmlFor="module-id" className="mb-1 block text-sm font-medium text-slate-700">Module</label><select id="module-id" name="module_id" required disabled={!modules.length} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">{modules.length ? modules.map((module) => <option key={module.id} value={module.id}>{module.title}</option>) : <option value="">Create a module first</option>}</select></div>
                    <div><label htmlFor="content-type" className="mb-1 block text-sm font-medium text-slate-700">Content type</label><select id="content-type" name="content_type" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="text">Text</option><option value="video">Video</option><option value="file">File link</option></select></div>
                    <div><label htmlFor="content-body" className="mb-1 block text-sm font-medium text-slate-700">Lesson content</label><textarea id="content-body" name="content_body" rows={5} maxLength={50000} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                    <div><label htmlFor="video-url" className="mb-1 block text-sm font-medium text-slate-700">Video URL (optional)</label><input id="video-url" name="video_url" type="url" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                  </>
                )}
                {activeAction === 'quiz' && (
                  <>
                    <div><label htmlFor="quiz-due-date" className="mb-1 block text-sm font-medium text-slate-700">Due date (optional)</label><input id="quiz-due-date" name="due_date" type="datetime-local" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                    <div><label htmlFor="question-text" className="mb-1 block text-sm font-medium text-slate-700">Question</label><textarea id="question-text" name="question_text" required minLength={2} maxLength={5000} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                    <div><label htmlFor="options" className="mb-1 block text-sm font-medium text-slate-700">Answer choices (one per line)</label><textarea id="options" name="options" required rows={4} placeholder={'Option 1\\nOption 2\\nOption 3'} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                    <div><label htmlFor="correct-answer" className="mb-1 block text-sm font-medium text-slate-700">Correct answer (exactly as listed above)</label><input id="correct-answer" name="correct_answer" required className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                  </>
                )}
                {activeAction === 'quiz' && <input type="hidden" name="time_limit_minutes" value="30" />}
                <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                  <button type="button" onClick={() => { setActiveCourse(null); setActiveAction(null) }} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Cancel</button>
                  <button type="submit" disabled={savingAction || (activeAction === 'lesson' && !modules.length)} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                    {savingAction && <Loader2 className="h-4 w-4 animate-spin" />}Save changes
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
      </div>
    </div>
  )
}
